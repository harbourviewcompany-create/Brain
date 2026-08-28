"""Connector registries: deterministic in-memory and restart-safe PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timedelta
from threading import RLock
from typing import Any
from uuid import UUID, uuid4

from brain.adapters.postgres import ConnectionPool, _json, dict_row

from .protocol import (
    AccessDisposition,
    ConnectorKind,
    ConnectorObservationReceipt,
    ConnectorSource,
    RawObservationItem,
    utcnow,
)


class InMemoryConnectorRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, ConnectorSource] = {}
        self._lock = RLock()
        # Source-scoped identity is intentional. Identical content independently
        # observed by two sources is corroboration, not a duplicate to erase.
        self._seen_hashes: set[tuple[str, str]] = set()

    def list_sources(self) -> list[ConnectorSource]:
        with self._lock:
            return list(self._sources.values())

    def get(self, source_key: str) -> ConnectorSource | None:
        with self._lock:
            return self._sources.get(source_key)

    def upsert(self, source: ConnectorSource) -> ConnectorSource:
        with self._lock:
            self._sources[source.source_key] = source
            return source

    def due_sources(self, now: datetime | None = None) -> list[ConnectorSource]:
        now = now or utcnow()
        with self._lock:
            due = [s for s in self._sources.values() if s.is_due(now)]
            due.sort(key=lambda s: (s.next_due_at, s.source_key))
            return due

    def claim_due_sources(
        self, *, limit: int, now: datetime | None = None
    ) -> list[ConnectorSource]:
        return self.due_sources(now)[: max(0, limit)]

    def mark_fetch(self, source_key: str, *, success: bool) -> None:
        with self._lock:
            src = self._sources.get(source_key)
            if src is None:
                return
            src.schedule_next(success=success)

    def remember_hash(self, content_hash: str, *, source_key: str = "") -> bool:
        """Compatibility helper; new code should use record_fetched_item()."""
        key = (source_key, content_hash)
        with self._lock:
            if key in self._seen_hashes:
                return False
            self._seen_hashes.add(key)
            if len(self._seen_hashes) > 50_000:
                # Bound the local fallback only. PostgreSQL mode has no arbitrary
                # truncation and is authoritative across restarts.
                self._seen_hashes = set(list(self._seen_hashes)[25_000:])
            return True

    def record_fetched_item(
        self,
        source: ConnectorSource,
        item: RawObservationItem,
        *,
        retrieved_at: datetime,
        ingestion_run_id: UUID | None = None,
    ) -> ConnectorObservationReceipt:
        del retrieved_at, ingestion_run_id
        is_new = self.remember_hash(item.content_hash, source_key=source.source_key)
        return ConnectorObservationReceipt(is_new=is_new, should_enqueue=is_new)

    def mark_observation_enqueue_failed(
        self,
        source: ConnectorSource,
        item: RawObservationItem,
        observation_id: UUID | None = None,
    ) -> None:
        """Release local dedupe state so a transient inbox failure can retry."""
        del observation_id
        with self._lock:
            self._seen_hashes.discard((source.source_key, item.content_hash))

    def seen_count(self) -> int:
        with self._lock:
            return len(self._seen_hashes)


class PostgresConnectorRegistry:
    """Restart-safe operational registry and raw acquisition ledger.

    The connector runtime is deliberately separate from the normalized MOD-017
    intelligence registry. It owns scheduling, leases, source-scoped dedupe and
    raw provenance only. It never persists connector credentials or HTTP headers.

    By default this adapter operates on system/global (`tenant_id is null`) rows.
    A tenant id can be supplied for a future tenant-scoped worker scheduler.
    """

    REQUIRED_TABLES = (
        "source_connector_runtime_state",
        "source_connector_ingestion_runs",
        "source_connector_observations",
    )

    def __init__(
        self,
        pool: ConnectionPool,
        *,
        tenant_id: UUID | None = None,
        lease_owner: str | None = None,
        lease_seconds: int = 180,
    ) -> None:
        self.pool = pool
        self.tenant_id = tenant_id
        self.lease_owner = lease_owner or f"brain-ingest-{uuid4()}"
        self.lease_seconds = max(30, int(lease_seconds))

    def available(self) -> bool:
        """Return whether migration 024's complete runtime surface exists."""
        try:
            with self.pool.connection() as conn:
                rows = conn.execute(
                    """
                    select name, to_regclass('public.' || name) is not null as present
                    from unnest(%s::text[]) as name
                    """,
                    (list(self.REQUIRED_TABLES),),
                ).fetchall()
            return len(rows) == len(self.REQUIRED_TABLES) and all(bool(row[1]) for row in rows)
        except Exception:
            return False

    def _scope_sql(self, alias: str = "") -> tuple[str, tuple[Any, ...]]:
        prefix = f"{alias}." if alias else ""
        if self.tenant_id is None:
            return f"{prefix}tenant_id is null", ()
        return f"{prefix}tenant_id = %s", (self.tenant_id,)

    @staticmethod
    def _public_config(source: ConnectorSource) -> dict[str, Any]:
        # Intentionally exclude source.headers and arbitrary source.metadata:
        # both can contain credentials. Only deterministic parser/runtime fields
        # are durable configuration.
        return {
            "json_items_path": source.json_items_path,
            "json_title_field": source.json_title_field,
            "json_body_field": source.json_body_field,
            "json_url_field": source.json_url_field,
            "json_id_field": source.json_id_field,
            "max_items_per_fetch": int(source.max_items_per_fetch),
            "timeout_seconds": float(source.timeout_seconds),
        }

    @staticmethod
    def _row_to_source(row: dict[str, Any]) -> ConnectorSource:
        cfg = dict(row.get("public_config") or {})
        return ConnectorSource(
            id=row["id"],
            source_key=row["source_key"],
            url=row["url"],
            kind=ConnectorKind(row["connector_kind"]),
            name=row["source_name"],
            access=AccessDisposition(row["access_disposition"]),
            refresh_seconds=int(row["refresh_seconds"]),
            enabled=bool(row["enabled"]),
            # Credentials are injected at runtime and are never rehydrated from DB.
            headers={},
            json_items_path=str(cfg.get("json_items_path") or ""),
            json_title_field=str(cfg.get("json_title_field") or "title"),
            json_body_field=str(cfg.get("json_body_field") or "body"),
            json_url_field=str(cfg.get("json_url_field") or "url"),
            json_id_field=str(cfg.get("json_id_field") or "id"),
            max_items_per_fetch=int(cfg.get("max_items_per_fetch") or 25),
            timeout_seconds=float(cfg.get("timeout_seconds") or 20.0),
            metadata={"durable_connector_registry": True},
            last_fetched_at=row.get("last_fetched_at"),
            last_success_at=row.get("last_success_at"),
            consecutive_failures=int(row.get("consecutive_failures") or 0),
            next_due_at=row["next_due_at"],
        )

    def list_sources(self) -> list[ConnectorSource]:
        scope, params = self._scope_sql("s")
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                select s.* from public.source_connector_runtime_state s
                where {scope}
                order by s.source_key
                """,
                params,
            )
            rows = cur.fetchall()
        return [self._row_to_source(dict(row)) for row in rows]

    def get(self, source_key: str) -> ConnectorSource | None:
        scope, params = self._scope_sql("s")
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                select s.* from public.source_connector_runtime_state s
                where {scope} and s.source_key = %s
                limit 1
                """,
                (*params, source_key),
            )
            row = cur.fetchone()
        return self._row_to_source(dict(row)) if row else None

    def upsert(self, source: ConnectorSource) -> ConnectorSource:
        config = self._public_config(source)
        values = (
            source.id,
            self.tenant_id,
            source.source_key,
            source.name or source.source_key,
            source.url,
            source.kind.value,
            source.access.value,
            max(30, int(source.refresh_seconds)),
            bool(source.enabled and source.access != AccessDisposition.PROHIBITED),
            _json(config),
            source.next_due_at,
        )
        if self.tenant_id is None:
            conflict = "(source_key) where tenant_id is null"
        else:
            conflict = "(tenant_id, source_key) where tenant_id is not null"
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                insert into public.source_connector_runtime_state (
                    id, tenant_id, source_key, source_name, url, connector_kind,
                    access_disposition, refresh_seconds, enabled, public_config,
                    next_due_at
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict {conflict} do update set
                    source_name = excluded.source_name,
                    url = excluded.url,
                    connector_kind = excluded.connector_kind,
                    access_disposition = excluded.access_disposition,
                    refresh_seconds = excluded.refresh_seconds,
                    enabled = excluded.enabled,
                    public_config = excluded.public_config,
                    updated_at = now()
                returning *
                """,
                values,
            )
            row = cur.fetchone()
            conn.commit()
        if not row:
            raise RuntimeError(f"connector_registry_upsert_failed:{source.source_key}")
        return self._row_to_source(dict(row))

    def due_sources(self, now: datetime | None = None) -> list[ConnectorSource]:
        now = now or utcnow()
        scope, params = self._scope_sql("s")
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                select s.* from public.source_connector_runtime_state s
                where {scope}
                  and s.enabled = true
                  and s.access_disposition not in ('prohibited','manual_only')
                  and s.next_due_at <= %s
                  and (s.lease_expires_at is null or s.lease_expires_at <= %s)
                order by s.next_due_at, s.source_key
                """,
                (*params, now, now),
            )
            rows = cur.fetchall()
        return [self._row_to_source(dict(row)) for row in rows]

    def claim_due_sources(
        self, *, limit: int, now: datetime | None = None
    ) -> list[ConnectorSource]:
        """Atomically lease due sources so concurrent workers cannot double-fetch."""
        if limit <= 0:
            return []
        now = now or utcnow()
        scope, params = self._scope_sql("s")
        expires_at = now + timedelta(seconds=self.lease_seconds)
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                with candidates as (
                    select s.id
                    from public.source_connector_runtime_state s
                    where {scope}
                      and s.enabled = true
                      and s.access_disposition not in ('prohibited','manual_only')
                      and s.next_due_at <= %s
                      and (s.lease_expires_at is null or s.lease_expires_at <= %s)
                    order by s.next_due_at, s.source_key
                    for update skip locked
                    limit %s
                )
                update public.source_connector_runtime_state s
                set lease_owner = %s, lease_expires_at = %s, updated_at = now()
                from candidates c
                where s.id = c.id
                returning s.*
                """,
                (*params, now, now, limit, self.lease_owner, expires_at),
            )
            rows = cur.fetchall()
            conn.commit()
        sources = [self._row_to_source(dict(row)) for row in rows]
        sources.sort(key=lambda source: (source.next_due_at, source.source_key))
        return sources

    def mark_fetch(self, source_key: str, *, success: bool) -> None:
        source = self.get(source_key)
        if source is None:
            return
        source.schedule_next(success=success)
        scope, params = self._scope_sql()
        with self.pool.connection() as conn:
            # Lease ownership matters after expiry: an old worker finishing late
            # must not clear/reschedule a newer worker's active lease.
            conn.execute(
                f"""
                update public.source_connector_runtime_state
                set last_fetched_at=%s,
                    last_success_at=%s,
                    consecutive_failures=%s,
                    next_due_at=%s,
                    lease_owner=null,
                    lease_expires_at=null,
                    updated_at=now()
                where {scope}
                  and source_key=%s
                  and (lease_owner is null or lease_owner=%s)
                """,
                (
                    source.last_fetched_at,
                    source.last_success_at,
                    source.consecutive_failures,
                    source.next_due_at,
                    *params,
                    source_key,
                    self.lease_owner,
                ),
            )
            conn.commit()

    def start_ingestion_run(self, source: ConnectorSource) -> UUID:
        run_id = uuid4()
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.source_connector_ingestion_runs (
                    run_id, tenant_id, source_id, connector_kind, status
                ) values (%s,%s,%s,%s,'started')
                """,
                (run_id, self.tenant_id, source.id, source.kind.value),
            )
            conn.commit()
        return run_id

    def finish_ingestion_run(
        self,
        run_id: UUID,
        *,
        status: str,
        retrieved_at: datetime | None,
        fetched_count: int,
        enqueued_count: int,
        deduped_count: int,
        http_status: int | None,
        duration_ms: float,
        error_message: str | None,
    ) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """
                update public.source_connector_ingestion_runs
                set status=%s,
                    completed_at=now(),
                    retrieved_at=%s,
                    fetched_count=%s,
                    enqueued_count=%s,
                    deduped_count=%s,
                    http_status=%s,
                    duration_ms=%s,
                    error_message=%s
                where run_id=%s
                """,
                (
                    status,
                    retrieved_at,
                    max(0, int(fetched_count)),
                    max(0, int(enqueued_count)),
                    max(0, int(deduped_count)),
                    http_status,
                    max(0.0, float(duration_ms)),
                    error_message[:4000] if error_message else None,
                    run_id,
                ),
            )
            conn.commit()

    def record_fetched_item(
        self,
        source: ConnectorSource,
        item: RawObservationItem,
        *,
        retrieved_at: datetime,
        ingestion_run_id: UUID | None = None,
    ) -> ConnectorObservationReceipt:
        # Preserve only JSON-safe, non-secret observation metadata. Connector
        # credentials belong to the source runtime injector and never enter here.
        metadata = {
            str(key): value
            for key, value in item.metadata.items()
            if isinstance(value, (str, int, float, bool))
            and key.lower()
            not in {
                "authorization",
                "api_key",
                "apikey",
                "token",
                "cookie",
                "password",
                "secret",
            }
        }
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                insert into public.source_connector_observations (
                    tenant_id, source_id, ingestion_run_id, item_id, content_hash,
                    source_url, title, raw_content, claim, observed_at, retrieved_at,
                    last_retrieved_at, confidence, signal_hints, entities, metadata
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict (source_id, content_hash) do update set
                    last_seen_at=now(),
                    last_retrieved_at=excluded.last_retrieved_at,
                    seen_count=public.source_connector_observations.seen_count + 1
                returning observation_id, seen_count, status
                """,
                (
                    self.tenant_id,
                    source.id,
                    ingestion_run_id,
                    item.item_id,
                    item.content_hash,
                    item.source_url,
                    item.title,
                    item.content,
                    item.claim,
                    item.observed_at,
                    retrieved_at,
                    retrieved_at,
                    float(item.confidence),
                    _json(list(item.signal_hints)),
                    _json(list(item.entities)),
                    _json(metadata),
                ),
            )
            row = cur.fetchone()
            conn.commit()
        if not row:
            raise RuntimeError(f"connector_observation_write_failed:{source.source_key}")
        return ConnectorObservationReceipt(
            is_new=int(row["seen_count"]) == 1,
            should_enqueue=str(row["status"]) == "captured",
            observation_id=row["observation_id"],
        )

    def mark_observation_enqueued(self, observation_id: UUID, inbox_id: UUID | str) -> None:
        try:
            parsed_inbox_id = inbox_id if isinstance(inbox_id, UUID) else UUID(str(inbox_id))
        except (TypeError, ValueError):
            parsed_inbox_id = None
        with self.pool.connection() as conn:
            conn.execute(
                """
                update public.source_connector_observations
                set status='enqueued', inbox_id=%s, last_seen_at=greatest(last_seen_at, now())
                where observation_id=%s
                """,
                (parsed_inbox_id, observation_id),
            )
            conn.commit()

    def mark_observation_enqueue_failed(
        self,
        source: ConnectorSource,
        item: RawObservationItem,
        observation_id: UUID | None = None,
    ) -> None:
        # The durable row intentionally stays `captured`; a later sighting of the
        # same source/hash receives should_enqueue=True and retries the inbox write.
        del source, item, observation_id

    def remember_hash(self, content_hash: str, *, source_key: str = "") -> bool:
        """Compatibility read only; record_fetched_item() is the authoritative path."""
        source = self.get(source_key)
        if source is None:
            return True
        with self.pool.connection() as conn:
            row = conn.execute(
                """
                select 1 from public.source_connector_observations
                where source_id=%s and content_hash=%s
                limit 1
                """,
                (source.id, content_hash),
            ).fetchone()
        return row is None

    def seen_count(self) -> int:
        scope, params = self._scope_sql("o")
        with self.pool.connection() as conn:
            row = conn.execute(
                f"select count(*) from public.source_connector_observations o where {scope}",
                params,
            ).fetchone()
        return int(row[0]) if row else 0
