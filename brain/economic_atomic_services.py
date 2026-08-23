from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Iterable, Protocol
from uuid import UUID, uuid4

from .economic_conformance import (
    AttributionPromotionService,
    BuildCandidate,
    CausalAttributionChain,
    CollectionMethod,
    CompoundingEmergenceService,
    ConformanceVerdict,
    CounterpartyInteraction,
    CounterpartyLiquidityService,
    LifecycleState,
    LiquidityPreference,
    MoneyPathComparison,
    MoneyPathComparisonService,
    OperatorDisposition,
    OpportunityLifecycle,
    OpportunityLifecycleService,
    ProfitEvent,
    ProfitNormalizationService,
    SourceActivationPolicy,
    SourcePolicyService,
    SourceRightsClass,
    TransactionClosure,
    TransactionLifecycleService,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class EconomicObjectStore(Protocol):
    def put(self, kind: str, object_id: UUID, payload: object) -> object | None: ...
    def list(self, kind: str) -> list[object]: ...


@dataclass(slots=True)
class EconomicAsymmetryEvidence:
    asymmetry_type: str
    indicators: dict[str, float]
    evidence_refs: list[str]
    magnitude: float
    confidence: float
    id: UUID = field(default_factory=uuid4)


class AsymmetryDetectionService:
    def detect(self, *, asymmetry_type: str, indicators: dict[str, float], evidence_refs: list[str]) -> EconomicAsymmetryEvidence:
        if not evidence_refs:
            raise ValueError("asymmetry_requires_evidence")
        if not indicators:
            raise ValueError("asymmetry_requires_indicators")
        bounded = [min(max(float(value), 0.0), 1.0) for value in indicators.values()]
        magnitude = sum(bounded) / len(bounded)
        confidence = min(1.0, len(evidence_refs) / 3.0) * (0.5 + 0.5 * magnitude)
        return EconomicAsymmetryEvidence(asymmetry_type, dict(indicators), list(evidence_refs), magnitude, confidence)


@dataclass(slots=True)
class InferredPressure:
    pressure_type: str
    magnitude: float
    confidence: float
    direction: str
    evidence_refs: list[str]
    valid_until: datetime
    id: UUID = field(default_factory=uuid4)


class PressureInferenceService:
    def infer(
        self,
        *,
        pressure_type: str,
        signal_strengths: Iterable[float],
        evidence_refs: list[str],
        direction: str,
        ttl_days: int = 30,
    ) -> InferredPressure:
        values = [min(max(float(value), 0.0), 1.0) for value in signal_strengths]
        if not values or not evidence_refs:
            raise ValueError("pressure_inference_requires_signals_and_evidence")
        magnitude = sum(values) / len(values)
        evidence_factor = min(1.0, len(evidence_refs) / max(len(values), 1))
        confidence = min(1.0, 0.6 * magnitude + 0.4 * evidence_factor)
        return InferredPressure(
            pressure_type=pressure_type,
            magnitude=magnitude,
            confidence=confidence,
            direction=direction,
            evidence_refs=list(evidence_refs),
            valid_until=utcnow() + timedelta(days=ttl_days),
        )


CANONICAL_MONEY_VERBS = {
    "buy", "sell", "finance", "lease", "broker", "refer", "introduce", "source",
    "aggregate", "arbitrate", "operate", "license", "insure", "advise", "build",
    "automate", "market", "distribute", "restructure", "acquire", "exit",
}


class AffordanceGenerationService:
    def generate(self, *, pressure_tags: Iterable[str], evidence_refs: list[str]) -> list[str]:
        if not evidence_refs:
            raise ValueError("affordance_generation_requires_evidence")
        tags = {tag.lower() for tag in pressure_tags}
        verbs: set[str] = set()
        rules = {
            "capacity": {"build", "lease", "finance", "acquire"},
            "distress": {"buy", "finance", "restructure", "broker"},
            "supply": {"source", "aggregate", "distribute", "market"},
            "regulatory": {"advise", "license", "insure"},
            "liquidity": {"sell", "broker", "refer", "introduce"},
            "operations": {"operate", "automate", "build"},
            "pricing": {"arbitrate", "market", "distribute"},
            "ownership": {"acquire", "exit"},
        }
        for tag in tags:
            for key, mapped in rules.items():
                if key in tag:
                    verbs.update(mapped)
        if not verbs:
            verbs = {"source", "advise", "introduce"}
        return sorted(verbs)


@dataclass(slots=True)
class GeneratedMoneyPath:
    payer_id: UUID | None
    payment_mechanism: str | None
    verb: str
    expected_net_value: float
    required_capital: float
    risk: float
    repeatability: float
    compounding_value: float
    valid_until: datetime
    evidence_refs: list[str]
    disposition: OperatorDisposition | None = None
    id: UUID = field(default_factory=uuid4)


class MoneyPathGenerationService:
    def generate(
        self,
        *,
        verb: str,
        payer_id: UUID | None,
        payment_mechanism: str | None,
        expected_net_value: float,
        required_capital: float,
        risk: float,
        repeatability: float,
        compounding_value: float,
        evidence_refs: list[str],
        ttl_days: int = 30,
    ) -> GeneratedMoneyPath:
        if verb not in CANONICAL_MONEY_VERBS:
            raise ValueError("unknown_money_verb")
        if not evidence_refs:
            raise ValueError("money_path_requires_evidence")
        disposition = None
        if payer_id is None or not payment_mechanism:
            disposition = OperatorDisposition.NON_MONETIZABLE
        return GeneratedMoneyPath(
            payer_id=payer_id,
            payment_mechanism=payment_mechanism,
            verb=verb,
            expected_net_value=expected_net_value,
            required_capital=required_capital,
            risk=risk,
            repeatability=repeatability,
            compounding_value=compounding_value,
            valid_until=utcnow() + timedelta(days=ttl_days),
            evidence_refs=list(evidence_refs),
            disposition=disposition,
        )


class MoneyPathLifecycleService:
    def stale(self, path: GeneratedMoneyPath, *, now: datetime | None = None) -> bool:
        return (now or utcnow()) >= path.valid_until

    def rank(self, paths: list[GeneratedMoneyPath]):
        comparable = [
            MoneyPathComparison(
                money_path_id=path.id,
                expected_net_value=path.expected_net_value,
                time_to_cash_days=max((path.valid_until - utcnow()).days, 0),
                required_capital=path.required_capital,
                risk=path.risk,
                repeatability=path.repeatability,
                compounding_value=path.compounding_value,
                evidence_refs=path.evidence_refs,
            )
            for path in paths
        ]
        return MoneyPathComparisonService().rank(comparable)


@dataclass(slots=True)
class CounterpartyProfileRecord:
    counterparty_id: UUID
    trust: float
    reachability: float
    decision_authority: float
    source_refs: list[str]
    updated_at: datetime = field(default_factory=utcnow)
    id: UUID = field(default_factory=uuid4)


class CounterpartyProfileService:
    def persist(self, store: EconomicObjectStore, profile: CounterpartyProfileRecord) -> CounterpartyProfileRecord:
        if not profile.source_refs:
            raise ValueError("counterparty_profile_requires_provenance")
        store.put("counterparty_profile_record", profile.id, profile)
        return profile


class BuyerMatchService:
    def score(self, profile: CounterpartyProfileRecord, response_history_weight: float) -> float:
        return 0.3 * profile.trust + 0.25 * profile.reachability + 0.25 * profile.decision_authority + 0.2 * response_history_weight


class SellerMatchService(BuyerMatchService):
    pass


@dataclass(slots=True)
class LiquidityGraph:
    nodes: list[object]
    preference_edges: list[LiquidityPreference]
    interaction_edges: list[CounterpartyInteraction]
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class LiquidityGraphService:
    def build_and_persist(
        self,
        store: EconomicObjectStore,
        *,
        counterparty_id: UUID,
        preferences: list[LiquidityPreference],
        interactions: list[CounterpartyInteraction],
        role_evidence: dict[str, list[str]],
    ) -> LiquidityGraph:
        node = CounterpartyLiquidityService().build_node(
            counterparty_id=counterparty_id,
            preferences=preferences,
            interactions=interactions,
            role_evidence=role_evidence,
        )
        graph = LiquidityGraph([node], preferences, interactions, list(node.evidence_refs))
        store.put("liquidity_graph", graph.id, graph)
        for pref in preferences:
            store.put("liquidity_preference", pref.id, pref)
        for interaction in interactions:
            store.put("counterparty_interaction", interaction.id, interaction)
        return graph


@dataclass(slots=True)
class OpportunityPortfolioRecord:
    opportunity_ids: list[UUID]
    dispositions: dict[str, str]
    suppressed_ids: list[UUID]
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class EconomicOpportunityScoringService:
    def score(self, *, expected_value: float, probability: float, risk: float, required_effort: float) -> float:
        if required_effort < 0 or risk < 0:
            raise ValueError("invalid_opportunity_inputs")
        return (max(expected_value, 0.0) * min(max(probability, 0.0), 1.0)) / (1.0 + risk + required_effort)


class CommercialSkepticService:
    def disposition(self, *, payer_verified: bool, payment_path_verified: bool, expected_value: float, evidence_refs: list[str]) -> OperatorDisposition:
        if not evidence_refs:
            raise ValueError("commercial_skeptic_requires_evidence")
        if not payer_verified or not payment_path_verified:
            return OperatorDisposition.NON_MONETIZABLE
        if expected_value <= 0:
            return OperatorDisposition.KILL
        return OperatorDisposition.ACT_NOW


class PortfolioAllocationService:
    def persist(
        self,
        store: EconomicObjectStore,
        *,
        lifecycles: list[OpportunityLifecycle],
        attention_limit: int,
    ) -> OpportunityPortfolioRecord:
        ranked = list(lifecycles)
        active = ranked[: max(attention_limit, 0)]
        suppressed = ranked[max(attention_limit, 0) :]
        record = OpportunityPortfolioRecord(
            opportunity_ids=[item.opportunity_id for item in ranked],
            dispositions={str(item.opportunity_id): item.disposition.value for item in ranked},
            suppressed_ids=[item.opportunity_id for item in suppressed],
            evidence_refs=[ref for item in ranked for ref in item.evidence_refs],
        )
        store.put("opportunity_portfolio", record.id, record)
        return record


class OpportunityStateService(OpportunityLifecycleService):
    pass


class TransactionStateService(TransactionLifecycleService):
    pass


@dataclass(slots=True)
class FeeProtectionDecision:
    protected: bool
    jurisdiction_reviewed: bool
    operator_approved: bool
    evidence_refs: list[str]


class FeeProtectionService:
    def verdict(self, decision: FeeProtectionDecision) -> ConformanceVerdict:
        if not decision.evidence_refs:
            return ConformanceVerdict.HOLD
        if not (decision.protected and decision.jurisdiction_reviewed and decision.operator_approved):
            return ConformanceVerdict.HOLD
        return ConformanceVerdict.GO


@dataclass(slots=True)
class MandateRecord:
    counterparty_id: UUID
    scope: str
    exclusive: bool
    jurisdiction: str
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class MandateService:
    def persist(self, store: EconomicObjectStore, mandate: MandateRecord) -> MandateRecord:
        if not mandate.evidence_refs:
            raise ValueError("mandate_requires_evidence")
        store.put("mandate_record", mandate.id, mandate)
        return mandate


@dataclass(slots=True)
class InternationalJurisdictionProfile:
    jurisdiction: str
    currency: str
    languages: list[str]
    registries: list[str]
    regulators: list[str]
    licensing_regimes: list[str]
    procurement_systems: list[str]
    courts: list[str]
    trade_rules: list[str]
    entity_types: list[str]
    import_export_rules: list[str]
    business_norms: list[str]
    source_reliability_notes: list[str]
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class SourcePlaneRegistryService:
    def persist(self, store: EconomicObjectStore, *, source_key: str, payload: object, evidence_refs: list[str]) -> UUID:
        if not evidence_refs:
            raise ValueError("source_plane_requires_provenance")
        object_id = uuid4()
        store.put("source_plane_registry", object_id, {"source_key": source_key, "payload": payload, "evidence_refs": evidence_refs})
        return object_id


class SourceRightsService:
    def verdict(self, policy: SourceActivationPolicy) -> ConformanceVerdict:
        return SourcePolicyService().activation_verdict(policy)


@dataclass(slots=True)
class SourceEconomicsRecord:
    source_key: str
    cost: float
    useful_observations: int
    false_positives: int
    attributable_value: float
    evidence_refs: list[str]

    @property
    def roi(self) -> float:
        return (self.attributable_value - self.cost) / max(self.cost, 1.0)

    @property
    def yield_rate(self) -> float:
        total = self.useful_observations + self.false_positives
        return self.useful_observations / max(total, 1)


class SourceEconomicsService:
    def evaluate(self, record: SourceEconomicsRecord) -> ConformanceVerdict:
        if not record.evidence_refs:
            return ConformanceVerdict.HOLD
        return ConformanceVerdict.GO if record.roi > 0 and record.yield_rate >= 0.5 else ConformanceVerdict.HOLD


class SourceDiscoveryService:
    def propose(self, store: EconomicObjectStore, *, candidate: dict[str, object], evidence_refs: list[str]) -> UUID:
        if not evidence_refs:
            raise ValueError("source_discovery_requires_evidence")
        object_id = uuid4()
        store.put("source_candidate", object_id, {"candidate": candidate, "evidence_refs": evidence_refs, "auto_activate": False})
        return object_id


class SourceReliabilityService:
    def calibrate(self, *, confirmations: int, contradictions: int, freshness: float, provenance_quality: float) -> float:
        if confirmations < 0 or contradictions < 0:
            raise ValueError("invalid_reliability_counts")
        empirical = confirmations / max(confirmations + contradictions, 1)
        return min(max(0.55 * empirical + 0.25 * freshness + 0.20 * provenance_quality, 0.0), 1.0)


class SourceLifecycleService:
    allowed = {
        "candidate": {"reviewed"},
        "reviewed": {"approved", "prohibited"},
        "approved": {"active", "prohibited"},
        "active": {"degraded", "suspended", "prohibited"},
        "degraded": {"active", "suspended", "prohibited"},
        "suspended": {"active", "prohibited"},
        "prohibited": set(),
    }

    def transition(self, *, from_state: str, to_state: str, evidence_refs: list[str]) -> str:
        if to_state not in self.allowed.get(from_state, set()):
            raise ValueError("invalid_source_transition")
        if not evidence_refs:
            raise ValueError("source_transition_requires_evidence")
        return to_state


class SourceROIService:
    def score(self, record: SourceEconomicsRecord) -> float:
        return record.roi


class AttributionDownstreamGateService:
    operations = {"source_promotion", "strategy_promotion", "graph_rewiring", "capital_reallocation"}

    def verdict(self, *, operation: str, chain: CausalAttributionChain) -> ConformanceVerdict:
        if operation not in self.operations:
            raise ValueError("unknown_attribution_operation")
        return AttributionPromotionService().promotion_verdict(chain)


class AttributionLifecycleService:
    allowed = {
        "provisional": {"supported", "disputed"},
        "supported": {"accepted", "disputed"},
        "disputed": {"revised"},
        "revised": {"supported", "accepted"},
        "accepted": set(),
    }

    def transition(self, *, from_state: str, to_state: str, evidence_refs: list[str]) -> str:
        if to_state not in self.allowed.get(from_state, set()):
            raise ValueError("invalid_attribution_transition")
        if not evidence_refs:
            raise ValueError("attribution_transition_requires_evidence")
        return to_state


@dataclass(slots=True)
class OwnedPlatform:
    name: str
    build_candidate_id: UUID
    payer_evidence_refs: list[str]
    resource_estimate: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class CapitalAsset:
    name: str
    owned_platform_id: UUID
    attributable_profit: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class CompoundingAssetService:
    def detect(self, *, pattern_key: str, transaction_ids: list[UUID], payer_ids: list[UUID], evidence_refs: list[str]):
        return CompoundingEmergenceService().detect_repeated_pattern(
            pattern_key=pattern_key,
            transaction_ids=transaction_ids,
            payer_ids=payer_ids,
            evidence_refs=evidence_refs,
        )


class ProductizationService:
    def build_candidate(self, *, candidate_type: str, pattern, resource_estimate: float) -> BuildCandidate:
        return CompoundingEmergenceService().create_build_candidate(
            candidate_type=candidate_type,
            pattern=pattern,
            resource_estimate=resource_estimate,
        )


class MarketplaceEmergenceService(ProductizationService):
    pass


class BusinessModelMutationService(ProductizationService):
    pass


class CompoundingLifecycleService:
    allowed = {
        "observed": {"hypothesized"},
        "hypothesized": {"validated"},
        "validated": {"build_candidate"},
        "build_candidate": {"approved", "killed"},
        "approved": {"operating"},
        "operating": {"matured", "killed"},
        "matured": set(),
        "killed": set(),
    }

    def transition(self, *, from_state: str, to_state: str, evidence_refs: list[str], resource_estimate: float | None = None) -> str:
        if to_state not in self.allowed.get(from_state, set()):
            raise ValueError("invalid_compounding_transition")
        if not evidence_refs:
            raise ValueError("compounding_transition_requires_evidence")
        if to_state in {"build_candidate", "approved", "operating"} and (resource_estimate is None or resource_estimate <= 0):
            raise ValueError("compounding_transition_requires_resource_estimate")
        return to_state


class ProfitEventPersistenceService:
    def persist(self, store: EconomicObjectStore, event: ProfitEvent) -> ProfitEvent:
        if not event.evidence_refs:
            raise ValueError("profit_event_requires_evidence")
        store.put("profit_event", event.id, event)
        return event


class ProfitService(ProfitNormalizationService):
    pass


class TransactionOutcomeService(TransactionLifecycleService):
    def terminal_outcomes(self, transaction_id: UUID, evidence_refs: list[str]) -> list[TransactionClosure]:
        return [
            self.close(transaction_id, 1.0, 1.0, evidence_refs),
            self.loss(transaction_id, evidence_refs),
            self.abandon(transaction_id, evidence_refs),
        ]
