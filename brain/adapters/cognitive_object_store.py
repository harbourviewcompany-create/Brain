from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

try:
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover
    dict_row = None
    Jsonb = None
    ConnectionPool = Any  # type: ignore[misc,assignment]


def jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return jsonable(asdict(value))
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    return value


class InMemoryCognitiveObjectStore:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict[str, Any]] = {}

    def save(
        self,
        kind: str,
        object_id: UUID | str,
        payload: Any,
        *,
        source_refs: list[str],
        world_valid_from: datetime | None = None,
        world_valid_to: datetime | None = None,
    ) -> None:
        if not source_refs:
            raise ValueError("cognitive object persistence requires source provenance")
        self.objects[(kind, str(object_id))] = {
            "kind": kind,
            "object_id": str(object_id),
            "payload": jsonable(payload),
            "source_refs": list(source_refs),
            "world_valid_from": world_valid_from.isoformat() if world_valid_from else None,
            "world_valid_to": world_valid_to.isoformat() if world_valid_to else None,
        }

    def get(self, kind: str, object_id: UUID | str) -> dict[str, Any] | None:
        return self.objects.get((kind, str(object_id)))

    def list(self, kind: str) -> list[dict[str, Any]]:
        return [value for (stored_kind, _), value in self.objects.items() if stored_kind == kind]


class PostgresCognitiveObjectStore(InMemoryCognitiveObjectStore):
    def __init__(self, dsn: str, *, pool: ConnectionPool | None = None) -> None:
        if pool is None and Jsonb is None:
            raise RuntimeError("PostgreSQL support requires project dependencies")
        super().__init__()
        self._owns_pool = pool is None
        self.pool = pool or ConnectionPool(conninfo=dsn, min_size=1, max_size=5, open=True)

    def close(self) -> None:
        if self._owns_pool:
            self.pool.close()

    def save(
        self,
        kind: str,
        object_id: UUID | str,
        payload: Any,
        *,
        source_refs: list[str],
        world_valid_from: datetime | None = None,
        world_valid_to: datetime | None = None,
    ) -> None:
        super().save(
            kind,
            object_id,
            payload,
            source_refs=source_refs,
            world_valid_from=world_valid_from,
            world_valid_to=world_valid_to,
        )
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.cognitive_objects (
                    object_id, kind, payload, source_refs,
                    world_valid_from, world_valid_to, learned_at, updated_at
                ) values (%s, %s, %s, %s, %s, %s, now(), now())
                on conflict (object_id, kind) do update set
                    payload = excluded.payload,
                    source_refs = excluded.source_refs,
                    world_valid_from = excluded.world_valid_from,
                    world_valid_to = excluded.world_valid_to,
                    updated_at = now()
                """,
                (
                    str(object_id),
                    kind,
                    Jsonb(jsonable(payload)),
                    list(source_refs),
                    world_valid_from,
                    world_valid_to,
                ),
            )
            conn.commit()

    def get(self, kind: str, object_id: UUID | str) -> dict[str, Any] | None:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select kind, object_id, payload, source_refs,
                       world_valid_from, world_valid_to, learned_at, updated_at
                from public.cognitive_objects
                where kind = %s and object_id = %s
                """,
                (kind, str(object_id)),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def list(self, kind: str) -> list[dict[str, Any]]:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select kind, object_id, payload, source_refs,
                       world_valid_from, world_valid_to, learned_at, updated_at
                from public.cognitive_objects
                where kind = %s
                order by learned_at asc, object_id asc
                """,
                (kind,),
            )
            return [dict(row) for row in cur.fetchall()]
