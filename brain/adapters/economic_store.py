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

from ..economic import (
    AsymmetryType,
    CounterpartyProfile,
    CounterpartyRole,
    EconomicAffordance,
    EconomicAsymmetry,
    EconomicOpportunity,
    MoneyPath,
    MoneyVerb,
    OpportunityType,
    PaymentModel,
    PressureEvent,
    PressureType,
    RevenueAttribution,
    Transaction,
)
from ..economic_runtime import (
    BusinessModelHypothesis,
    CompoundingAsset,
    EconomicObjectState,
    EconomicROI,
    FeeControl,
    KillDecision,
    SourcePlane,
    SourcePlaneType,
    SourceRightsClass,
    SourceRightsProfile,
    TransitionRecord,
)
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


def _dt(value: str | datetime | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _uuid(value: str | UUID | None) -> UUID | None:
    if value is None or isinstance(value, UUID):
        return value
    return UUID(value)


def _uuid_list(values: list[str | UUID] | None) -> list[UUID]:
    return [UUID(str(v)) for v in (values or [])]


def _decode(kind: str, payload: dict[str, Any]) -> Any:
    p = dict(payload)
    if kind == "asymmetry":
        return EconomicAsymmetry(
            entity_id=UUID(p["entity_id"]),
            kind=AsymmetryType(p["kind"]),
            magnitude=float(p["magnitude"]),
            confidence=float(p["confidence"]),
            evidence_ids=_uuid_list(p.get("evidence_ids")),
            id=UUID(p["id"]),
            created_at=_dt(p["created_at"]),
            metadata=dict(p.get("metadata") or {}),
        )
    if kind == "pressure":
        return PressureEvent(
            entity_id=UUID(p["entity_id"]),
            kind=PressureType(p["kind"]),
            magnitude=float(p["magnitude"]),
            confidence=float(p["confidence"]),
            direction=p.get("direction", "increasing"),
            evidence_ids=_uuid_list(p.get("evidence_ids")),
            id=UUID(p["id"]),
            created_at=_dt(p["created_at"]),
            valid_until=_dt(p.get("valid_until")),
            metadata=dict(p.get("metadata") or {}),
        )
    if kind == "affordance":
        return EconomicAffordance(
            entity_id=UUID(p["entity_id"]),
            verb=MoneyVerb(p["verb"]),
            rationale=p["rationale"],
            confidence=float(p["confidence"]),
            evidence_ids=_uuid_list(p.get("evidence_ids")),
            id=UUID(p["id"]),
            created_at=_dt(p["created_at"]),
        )
    if kind == "money_path":
        return MoneyPath(
            verb=MoneyVerb(p["verb"]),
            payment_model=PaymentModel(p["payment_model"]),
            buyer_entity_id=_uuid(p.get("buyer_entity_id")),
            expected_gross_value=float(p["expected_gross_value"]),
            expected_net_value=float(p["expected_net_value"]),
            time_to_cash_days=float(p["time_to_cash_days"]),
            conversion_probability=float(p["conversion_probability"]),
            collection_risk=float(p.get("collection_risk", 0.0)),
            fee_protection_required=bool(p.get("fee_protection_required", False)),
            id=UUID(p["id"]),
            created_at=_dt(p["created_at"]),
            metadata=dict(p.get("metadata") or {}),
        )
    if kind == "opportunity":
        return EconomicOpportunity(
            kind=OpportunityType(p["kind"]),
            entity_id=UUID(p["entity_id"]),
            money_path_ids=_uuid_list(p.get("money_path_ids")),
            gross_value=float(p["gross_value"]),
            net_value=float(p["net_value"]),
            conversion_probability=float(p["conversion_probability"]),
            urgency=float(p["urgency"]),
            access_advantage=float(p["access_advantage"]),
            evidence_confidence=float(p["evidence_confidence"]),
            repeatability=float(p["repeatability"]),
            strategic_compounding_value=float(p["strategic_compounding_value"]),
            required_capital=float(p["required_capital"]),
            required_operator_hours=float(p["required_operator_hours"]),
            legal_reputation_risk=float(p["legal_reputation_risk"]),
            operational_complexity=float(p["operational_complexity"]),
            time_decay=float(p.get("time_decay", 0.0)),
            id=UUID(p["id"]),
            created_at=_dt(p["created_at"]),
            metadata=dict(p.get("metadata") or {}),
        )
    if kind == "counterparty":
        return CounterpartyProfile(
            entity_id=UUID(p["entity_id"]),
            roles={CounterpartyRole(v) for v in p.get("roles", [])},
            needs=list(p.get("needs") or []),
            assets=list(p.get("assets") or []),
            budget_estimate=p.get("budget_estimate"),
            urgency=float(p.get("urgency", 0.0)),
            trust=float(p.get("trust", 0.5)),
            reachability=float(p.get("reachability", 0.0)),
            decision_authority=float(p.get("decision_authority", 0.0)),
            response_rate=p.get("response_rate"),
            id=UUID(p["id"]),
            updated_at=_dt(p["updated_at"]),
            metadata=dict(p.get("metadata") or {}),
        )
    if kind == "transaction":
        return Transaction(
            opportunity_id=UUID(p["opportunity_id"]),
            buyer_entity_id=_uuid(p.get("buyer_entity_id")),
            seller_entity_id=_uuid(p.get("seller_entity_id")),
            payment_model=PaymentModel(p["payment_model"]),
            expected_revenue=float(p["expected_revenue"]),
            expected_profit=float(p["expected_profit"]),
            capital_at_risk=float(p["capital_at_risk"]),
            fee_protected=bool(p["fee_protected"]),
            status=p.get("status", "detected"),
            id=UUID(p["id"]),
            created_at=_dt(p["created_at"]),
            metadata=dict(p.get("metadata") or {}),
        )
    if kind == "revenue_attribution":
        return RevenueAttribution(
            transaction_id=UUID(p["transaction_id"]),
            opportunity_id=UUID(p["opportunity_id"]),
            source_ids=list(p.get("source_ids") or []),
            gross_revenue=float(p["gross_revenue"]),
            net_profit=float(p["net_profit"]),
            operator_hours=float(p["operator_hours"]),
            data_compute_cost=float(p["data_compute_cost"]),
            attribution_confidence=float(p["attribution_confidence"]),
            id=UUID(p["id"]),
            created_at=_dt(p["created_at"]),
        )
    if kind == "source_rights":
        return SourceRightsProfile(
            source_key=p["source_key"],
            rights_class=SourceRightsClass(p["rights_class"]),
            jurisdiction=p["jurisdiction"],
            permitted_collection=bool(p["permitted_collection"]),
            permitted_storage=bool(p["permitted_storage"]),
            permitted_commercial_use=bool(p["permitted_commercial_use"]),
            permitted_redistribution=bool(p.get("permitted_redistribution", False)),
            retention_days=p.get("retention_days"),
            notes=list(p.get("notes") or []),
            id=UUID(p["id"]),
            reviewed_at=_dt(p["reviewed_at"]),
        )
    if kind == "source_plane":
        return SourcePlane(
            source_key=p["source_key"],
            plane=SourcePlaneType(p["plane"]),
            jurisdiction=p["jurisdiction"],
            rights_profile_id=UUID(p["rights_profile_id"]),
            refresh_seconds=int(p["refresh_seconds"]),
            reliability=float(p["reliability"]),
            estimated_cost=float(p.get("estimated_cost", 0.0)),
            signal_yield=float(p.get("signal_yield", 0.0)),
            opportunity_yield=float(p.get("opportunity_yield", 0.0)),
            attributed_net_profit=float(p.get("attributed_net_profit", 0.0)),
            status=p.get("status", "candidate"),
            id=UUID(p["id"]),
            created_at=_dt(p["created_at"]),
        )
    if kind == "fee_control":
        return FeeControl(
            transaction_id=UUID(p["transaction_id"]),
            mandate=bool(p.get("mandate", False)),
            introduction_logged=bool(p.get("introduction_logged", False)),
            fee_agreement=bool(p.get("fee_agreement", False)),
            exclusivity=bool(p.get("exclusivity", False)),
            origination_evidence=bool(p.get("origination_evidence", False)),
            jurisdiction_reviewed=bool(p.get("jurisdiction_reviewed", False)),
            id=UUID(p["id"]),
        )
    if kind == "economic_roi":
        return EconomicROI(
            object_key=p["object_key"],
            gross_revenue=float(p["gross_revenue"]),
            net_profit=float(p["net_profit"]),
            total_cost=float(p["total_cost"]),
            roi=float(p["roi"]),
            attribution_confidence=float(p["attribution_confidence"]),
            id=UUID(p["id"]),
        )
    if kind == "compounding_asset":
        return CompoundingAsset(
            kind=p["kind"],
            key=p["key"],
            evidence_count=int(p["evidence_count"]),
            payer_count=int(p["payer_count"]),
            expected_value=float(p["expected_value"]),
            resource_estimate=float(p["resource_estimate"]),
            status=EconomicObjectState(p["status"]),
            id=UUID(p["id"]),
            created_at=_dt(p["created_at"]),
        )
    if kind == "business_model":
        return BusinessModelHypothesis(
            problem_pattern=p["problem_pattern"],
            solution_pattern=p["solution_pattern"],
            payer_pattern=p["payer_pattern"],
            occurrences=int(p["occurrences"]),
            unique_payers=int(p["unique_payers"]),
            expected_net_value=float(p["expected_net_value"]),
            resource_estimate=float(p["resource_estimate"]),
            status=EconomicObjectState(p["status"]),
            id=UUID(p["id"]),
        )
    if kind == "kill_decision":
        return KillDecision(
            opportunity_id=UUID(p["opportunity_id"]),
            disposition=p["disposition"],
            reasons=list(p.get("reasons") or []),
            score=float(p["score"]),
            formula_run_id=UUID(p["formula_run_id"]),
            id=UUID(p["id"]),
            created_at=_dt(p["created_at"]),
        )
    return p


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
                self._cache.setdefault(row["kind"], {})[row["id"]] = _decode(
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
