"""Ingest service — fetch due sources and enqueue sensory inbox."""
from __future__ import annotations
import json
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
        self.revenue = revenue
        # Optional Reasoner. Off by default. The limit is scoped to one public
        # ingest operation: a scheduled batch shares one budget across its due
        # sources, while every forced ingest_source() call gets a fresh budget.
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
        # Forced/manual ingests are distinct operations and therefore receive
        # their own extraction budget instead of inheriting service lifetime state.
        self._extractions_this_batch = 0
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
        """Best-effort classification, evidence-grounded enrichment, and action queueing."""
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
                self._emit_scored_signal_event(source, item, scored, signal=signal)
                return None
            offer = self.revenue.money.package_offer(signal, scored)
            action = self.revenue.queue_action_from_scored(signal, scored, offer)
            self._attach_extraction_review_evidence(action, signal)
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
            from .entity_extractor import EXTRACTABLE_FIELDS, extract_revenue_entities

            extraction = extract_revenue_entities(item, reasoner=self.entity_extractor)
        except Exception:
            return signal, scored

        confidences = extraction.pop("extraction_confidence", {})
        provenance = extraction.pop("extraction_provenance", {})

        # Connector/source metadata is authoritative. Model extraction may fill
        # missing fields, never replace a non-empty source-provided value.
        enrichment = {
            field: value
            for field, value in extraction.items()
            if field in EXTRACTABLE_FIELDS
            and not (isinstance(item.metadata.get(field), str) and item.metadata[field].strip())
        }
        if not enrichment:
            return signal, scored

        used_provenance = {
            field: provenance[field]
            for field in enrichment
            if isinstance(provenance.get(field), dict)
        }
        used_confidences = {
            field: confidences[field]
            for field in enrichment
            if field in confidences
        }
        enriched_item = RawObservationItem(
            title=item.title, content=item.content, claim=item.claim,
            source_url=item.source_url, item_id=item.item_id, content_hash=item.content_hash,
            observed_at=item.observed_at, confidence=item.confidence,
            signal_hints=list(item.signal_hints), entities=list(item.entities),
            metadata={**item.metadata, **enrichment},
        )
        re_signal = revenue_signal_from_observation(
            enriched_item,
            source_id=source.source_key,
            extra_metadata={
                "extraction_grounded": True,
                "extraction_confidence": used_confidences,
                "extraction_provenance": used_provenance,
            },
        )
        if re_signal is None:
            return signal, scored
        re_scored = self.revenue.money.score_signal(re_signal)
        return re_signal, re_scored

    def _attach_extraction_review_evidence(self, action: Any, signal: Any) -> None:
        """Persist extraction provenance on the approval action without schema changes."""
        provenance = signal.metadata.get("extraction_provenance") if hasattr(signal, "metadata") else None
        if not isinstance(provenance, dict) or not provenance:
            return
        review_ref = "extraction_provenance:" + json.dumps(
            provenance, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        )
        if review_ref not in action.evidence_refs:
            action.evidence_refs.append(review_ref)
        store = getattr(self.revenue, "store", None)
        if store is not None:
            store.save_action(action)

    def _emit_scored_signal_event(
        self, source: ConnectorSource, item: RawObservationItem, scored: Any, *, signal: Any | None = None,
    ) -> None:
        if self.event_store is None or not hasattr(self.event_store, "append"):
            return
        try:
            payload: dict[str, Any] = {
                "source_key": source.source_key, "item_id": item.item_id,
                "money_lane_id": scored.lane_id, "score": scored.score,
                "actionable": scored.actionable, "rejection_reasons": list(scored.rejection_reasons),
            }
            if signal is not None and isinstance(getattr(signal, "metadata", None), dict):
                provenance = signal.metadata.get("extraction_provenance")
                if isinstance(provenance, dict) and provenance:
                    payload["extraction_provenance"] = provenance
            self.event_store.append(BrainEvent("revenue.signal_scored", "connector", source.id, payload))
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
