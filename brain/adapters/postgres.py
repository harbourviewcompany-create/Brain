from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any
from uuid import UUID

try:
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
    from psycopg_pool import ConnectionPool
except ImportError:  # Allows domain/unit tests before infrastructure extras are installed.
    dict_row = None
    Jsonb = None
    ConnectionPool = Any  # type: ignore[misc,assignment]

from ..events import BrainEvent


def _json(value: dict[str, Any]) -> Any:
    return Jsonb(value) if Jsonb is not None else value


class PostgresEventStore:
    """Canonical append-only storage for cognitive events.

    The database enforces append-only behavior with triggers. The adapter therefore
    exposes append/read operations only; mutation APIs intentionally do not exist.
    """

    def __init__(self, dsn: str, *, pool: ConnectionPool | None = None) -> None:
        if pool is None and Jsonb is None:
            raise RuntimeError(
                "PostgreSQL support requires project dependencies; install with `pip install -e .`"
            )
        self._owns_pool = pool is None
        self.pool = pool or ConnectionPool(conninfo=dsn, min_size=1, max_size=10, open=True)

    def close(self) -> None:
        if self._owns_pool:
            self.pool.close()

    def append(self, event: BrainEvent) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.brain_events (
                    id, event_type, aggregate_type, aggregate_id,
                    causation_id, correlation_id, payload, occurred_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do nothing
                """,
                (
                    event.id,
                    event.event_type,
                    event.aggregate_type,
                    event.aggregate_id,
                    event.causation_id,
                    event.correlation_id,
                    _json(event.payload),
                    event.occurred_at,
                ),
            )
            conn.commit()

    def append_many(self, events: Iterable[BrainEvent]) -> int:
        events = list(events)
        if not events:
            return 0
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    insert into public.brain_events (
                        id, event_type, aggregate_type, aggregate_id,
                        causation_id, correlation_id, payload, occurred_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do nothing
                    """,
                    [
                        (
                            e.id,
                            e.event_type,
                            e.aggregate_type,
                            e.aggregate_id,
                            e.causation_id,
                            e.correlation_id,
                            _json(e.payload),
                            e.occurred_at,
                        )
                        for e in events
                    ],
                )
            conn.commit()
        return len(events)

    def read_all(self, *, limit: int | None = None) -> list[BrainEvent]:
        sql = """
            select id, event_type, aggregate_type, aggregate_id,
                   causation_id, correlation_id, payload, occurred_at
            from public.brain_events
            order by occurred_at asc, id asc
        """
        params: tuple[Any, ...] = ()
        if limit is not None:
            if limit <= 0:
                return []
            sql += " limit %s"
            params = (limit,)

        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return [self._row_to_event(row) for row in cur.fetchall()]

    def read_after(self, occurred_at: datetime, event_id: UUID) -> list[BrainEvent]:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select id, event_type, aggregate_type, aggregate_id,
                       causation_id, correlation_id, payload, occurred_at
                from public.brain_events
                where (occurred_at, id) > (%s, %s)
                order by occurred_at asc, id asc
                """,
                (occurred_at, event_id),
            )
            return [self._row_to_event(row) for row in cur.fetchall()]

    @staticmethod
    def _row_to_event(row: dict[str, Any]) -> BrainEvent:
        return BrainEvent(
            id=row["id"],
            event_type=row["event_type"],
            aggregate_type=row["aggregate_type"],
            aggregate_id=row["aggregate_id"],
            causation_id=row["causation_id"],
            correlation_id=row["correlation_id"],
            payload=dict(row["payload"]),
            occurred_at=row["occurred_at"],
        )


class ProjectionCheckpointStore:
    """Persists disposable projection snapshots and replay progress."""

    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def save(
        self,
        projection_name: str,
        *,
        last_event_id: UUID | None,
        event_count: int,
        state: dict[str, Any],
    ) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.projection_checkpoints (
                    projection_name, last_event_id, event_count, state, updated_at
                ) values (%s, %s, %s, %s, now())
                on conflict (projection_name) do update set
                    last_event_id = excluded.last_event_id,
                    event_count = excluded.event_count,
                    state = excluded.state,
                    updated_at = now()
                """,
                (projection_name, last_event_id, event_count, _json(state)),
            )
            conn.commit()

    def get(self, projection_name: str) -> dict[str, Any] | None:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select projection_name, last_event_id, event_count, state, updated_at
                from public.projection_checkpoints
                where projection_name = %s
                """,
                (projection_name,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
