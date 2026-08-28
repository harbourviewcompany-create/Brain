"""Ingest service — fetch due sources and enqueue provenance-preserved observations."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from ..events import BrainEvent
from ..logging_config import get_logger
from .http_json import HttpJsonConnector
from .protocol import (
    AccessDisposition,
    ConnectorKind,
    ConnectorSource,
    FetchResult,
    FetchStatus,
    InboxEnqueuer,
    RawObservationItem,
    SourceConnector,
    utcnow,
)
from .revenue_adapter import revenue_signal_from_observation
from .rss import RssConnector
from .store import InMemoryConnectorRegistry, PostgresConnectorRegistry

log = get_logger("connectors.service")


def _pool_for(event_store: Any | None) -> Any | None:
    if event_store is None:
        return None
    pool = getattr(event_store, "pool", None)
    if pool is not None:
        return pool
    nested = getattr(event_store, "event_store", None)
    return getattr(nested, "pool", None) if nested is not None else None


def _default_registry(event_store: Any | None) -> Any:
    """Prefer restart-safe acquisition state without breaking pre-024 deployments.

    Migration 024 is deliberately capability-detected because current production may
    still be on the approved pre-tenant migration ceiling. In that state ingestion
    remains functional but announces that its connector schedule/dedupe is ephemeral.
    """
    pool = _pool_for(event_store)
    if pool is not None:
        durable = PostgresConnectorRegistry(pool)
        if durable.available():
            log.info("connector ingestion bound to durable PostgreSQL registry")
            return durable
        log.warning(
            "migration 024 connector runtime is unavailable; connector scheduling and "
            "raw acquisition provenance remain in-memory until the migration is applied"
        )
    return InMemoryConnectorRegistry()


@dataclass(slots=True)
class IngestItemResult:
    source_key: str
    item_id: str
    content_hash: str
    enqueued: bool
    deduped: bool
    inbox_id: str | None = None
    observation_id: str | None = None
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
    ingestion_run_id: str | None = None
    retrieved_at: datetime | None = None
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
                {
                    "source_key": r.source_key,
                    "status": r.status,
                    "fetched": r.fetched,
                    "enqueued": r.enqueued,
                    "deduped": r.deduped,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                    "http_status": r.http_status,
                    "ingestion_run_id": r.ingestion_run_id,
                    "retrieved_at": r.retrieved_at.isoformat() if r.retrieved_at else None,
                }
                for r in self.results
            ],
        }


class IngestService:
    def __init__(
        self,
        registry: Any | None = None,
        inbox: InboxEnqueuer | None = None,
        event_store: Any | None = None,
        connectors: list[SourceConnector] | None = None,
        *,
        max_sources_per_tick: int = 10,
        max_enqueue_per_source: int = 25,
        default_source_reliability: float = 0.65,
        revenue: Any | None = None,
    ) -> None:
        self.registry = registry if registry is not None else _default_registry(event_store)
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
        self._runs: list[IngestBatchResult] = []

    def register_source(self, source: ConnectorSource) -> ConnectorSource:
        if source.access in {
            AccessDisposition.PROHIBITED,
            AccessDisposition.UNKNOWN,
        }:
            source.enabled = False
        return self.registry.upsert(source)

    def register_rss(
        self,
        *,
        source_key: str,
        url: str,
        name: str = "",
        refresh_seconds: int = 300,
        access: AccessDisposition = AccessDisposition.ALLOWED,
        max_items: int = 25,
    ) -> ConnectorSource:
        return self.register_source(
            ConnectorSource(
                source_key=source_key,
                url=url,
                kind=ConnectorKind.RSS,
                name=name or source_key,
                refresh_seconds=refresh_seconds,
                access=access,
                max_items_per_fetch=max_items,
            )
        )

    def register_http_json(
        self,
        *,
        source_key: str,
        url: str,
        name: str = "",
        refresh_seconds: int = 300,
        items_path: str = "",
        title_field: str = "title",
        body_field: str = "body",
        url_field: str = "url",
        id_field: str = "id",
        access: AccessDisposition = AccessDisposition.ALLOWED,
        headers: dict[str, str] | None = None,
    ) -> ConnectorSource:
        return self.register_source(
            ConnectorSource(
                source_key=source_key,
                url=url,
                kind=ConnectorKind.HTTP_JSON,
                name=name or source_key,
                refresh_seconds=refresh_seconds,
                access=access,
                json_items_path=items_path,
                json_title_field=title_field,
                json_body_field=body_field,
                json_url_field=url_field,
                json_id_field=id_field,
                headers=dict(headers or {}),
            )
        )

    def _connector_for(self, source: ConnectorSource) -> SourceConnector | None:
        for connector in self.connectors:
            if connector.supports(source):
                return connector
        return None

    def _due_sources(self, now: datetime) -> list[ConnectorSource]:
        claimer = getattr(self.registry, "claim_due_sources", None)
        if callable(claimer):
            return list(claimer(limit=self.max_sources_per_tick, now=now))
        return list(self.registry.due_sources(now))[: self.max_sources_per_tick]

    def ingest_due_sources(self, *, now: datetime | None = None) -> IngestBatchResult:
        started = now or utcnow()
        due = self._due_sources(started)
        batch = IngestBatchResult(
            started_at=started,
            finished_at=started,
            sources_due=len(due),
            sources_fetched=0,
            observations_enqueued=0,
            observations_deduped=0,
            failures=0,
        )
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
            return IngestSourceResult(
                source_key=source_key,
                status=FetchStatus.SKIPPED.value,
                error="source_not_found",
            )
        return self._ingest_one(source)

    def _start_ingestion_run(self, source: ConnectorSource) -> UUID | None:
        starter = getattr(self.registry, "start_ingestion_run", None)
        if not callable(starter):
            return None
        return starter(source)

    def _finish_ingestion_run(self, run_id: UUID | None, result: IngestSourceResult) -> None:
        if run_id is None:
            return
        finisher = getattr(self.registry, "finish_ingestion_run", None)
        if not callable(finisher):
            return
        finisher(
            run_id,
            status=result.status,
            retrieved_at=result.retrieved_at,
            fetched_count=result.fetched,
            enqueued_count=result.enqueued,
            deduped_count=result.deduped,
            http_status=result.http_status,
            duration_ms=result.duration_ms,
            error_message=result.error,
        )

    def _ingest_one(self, source: ConnectorSource) -> IngestSourceResult:
        if source.access in {
            AccessDisposition.PROHIBITED,
            AccessDisposition.MANUAL_ONLY,
            AccessDisposition.UNKNOWN,
        }:
            self.registry.mark_fetch(source.source_key, success=True)
            return IngestSourceResult(
                source_key=source.source_key,
                status=FetchStatus.SKIPPED.value,
                error=f"access_{source.access.value}",
            )

        connector = self._connector_for(source)
        if connector is None:
            self.registry.mark_fetch(source.source_key, success=False)
            return IngestSourceResult(
                source_key=source.source_key,
                status=FetchStatus.FAILED.value,
                error=f"no_connector_for_kind:{source.kind}",
            )

        try:
            run_id = self._start_ingestion_run(source)
        except Exception as exc:
            # A durable registry that cannot open its provenance ledger must not
            # fetch and silently degrade to untracked observations.
            self.registry.mark_fetch(source.source_key, success=False)
            return IngestSourceResult(
                source_key=source.source_key,
                status=FetchStatus.FAILED.value,
                error=f"ingestion_run_start_failed:{type(exc).__name__}",
            )

        try:
            fetch: FetchResult = connector.fetch(source)
        except Exception as exc:  # connector contract guard
            result = IngestSourceResult(
                source_key=source.source_key,
                status=FetchStatus.FAILED.value,
                error=f"connector_exception:{type(exc).__name__}",
                ingestion_run_id=str(run_id) if run_id else None,
            )
            self.registry.mark_fetch(source.source_key, success=False)
            self._finish_ingestion_run(run_id, result)
            return result

        out = IngestSourceResult(
            source_key=source.source_key,
            status=fetch.status.value,
            fetched=len(fetch.items),
            error=fetch.error,
            duration_ms=fetch.duration_ms,
            http_status=fetch.http_status,
            ingestion_run_id=str(run_id) if run_id else None,
            retrieved_at=fetch.retrieved_at,
        )
        if not fetch.ok:
            self.registry.mark_fetch(source.source_key, success=False)
            self._emit_fetch_event(source, fetch, enqueued=0)
            self._finish_ingestion_run(run_id, out)
            return out

        for item in fetch.items[: self.max_enqueue_per_source]:
            item_result = self._enqueue_item(
                source,
                item,
                retrieved_at=fetch.retrieved_at,
                ingestion_run_id=run_id,
            )
            out.items.append(item_result)
            if item_result.deduped:
                out.deduped += 1
            elif item_result.enqueued:
                out.enqueued += 1

        self.registry.mark_fetch(source.source_key, success=True)
        self._emit_fetch_event(source, fetch, enqueued=out.enqueued)
        self._finish_ingestion_run(run_id, out)
        return out

    def _enqueue_item(
        self,
        source: ConnectorSource,
        item: RawObservationItem,
        *,
        retrieved_at: datetime,
        ingestion_run_id: UUID | None,
    ) -> IngestItemResult:
        try:
            receipt = self.registry.record_fetched_item(
                source,
                item,
                retrieved_at=retrieved_at,
                ingestion_run_id=ingestion_run_id,
            )
        except Exception:
            # Provenance is part of correctness. Never enqueue an item after a
            # durable raw-observation write failed, because the sensory event
            # would no longer be replayable or auditable.
            return IngestItemResult(
                source_key=source.source_key,
                item_id=item.item_id,
                content_hash=item.content_hash,
                enqueued=False,
                deduped=False,
            )

        observation_id = str(receipt.observation_id) if receipt.observation_id else None
        if not receipt.is_new:
            return IngestItemResult(
                source_key=source.source_key,
                item_id=item.item_id,
                content_hash=item.content_hash,
                enqueued=False,
                deduped=True,
                observation_id=observation_id,
            )
        if self.inbox is None:
            return IngestItemResult(
                source_key=source.source_key,
                item_id=item.item_id,
                content_hash=item.content_hash,
                enqueued=False,
                deduped=False,
                observation_id=observation_id,
            )

        payload = {
            "source_reliability": self.default_source_reliability,
            "supports": True,
            "belief_statement": item.claim,
            "belief_confidence": min(0.7, max(0.2, item.confidence)),
            "novelty": 0.55,
            "urgency": 0.25,
            "commercial_upside": 0.0,
            "contradiction_value": 0.0,
            "uncertainty_reduction": 0.5,
            "noise_probability": 0.15,
            "operator_burden": 0.0,
            "source_type": "external_observation",
            "metadata": {
                "source_type": "external_observation",
                "connector": source.kind.value,
                "item_id": item.item_id,
                "content_hash": item.content_hash,
                "source_url": item.source_url,
                "title": item.title,
                "observed_at": item.observed_at.isoformat(),
                "retrieved_at": retrieved_at.isoformat(),
                "connector_observation_id": observation_id,
                "ingestion_run_id": str(ingestion_run_id) if ingestion_run_id else None,
                "signal_hints": list(item.signal_hints),
                "entities": list(item.entities),
                "source_name": source.name,
                **{
                    k: v
                    for k, v in item.metadata.items()
                    if isinstance(v, (str, int, float, bool))
                    and k.lower()
                    not in {
                        "authorization",
                        "api_key",
                        "apikey",
                        "token",
                        "cookie",
                        "password",
                        "secret",
                    }
                },
            },
        }
        try:
            enqueued = self.inbox.enqueue(
                source_key=source.source_key,
                content=item.content,
                claim=item.claim,
                payload=payload,
            )
            inbox_id = getattr(enqueued, "id", enqueued)
            marker = getattr(self.registry, "mark_observation_enqueued", None)
            if receipt.observation_id is not None and callable(marker):
                marker(receipt.observation_id, inbox_id)
            revenue_action_id = self._maybe_queue_revenue_action(source, item)
            return IngestItemResult(
                source_key=source.source_key,
                item_id=item.item_id,
                content_hash=item.content_hash,
                enqueued=True,
                deduped=False,
                inbox_id=str(inbox_id),
                observation_id=observation_id,
                revenue_action_id=revenue_action_id,
            )
        except Exception:
            return IngestItemResult(
                source_key=source.source_key,
                item_id=item.item_id,
                content_hash=item.content_hash,
                enqueued=False,
                deduped=False,
                observation_id=observation_id,
            )

    def _maybe_queue_revenue_action(
        self, source: ConnectorSource, item: RawObservationItem
    ) -> str | None:
        """Best-effort classify and queue an approval-required revenue candidate."""
        if self.revenue is None:
            return None
        try:
            signal = revenue_signal_from_observation(item, source_id=source.source_key)
            if signal is None:
                return None
            scored = self.revenue.money.score_signal(signal)
            if not scored.actionable:
                self._emit_scored_signal_event(source, item, scored)
                return None
            offer = self.revenue.money.package_offer(signal, scored)
            action = self.revenue.queue_action_from_scored(signal, scored, offer)
            return str(action.id)
        except Exception:
            return None

    def _emit_scored_signal_event(
        self, source: ConnectorSource, item: RawObservationItem, scored: Any
    ) -> None:
        if self.event_store is None or not hasattr(self.event_store, "append"):
            return
        try:
            self.event_store.append(
                BrainEvent(
                    "revenue.signal_scored",
                    "connector",
                    source.id,
                    {
                        "source_key": source.source_key,
                        "item_id": item.item_id,
                        "money_lane_id": scored.lane_id,
                        "score": scored.score,
                        "actionable": scored.actionable,
                        "rejection_reasons": list(scored.rejection_reasons),
                    },
                )
            )
        except Exception:
            pass

    def _emit_fetch_event(
        self, source: ConnectorSource, fetch: FetchResult, *, enqueued: int
    ) -> None:
        if self.event_store is None or not hasattr(self.event_store, "append"):
            return
        try:
            self.event_store.append(
                BrainEvent(
                    "ingest.fetch_completed",
                    "connector",
                    source.id,
                    {
                        "source_key": source.source_key,
                        "kind": source.kind.value,
                        "status": fetch.status.value,
                        "url": source.url,
                        "items": len(fetch.items),
                        "enqueued": enqueued,
                        "error": fetch.error,
                        "http_status": fetch.http_status,
                        "retrieved_at": fetch.retrieved_at.isoformat(),
                        "duration_ms": fetch.duration_ms,
                        "bytes_read": fetch.bytes_read,
                    },
                )
            )
        except Exception:
            pass

    def _emit_batch_event(self, batch: IngestBatchResult) -> None:
        if self.event_store is None or not hasattr(self.event_store, "append"):
            return
        try:
            self.event_store.append(
                BrainEvent("ingest.batch_completed", "connector", uuid4(), batch.as_dict())
            )
        except Exception:
            pass

    def status(self) -> dict[str, Any]:
        sources = self.registry.list_sources()
        return {
            "sources": len(sources),
            "enabled": sum(1 for s in sources if s.enabled),
            "due": len(self.registry.due_sources()),
            "seen_hashes": self.registry.seen_count(),
            "durable_registry": isinstance(self.registry, PostgresConnectorRegistry),
            "batches_run": len(self._runs),
            "last_batch": self._runs[-1].as_dict() if self._runs else None,
        }
