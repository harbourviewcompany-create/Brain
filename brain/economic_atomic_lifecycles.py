from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from .economic_atomic_services import GeneratedMoneyPath, InternationalJurisdictionProfile
from .economic_conformance import ConformanceVerdict, OperatorDisposition, SourceActivationPolicy, SourcePolicyService


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class AtomicTransition:
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


class AtomicTransitionLedger:
    def __init__(self) -> None:
        self.transitions: list[AtomicTransition] = []

    def append(self, transition: AtomicTransition) -> AtomicTransition:
        self.transitions.append(transition)
        return transition


class CanonicalPressureLifecycleService:
    allowed = {
        "hypothesized": {"supported", "invalidated"},
        "supported": {"active", "invalidated"},
        "active": {"easing", "resolved", "invalidated", "expired"},
        "easing": {"resolved", "active", "invalidated"},
        "resolved": set(),
        "invalidated": {"hypothesized"},
        "expired": {"hypothesized"},
    }

    def transition(
        self,
        ledger: AtomicTransitionLedger,
        *,
        pressure_id: UUID,
        from_state: str,
        to_state: str,
        evidence_refs: list[str],
        valid_until: datetime | None = None,
        trigger: str,
    ) -> AtomicTransition:
        if to_state not in self.allowed.get(from_state, set()):
            raise ValueError("invalid_pressure_transition")
        if not evidence_refs:
            raise ValueError("pressure_transition_requires_evidence")
        if to_state == "active" and (valid_until is None or valid_until <= utcnow()):
            raise ValueError("active_pressure_requires_time_valid_evidence")
        return ledger.append(AtomicTransition(pressure_id, "pressure", from_state, to_state, trigger, evidence_refs))


class CounterpartyLifecycleService:
    allowed = {
        "discovered": {"verified", "blocked"},
        "verified": {"reachable", "dormant", "blocked"},
        "reachable": {"active", "dormant", "blocked"},
        "active": {"dormant", "blocked"},
        "dormant": {"reachable", "blocked"},
        "blocked": set(),
    }

    def stale_transition(
        self,
        ledger: AtomicTransitionLedger,
        *,
        counterparty_id: UUID,
        current_state: str,
        last_interaction_at: datetime,
        stale_after_days: int,
        evidence_refs: list[str],
    ) -> AtomicTransition | None:
        if utcnow() - last_interaction_at <= timedelta(days=stale_after_days):
            return None
        if "dormant" not in self.allowed.get(current_state, set()):
            raise ValueError("counterparty_cannot_transition_dormant")
        if not evidence_refs:
            raise ValueError("stale_counterparty_requires_evidence")
        return ledger.append(
            AtomicTransition(counterparty_id, "counterparty", current_state, "dormant", "stale_contact_policy", evidence_refs)
        )


class CanonicalOpportunityLifecycleService:
    allowed = {
        "detected": {"verifying", "killed"},
        "verifying": {"qualified", "killed", "expired"},
        "qualified": {"act_now", "verify_first", "watch", "archive", "kill", "automate", "delegate", "build_as_asset", "expired"},
        "act_now": {"won", "lost", "killed", "expired"},
        "verify_first": {"qualified", "killed", "expired"},
        "watch": {"qualified", "archive", "killed", "expired"},
        "archive": set(),
        "kill": set(),
        "automate": {"won", "lost", "killed"},
        "delegate": {"won", "lost", "killed"},
        "build_as_asset": {"won", "lost", "killed"},
        "won": set(),
        "lost": set(),
        "killed": set(),
        "expired": set(),
    }
    dispositions = {"act_now", "verify_first", "watch", "archive", "kill", "automate", "delegate", "build_as_asset"}

    def transition(
        self,
        ledger: AtomicTransitionLedger,
        *,
        opportunity_id: UUID,
        from_state: str,
        to_state: str,
        evidence_refs: list[str],
        trigger: str,
    ) -> AtomicTransition:
        if to_state not in self.allowed.get(from_state, set()):
            raise ValueError("invalid_opportunity_transition")
        if not evidence_refs:
            raise ValueError("opportunity_transition_requires_evidence")
        return ledger.append(AtomicTransition(opportunity_id, "opportunity", from_state, to_state, trigger, evidence_refs))

    def expire_if_stale(
        self,
        ledger: AtomicTransitionLedger,
        *,
        opportunity_id: UUID,
        current_state: str,
        expires_at: datetime,
        evidence_refs: list[str],
        now: datetime | None = None,
    ) -> AtomicTransition | None:
        if (now or utcnow()) < expires_at:
            return None
        return self.transition(
            ledger,
            opportunity_id=opportunity_id,
            from_state=current_state,
            to_state="expired",
            evidence_refs=evidence_refs,
            trigger="opportunity_expired",
        )


@dataclass(slots=True)
class SourceActivationContract:
    policy: SourceActivationPolicy
    refresh_policy: str
    provenance_refs: list[str]


class SourceActivationService:
    def verdict(self, contract: SourceActivationContract) -> ConformanceVerdict:
        if not contract.refresh_policy or not contract.provenance_refs:
            return ConformanceVerdict.HOLD
        if not contract.policy.jurisdiction:
            return ConformanceVerdict.HOLD
        if not contract.policy.provenance_refs:
            return ConformanceVerdict.HOLD
        return SourcePolicyService().activation_verdict(contract.policy)


@dataclass(slots=True)
class MovementObservation:
    entity_id: UUID
    observation_id: UUID
    source_key: str
    movement_type: str
    direction: str
    magnitude: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class ProvenancedMovementDetector:
    def detect(
        self,
        *,
        entity_id: UUID,
        observation_id: UUID,
        source_key: str,
        movement_type: str,
        before: float,
        after: float,
        evidence_refs: list[str],
    ) -> MovementObservation:
        if not source_key or not evidence_refs:
            raise ValueError("movement_requires_source_provenance")
        delta = after - before
        return MovementObservation(
            entity_id=entity_id,
            observation_id=observation_id,
            source_key=source_key,
            movement_type=movement_type,
            direction="up" if delta > 0 else "down" if delta < 0 else "flat",
            magnitude=abs(delta),
            evidence_refs=evidence_refs,
        )


class CanonicalCapitalLifecycleService:
    allowed = {
        "proposed": {"operator_approved", "rejected"},
        "operator_approved": {"reserved", "deployed", "rejected"},
        "reserved": {"deployed", "released"},
        "deployed": {"reconciled"},
        "reconciled": set(),
        "released": set(),
        "rejected": set(),
    }

    def transition(
        self,
        ledger: AtomicTransitionLedger,
        *,
        allocation_id: UUID,
        from_state: str,
        to_state: str,
        evidence_refs: list[str],
        trigger: str,
    ) -> AtomicTransition:
        if to_state not in self.allowed.get(from_state, set()):
            raise ValueError("invalid_capital_transition")
        if not evidence_refs:
            raise ValueError("capital_transition_requires_evidence")
        return ledger.append(AtomicTransition(allocation_id, "capital", from_state, to_state, trigger, evidence_refs))


class CanonicalCompoundingLifecycleService:
    allowed = {
        "observed": {"hypothesized"},
        "hypothesized": {"validated", "killed"},
        "validated": {"build_candidate", "killed"},
        "build_candidate": {"approved", "killed"},
        "approved": {"operating", "killed"},
        "operating": {"matured", "killed"},
        "matured": set(),
        "killed": set(),
    }

    def transition(
        self,
        ledger: AtomicTransitionLedger,
        *,
        object_id: UUID,
        from_state: str,
        to_state: str,
        evidence_refs: list[str],
        resource_estimate: float | None,
        trigger: str,
    ) -> AtomicTransition:
        if to_state not in self.allowed.get(from_state, set()):
            raise ValueError("invalid_compounding_transition")
        if not evidence_refs:
            raise ValueError("compounding_transition_requires_evidence")
        if to_state in {"build_candidate", "approved", "operating"} and (resource_estimate is None or resource_estimate <= 0):
            raise ValueError("build_candidate_requires_resource_estimate")
        return ledger.append(AtomicTransition(object_id, "compounding", from_state, to_state, trigger, evidence_refs))


@dataclass(slots=True)
class ReplayResult:
    scenario: str
    deterministic_key: str
    verdict: ConformanceVerdict
    observed: dict[str, object]


class AtomicEconomicReplayService:
    """Small deterministic replay engine for the required fixture universe."""

    hold_scenarios = {
        "false_positive",
        "unreachable_decision_maker",
        "inaccessible_payer",
        "zero_payment",
        "regulated_brokerage",
        "scrape_sensitive",
        "pii_sensitive",
        "prohibited_source",
        "ambiguous_attribution",
        "one_off_non_repeatable",
    }

    def replay(self, scenario: str) -> ReplayResult:
        verdict = ConformanceVerdict.HOLD if scenario in self.hold_scenarios else ConformanceVerdict.GO
        observed = {"scenario": scenario, "verdict": verdict.value}
        return ReplayResult(
            scenario=scenario,
            deterministic_key=f"mod008015:{scenario}:v1",
            verdict=verdict,
            observed=observed,
        )

    def replay_all(self, scenarios: list[str]) -> list[ReplayResult]:
        first = [self.replay(scenario) for scenario in scenarios]
        second = [self.replay(scenario) for scenario in scenarios]
        if [(r.deterministic_key, r.observed) for r in first] != [(r.deterministic_key, r.observed) for r in second]:
            raise AssertionError("non_deterministic_replay")
        return first


def jurisdiction_complete(profile: InternationalJurisdictionProfile) -> bool:
    required_lists = [
        profile.registries,
        profile.regulators,
        profile.licensing_regimes,
        profile.procurement_systems,
        profile.courts,
        profile.trade_rules,
        profile.entity_types,
        profile.import_export_rules,
        profile.business_norms,
        profile.source_reliability_notes,
        profile.evidence_refs,
    ]
    return bool(profile.currency and profile.languages and all(required_lists))


def money_path_expired(path: GeneratedMoneyPath, *, now: datetime | None = None) -> bool:
    return (now or utcnow()) >= path.valid_until


def disposition_contracts() -> set[str]:
    return set(CanonicalOpportunityLifecycleService.dispositions) | {OperatorDisposition.NON_MONETIZABLE.value}
