from __future__ import annotations

from typing import Any
from uuid import UUID

try:
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
    from psycopg_pool import ConnectionPool
except ImportError:
    dict_row = None
    Jsonb = None
    ConnectionPool = Any  # type: ignore[misc,assignment]

from ..developmental.evidence_store import (
    DevelopmentalEvidenceCodec,
    DevelopmentalEvidenceEvent,
)


class PostgresDevelopmentalEvidenceStore:
    """Durable AGENT-017/018 evidence snapshots plus append-only event history."""

    def __init__(self, dsn: str | None = None, *, pool: ConnectionPool | None = None) -> None:
        if pool is None and ConnectionPool is Any:
            raise RuntimeError("PostgreSQL support requires psycopg dependencies")
        if pool is None and not dsn:
            raise ValueError("dsn_or_pool_required")
        self._owns_pool = pool is None
        self.pool = pool or ConnectionPool(conninfo=dsn, min_size=1, max_size=10, open=True)

    def close(self) -> None:
        if self._owns_pool:
            self.pool.close()

    def put(self, record: Any, *, event_type: str, evidence_refs: list[str]) -> None:
        if not evidence_refs:
            raise ValueError("developmental_evidence_write_requires_evidence")
        record_id = getattr(record, "id", None)
        if not isinstance(record_id, UUID):
            raise ValueError("developmental_record_requires_uuid_id")
        kind = type(record).__name__
        payload = DevelopmentalEvidenceCodec.encode(record)
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    insert into public.developmental_evidence_objects (kind, id, payload, updated_at)
                    values (%s, %s, %s, now())
                    on conflict (kind, id) do update set
                        payload = excluded.payload,
                        updated_at = now()
                    """,
                    (kind, record_id, Jsonb(payload)),
                )
                cur.execute(
                    """
                    insert into public.developmental_evidence_events (
                        event_type, record_kind, record_id, payload, evidence_refs
                    ) values (%s, %s, %s, %s, %s)
                    returning id, sequence, created_at
                    """,
                    (event_type, kind, record_id, Jsonb(payload), evidence_refs),
                )
                cur.fetchone()
            conn.commit()

    def get(self, record_kind: str, record_id: UUID) -> Any | None:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "select payload from public.developmental_evidence_objects where kind = %s and id = %s",
                (record_kind, record_id),
            )
            row = cur.fetchone()
            return None if row is None else DevelopmentalEvidenceCodec.decode(dict(row["payload"]))

    def list(self, record_kind: str) -> list[Any]:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "select payload from public.developmental_evidence_objects where kind = %s order by updated_at, id",
                (record_kind,),
            )
            return [DevelopmentalEvidenceCodec.decode(dict(row["payload"])) for row in cur.fetchall()]

    def events(self) -> list[DevelopmentalEvidenceEvent]:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select id, sequence, event_type, record_kind, record_id, payload,
                       evidence_refs, created_at
                from public.developmental_evidence_events
                order by sequence asc
                """
            )
            return [
                DevelopmentalEvidenceEvent(
                    id=row["id"],
                    sequence=int(row["sequence"]),
                    event_type=row["event_type"],
                    record_kind=row["record_kind"],
                    record_id=row["record_id"],
                    payload=dict(row["payload"]),
                    evidence_refs=list(row["evidence_refs"] or []),
                )
                for row in cur.fetchall()
            ]
