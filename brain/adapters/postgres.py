from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
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


def _jsonable(value: Any) -> Any:
    """Convert cognitive payloads to deterministic JSON-safe primitives."""
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return _jsonable(value.value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return [_jsonable(item) for item in sorted(value, key=str)]
    return value


def _json(value: Any) -> Any:
    normalized = _jsonable(value)
    return Jsonb(normalized) if Jsonb is not None else normalized


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
                            event.id,
                            event.event_type,
                            event.aggregate_type,
                            event.aggregate_id,
                            event.causation_id,
                            event.correlation_id,
                            _json(event.payload),
                            event.occurred_at,
                        )
                        for event in events
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

    def read_recent(
        self,
        *,
        event_types: Iterable[str],
        limit: int = 200,
    ) -> list[BrainEvent]:
        """Read the newest events for selected types without scanning/sorting the ledger.

        `brain_events_type_idx (event_type, occurred_at)` is part of the baseline
        schema. Querying each requested type independently lets PostgreSQL walk
        that index backward and stop at `limit`, rather than materializing and
        sorting the entire append-only ledger. The small bounded result sets are
        then merged in process to preserve one globally newest-first response.
        """
        if limit <= 0:
            return []
        types = sorted({str(value).strip() for value in event_types if str(value).strip()})
        if not types:
            return []

        events: list[BrainEvent] = []
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            for event_type in types:
                cur.execute(
                    """
                        select id, event_type, aggregate_type, aggregate_id,
                               causation_id, correlation_id, payload, occurred_at
                        from public.brain_events
                        where event_type = %s
                        order by occurred_at desc
                        limit %s
                    """,
                    (event_type, limit),
                )
                events.extend(self._row_to_event(row) for row in cur.fetchall())

        events.sort(key=lambda event: (event.occurred_at, str(event.id)), reverse=True)
        return events[:limit]

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
