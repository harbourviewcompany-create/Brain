"""Ingest service — fetch due sources and enqueue sensory inbox."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4
from ..events import BrainEvent
from .http_json import HttpJsonConnector
from .protocol import (
    AccessDisposition, ConnectorKind, ConnectorSource, FetchResult, FetchStatus,
    InboxEnqueuer, RawObservationItem, SourceConnector, utcnow,
)
from .revenue_adapter import revenue_signal_from_observation
from .rss import RssConnector
from .store import InMemoryConnectorRegistry

@dataclass(slots=True)
class IngestItemResult:
    source_key: str
    item_id: str
    content_hash: str
    enqueued: bool
    deduped: bool
    inbox_id: str | None = None
    revenue_action_id: str | None = None

@dataclass(slots=True)
class IngestSourceResult:
    source_key: str
    status: str
    fetched: int = 0
    enqueued: int = 0
    deduped: int = 0
    error: str | None = None
    duration_ms: float = 0.0
    http_status: int | None = None
    items: list[IngestItemResult] = field(default_factory=list)

@dataclass(slots=True)
class IngestBatchResult:
    started_at: datetime
    finished_at: datetime
    sources_due: int
    sources_fetched: int
    observations_enqueued: int
    observations_deduped: int
    failures: int
    results: list[IngestSourceResult] = field(default_factory=list)
    def as_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "sources_due": self.sources_due,
            "sources_fetched": self.sources_fetched,
            "observations_enqueued": self.observations_enqueued,
            "observations_deduped": self.observations_deduped,
            "failures": self.failures,
            "results": [
                {"source_key": r.source_key, "status": r.status, "fetched": r.fetched,
                 "enqueued": r.enqueued, "deduped": r.deduped, "error": r.error,
                 "duration_ms": r.duration_ms, "http_status": r.http_status}
                for r in self.results
            ],
        }

class IngestService:
    def __init__(self, registry: InMemoryConnectorRegistry | None = None,
                 inbox: InboxEnqueuer | None = None, event_store: Any | None = None,
                 connectors: list[SourceConnector] | None = None, *,
                 max_sources_per_tick: int = 10, max_enqueue_per_source: int = 25,
                 default_source_reliability: float = 0.65,
                 revenue: Any | None = None,
                 entity_extractor: Any | None = None,
                 max_extractions_per_batch: int = 20) -> None:
        self.registry = registry or InMemoryConnectorRegistry()
        self.inbox = inbox
        self.event_store = event_store
        self.connectors: list[SourceConnector] = connectors or [RssConnector(), HttpJsonConnector()]
        self.max_sources_per_tick = max(1, max_sources_per_tick)
        self.max_enqueue_per_source = max(1, max_enqueue_per_source)
        self.default_source_reliability = default_source_reliability
        # Optional RevenueExecutionSpine. When set, every ingested item is
        # also run through the revenue adapter; a queued action is always
        # created in APPROVAL_REQUIRED state — ingestion can propose a
        # candidate revenue action, it can never approve or execute one.
        self.revenue = revenue
        # Optional Reasoner (see brain/connectors/entity_extractor.py). Off
        # by default — nothing spends an API call unless this is passed in
        # explicitly. When set, a classified-but-non-actionable candidate
        # gets one extraction attempt before being logged as scored-only,
        # bounded by max_extractions_per_batch per ingest_due_sources call.
        self.entity_extractor = entity_extractor
        self.max_extractions_per_batch = max(0, max_extractions_per_batch)
        self._extractions_this_batch = 0
        self._runs: list[IngestBatchResult] = []

    def register_source(self, source: ConnectorSource) -> ConnectorSource:
        if source.access == AccessDisposition.PROHIBITED:
            source.enabled = False
        return self.registry.upsert(source)

    def register_rss(self, *, source_key: str, url: str, name: str = "",
                     refresh_seconds: int = 300, access: AccessDisposition = AccessDisposition.ALLOWED,
                     max_items: int = 25) -> ConnectorSource:
        return self.register_source(ConnectorSource(
            source_key=source_key, url=url, kind=ConnectorKind.RSS, name=name or source_key,
            refresh_seconds=refresh_seconds, access=access, max_items_per_fetch=max_items))

    def register_http_json(self, *, source_key: str, url: str, name: str = "",
                           refresh_seconds: int = 300, items_path: str = "",
                           title_field: str = "title", body_field: str = "body",
                           url_field: str = "url", id_field: str = "id",
                           access: AccessDisposition = AccessDisposition.ALLOWED,
                           headers: dict[str, str] | None = None) -> ConnectorSource:
        return self.register_source(ConnectorSource(
            source_key=source_key, url=url, kind=ConnectorKind.HTTP_JSON, name=name or source_key,
            refresh_seconds=refresh_seconds, access=access, json_items_path=items_path,
            json_title_field=title_field, json_body_field=body_field, json_url_field=url_field,
            json_id_field=id_field, headers=dict(headers or {})))

    def _connector_for(self, source: ConnectorSource) -> SourceConnector | None:
        for c in self.connectors:
            if c.supports(source):
                return c
        return None

    def ingest_due_sources(self, *, now: datetime | None = None) -> IngestBatchResult:
        started = now or utcnow()
        self._extractions_this_batch = 0
        due = self.registry.due_sources(started)[: self.max_sources_per_tick]
        batch = IngestBatchResult(started_at=started, finished_at=started, sources_due=len(due),
            sources_fetched=0, observations_enqueued=0, observations_deduped=0, failures=0)
        for source in due:
            result = self._ingest_one(source)
            batch.results.append(result)
            batch.sources_fetched += 1
            batch.observations_enqueued += result.enqueued
            batch.observations_deduped += result.deduped
            if result.status == FetchStatus.FAILED.value:
                batch.failures += 1
        batch.finished_at = utcnow()
        self._runs.append(batch)
        self._emit_batch_event(batch)
        return batch

    def ingest_source(self, source_key: str) -> IngestSourceResult:
        source = self.registry.get(source_key)
        if source is None:
            return IngestSourceResult(source_key=source_key, status=FetchStatus.SKIPPED.value, error="source_not_found")
        return self._ingest_one(source)

    def _ingest_one(self, source: ConnectorSource) -> IngestSourceResult:
        if source.access in {AccessDisposition.PROHIBITED, AccessDisposition.MANUAL_ONLY}:
            self.registry.mark_fetch(source.source_key, success=True)
            return IngestSourceResult(source_key=source.source_key, status=FetchStatus.SKIPPED.value,
                error=f"access_{source.access.value}")
        connector = self._connector_for(source)
        if connector is None:
            self.registry.mark_fetch(source.source_key, success=False)
            return IngestSourceResult(source_key=source.source_key, status=FetchStatus.FAILED.value,
                error=f"no_connector_for_kind:{source.kind}")
        fetch: FetchResult = connector.fetch(source)
        out = IngestSourceResult(source_key=source.source_key, status=fetch.status.value,
            fetched=len(fetch.items), error=fetch.error, duration_ms=fetch.duration_ms, http_status=fetch.http_status)
        if not fetch.ok:
            self.registry.mark_fetch(source.source_key, success=False)
            self._emit_fetch_event(source, fetch, enqueued=0)
            return out
        enqueued = 0
        for item in fetch.items[: self.max_enqueue_per_source]:
            item_result = self._enqueue_item(source, item)
            out.items.append(item_result)
            if item_result.deduped:
                out.deduped += 1
            elif item_result.enqueued:
                enqueued += 1
        out.enqueued = enqueued
        self.registry.mark_fetch(source.source_key, success=True)
        self._emit_fetch_event(source, fetch, enqueued=enqueued)
        return out

    def _enqueue_item(self, source: ConnectorSource, item: RawObservationItem) -> IngestItemResult:
        is_new = self.registry.remember_hash(item.content_hash)
        if not is_new:
            return IngestItemResult(source_key=source.source_key, item_id=item.item_id,
                content_hash=item.content_hash, enqueued=False, deduped=True)
        if self.inbox is None:
            return IngestItemResult(source_key=source.source_key, item_id=item.item_id,
                content_hash=item.content_hash, enqueued=False, deduped=False)
        payload = {
            "source_reliability": self.default_source_reliability, "supports": True,
            "belief_statement": item.claim, "belief_confidence": min(0.7, max(0.2, item.confidence)),
            "novelty": 0.55, "urgency": 0.25, "commercial_upside": 0.0, "contradiction_value": 0.0,
            "uncertainty_reduction": 0.5, "noise_probability": 0.15, "operator_burden": 0.0,
            "source_type": "external_observation",
            "metadata": {
                "source_type": "external_observation", "connector": source.kind.value,
                "item_id": item.item_id, "content_hash": item.content_hash, "source_url": item.source_url,
                "title": item.title, "observed_at": item.observed_at.isoformat(),
                "signal_hints": list(item.signal_hints), "entities": list(item.entities),
                "source_name": source.name,
                **{k: v for k, v in item.metadata.items() if isinstance(v, (str, int, float, bool))},
            },
        }
        try:
            enqueued = self.inbox.enqueue(source_key=source.source_key, content=item.content, claim=item.claim, payload=payload)
            revenue_action_id = self._maybe_queue_revenue_action(source, item)
            return IngestItemResult(source_key=source.source_key, item_id=item.item_id,
                content_hash=item.content_hash, enqueued=True, deduped=False,
                inbox_id=str(getattr(enqueued, "id", enqueued)), revenue_action_id=revenue_action_id)
        except Exception:
            return IngestItemResult(source_key=source.source_key, item_id=item.item_id,
                content_hash=item.content_hash, enqueued=False, deduped=False)

    def _maybe_queue_revenue_action(self, source: ConnectorSource, item: RawObservationItem) -> str | None:
        """Best-effort: classify the item and queue a draft revenue action.

        Never raises — a classification/queueing failure must not break
        ingestion of the underlying observation. Always lands the action
        in APPROVAL_REQUIRED state; nothing here can approve or execute.

        When a lane is inferred but the signal fails NoFantasyFilter (the
        common case for unenriched automated feeds — no named buyer,
        seller, or contact channel), and self.entity_extractor is set and
        this batch's extraction budget isn't exhausted, one extraction
        attempt is made and the signal is re-scored with any fields it
        found. Whether or not that changes the outcome, a
        `revenue.signal_scored` event is emitted with the final rejection
        reasons so the candidate is visible to an operator instead of
        silently disappearing.
        """
        if self.revenue is None:
            return None
        try:
            signal = revenue_signal_from_observation(item, source_id=source.source_key)
            if signal is None:
                return None
            scored = self.revenue.money.score_signal(signal)
            if not scored.actionable:
                signal, scored = self._maybe_extract_and_rescore(source, item, signal, scored)
            if not scored.actionable:
                self._emit_scored_signal_event(source, item, scored)
                return None
            offer = self.revenue.money.package_offer(signal, scored)
            action = self.revenue.queue_action_from_scored(signal, scored, offer)
            return str(action.id)
        except Exception:
            return None

    def _maybe_extract_and_rescore(
        self, source: ConnectorSource, item: RawObservationItem, signal: Any, scored: Any,
    ) -> tuple[Any, Any]:
        if self.entity_extractor is None:
            return signal, scored
        if self._extractions_this_batch >= self.max_extractions_per_batch:
            return signal, scored
        self._extractions_this_batch += 1
        try:
            from .entity_extractor import extract_revenue_entities

            enrichment = extract_revenue_entities(item, reasoner=self.entity_extractor)
        except Exception:
            return signal, scored
        confidences = enrichment.pop("extraction_confidence", {})
        if not enrichment:
            return signal, scored
        enriched_item = RawObservationItem(
            title=item.title, content=item.content, claim=item.claim,
            source_url=item.source_url, item_id=item.item_id, content_hash=item.content_hash,
            observed_at=item.observed_at, confidence=item.confidence,
            signal_hints=list(item.signal_hints), entities=list(item.entities),
            metadata={**item.metadata, **enrichment, "extraction_confidence": confidences},
        )
        re_signal = revenue_signal_from_observation(enriched_item, source_id=source.source_key)
        if re_signal is None:
            return signal, scored
        re_scored = self.revenue.money.score_signal(re_signal)
        return re_signal, re_scored

    def _emit_scored_signal_event(self, source: ConnectorSource, item: RawObservationItem, scored: Any) -> None:
        if self.event_store is None or not hasattr(self.event_store, "append"):
            return
        try:
            self.event_store.append(BrainEvent("revenue.signal_scored", "connector", source.id, {
                "source_key": source.source_key, "item_id": item.item_id,
                "money_lane_id": scored.lane_id, "score": scored.score,
                "actionable": scored.actionable, "rejection_reasons": list(scored.rejection_reasons),
            }))
        except Exception:
            pass

    def _emit_fetch_event(self, source: ConnectorSource, fetch: FetchResult, *, enqueued: int) -> None:
        if self.event_store is None or not hasattr(self.event_store, "append"):
            return
        try:
            self.event_store.append(BrainEvent("ingest.fetch_completed", "connector", source.id, {
                "source_key": source.source_key, "kind": source.kind.value, "status": fetch.status.value,
                "url": source.url, "items": len(fetch.items), "enqueued": enqueued, "error": fetch.error,
                "http_status": fetch.http_status, "duration_ms": fetch.duration_ms, "bytes_read": fetch.bytes_read,
            }))
        except Exception:
            pass

    def _emit_batch_event(self, batch: IngestBatchResult) -> None:
        if self.event_store is None or not hasattr(self.event_store, "append"):
            return
        try:
            self.event_store.append(BrainEvent("ingest.batch_completed", "connector", uuid4(), batch.as_dict()))
        except Exception:
            pass

    def status(self) -> dict[str, Any]:
        sources = self.registry.list_sources()
        return {
            "sources": len(sources), "enabled": sum(1 for s in sources if s.enabled),
            "due": len(self.registry.due_sources()), "seen_hashes": self.registry.seen_count(),
            "batches_run": len(self._runs),
            "last_batch": self._runs[-1].as_dict() if self._runs else None,
        }
