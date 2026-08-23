"""Durable belief projection (Postgres) with in-memory fallback helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

try:
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
    from psycopg_pool import ConnectionPool
except ImportError:
    dict_row = None
    Jsonb = None
    ConnectionPool = Any  # type: ignore[misc, assignment]

from brain.domain import Belief, BeliefState


def _json(value: Any) -> Any:
    return Jsonb(value) if Jsonb is not None else value


class PostgresBeliefStore:
    """Current-state projection for beliefs — rebuildable from brain_events."""

    def __init__(self, pool: ConnectionPool) -> None:
        if dict_row is None:
            raise RuntimeError("PostgreSQL support requires project dependencies; install with `pip install -e .`")
        self.pool = pool

    def upsert(self, belief: Belief) -> None:
        unknowns = list(belief.unknowns) if belief.unknowns else []
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.beliefs (
                    id, statement, confidence, state, unknowns, version, created_at, updated_at
                ) values (%s, %s, %s, %s, %s, %s, coalesce(%s, now()), coalesce(%s, now()))
                on conflict (id) do update set
                    statement = excluded.statement,
                    confidence = excluded.confidence,
                    state = excluded.state,
                    unknowns = excluded.unknowns,
                    version = excluded.version,
                    updated_at = coalesce(excluded.updated_at, now())
                """,
                (
                    belief.id,
                    belief.statement,
                    belief.confidence,
                    str(belief.state),
                    _json(unknowns),
                    belief.version,
                    getattr(belief, "updated_at", None),
                    getattr(belief, "updated_at", None),
                ),
            )
            conn.commit()

    def get(self, belief_id: UUID) -> Belief | None:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select id, statement, confidence, state, unknowns, version, created_at, updated_at
                from public.beliefs
                where id = %s
                """,
                (belief_id,),
            )
            row = cur.fetchone()
            return self._row_to_belief(row) if row else None

    def list_all(self) -> list[Belief]:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select id, statement, confidence, state, unknowns, version, created_at, updated_at
                from public.beliefs
                order by updated_at desc nulls last, created_at desc
                """
            )
            return [self._row_to_belief(row) for row in cur.fetchall()]

    def load_into(self, target: dict[UUID, Belief]) -> int:
        """Hydrate an in-memory belief map from the projection table."""
        items = self.list_all()
        for b in items:
            target[b.id] = b
        return len(items)

    @staticmethod
    def _row_to_belief(row: dict[str, Any]) -> Belief:
        raw_state = row.get("state") or "hypothesis"
        try:
            state = BeliefState(str(raw_state).split(".")[-1].lower())
        except ValueError:
            state = BeliefState.HYPOTHESIS
        unknowns = row.get("unknowns") or []
        if not isinstance(unknowns, list):
            unknowns = []
        updated = row.get("updated_at")
        if not isinstance(updated, datetime):
            updated = None
        belief = Belief(
            statement=str(row["statement"]),
            confidence=float(row["confidence"]),
            state=state,
            id=row["id"],
            unknowns=list(unknowns),
            version=int(row.get("version") or 1),
        )
        if updated is not None:
            belief.updated_at = updated
        return belief


def serialize_belief(belief: Belief) -> dict[str, Any]:
    return {
        "id": str(belief.id),
        "statement": belief.statement,
        "confidence": belief.confidence,
        "state": str(belief.state),
        "version": belief.version,
        "created_at": None,
        "updated_at": belief.updated_at.isoformat() if getattr(belief, "updated_at", None) else None,
    }
