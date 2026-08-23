from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from math import exp
from typing import Any, Protocol
from uuid import UUID, uuid4

from .economic import CommercialDisposition, CounterpartyProfile, CounterpartyRole, EconomicOpportunity


def utcnow() -> datetime:
    return datetime.now(UTC)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class EconomicStoreLike(Protocol):
    def put(self, kind: str, object_id: UUID, payload: Any) -> None: ...
    def get(self, kind: str, object_id: UUID) -> Any | None: ...
    def list(self, kind: str) -> list[Any]: ...


@dataclass(slots=True)
class LiquidityPreference:
    counterparty_id: UUID
    role: CounterpartyRole
    categories: list[str] = field(default_factory=list)
    geographies: list[str] = field(default_factory=list)
    min_value: float | None = None
    max_value: float | None = None
    timing_days: float | None = None
    constraints: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class CounterpartyInteraction:
    counterparty_id: UUID
    channel: str
    outcome: str
    responded: bool
    response_seconds: float | None = None
    decision_maker_reached: bool = False
    positive_signal: bool = False
    negative_signal: bool = False
    evidence_refs: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class CounterpartyMatch:
    counterparty_id: UUID
    role: CounterpartyRole
    score: float
    preference_fit: float
    response_history_score: float
    explanation: list[str]
    provenance: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class OpportunityDispositionRecord:
    opportunity_id: UUID
    disposition: CommercialDisposition
    score: float
    effective_score: float
    reasons: list[str]
    next_action: str | None
    evidence_state: str
    expires_at: datetime | None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


class CounterpartyLiquidityService:
    """Persistent liquidity graph behavior with response-history and preference weighting."""

    def __init__(self, store: EconomicStoreLike) -> None:
        self.store = store

    def save_preference(self, preference: LiquidityPreference) -> LiquidityPreference:
        if not preference.evidence_refs:
            raise ValueError("liquidity_preference_requires_evidence")
        self.store.put("liquidity_preference", preference.id, preference)
        return preference

    def record_interaction(self, interaction: CounterpartyInteraction) -> CounterpartyInteraction:
        if not interaction.evidence_refs:
            raise ValueError("counterparty_interaction_requires_evidence")
        self.store.put("counterparty_interaction", interaction.id, interaction)
        return interaction

    def _preferences(self, counterparty_id: UUID, role: CounterpartyRole) -> list[LiquidityPreference]:
        return [
            item
            for item in self.store.list("liquidity_preference")
            if item.counterparty_id == counterparty_id and item.role is role
        ]

    def _interactions(self, counterparty_id: UUID) -> list[CounterpartyInteraction]:
        return [
            item
            for item in self.store.list("counterparty_interaction")
            if item.counterparty_id == counterparty_id
        ]

    def response_history_score(self, counterparty_id: UUID) -> float:
        interactions = self._interactions(counterparty_id)
        if not interactions:
            return 0.5
        recent = sorted(interactions, key=lambda item: item.occurred_at, reverse=True)[:20]
        weighted = 0.0
        weight_total = 0.0
        for index, item in enumerate(recent):
            recency_weight = exp(-0.12 * index)
            signal = 0.0
            signal += 0.45 if item.responded else -0.25
            signal += 0.25 if item.decision_maker_reached else 0.0
            signal += 0.25 if item.positive_signal else 0.0
            signal -= 0.35 if item.negative_signal else 0.0
            if item.response_seconds is not None:
                signal += 0.15 * exp(-max(item.response_seconds, 0.0) / 172800.0)
            weighted += recency_weight * signal
            weight_total += recency_weight
        normalized = 0.5 + (weighted / max(weight_total, 1e-9)) * 0.5
        return _clamp01(normalized)

    def preference_fit(
        self,
        profile: CounterpartyProfile,
        role: CounterpartyRole,
        *,
        category: str | None = None,
        geography: str | None = None,
        value: float | None = None,
    ) -> tuple[float, list[str]]:
        preferences = self._preferences(profile.id, role)
        if not preferences:
            return 0.5, ["no_explicit_liquidity_preference"]
        best_score = 0.0
        best_reasons: list[str] = []
        for preference in preferences:
            score = 0.5
            reasons: list[str] = []
            if category is not None and preference.categories:
                matched = category.lower() in {item.lower() for item in preference.categories}
                score += 0.2 if matched else -0.2
                reasons.append(f"category_match={matched}")
            if geography is not None and preference.geographies:
                matched = geography.lower() in {item.lower() for item in preference.geographies}
                score += 0.15 if matched else -0.15
                reasons.append(f"geography_match={matched}")
            if value is not None:
                inside_min = preference.min_value is None or value >= preference.min_value
                inside_max = preference.max_value is None or value <= preference.max_value
                matched = inside_min and inside_max
                score += 0.15 if matched else -0.2
                reasons.append(f"value_range_match={matched}")
            score = _clamp01(score)
            if score > best_score:
                best_score = score
                best_reasons = reasons
        return best_score, best_reasons

    def rank(
        self,
        role: CounterpartyRole,
        *,
        category: str | None = None,
        geography: str | None = None,
        value: float | None = None,
        minimum_budget: float = 0.0,
        limit: int = 10,
    ) -> list[CounterpartyMatch]:
        matches: list[CounterpartyMatch] = []
        for profile in self.store.list("counterparty"):
            if role not in profile.roles:
                continue
            budget = profile.budget_estimate or 0.0
            if budget < minimum_budget:
                continue
            pref_fit, pref_reasons = self.preference_fit(
                profile,
                role,
                category=category,
                geography=geography,
                value=value,
            )
            response_score = self.response_history_score(profile.id)
            score = _clamp01(
                0.20 * _clamp01(profile.trust)
                + 0.18 * _clamp01(profile.reachability)
                + 0.20 * _clamp01(profile.decision_authority)
                + 0.10 * _clamp01(profile.urgency)
                + 0.17 * response_score
                + 0.15 * pref_fit
            )
            interactions = self._interactions(profile.id)
            preferences = self._preferences(profile.id, role)
            provenance = sorted(
                {
                    ref
                    for item in [*interactions, *preferences]
                    for ref in item.evidence_refs
                }
            )
            explanation = [
                f"role={role.value}",
                f"trust={profile.trust:.2f}",
                f"reachability={profile.reachability:.2f}",
                f"decision_authority={profile.decision_authority:.2f}",
                f"response_history={response_score:.2f}",
                f"preference_fit={pref_fit:.2f}",
                *pref_reasons,
            ]
            match = CounterpartyMatch(
                counterparty_id=profile.id,
                role=role,
                score=score,
                preference_fit=pref_fit,
                response_history_score=response_score,
                explanation=explanation,
                provenance=provenance,
            )
            self.store.put("counterparty_match", match.id, match)
            matches.append(match)
        return sorted(matches, key=lambda item: (item.score, str(item.counterparty_id)), reverse=True)[:limit]


class CommercialPortfolioService:
    """Opportunity decay, expiry and complete disposition semantics under attention constraints."""

    def __init__(self, store: EconomicStoreLike) -> None:
        self.store = store

    @staticmethod
    def effective_score(
        opportunity: EconomicOpportunity,
        *,
        at: datetime | None = None,
        half_life_days: float = 30.0,
    ) -> float:
        at = at or utcnow()
        age_days = max((at - opportunity.created_at).total_seconds() / 86400.0, 0.0)
        decay_multiplier = exp(-0.69314718056 * age_days / max(half_life_days, 0.01))
        return opportunity.score() * decay_multiplier * (1.0 - _clamp01(opportunity.time_decay))

    def disposition(
        self,
        opportunity: EconomicOpportunity,
        *,
        qualified_payment_path: bool,
        evidence_state: str = "supported",
        at: datetime | None = None,
        half_life_days: float = 30.0,
        archive_after_days: float = 120.0,
    ) -> OpportunityDispositionRecord:
        at = at or utcnow()
        age_days = max((at - opportunity.created_at).total_seconds() / 86400.0, 0.0)
        score = opportunity.score()
        effective = self.effective_score(opportunity, at=at, half_life_days=half_life_days)
        expires_at = opportunity.created_at + timedelta(days=max(archive_after_days, 1.0))
        reasons: list[str] = []
        next_action: str | None = None

        if not qualified_payment_path:
            disposition = CommercialDisposition.KILL
            reasons.append("no_qualified_payer_payment_path")
        elif opportunity.legal_reputation_risk >= 0.8:
            disposition = CommercialDisposition.KILL
            reasons.append("excessive_legal_reputation_risk")
        elif age_days >= archive_after_days or effective <= 1e-9:
            disposition = CommercialDisposition.ARCHIVE
            reasons.append("expired_or_decayed_below_attention_floor")
        elif opportunity.evidence_confidence < 0.65 or evidence_state not in {"supported", "verified"}:
            disposition = CommercialDisposition.VERIFY_FIRST
            reasons.append("evidence_requires_verification")
            next_action = "collect_missing_evidence"
        elif (
            opportunity.repeatability >= 0.85
            and opportunity.operational_complexity <= 0.35
            and opportunity.required_operator_hours >= 3.0
        ):
            disposition = CommercialDisposition.AUTOMATE
            reasons.append("repeatable_low_complexity_operator_work")
            next_action = "design_automation_candidate"
        elif (
            opportunity.required_operator_hours >= 8.0
            and opportunity.strategic_compounding_value < 0.55
            and opportunity.evidence_confidence >= 0.75
        ):
            disposition = CommercialDisposition.DELEGATE
            reasons.append("operator_attention_better_allocated_elsewhere")
            next_action = "prepare_delegation_packet"
        elif (
            opportunity.strategic_compounding_value >= 0.85
            and opportunity.repeatability >= 0.65
        ):
            disposition = CommercialDisposition.BUILD_AS_ASSET
            reasons.append("high_compounding_repeatable_pattern")
            next_action = "validate_build_candidate"
        elif opportunity.urgency >= 0.7 and opportunity.evidence_confidence >= 0.75:
            disposition = CommercialDisposition.ACT_NOW
            reasons.append("urgent_high_confidence_opportunity")
            next_action = "route_to_approval_or_execution_plan"
        else:
            disposition = CommercialDisposition.WATCH
            reasons.append("valid_but_below_immediate_attention_threshold")
            next_action = "monitor_for_change"

        record = OpportunityDispositionRecord(
            opportunity_id=opportunity.id,
            disposition=disposition,
            score=score,
            effective_score=effective,
            reasons=reasons,
            next_action=next_action,
            evidence_state=evidence_state,
            expires_at=expires_at,
        )
        self.store.put("opportunity_disposition", record.id, record)
        return record

    def expire_due(
        self,
        *,
        at: datetime | None = None,
        archive_after_days: float = 120.0,
    ) -> list[OpportunityDispositionRecord]:
        at = at or utcnow()
        expired: list[OpportunityDispositionRecord] = []
        latest_by_opportunity: dict[UUID, OpportunityDispositionRecord] = {}
        for record in self.store.list("opportunity_disposition"):
            latest_by_opportunity[record.opportunity_id] = record
        for opportunity in self.store.list("opportunity"):
            age_days = max((at - opportunity.created_at).total_seconds() / 86400.0, 0.0)
            if age_days < archive_after_days:
                continue
            existing = latest_by_opportunity.get(opportunity.id)
            if existing and existing.disposition in {CommercialDisposition.ARCHIVE, CommercialDisposition.KILL}:
                continue
            record = OpportunityDispositionRecord(
                opportunity_id=opportunity.id,
                disposition=CommercialDisposition.ARCHIVE,
                score=opportunity.score(),
                effective_score=self.effective_score(opportunity, at=at),
                reasons=["opportunity_expired"],
                next_action=None,
                evidence_state=str(opportunity.metadata.get("evidence_state", "unknown")),
                expires_at=opportunity.created_at + timedelta(days=archive_after_days),
            )
            self.store.put("opportunity_disposition", record.id, record)
            expired.append(record)
        return expired
