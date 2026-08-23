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

from ..economic_codec import decode, encode
from ..economic_runtime import TransitionRecord
from ..formulas import FormulaRunResult


class PostgresEconomicStore:
    """Durable typed economic cognition store backed by the canonical JSONB ledger."""

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
        self._hydrate()

    def close(self) -> None:
        if self._owns_pool:
            self.pool.close()

    def _hydrate(self) -> None:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select kind, id, payload from public.economic_objects")
            for row in cur.fetchall():
                self._cache.setdefault(row["kind"], {})[row["id"]] = decode(
                    row["kind"], dict(row["payload"] or {})
                )
            cur.execute(
                """
                select id, object_id, object_type, from_state, to_state, trigger,
                       actor, evidence_ids, formula_run_ids, acceptance_test, created_at
                from public.economic_transitions order by created_at asc
                """
            )
            self._transition_cache = [
                TransitionRecord(
                    id=row["id"],
                    object_id=row["object_id"],
                    object_type=row["object_type"],
                    from_state=row["from_state"],
                    to_state=row["to_state"],
                    trigger=row["trigger"],
                    actor=row["actor"],
                    evidence_ids=list(row["evidence_ids"] or []),
                    formula_run_ids=list(row["formula_run_ids"] or []),
                    acceptance_test=row["acceptance_test"],
                    created_at=row["created_at"],
                )
                for row in cur.fetchall()
            ]
            cur.execute(
                """
                select id, formula_id, owner_object_id, owner_object_type, inputs, output,
                       service, table_store, dashboard, decision_consequence, audit_evidence
                from public.economic_formula_runs
                """
            )
            self._formula_cache = {
                row["id"]: FormulaRunResult(
                    formula_id=row["formula_id"],
                    run_id=row["id"],
                    owner_object_id=row["owner_object_id"],
                    owner_object_type=row["owner_object_type"],
                    service=row["service"],
                    table_store=row["table_store"],
                    dashboard=row["dashboard"],
                    decision_consequence=row["decision_consequence"],
                    inputs=dict(row["inputs"] or {}),
                    output=float(row["output"]),
                    audit_evidence=dict(row["audit_evidence"] or {}),
                )
                for row in cur.fetchall()
            }

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
                (kind, object_id, Jsonb(encode(payload))),
            )
            conn.commit()

    def get(self, kind: str, object_id: UUID) -> Any | None:
        return self._cache.get(kind, {}).get(object_id)

    def list(self, kind: str) -> list[Any]:
        return list(self._cache.get(kind, {}).values())

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
        return [transition for transition in self._transition_cache if transition.object_id == object_id]

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
                    Jsonb(encode(run.inputs)),
                    run.output,
                    run.service,
                    run.table_store,
                    run.dashboard,
                    run.decision_consequence,
                    Jsonb(encode(run.audit_evidence)),
                ),
            )
            conn.commit()
