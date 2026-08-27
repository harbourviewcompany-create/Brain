from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from .postgres import ConnectionPool, _json, dict_row
from ..domain import utcnow


def _organism_payload(value: Any) -> Any:
    if is_dataclass(value):
        return _organism_payload(asdict(value))
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _organism_payload(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_organism_payload(item) for item in value]
    return value


class PostgresSensoryInbox:
    """Durable inbox for stimuli waiting to enter the cognitive loop."""

    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def enqueue(self, *, source_key: str, content: str, claim: str, payload: dict[str, Any] | None = None) -> UUID:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("insert into public.sensory_inbox (source_key, content, claim, payload) values (%s,%s,%s,%s) returning id", (source_key, content, claim, _json(payload or {})))
                row = cur.fetchone()
            conn.commit()
        return row["id"]

    def claim_next(self) -> dict[str, Any] | None:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    with next_item as (
                        select id from public.sensory_inbox
                        where status='pending' and available_at <= now()
                        order by available_at asc, created_at asc
                        for update skip locked limit 1
                    )
                    update public.sensory_inbox i
                    set status='processing', claimed_at=now(), attempts=attempts+1
                    from next_item n where i.id=n.id returning i.*
                """)
                row = cur.fetchone()
            conn.commit()
        return dict(row) if row else None

    def complete(self, inbox_id: UUID) -> None:
        with self.pool.connection() as conn:
            conn.execute("update public.sensory_inbox set status='completed', completed_at=now(), last_error=null where id=%s", (inbox_id,))
            conn.commit()

    def fail(self, inbox_id: UUID, error: str, *, retry: bool = True) -> None:
        with self.pool.connection() as conn:
            conn.execute("""
                update public.sensory_inbox
                set status=%s, last_error=%s,
                    available_at=case when %s then now()+interval '1 minute' else available_at end
                where id=%s
            """, ("pending" if retry else "failed", error[:4000], retry, inbox_id))
            conn.commit()

    def pending_count(self) -> int:
        return self.stats()["pending"]

    def stats(self) -> dict[str, int]:
        """Return the same queue-health contract as InMemorySensoryInbox."""
        counts = {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "total": 0,
        }
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                select status, count(*)::bigint as count
                from public.sensory_inbox
                group by status
            """)
            rows = cur.fetchall()
        for row in rows:
            status = str(row["status"])
            count = int(row["count"])
            if status in counts:
                counts[status] = count
            counts["total"] += count
        return counts


class CognitiveCycleRunStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def save(self, inbox_id: UUID, result: Any) -> None:
        with self.pool.connection() as conn:
            conn.execute("""
                insert into public.cognitive_cycle_runs (
                    id,inbox_id,observation_id,belief_id,evidence_id,attention_score,
                    contradiction_detected,task_ids,event_ids,status,completed_at
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,'completed',now())
                on conflict (id) do nothing
            """, (result.cycle_id,inbox_id,result.observation_id,result.belief_id,result.evidence_id,result.attention_score,result.contradiction_detected,result.task_ids,result.event_ids))
            conn.commit()


class InMemoryCognitiveOrganismStore:
    """Deterministic durable-store stand-in for tests and local operator use."""

    def __init__(self) -> None:
        self.checkpoints: dict[str, dict[str, Any]] = {}
        self.audit_events: list[dict[str, Any]] = []

    def save_checkpoint(self, checkpoint_name: str, payload: dict[str, Any]) -> None:
        encoded = dict(_organism_payload(payload))
        self.checkpoints[checkpoint_name] = encoded
        self.append_audit_event(
            "COGNITIVE_ORGANISM_CHECKPOINT_SAVED",
            "cognitive_organism_checkpoint",
            checkpoint_name,
            encoded,
        )

    def load_checkpoint(self, checkpoint_name: str) -> dict[str, Any] | None:
        payload = self.checkpoints.get(checkpoint_name)
        return dict(payload) if payload else None

    def append_audit_event(
        self,
        event_type: str,
        object_type: str,
        object_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": str(uuid4()),
            "event_type": event_type,
            "object_type": object_type,
            "object_id": object_id,
            "payload": _organism_payload(payload or {}),
            "created_at": utcnow().isoformat(),
        }
        self.audit_events.append(event)
        return dict(event)

    def list_audit_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        return list(reversed(self.audit_events[-limit:]))


class PostgresCognitiveOrganismStore:
    """Production persistence adapter for organism checkpoints and audit events.

    The adapter intentionally stores replayable JSON checkpoints and append-only audit
    events. It does not execute external actions, send outreach or mutate autonomy policy.
    """

    def __init__(self, dsn: str | None = None, *, pool: ConnectionPool | None = None) -> None:
        if pool is None:
            if dict_row is None:
                raise RuntimeError("PostgreSQL support requires project dependencies")
            if not dsn:
                raise ValueError("dsn_required_for_postgres_cognitive_organism_store")
            self._owns_pool = True
            self.pool = ConnectionPool(conninfo=dsn, min_size=1, max_size=10, open=True)
        else:
            self._owns_pool = False
            self.pool = pool

    def close(self) -> None:
        if self._owns_pool:
            self.pool.close()

    def save_checkpoint(self, checkpoint_name: str, payload: dict[str, Any]) -> None:
        encoded = dict(_organism_payload(payload))
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.cognitive_organism_checkpoints (
                    checkpoint_name, payload, updated_at
                ) values (%s, %s, now())
                on conflict (checkpoint_name) do update set
                    payload = excluded.payload,
                    updated_at = now()
                """,
                (checkpoint_name, _json(encoded)),
            )
            conn.execute(
                """
                insert into public.organism_audit_events (
                    event_type, object_type, object_id, payload
                ) values (%s, %s, %s, %s)
                """,
                (
                    "COGNITIVE_ORGANISM_CHECKPOINT_SAVED",
                    "cognitive_organism_checkpoint",
                    checkpoint_name,
                    _json(encoded),
                ),
            )
            conn.commit()

    def load_checkpoint(self, checkpoint_name: str) -> dict[str, Any] | None:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select payload from public.cognitive_organism_checkpoints
                where checkpoint_name = %s
                """,
                (checkpoint_name,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return dict(row["payload"])

    def append_audit_event(
        self,
        event_type: str,
        object_type: str,
        object_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        encoded = dict(_organism_payload(payload or {}))
        event_id = uuid4()
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.organism_audit_events (
                    id, event_type, object_type, object_id, payload
                ) values (%s, %s, %s, %s, %s)
                """,
                (event_id, event_type, object_type, object_id, _json(encoded)),
            )
            conn.commit()
        return {
            "id": str(event_id),
            "event_type": event_type,
            "object_type": object_type,
            "object_id": object_id,
            "payload": encoded,
        }

    def list_audit_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select id, created_at, event_type, object_type, object_id, payload
                from public.organism_audit_events
                order by created_at desc, id desc
                limit %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [
            {
                "id": str(row["id"]),
                "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
                "event_type": row["event_type"],
                "object_type": row["object_type"],
                "object_id": row["object_id"],
                "payload": dict(row["payload"]),
            }
            for row in rows
        ]
