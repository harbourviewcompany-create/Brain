from __future__ import annotations

from typing import Any
from uuid import UUID

from .postgres import ConnectionPool, _json, dict_row


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
