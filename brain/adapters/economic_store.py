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
except ImportError:
    dict_row = None
    Jsonb = None
    ConnectionPool = Any  # type: ignore[misc,assignment]

from ..economic_runtime import TransitionRecord
from ..formulas import FormulaRunResult


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, set):
        return [_jsonable(v) for v in sorted(value, key=str)]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


class PostgresEconomicStore:
    """JSONB persistence for economic cognition objects and transition/formula evidence.

    The economic runtime keeps typed objects during a process. The database is the
    durable event/object ledger; operator/read APIs may use ``list_payloads`` after
    restarts without requiring Python dataclass reconstruction.
    """

    def __init__(self, dsn: str | None = None, *, pool: ConnectionPool | None = None) -> None:
        if pool is None and ConnectionPool is Any:
            raise RuntimeError("PostgreSQL support requires psycopg dependencies")
        if pool is None and not dsn:
            raise ValueError("dsn_or_pool_required")
        self._owns_pool = pool is None
        self.pool = pool or ConnectionPool(conninfo=dsn, min_size=1, max_size=10, open=True)
        self._cache: dict[str, dict[UUID, Any]] = {}
        self._transition_cache: list[TransitionRecord] = []
        self._formula_cache: dict[UUID, FormulaRunResult] = {}

    def close(self) -> None:
        if self._owns_pool:
            self.pool.close()

    def put(self, kind: str, object_id: UUID, payload: Any) -> None:
        self._cache.setdefault(kind, {})[object_id] = payload
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.economic_objects (kind, id, payload, updated_at)
                values (%s, %s, %s, now())
                on conflict (kind, id) do update set
                    payload = excluded.payload,
                    updated_at = now()
                """,
                (kind, object_id, Jsonb(_jsonable(payload))),
            )
            conn.commit()

    def get(self, kind: str, object_id: UUID) -> Any | None:
        cached = self._cache.get(kind, {}).get(object_id)
        if cached is not None:
            return cached
        return None

    def list(self, kind: str) -> list[Any]:
        return list(self._cache.get(kind, {}).values())

    def list_payloads(self, kind: str) -> list[dict[str, Any]]:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "select payload from public.economic_objects where kind = %s order by updated_at desc",
                (kind,),
            )
            return [dict(row["payload"] or {}) for row in cur.fetchall()]

    def append_transition(self, transition: TransitionRecord) -> None:
        self._transition_cache.append(transition)
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.economic_transitions (
                    id, object_id, object_type, from_state, to_state, trigger,
                    actor, evidence_ids, formula_run_ids, acceptance_test, created_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    transition.id,
                    transition.object_id,
                    transition.object_type,
                    transition.from_state,
                    transition.to_state,
                    transition.trigger,
                    transition.actor,
                    transition.evidence_ids,
                    transition.formula_run_ids,
                    transition.acceptance_test,
                    transition.created_at,
                ),
            )
            conn.commit()

    def transitions(self, object_id: UUID | None = None) -> list[TransitionRecord]:
        if object_id is None:
            return list(self._transition_cache)
        return [t for t in self._transition_cache if t.object_id == object_id]

    def save_formula_run(self, run: FormulaRunResult) -> None:
        self._formula_cache[run.run_id] = run
        with self.pool.connection() as conn:
            conn.execute(
                """
                insert into public.economic_formula_runs (
                    id, formula_id, owner_object_id, owner_object_type, inputs, output,
                    service, table_store, dashboard, decision_consequence, audit_evidence
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (id) do nothing
                """,
                (
                    run.run_id,
                    run.formula_id,
                    run.owner_object_id,
                    run.owner_object_type,
                    Jsonb(_jsonable(run.inputs)),
                    run.output,
                    run.service,
                    run.table_store,
                    run.dashboard,
                    run.decision_consequence,
                    Jsonb(_jsonable(run.audit_evidence)),
                ),
            )
            conn.commit()
