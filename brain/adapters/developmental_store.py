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


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return value


class InMemoryDevelopmentalStore:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict[str, Any]] = {}
        self.transitions: list[dict[str, Any]] = []
        self.scores: list[dict[str, Any]] = []

    def save(self, kind: str, object_id: UUID | str, payload: Any, source_refs: list[str]) -> None:
        self.objects[(kind, str(object_id))] = {
            "kind": kind,
            "object_id": str(object_id),
            "payload": _jsonable(payload),
            "source_refs": list(source_refs),
        }

    def get(self, kind: str, object_id: UUID | str) -> dict[str, Any] | None:
        return self.objects.get((kind, str(object_id)))

    def list(self, kind: str) -> list[dict[str, Any]]:
        return [value for (stored_kind, _), value in self.objects.items() if stored_kind == kind]

    def log_transition(
        self,
        module_key: str,
        previous_state: str,
        new_state: str,
        evidence_refs: list[str],
        reason: str,
    ) -> None:
        self.transitions.append(
            {
                "module_key": module_key,
                "previous_state": previous_state,
                "new_state": new_state,
                "evidence_refs": list(evidence_refs),
                "reason": reason,
            }
        )

    def save_score(self, module_key: str, score: float, dimensions: dict[str, float]) -> None:
        self.scores.append({"module_key": module_key, "score": score, "dimensions": dict(dimensions)})


class PostgresDevelopmentalStore(InMemoryDevelopmentalStore):
    def __init__(self, dsn: str, *, pool: ConnectionPool | None = None) -> None:
        if pool is None and Jsonb is None:
            raise RuntimeError("PostgreSQL support requires project dependencies")
        super().__init__()
        self._owns_pool = pool is None
        self.pool = pool or ConnectionPool(conninfo=dsn, min_size=1, max_size=5, open=True)

    def close(self) -> None:
        if self._owns_pool:
            self.pool.close()

    def save(self, kind: str, object_id: UUID | str, payload: Any, source_refs: list[str]) -> None:
        super().save(kind, object_id, payload, source_refs)
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.developmental_objects (
                    object_id, kind, payload, source_refs, updated_at
                ) values (%s, %s, %s, %s, now())
                on conflict (object_id, kind) do update set
                    payload = excluded.payload,
                    source_refs = excluded.source_refs,
                    updated_at = now()
                """,
                (str(object_id), kind, Jsonb(_jsonable(payload)), list(source_refs)),
            )
            conn.commit()

    def get(self, kind: str, object_id: UUID | str) -> dict[str, Any] | None:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select kind, object_id, payload, source_refs
                from public.developmental_objects
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
                select kind, object_id, payload, source_refs
                from public.developmental_objects
                where kind = %s order by updated_at asc, object_id asc
                """,
                (kind,),
            )
            return [dict(row) for row in cur.fetchall()]

    def log_transition(
        self,
        module_key: str,
        previous_state: str,
        new_state: str,
        evidence_refs: list[str],
        reason: str,
    ) -> None:
        super().log_transition(module_key, previous_state, new_state, evidence_refs, reason)
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.developmental_transitions (
                    module_key, previous_state, new_state, evidence_refs, reason
                ) values (%s, %s, %s, %s, %s)
                """,
                (module_key, previous_state, new_state, list(evidence_refs), reason),
            )
            conn.commit()

    def save_score(self, module_key: str, score: float, dimensions: dict[str, float]) -> None:
        super().save_score(module_key, score, dimensions)
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.developmental_scores (module_key, score, dimensions)
                values (%s, %s, %s)
                """,
                (module_key, score, Jsonb(_jsonable(dimensions))),
            )
            conn.commit()
