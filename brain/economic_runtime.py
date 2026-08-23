from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from math import exp
from typing import Any, Protocol
from uuid import UUID, uuid4

from .economic import (
    AsymmetryType,
    CapitalState,
    CommercialDisposition,
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
from .formulas import FormulaRunResult, default_formula_registry


def utcnow() -> datetime:
    return datetime.now(UTC)


class EconomicObjectState(StrEnum):
    HYPOTHESIZED = "hypothesized"
    SUPPORTED = "supported"
    ACTIVE = "active"
    EASING = "easing"
    RESOLVED = "resolved"
    INVALIDATED = "invalidated"
    GENERATED = "generated"
    VERIFIED = "verified"
    QUALIFIED = "qualified"
    REJECTED = "rejected"
    EXPIRED = "expired"
    DISCOVERED = "discovered"
    REACHABLE = "reachable"
    DORMANT = "dormant"
    BLOCKED = "blocked"
    DETECTED = "detected"
    VERIFYING = "verifying"
    PROTECTED = "protected"
    APPROVED = "approved"
    CONTACTED = "contacted"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"
    ABANDONED = "abandoned"
    PROVISIONAL = "provisional"
    ACCEPTED = "accepted"
    DISPUTED = "disputed"
    REVISED = "revised"
    OBSERVED = "observed"
    VALIDATED = "validated"
    BUILD_CANDIDATE = "build_candidate"
    OPERATING = "operating"


class SourceRightsClass(StrEnum):
    PUBLIC_SAFE = "public_safe"
    PUBLIC_TERMS_RESTRICTED = "public_terms_restricted"
    PERMISSIONED = "permissioned"
    PAID_LICENSED = "paid_licensed"
    SCRAPE_SENSITIVE = "scrape_sensitive"
    PII_SENSITIVE = "pii_sensitive"
    REGULATED_DATA = "regulated_data"
    PROHIBITED = "prohibited"


class SourcePlaneType(StrEnum):
    CORPORATE = "corporate_registries"
    LICENSING = "licensing"
    REGULATORY = "regulators"
    LEGAL = "legal_courts"
    FINANCIAL = "financial"
    EMPLOYMENT = "employment"
    REAL_ESTATE = "real_estate"
    TRADE = "trade_customs"
    MARKETPLACE = "marketplaces"
    LOCAL_GOVERNMENT = "local_government"
    WEB_CHANGE = "web_changes"
    SOCIAL = "social_professional"
    SCIENTIFIC = "scientific_technical"
    CONSUMER_DEMAND = "consumer_demand"
    INFRASTRUCTURE = "infrastructure"
    GEOSPATIAL = "geospatial"
    PROCUREMENT = "procurement"
    EVENTS = "events"
    DISTRESS = "distress"
    PUBLIC_DOCUMENTS = "overlooked_public_documents"


@dataclass(slots=True)
class TransitionRecord:
    object_id: UUID
    object_type: str
    from_state: str
    to_state: str
    trigger: str
    actor: str = "brain"
    evidence_ids: list[UUID] = field(default_factory=list)
    formula_run_ids: list[UUID] = field(default_factory=list)
    acceptance_test: str = "economic_state_machine"
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class SourceRightsProfile:
    source_key: str
    rights_class: SourceRightsClass
    jurisdiction: str
    permitted_collection: bool
    permitted_storage: bool
    permitted_commercial_use: bool
    permitted_redistribution: bool = False
    retention_days: int | None = None
    notes: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    reviewed_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class SourcePlane:
    source_key: str
    plane: SourcePlaneType
    jurisdiction: str
    rights_profile_id: UUID
    refresh_seconds: int
    reliability: float
    estimated_cost: float = 0.0
    signal_yield: float = 0.0
    opportunity_yield: float = 0.0
    attributed_net_profit: float = 0.0
    status: str = "candidate"
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)

    @property
    def roi(self) -> float:
        cost = max(self.estimated_cost, 0.01)
        return self.attributed_net_profit / cost


@dataclass(slots=True)
class JurisdictionProfile:
    code: str
    currency: str
    languages: list[str]
    sanctions_review_required: bool = False
    brokerage_review_required: bool = False
    data_restrictions: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class KillDecision:
    opportunity_id: UUID
    disposition: CommercialDisposition
    reasons: list[str]
    score: float
    formula_run_id: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class OpportunityPortfolio:
    act_now: list[UUID] = field(default_factory=list)
    verify_first: list[UUID] = field(default_factory=list)
    watch: list[UUID] = field(default_factory=list)
    suppressed: list[UUID] = field(default_factory=list)
    generated_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class FeeControl:
    transaction_id: UUID
    mandate: bool = False
    introduction_logged: bool = False
    fee_agreement: bool = False
    exclusivity: bool = False
    origination_evidence: bool = False
    jurisdiction_reviewed: bool = False
    id: UUID = field(default_factory=uuid4)

    def sufficient(self, *, fee_sensitive: bool) -> bool:
        if not self.jurisdiction_reviewed:
            return False
        if not fee_sensitive:
            return True
        return self.introduction_logged and self.origination_evidence and (
            self.fee_agreement or self.mandate
        )


@dataclass(slots=True)
class EconomicROI:
    object_key: str
    gross_revenue: float
    net_profit: float
    total_cost: float
    roi: float
    attribution_confidence: float
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class CompoundingAsset:
    kind: str
    key: str
    evidence_count: int
    payer_count: int
    expected_value: float
    resource_estimate: float
    status: EconomicObjectState = EconomicObjectState.OBSERVED
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class BusinessModelHypothesis:
    problem_pattern: str
    solution_pattern: str
    payer_pattern: str
    occurrences: int
    unique_payers: int
    expected_net_value: float
    resource_estimate: float
    status: EconomicObjectState = EconomicObjectState.OBSERVED
    id: UUID = field(default_factory=uuid4)


class EconomicStore(Protocol):
    def put(self, kind: str, object_id: UUID, payload: Any) -> None: ...
    def get(self, kind: str, object_id: UUID) -> Any | None: ...
    def list(self, kind: str) -> list[Any]: ...
    def append_transition(self, transition: TransitionRecord) -> None: ...
    def transitions(self, object_id: UUID | None = None) -> list[TransitionRecord]: ...
    def save_formula_run(self, run: FormulaRunResult) -> None: ...


@dataclass
class InMemoryEconomicStore:
    objects: dict[str, dict[UUID, Any]] = field(default_factory=dict)
    transition_log: list[TransitionRecord] = field(default_factory=list)
    formula_runs: dict[UUID, FormulaRunResult] = field(default_factory=dict)

    def put(self, kind: str, object_id: UUID, payload: Any) -> None:
        self.objects.setdefault(kind, {})[object_id] = payload

    def get(self, kind: str, object_id: UUID) -> Any | None:
        return self.objects.get(kind, {}).get(object_id)

    def list(self, kind: str) -> list[Any]:
        return list(self.objects.get(kind, {}).values())

    def append_transition(self, transition: TransitionRecord) -> None:
        self.transition_log.append(transition)

    def transitions(self, object_id: UUID | None = None) -> list[TransitionRecord]:
        if object_id is None:
            return list(self.transition_log)
        return [t for t in self.transition_log if t.object_id == object_id]

    def save_formula_run(self, run: FormulaRunResult) -> None:
        self.formula_runs[run.run_id] = run


class EconomicStateMachine:
    ALLOWED: dict[str, dict[str, set[str]]] = {
        "pressure": {
            "hypothesized": {"supported", "invalidated"},
            "supported": {"active", "invalidated"},
            "active": {"easing", "resolved", "invalidated"},
            "easing": {"active", "resolved", "invalidated"},
        },
        "money_path": {
            "generated": {"verified", "rejected", "expired"},
            "verified": {"qualified", "rejected", "expired"},
            "qualified": {"expired", "rejected"},
        },
        "counterparty": {
            "discovered": {"verified", "blocked"},
            "verified": {"reachable", "dormant", "blocked"},
            "reachable": {"active", "dormant", "blocked"},
            "active": {"dormant", "blocked"},
            "dormant": {"reachable", "blocked"},
        },
        "transaction": {
            "detected": {"qualified", "abandoned"},
            "qualified": {"protected", "abandoned"},
            "protected": {"approved", "abandoned"},
            "approved": {"contacted", "abandoned"},
            "contacted": {"negotiation", "lost", "abandoned"},
            "negotiation": {"won", "lost", "abandoned"},
        },
        "attribution": {
            "provisional": {"supported", "disputed"},
            "supported": {"accepted", "disputed"},
            "disputed": {"revised"},
            "revised": {"supported", "accepted", "disputed"},
        },
        "compounding": {
            "observed": {"hypothesized", "rejected"},
            "hypothesized": {"validated", "rejected"},
            "validated": {"build_candidate", "rejected"},
            "build_candidate": {"approved", "rejected"},
            "approved": {"operating"},
        },
    }

    def transition(
        self,
        store: EconomicStore,
        *,
        machine: str,
        object_id: UUID,
        from_state: str,
        to_state: str,
        trigger: str,
        evidence_ids: list[UUID] | None = None,
        formula_run_ids: list[UUID] | None = None,
        actor: str = "brain",
    ) -> TransitionRecord:
        allowed = self.ALLOWED.get(machine, {}).get(from_state, set())
        if to_state not in allowed:
            raise ValueError(f"blocked_transition:{machine}:{from_state}->{to_state}")
        record = TransitionRecord(
            object_id=object_id,
            object_type=machine,
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            actor=actor,
            evidence_ids=list(evidence_ids or []),
            formula_run_ids=list(formula_run_ids or []),
        )
        store.append_transition(record)
        return record


class EconomicRuntime:
    """Persistent orchestration for MOD-008 through MOD-015."""

    def __init__(self, store: EconomicStore | None = None) -> None:
        self.store = store or InMemoryEconomicStore()
        self.formulas = default_formula_registry()
        self.states = EconomicStateMachine()

    # MOD-008
    def detect_asymmetry(
        self,
        entity_id: UUID,
        kind: AsymmetryType,
        magnitude: float,
        confidence: float,
        evidence_ids: list[UUID],
    ) -> EconomicAsymmetry:
        if not evidence_ids:
            raise ValueError("asymmetry_requires_evidence")
        obj = EconomicAsymmetry(entity_id, kind, magnitude, confidence, evidence_ids)
        self.store.put("asymmetry", obj.id, obj)
        return obj

    def infer_pressure(
        self,
        entity_id: UUID,
        kind: PressureType,
        magnitude: float,
        confidence: float,
        evidence_ids: list[UUID],
        *,
        half_life_days: float = 30.0,
    ) -> PressureEvent:
        if not evidence_ids:
            raise ValueError("pressure_requires_evidence")
        valid_until = utcnow() + timedelta(days=max(half_life_days * 4, 1.0))
        obj = PressureEvent(
            entity_id=entity_id,
            kind=kind,
            magnitude=magnitude,
            confidence=confidence,
            evidence_ids=evidence_ids,
            valid_until=valid_until,
            metadata={"state": "hypothesized", "half_life_days": half_life_days},
        )
        self.store.put("pressure", obj.id, obj)
        return obj

    def pressure_effective_magnitude(self, pressure: PressureEvent, at: datetime | None = None) -> float:
        at = at or utcnow()
        age_days = max((at - pressure.created_at).total_seconds() / 86400.0, 0.0)
        half_life = max(float(pressure.metadata.get("half_life_days", 30.0)), 0.01)
        return pressure.magnitude * exp(-0.69314718056 * age_days / half_life)

    # MOD-009
    def generate_affordances(
        self,
        entity_id: UUID,
        pressure_types: list[PressureType],
        evidence_ids: list[UUID],
    ) -> list[EconomicAffordance]:
        mapping: dict[PressureType, tuple[MoneyVerb, ...]] = {
            PressureType.CASH: (MoneyVerb.BROKER, MoneyVerb.LIQUIDATE, MoneyVerb.FINANCE),
            PressureType.INVENTORY: (MoneyVerb.SELL, MoneyVerb.BROKER, MoneyVerb.RESELL),
            PressureType.HIRING: (MoneyVerb.RECRUIT, MoneyVerb.REFER),
            PressureType.COMPLIANCE: (MoneyVerb.ADVISE, MoneyVerb.VERIFY, MoneyVerb.CERTIFY),
            PressureType.EXPANSION: (MoneyVerb.SOURCE, MoneyVerb.RECRUIT, MoneyVerb.INTRODUCE),
            PressureType.SUPPLY: (MoneyVerb.SOURCE, MoneyVerb.MATCH, MoneyVerb.AGGREGATE),
            PressureType.DEMAND: (MoneyVerb.SELL, MoneyVerb.MATCH, MoneyVerb.BUILD),
            PressureType.EXIT: (MoneyVerb.ACQUIRE, MoneyVerb.BROKER, MoneyVerb.LIQUIDATE),
        }
        verbs: list[MoneyVerb] = []
        for pressure in pressure_types:
            verbs.extend(mapping.get(pressure, (MoneyVerb.MONITOR, MoneyVerb.VERIFY)))
        result = []
        for verb in dict.fromkeys(verbs):
            obj = EconomicAffordance(
                entity_id=entity_id,
                verb=verb,
                rationale=f"{verb.value} is an economic affordance of {','.join(p.value for p in pressure_types)}",
                confidence=0.65,
                evidence_ids=evidence_ids,
            )
            self.store.put("affordance", obj.id, obj)
            result.append(obj)
        return result

    def generate_money_path(
        self,
        *,
        affordance: EconomicAffordance,
        payment_model: PaymentModel,
        buyer_entity_id: UUID | None,
        gross_value: float,
        net_value: float,
        time_to_cash_days: float,
        conversion_probability: float,
        collection_risk: float = 0.0,
        fee_protection_required: bool = False,
    ) -> MoneyPath:
        obj = MoneyPath(
            verb=affordance.verb,
            payment_model=payment_model,
            buyer_entity_id=buyer_entity_id,
            expected_gross_value=gross_value,
            expected_net_value=net_value,
            time_to_cash_days=time_to_cash_days,
            conversion_probability=conversion_probability,
            collection_risk=collection_risk,
            fee_protection_required=fee_protection_required,
            metadata={"state": "generated", "affordance_id": str(affordance.id)},
        )
        self.store.put("money_path", obj.id, obj)
        return obj

    def qualify_money_path(self, path_id: UUID, *, payer_verified: bool) -> MoneyPath:
        path = self._required("money_path", path_id)
        state = str(path.metadata.get("state", "generated"))
        if state == "generated":
            self.states.transition(
                self.store,
                machine="money_path",
                object_id=path.id,
                from_state="generated",
                to_state="verified",
                trigger="payer_check",
            )
            state = "verified"
        if not payer_verified or path.buyer_entity_id is None:
            raise ValueError("money_path_requires_verified_payer")
        self.states.transition(
            self.store,
            machine="money_path",
            object_id=path.id,
            from_state=state,
            to_state="qualified",
            trigger="payer_and_payment_mechanism_verified",
        )
        path.metadata["state"] = "qualified"
        self.store.put("money_path", path.id, path)
        return path

    # MOD-010
    def upsert_counterparty(self, profile: CounterpartyProfile, *, verified: bool = False) -> CounterpartyProfile:
        profile.metadata["state"] = "verified" if verified else profile.metadata.get("state", "discovered")
        self.store.put("counterparty", profile.id, profile)
        return profile

    def ranked_counterparties(
        self,
        role: CounterpartyRole,
        *,
        minimum_budget: float = 0.0,
        limit: int = 10,
    ) -> list[tuple[CounterpartyProfile, float, list[str]]]:
        ranked = []
        for profile in self.store.list("counterparty"):
            if role not in profile.roles:
                continue
            budget = profile.budget_estimate or 0.0
            if budget < minimum_budget:
                continue
            score = (
                0.30 * profile.trust
                + 0.30 * profile.reachability
                + 0.25 * profile.decision_authority
                + 0.15 * profile.urgency
            )
            reasons = [
                f"role={role.value}",
                f"trust={profile.trust:.2f}",
                f"reachability={profile.reachability:.2f}",
                f"decision_authority={profile.decision_authority:.2f}",
            ]
            ranked.append((profile, score, reasons))
        return sorted(ranked, key=lambda item: item[1], reverse=True)[:limit]

    # MOD-011
    def register_opportunity(self, opportunity: EconomicOpportunity) -> FormulaRunResult:
        run = self.formulas.evaluate(
            "economic_opportunity_priority",
            {
                "net_value": opportunity.net_value,
                "conversion_probability": opportunity.conversion_probability,
                "urgency": opportunity.urgency,
                "access_advantage": opportunity.access_advantage,
                "evidence_confidence": opportunity.evidence_confidence,
                "repeatability": opportunity.repeatability,
                "strategic_compounding_value": opportunity.strategic_compounding_value,
                "required_capital": opportunity.required_capital,
                "required_operator_hours": opportunity.required_operator_hours,
                "legal_reputation_risk": opportunity.legal_reputation_risk,
                "operational_complexity": opportunity.operational_complexity,
                "time_decay": opportunity.time_decay,
            },
            owner_object_id=str(opportunity.id),
            owner_object_type="EconomicOpportunity",
        )
        opportunity.metadata["formula_run_id"] = str(run.run_id)
        opportunity.metadata["score"] = run.output
        self.store.save_formula_run(run)
        self.store.put("opportunity", opportunity.id, opportunity)
        return run

    def kill_review(self, opportunity_id: UUID) -> KillDecision:
        opportunity = self._required("opportunity", opportunity_id)
        reasons: list[str] = []
        paths = [self.store.get("money_path", path_id) for path_id in opportunity.money_path_ids]
        qualified_paths = [p for p in paths if p and p.metadata.get("state") == "qualified"]
        if not qualified_paths:
            reasons.append("no_qualified_payer_payment_path")
        if opportunity.evidence_confidence < 0.5:
            reasons.append("weak_evidence")
        if opportunity.access_advantage < 0.25:
            reasons.append("weak_access")
        if opportunity.legal_reputation_risk >= 0.8:
            reasons.append("excessive_legal_reputation_risk")
        if opportunity.required_capital > max(opportunity.net_value, 0.0):
            reasons.append("capital_exceeds_expected_net_value")
        score = float(opportunity.metadata.get("score", opportunity.score()))
        if reasons:
            disposition = CommercialDisposition.KILL
        elif opportunity.evidence_confidence < 0.75:
            disposition = CommercialDisposition.VERIFY_FIRST
        elif opportunity.strategic_compounding_value >= 0.85:
            disposition = CommercialDisposition.BUILD_AS_ASSET
        elif opportunity.urgency >= 0.7:
            disposition = CommercialDisposition.ACT_NOW
        else:
            disposition = CommercialDisposition.WATCH
        run_id = UUID(str(opportunity.metadata["formula_run_id"]))
        decision = KillDecision(opportunity.id, disposition, reasons, score, run_id)
        self.store.put("kill_decision", decision.id, decision)
        return decision

    def portfolio(self, *, act_now_limit: int = 3, verify_limit: int = 7, watch_limit: int = 20) -> OpportunityPortfolio:
        decisions = sorted(self.store.list("kill_decision"), key=lambda d: d.score, reverse=True)
        portfolio = OpportunityPortfolio()
        for decision in decisions:
            if decision.disposition is CommercialDisposition.ACT_NOW and len(portfolio.act_now) < act_now_limit:
                portfolio.act_now.append(decision.opportunity_id)
            elif decision.disposition is CommercialDisposition.VERIFY_FIRST and len(portfolio.verify_first) < verify_limit:
                portfolio.verify_first.append(decision.opportunity_id)
            elif decision.disposition in {CommercialDisposition.WATCH, CommercialDisposition.BUILD_AS_ASSET} and len(portfolio.watch) < watch_limit:
                portfolio.watch.append(decision.opportunity_id)
            else:
                portfolio.suppressed.append(decision.opportunity_id)
        return portfolio

    # MOD-012
    def register_transaction(self, transaction: Transaction) -> Transaction:
        transaction.metadata.setdefault("state", "detected")
        transaction.metadata.setdefault("approval", "pending")
        self.store.put("transaction", transaction.id, transaction)
        return transaction

    def set_fee_control(self, control: FeeControl) -> FeeControl:
        self.store.put("fee_control", control.id, control)
        return control

    def approve_transaction_action(self, transaction_id: UUID, *, operator_approved: bool) -> Transaction:
        transaction = self._required("transaction", transaction_id)
        controls = [c for c in self.store.list("fee_control") if c.transaction_id == transaction_id]
        control = controls[-1] if controls else None
        fee_sensitive = transaction.expected_revenue > 0
        if control is None or not control.sufficient(fee_sensitive=fee_sensitive):
            raise ValueError("transaction_hold:insufficient_fee_or_jurisdiction_control")
        if not operator_approved:
            raise ValueError("transaction_hold:operator_approval_required")
        transaction.metadata["approval"] = "approved"
        transaction.metadata["state"] = "approved"
        transaction.status = "approved"
        self.store.put("transaction", transaction.id, transaction)
        return transaction

    # MOD-013
    def register_source_rights(self, profile: SourceRightsProfile) -> SourceRightsProfile:
        if profile.rights_class is SourceRightsClass.PROHIBITED:
            profile.permitted_collection = False
            profile.permitted_storage = False
            profile.permitted_commercial_use = False
        self.store.put("source_rights", profile.id, profile)
        return profile

    def activate_source_plane(self, source: SourcePlane) -> SourcePlane:
        rights = self._required("source_rights", source.rights_profile_id)
        if not rights.permitted_collection:
            raise ValueError("source_hold:collection_not_permitted")
        if not rights.permitted_storage:
            raise ValueError("source_hold:storage_not_permitted")
        if rights.rights_class in {
            SourceRightsClass.PUBLIC_TERMS_RESTRICTED,
            SourceRightsClass.SCRAPE_SENSITIVE,
            SourceRightsClass.PII_SENSITIVE,
            SourceRightsClass.REGULATED_DATA,
        } and not rights.notes:
            raise ValueError("source_hold:sensitive_source_requires_review_notes")
        source.status = "active"
        self.store.put("source_plane", source.id, source)
        return source

    # MOD-014
    def attribute_revenue(self, attribution: RevenueAttribution, *, total_external_cost: float = 0.0) -> EconomicROI:
        self.store.put("revenue_attribution", attribution.id, attribution)
        cost = attribution.data_compute_cost + total_external_cost
        roi = (attribution.net_profit - cost) / max(cost, 1.0)
        record = EconomicROI(
            object_key=f"opportunity:{attribution.opportunity_id}",
            gross_revenue=attribution.gross_revenue,
            net_profit=attribution.net_profit,
            total_cost=cost,
            roi=roi,
            attribution_confidence=attribution.attribution_confidence,
        )
        self.store.put("economic_roi", record.id, record)
        return record

    def can_major_learn(self, attribution_confidence: float, threshold: float = 0.7) -> bool:
        return attribution_confidence >= threshold

    # MOD-015
    def detect_compounding_asset(
        self,
        *,
        kind: str,
        key: str,
        evidence_count: int,
        payer_count: int,
        expected_value: float,
        resource_estimate: float,
    ) -> CompoundingAsset:
        asset = CompoundingAsset(kind, key, evidence_count, payer_count, expected_value, resource_estimate)
        if evidence_count >= 3 and payer_count >= 2:
            asset.status = EconomicObjectState.VALIDATED
        self.store.put("compounding_asset", asset.id, asset)
        return asset

    def business_model_hypothesis(
        self,
        *,
        problem_pattern: str,
        solution_pattern: str,
        payer_pattern: str,
        occurrences: int,
        unique_payers: int,
        expected_net_value: float,
        resource_estimate: float,
    ) -> BusinessModelHypothesis:
        hypothesis = BusinessModelHypothesis(
            problem_pattern,
            solution_pattern,
            payer_pattern,
            occurrences,
            unique_payers,
            expected_net_value,
            resource_estimate,
        )
        if occurrences >= 3 and unique_payers >= 2 and expected_net_value > resource_estimate:
            hypothesis.status = EconomicObjectState.BUILD_CANDIDATE
        self.store.put("business_model", hypothesis.id, hypothesis)
        return hypothesis

    def operator_snapshot(self) -> dict[str, Any]:
        portfolio = self.portfolio()
        sources = self.store.list("source_plane")
        return {
            "act_now": [str(x) for x in portfolio.act_now],
            "verify_first": [str(x) for x in portfolio.verify_first],
            "watch": [str(x) for x in portfolio.watch],
            "suppressed_count": len(portfolio.suppressed),
            "active_pressures": len([
                p for p in self.store.list("pressure")
                if p.metadata.get("state") not in {"resolved", "invalidated"}
            ]),
            "qualified_money_paths": len([
                p for p in self.store.list("money_path") if p.metadata.get("state") == "qualified"
            ]),
            "active_sources": len([s for s in sources if s.status == "active"]),
            "source_roi": sorted(
                ({"source_key": s.source_key, "roi": s.roi} for s in sources),
                key=lambda row: row["roi"],
                reverse=True,
            ),
            "transactions": [
                {
                    "id": str(t.id),
                    "status": t.status,
                    "expected_revenue": t.expected_revenue,
                    "expected_profit": t.expected_profit,
                    "fee_protected": t.fee_protected,
                }
                for t in self.store.list("transaction")
            ],
            "compounding_assets": [
                {"id": str(a.id), "kind": a.kind, "key": a.key, "status": str(a.status)}
                for a in self.store.list("compounding_asset")
            ],
        }

    def _required(self, kind: str, object_id: UUID) -> Any:
        value = self.store.get(kind, object_id)
        if value is None:
            raise KeyError(f"{kind}_not_found:{object_id}")
        return value
