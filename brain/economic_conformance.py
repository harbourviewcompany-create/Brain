from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Iterable
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


class ConformanceVerdict(StrEnum):
    GO = "GO"
    HOLD = "HOLD"


class LifecycleState(StrEnum):
    DETECTED = "detected"
    HYPOTHESIZED = "hypothesized"
    SUPPORTED = "supported"
    ACTIVE = "active"
    DEGRADED = "degraded"
    SUSPENDED = "suspended"
    PROHIBITED = "prohibited"
    CLOSED = "closed"
    LOST = "lost"
    ABANDONED = "abandoned"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    ARCHIVED = "archived"
    AUTOMATED = "automated"
    DELEGATED = "delegated"
    KILLED = "killed"
    DEPLOYED = "deployed"
    RECONCILED = "reconciled"
    BUILD_CANDIDATE = "build_candidate"
    MATURED = "matured"


class CollectionMethod(StrEnum):
    PUBLIC_API = "public_api"
    LICENSED_API = "licensed_api"
    MANUAL_REVIEW = "manual_review"
    USER_PROVIDED = "user_provided"
    SCRAPE = "scrape"
    PII_COLLECTION = "pii_collection"
    PROHIBITED = "prohibited"


class SourceRightsClass(StrEnum):
    PUBLIC_SAFE = "public_safe"
    PUBLIC_TERMS_RESTRICTED = "public_terms_restricted"
    PERMISSIONED = "permissioned"
    PAID_LICENSED = "paid_licensed"
    SCRAPE_SENSITIVE = "scrape_sensitive"
    PII_SENSITIVE = "pii_sensitive"
    REGULATED_DATA = "regulated_data"
    PROHIBITED = "prohibited"


class OperatorDisposition(StrEnum):
    ACT_NOW = "act_now"
    VERIFY_FIRST = "verify_first"
    WATCH = "watch"
    KILL = "kill"
    ARCHIVE = "archive"
    AUTOMATE = "automate"
    DELEGATE = "delegate"
    NON_MONETIZABLE = "non_monetizable"


@dataclass(slots=True)
class AuditEvent:
    object_id: UUID
    object_type: str
    from_state: str
    to_state: str
    trigger: str
    evidence_refs: list[str]
    actor: str = "brain"
    formula_run_ref: str | None = None
    acceptance_test: str = "mod_008_015_atomic_conformance"
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ConformanceStore:
    objects: dict[str, dict[UUID, object]] = field(default_factory=dict)
    audit_log: list[AuditEvent] = field(default_factory=list)

    def put(self, kind: str, object_id: UUID, payload: object) -> object:
        self.objects.setdefault(kind, {})[object_id] = payload
        return payload

    def list(self, kind: str) -> list[object]:
        return list(self.objects.get(kind, {}).values())

    def append(self, event: AuditEvent) -> AuditEvent:
        self.audit_log.append(event)
        return event


class EconomicStateMachineService:
    """State transition service for economic lifecycles with fail-closed evidence gates."""

    allowed: dict[str, set[tuple[LifecycleState, LifecycleState]]] = {
        "pressure": {
            (LifecycleState.HYPOTHESIZED, LifecycleState.SUPPORTED),
            (LifecycleState.SUPPORTED, LifecycleState.ACTIVE),
            (LifecycleState.ACTIVE, LifecycleState.DEGRADED),
            (LifecycleState.DEGRADED, LifecycleState.INVALIDATED),
            (LifecycleState.ACTIVE, LifecycleState.EXPIRED),
        },
        "opportunity": {
            (LifecycleState.DETECTED, LifecycleState.SUPPORTED),
            (LifecycleState.SUPPORTED, LifecycleState.ACTIVE),
            (LifecycleState.ACTIVE, LifecycleState.ARCHIVED),
            (LifecycleState.ACTIVE, LifecycleState.AUTOMATED),
            (LifecycleState.ACTIVE, LifecycleState.DELEGATED),
            (LifecycleState.ACTIVE, LifecycleState.KILLED),
            (LifecycleState.ACTIVE, LifecycleState.EXPIRED),
        },
        "transaction": {
            (LifecycleState.DETECTED, LifecycleState.ACTIVE),
            (LifecycleState.ACTIVE, LifecycleState.CLOSED),
            (LifecycleState.ACTIVE, LifecycleState.LOST),
            (LifecycleState.ACTIVE, LifecycleState.ABANDONED),
        },
        "source": {
            (LifecycleState.HYPOTHESIZED, LifecycleState.SUPPORTED),
            (LifecycleState.SUPPORTED, LifecycleState.ACTIVE),
            (LifecycleState.ACTIVE, LifecycleState.DEGRADED),
            (LifecycleState.DEGRADED, LifecycleState.SUSPENDED),
            (LifecycleState.SUSPENDED, LifecycleState.PROHIBITED),
            (LifecycleState.ACTIVE, LifecycleState.PROHIBITED),
        },
        "capital": {
            (LifecycleState.SUPPORTED, LifecycleState.DEPLOYED),
            (LifecycleState.DEPLOYED, LifecycleState.RECONCILED),
        },
        "compounding": {
            (LifecycleState.HYPOTHESIZED, LifecycleState.SUPPORTED),
            (LifecycleState.SUPPORTED, LifecycleState.BUILD_CANDIDATE),
            (LifecycleState.BUILD_CANDIDATE, LifecycleState.MATURED),
            (LifecycleState.BUILD_CANDIDATE, LifecycleState.KILLED),
        },
    }

    def transition(
        self,
        store: ConformanceStore,
        *,
        machine: str,
        object_id: UUID,
        from_state: LifecycleState,
        to_state: LifecycleState,
        trigger: str,
        evidence_refs: list[str],
        valid_until: datetime | None = None,
        formula_run_ref: str | None = None,
    ) -> AuditEvent:
        if (from_state, to_state) not in self.allowed.get(machine, set()):
            raise ValueError(f"blocked_transition:{machine}:{from_state}->{to_state}")
        if not evidence_refs:
            raise ValueError("transition_requires_evidence")
        if to_state in {LifecycleState.ACTIVE, LifecycleState.SUPPORTED}:
            if valid_until is not None and valid_until <= utcnow():
                raise ValueError("transition_requires_time_valid_evidence")
        event = AuditEvent(
            object_id=object_id,
            object_type=machine,
            from_state=from_state.value,
            to_state=to_state.value,
            trigger=trigger,
            evidence_refs=evidence_refs,
            formula_run_ref=formula_run_ref,
        )
        return store.append(event)


@dataclass(slots=True)
class MoneyPathComparison:
    money_path_id: UUID
    expected_net_value: float
    time_to_cash_days: float
    required_capital: float
    risk: float
    repeatability: float
    compounding_value: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)

    def score(self) -> float:
        numerator = max(self.expected_net_value, 0.0) * (
            1.0 + self.repeatability + self.compounding_value
        )
        denominator = (
            1.0
            + max(self.time_to_cash_days, 0.0)
            + max(self.required_capital, 0.0)
            + max(self.risk, 0.0)
        )
        return numerator / denominator


@dataclass(slots=True)
class MoneyPathRanking:
    fastest: UUID
    highest_value: UUID
    lowest_capital: UUID
    lowest_risk: UUID
    most_repeatable: UUID
    most_compounding: UUID
    best_overall: UUID
    formula_run_ref: str
    id: UUID = field(default_factory=uuid4)


class MoneyPathComparisonService:
    def rank(self, paths: list[MoneyPathComparison]) -> MoneyPathRanking:
        if not paths:
            raise ValueError("money_path_comparison_requires_paths")
        if any(not path.evidence_refs for path in paths):
            raise ValueError("money_path_requires_evidence")
        return MoneyPathRanking(
            fastest=min(paths, key=lambda p: p.time_to_cash_days).money_path_id,
            highest_value=max(paths, key=lambda p: p.expected_net_value).money_path_id,
            lowest_capital=min(paths, key=lambda p: p.required_capital).money_path_id,
            lowest_risk=min(paths, key=lambda p: p.risk).money_path_id,
            most_repeatable=max(paths, key=lambda p: p.repeatability).money_path_id,
            most_compounding=max(paths, key=lambda p: p.compounding_value).money_path_id,
            best_overall=max(paths, key=lambda p: p.score()).money_path_id,
            formula_run_ref="money_path_atomic_rank_v1",
        )


@dataclass(slots=True)
class LiquidityPreference:
    counterparty_id: UUID
    preference_type: str
    value: str
    strength: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class CounterpartyInteraction:
    counterparty_id: UUID
    channel: str
    outcome: str
    response_hours: float | None
    evidence_refs: list[str]
    occurred_at: datetime = field(default_factory=utcnow)
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class CounterpartyNode:
    counterparty_id: UUID
    inferred_roles: list[str]
    verified_roles: list[str]
    liquidity_preferences: list[LiquidityPreference]
    response_history_weight: float
    stale_contact: bool
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class CounterpartyLiquidityService:
    def build_node(
        self,
        *,
        counterparty_id: UUID,
        preferences: list[LiquidityPreference],
        interactions: list[CounterpartyInteraction],
        role_evidence: dict[str, list[str]],
        stale_after_days: int = 90,
    ) -> CounterpartyNode:
        if not role_evidence:
            raise ValueError("role_inference_requires_evidence")
        if any(not pref.evidence_refs for pref in preferences):
            raise ValueError("liquidity_preference_requires_evidence")
        if any(not event.evidence_refs for event in interactions):
            raise ValueError("counterparty_interaction_requires_evidence")
        verified_roles = [role for role, evidence in role_evidence.items() if len(evidence) >= 2]
        successful = sum(1 for item in interactions if item.outcome == "response")
        response_weight = successful / max(len(interactions), 1)
        latest = max((item.occurred_at for item in interactions), default=utcnow())
        stale_contact = utcnow() - latest > timedelta(days=stale_after_days)
        evidence_refs = [ref for refs in role_evidence.values() for ref in refs]
        return CounterpartyNode(
            counterparty_id=counterparty_id,
            inferred_roles=list(role_evidence),
            verified_roles=verified_roles,
            liquidity_preferences=preferences,
            response_history_weight=response_weight,
            stale_contact=stale_contact,
            evidence_refs=evidence_refs,
        )


@dataclass(slots=True)
class OpportunityLifecycle:
    opportunity_id: UUID
    disposition: OperatorDisposition
    state: LifecycleState
    rationale: str
    evidence_refs: list[str]
    expires_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)


class OpportunityLifecycleService:
    def disposition_to_state(
        self,
        *,
        opportunity_id: UUID,
        disposition: OperatorDisposition,
        evidence_refs: list[str],
        rationale: str,
    ) -> OpportunityLifecycle:
        if not evidence_refs:
            raise ValueError("opportunity_disposition_requires_evidence")
        state_map = {
            OperatorDisposition.ACT_NOW: LifecycleState.ACTIVE,
            OperatorDisposition.VERIFY_FIRST: LifecycleState.SUPPORTED,
            OperatorDisposition.WATCH: LifecycleState.SUPPORTED,
            OperatorDisposition.KILL: LifecycleState.KILLED,
            OperatorDisposition.ARCHIVE: LifecycleState.ARCHIVED,
            OperatorDisposition.AUTOMATE: LifecycleState.AUTOMATED,
            OperatorDisposition.DELEGATE: LifecycleState.DELEGATED,
            OperatorDisposition.NON_MONETIZABLE: LifecycleState.KILLED,
        }
        return OpportunityLifecycle(
            opportunity_id=opportunity_id,
            disposition=disposition,
            state=state_map[disposition],
            rationale=rationale,
            evidence_refs=evidence_refs,
        )

    def expire_if_stale(self, lifecycle: OpportunityLifecycle, now: datetime | None = None) -> bool:
        if lifecycle.expires_at is None:
            return False
        return (now or utcnow()) >= lifecycle.expires_at


@dataclass(slots=True)
class TransactionClosure:
    transaction_id: UUID
    outcome: LifecycleState
    gross_revenue: float
    net_profit: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class TransactionLifecycleService:
    def close(
        self,
        transaction_id: UUID,
        gross: float,
        net: float,
        evidence_refs: list[str],
    ) -> TransactionClosure:
        if not evidence_refs:
            raise ValueError("transaction_close_requires_evidence")
        return TransactionClosure(transaction_id, LifecycleState.CLOSED, gross, net, evidence_refs)

    def loss(self, transaction_id: UUID, evidence_refs: list[str]) -> TransactionClosure:
        if not evidence_refs:
            raise ValueError("transaction_loss_requires_evidence")
        return TransactionClosure(transaction_id, LifecycleState.LOST, 0.0, 0.0, evidence_refs)

    def abandon(self, transaction_id: UUID, evidence_refs: list[str]) -> TransactionClosure:
        if not evidence_refs:
            raise ValueError("transaction_abandon_requires_evidence")
        return TransactionClosure(transaction_id, LifecycleState.ABANDONED, 0.0, 0.0, evidence_refs)


@dataclass(slots=True)
class SourceActivationPolicy:
    source_key: str
    rights_class: SourceRightsClass
    collection_method: CollectionMethod
    provenance_refs: list[str]
    jurisdiction: str
    permits_collection: bool
    permits_storage: bool
    permits_commercial_use: bool
    id: UUID = field(default_factory=uuid4)


class SourcePolicyService:
    def activation_verdict(self, policy: SourceActivationPolicy) -> ConformanceVerdict:
        if not policy.provenance_refs:
            return ConformanceVerdict.HOLD
        if policy.rights_class == SourceRightsClass.PROHIBITED:
            return ConformanceVerdict.HOLD
        if policy.collection_method in {CollectionMethod.PROHIBITED, CollectionMethod.PII_COLLECTION}:
            return ConformanceVerdict.HOLD
        if not (
            policy.permits_collection
            and policy.permits_storage
            and policy.permits_commercial_use
        ):
            return ConformanceVerdict.HOLD
        if policy.rights_class in {
            SourceRightsClass.SCRAPE_SENSITIVE,
            SourceRightsClass.PII_SENSITIVE,
            SourceRightsClass.REGULATED_DATA,
        }:
            return ConformanceVerdict.HOLD
        return ConformanceVerdict.GO


@dataclass(slots=True)
class JurisdictionCognition:
    jurisdiction: str
    currency: str
    languages: list[str]
    sanctions_review_required: bool
    brokerage_review_required: bool
    privacy_review_required: bool
    source_restrictions: list[str]
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class MovementChangeSignal:
    entity_id: UUID
    movement_type: str
    direction: str
    magnitude: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class MovementChangeDetector:
    def detect(
        self,
        *,
        entity_id: UUID,
        before: float,
        after: float,
        evidence_refs: list[str],
    ) -> MovementChangeSignal:
        if not evidence_refs:
            raise ValueError("movement_detection_requires_evidence")
        delta = after - before
        direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
        return MovementChangeSignal(
            entity_id=entity_id,
            movement_type="numeric_delta",
            direction=direction,
            magnitude=abs(delta),
            evidence_refs=evidence_refs,
        )


@dataclass(slots=True)
class ProfitEvent:
    transaction_id: UUID
    gross_revenue: float
    direct_cost: float
    operator_cost: float
    data_compute_cost: float
    currency: str
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)

    @property
    def net_profit(self) -> float:
        return self.gross_revenue - self.direct_cost - self.operator_cost - self.data_compute_cost


@dataclass(slots=True)
class NormalizedProfit:
    profit_event_id: UUID
    original_currency: str
    reporting_currency: str
    fx_rate: float
    gross_revenue: float
    net_profit: float
    id: UUID = field(default_factory=uuid4)


class ProfitNormalizationService:
    def normalize(
        self,
        event: ProfitEvent,
        *,
        reporting_currency: str,
        fx_rate: float,
    ) -> NormalizedProfit:
        if not event.evidence_refs:
            raise ValueError("profit_event_requires_evidence")
        if fx_rate <= 0:
            raise ValueError("fx_rate_must_be_positive")
        return NormalizedProfit(
            profit_event_id=event.id,
            original_currency=event.currency,
            reporting_currency=reporting_currency,
            fx_rate=fx_rate,
            gross_revenue=event.gross_revenue * fx_rate,
            net_profit=event.net_profit * fx_rate,
        )


@dataclass(slots=True)
class CausalAttributionChain:
    profit_event_id: UUID
    transaction_id: UUID
    opportunity_id: UUID
    money_path_id: UUID
    pressure_id: UUID
    signal_id: UUID
    observation_id: UUID
    source_key: str
    sensor_id: UUID
    action_id: UUID
    confidence: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class AttributionPromotionService:
    threshold = 0.7

    def promotion_verdict(self, chain: CausalAttributionChain) -> ConformanceVerdict:
        required = [
            chain.profit_event_id,
            chain.transaction_id,
            chain.opportunity_id,
            chain.money_path_id,
            chain.pressure_id,
            chain.signal_id,
            chain.observation_id,
            chain.source_key,
            chain.sensor_id,
            chain.action_id,
        ]
        if any(item is None or item == "" for item in required):
            return ConformanceVerdict.HOLD
        if not chain.evidence_refs:
            return ConformanceVerdict.HOLD
        if chain.confidence < self.threshold:
            return ConformanceVerdict.HOLD
        return ConformanceVerdict.GO


@dataclass(slots=True)
class CapitalDeployment:
    capital_state_id: UUID
    opportunity_id: UUID
    amount: float
    currency: str
    evidence_refs: list[str]
    state: LifecycleState = LifecycleState.DEPLOYED
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class CapitalReconciliation:
    deployment_id: UUID
    returned_amount: float
    net_profit: float
    evidence_refs: list[str]
    state: LifecycleState = LifecycleState.RECONCILED
    id: UUID = field(default_factory=uuid4)


class CapitalLifecycleService:
    def deploy(
        self,
        *,
        capital_state_id: UUID,
        opportunity_id: UUID,
        amount: float,
        currency: str,
        evidence_refs: list[str],
    ) -> CapitalDeployment:
        if amount <= 0:
            raise ValueError("capital_deployment_requires_positive_amount")
        if not evidence_refs:
            raise ValueError("capital_deployment_requires_evidence")
        return CapitalDeployment(capital_state_id, opportunity_id, amount, currency, evidence_refs)

    def reconcile(
        self,
        deployment: CapitalDeployment,
        *,
        returned_amount: float,
        net_profit: float,
        evidence_refs: list[str],
    ) -> CapitalReconciliation:
        if not evidence_refs:
            raise ValueError("capital_reconciliation_requires_evidence")
        return CapitalReconciliation(deployment.id, returned_amount, net_profit, evidence_refs)


@dataclass(slots=True)
class RepeatedTransactionPattern:
    pattern_key: str
    transaction_ids: list[UUID]
    payer_ids: list[UUID]
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class StrategicAssetScore:
    asset_key: str
    evidence_count: int
    payer_count: int
    expected_value: float
    resource_estimate: float
    score: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class BuildCandidate:
    candidate_type: str
    pattern_id: UUID
    repeated_evidence: bool
    payer_evidence: bool
    resource_estimate: float
    evidence_refs: list[str]
    state: LifecycleState = LifecycleState.BUILD_CANDIDATE
    id: UUID = field(default_factory=uuid4)


class CompoundingEmergenceService:
    def detect_repeated_pattern(
        self,
        *,
        pattern_key: str,
        transaction_ids: list[UUID],
        payer_ids: list[UUID],
        evidence_refs: list[str],
    ) -> RepeatedTransactionPattern:
        if len(transaction_ids) < 2:
            raise ValueError("repeated_transaction_requires_multiple_transactions")
        if not payer_ids:
            raise ValueError("repeated_transaction_requires_payer_evidence")
        if not evidence_refs:
            raise ValueError("repeated_transaction_requires_evidence")
        return RepeatedTransactionPattern(pattern_key, transaction_ids, payer_ids, evidence_refs)

    def score_asset(
        self,
        *,
        asset_key: str,
        evidence_count: int,
        payer_count: int,
        expected_value: float,
        resource_estimate: float,
        evidence_refs: list[str],
    ) -> StrategicAssetScore:
        if resource_estimate <= 0:
            raise ValueError("strategic_asset_requires_resource_estimate")
        if evidence_count <= 0 or payer_count <= 0 or not evidence_refs:
            raise ValueError("strategic_asset_requires_evidence_and_payers")
        score = (expected_value * evidence_count * payer_count) / resource_estimate
        return StrategicAssetScore(
            asset_key,
            evidence_count,
            payer_count,
            expected_value,
            resource_estimate,
            score,
            evidence_refs,
        )

    def create_build_candidate(
        self,
        *,
        candidate_type: str,
        pattern: RepeatedTransactionPattern,
        resource_estimate: float,
    ) -> BuildCandidate:
        if resource_estimate <= 0:
            raise ValueError("build_candidate_requires_resource_estimate")
        return BuildCandidate(
            candidate_type=candidate_type,
            pattern_id=pattern.id,
            repeated_evidence=len(pattern.transaction_ids) >= 2,
            payer_evidence=bool(pattern.payer_ids),
            resource_estimate=resource_estimate,
            evidence_refs=pattern.evidence_refs,
        )


@dataclass(slots=True)
class OperatorSurfaceRequirement:
    surface_id: str
    panels: list[str]
    approval_gates: list[str]
    evidence_refs: list[str]


class OperatorSurfaceConformanceService:
    required_panels = {
        "pressure_map",
        "money_path_explorer",
        "liquidity_graph",
        "kill_board",
        "transaction_pipeline",
        "source_mesh",
        "profit_capital_ledger",
        "compounding_board",
    }

    def verdict(self, surface: OperatorSurfaceRequirement) -> ConformanceVerdict:
        if not self.required_panels.issubset(set(surface.panels)):
            return ConformanceVerdict.HOLD
        if "external_action_approval" not in surface.approval_gates:
            return ConformanceVerdict.HOLD
        if not surface.evidence_refs:
            return ConformanceVerdict.HOLD
        return ConformanceVerdict.GO


@dataclass(slots=True)
class DeterministicFixtureFamily:
    fixture_id: str
    scenarios: list[str]
    expected_transitions: list[str]
    expected_negative_gates: list[str]
    expected_operator_panels: list[str]
    evidence_refs: list[str]


class FixtureUniverseValidator:
    required_scenarios = {
        "expansion",
        "distress",
        "supply_gap",
        "false_positive",
        "equipment",
        "hiring",
        "facility_permit",
        "regulatory_change",
        "fragmented_market",
        "active_buyer",
        "latent_buyer",
        "distressed_seller",
        "conflicting_role",
        "unreachable_decision_maker",
        "crowded_obvious",
        "inaccessible_payer",
        "zero_payment",
        "micro_cash",
        "strategic_mandate",
        "success_fee_intro",
        "exclusive_mandate",
        "regulated_brokerage",
        "public_registry",
        "paid_licensed",
        "scrape_sensitive",
        "pii_sensitive",
        "prohibited_source",
        "profitable_deal",
        "high_revenue_low_profit",
        "ambiguous_attribution",
        "multi_currency",
        "repeated_buyer_matching",
        "repeated_market_entry",
        "one_off_non_repeatable",
    }

    def validate(self, fixture: DeterministicFixtureFamily) -> ConformanceVerdict:
        if not self.required_scenarios.issubset(set(fixture.scenarios)):
            return ConformanceVerdict.HOLD
        if not fixture.expected_negative_gates:
            return ConformanceVerdict.HOLD
        if not fixture.expected_transitions:
            return ConformanceVerdict.HOLD
        if not fixture.evidence_refs:
            return ConformanceVerdict.HOLD
        return ConformanceVerdict.GO


def summarize_mod_008_015_verdict(statuses: Iterable[ConformanceVerdict]) -> ConformanceVerdict:
    return ConformanceVerdict.GO if all(status == ConformanceVerdict.GO for status in statuses) else ConformanceVerdict.HOLD
