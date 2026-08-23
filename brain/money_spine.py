from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class OpportunityClass(StrEnum):
    HIGH_INTENT_LEAD = "high_intent_lead"
    BUYER_SELLER_MATCH = "buyer_seller_match"
    DISTRESSED_ASSET = "distressed_asset"
    PROCUREMENT_MATCH = "procurement_match"
    HIRING_PAIN = "hiring_pain"
    LOCAL_BUSINESS_GAP = "local_business_gap"
    UNDERPRICED_ASSET = "underpriced_asset"
    PAID_INTELLIGENCE = "paid_intelligence"
    SERVICE_WRAPPER = "service_wrapper"
    AUTOMATION_AUDIT = "automation_audit"


class AutomationReadiness(StrEnum):
    MANUAL_FIRST = "manual_first"
    SEMI_AUTOMATED = "semi_automated"
    AUTOMATE_AFTER_PROOF = "automate_after_proof"
    NOT_WORTH_AUTOMATING = "not_worth_automating"


class ExperimentDecision(StrEnum):
    SCALE = "scale"
    MODIFY = "modify"
    KILL = "kill"
    CONTINUE = "continue"


@dataclass(slots=True)
class MoneyLane:
    lane_id: str
    title: str
    opportunity_class: OpportunityClass
    packaged_offer: str
    buyer_type: str
    seller_or_target_type: str
    source_targets: list[str]
    search_queries: list[str]
    first_48_hour_action: str
    price_low: float
    price_high: float
    repeatability: float
    fulfillment_difficulty: float
    time_to_cash_days: float
    automation_readiness: AutomationReadiness = AutomationReadiness.MANUAL_FIRST
    legal_access_risk: float = 0.0
    priority_score: float = 0.5
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class RevenueSignal:
    raw_signal: str
    source_id: str
    money_lane_id: str
    evidence_refs: list[str]
    named_buyer: str | None = None
    named_seller: str | None = None
    decision_maker: str | None = None
    visible_pain: str | None = None
    urgency_reason: str | None = None
    payment_path: str | None = None
    contact_channel: str | None = None
    commercial_value: float = 0.5
    confidence: float = 0.5
    urgency: float = 0.0
    contactability: float = 0.0
    execution_difficulty: float = 0.5
    legal_access_risk: float = 0.0
    time_delay: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ScoredOpportunity:
    signal_id: UUID
    lane_id: str
    score: float
    actionable: bool
    rejection_reasons: list[str]
    next_action: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class PackagedOffer:
    opportunity_id: UUID
    title: str
    offer_name: str
    buyer_type: str
    target_contact: str
    price_low: float
    price_high: float
    evidence_refs: list[str]
    outreach_script: str
    follow_up_script: str
    approval_required: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class RevenueExperiment:
    lane_id: str
    hypothesis: str
    buyer_type: str
    offer: str
    price: float
    outreach_target: int
    success_reply_threshold: int
    success_paid_threshold: int
    kill_after_outreach: int
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class RevenueExperimentResult:
    experiment_id: UUID
    outreach_sent: int
    replies: int
    meetings: int
    paid_conversions: int
    revenue: float
    operator_hours: float
    decision: ExperimentDecision
    lesson: str


@dataclass(slots=True)
class DailyRevenueQuota:
    raw_signals_reviewed: int = 50
    signals_logged: int = 20
    qualified_opportunities: int = 10
    prioritized_opportunities: int = 5
    direct_revenue_actions: int = 3
    sellable_assets_created: int = 1
    lessons_recorded: int = 1


@dataclass(slots=True)
class DailyRevenueReport:
    raw_signals_reviewed: int
    signals_logged: int
    qualified_opportunities: int
    prioritized_opportunities: int
    direct_revenue_actions: int
    sellable_assets_created: int
    lessons_recorded: int
    quota: DailyRevenueQuota = field(default_factory=DailyRevenueQuota)

    @property
    def passed(self) -> bool:
        q = self.quota
        return (
            self.raw_signals_reviewed >= q.raw_signals_reviewed
            and self.signals_logged >= q.signals_logged
            and self.qualified_opportunities >= q.qualified_opportunities
            and self.prioritized_opportunities >= q.prioritized_opportunities
            and self.direct_revenue_actions >= q.direct_revenue_actions
            and self.sellable_assets_created >= q.sellable_assets_created
            and self.lessons_recorded >= q.lessons_recorded
        )

    @property
    def gaps(self) -> list[str]:
        q = self.quota
        checks = {
            "raw_signals_reviewed": self.raw_signals_reviewed - q.raw_signals_reviewed,
            "signals_logged": self.signals_logged - q.signals_logged,
            "qualified_opportunities": self.qualified_opportunities - q.qualified_opportunities,
            "prioritized_opportunities": self.prioritized_opportunities - q.prioritized_opportunities,
            "direct_revenue_actions": self.direct_revenue_actions - q.direct_revenue_actions,
            "sellable_assets_created": self.sellable_assets_created - q.sellable_assets_created,
            "lessons_recorded": self.lessons_recorded - q.lessons_recorded,
        }
        return [name for name, delta in checks.items() if delta < 0]


class NoFantasyFilter:
    """Rejects interesting-but-non-commercial signals from today's revenue queue."""

    def evaluate(self, signal: RevenueSignal) -> list[str]:
        reasons: list[str] = []
        if not any([signal.named_buyer, signal.named_seller, signal.decision_maker]):
            reasons.append("no_named_buyer_seller_or_decision_maker")
        if not any([signal.visible_pain, signal.urgency_reason, signal.payment_path]):
            reasons.append("no_visible_pain_urgency_or_payment_path")
        if not signal.contact_channel:
            reasons.append("no_contact_channel")
        if not signal.evidence_refs:
            reasons.append("no_evidence_refs")
        if signal.legal_access_risk >= 0.75:
            reasons.append("legal_access_risk_too_high")
        if signal.time_delay > 0.75:
            reasons.append("time_delay_too_high_for_immediate_revenue")
        return reasons


class MoneySpineService:
    """Converts signals into sellable offers, experiments, outcomes, and learning updates."""

    def __init__(self, lanes: list[MoneyLane] | None = None):
        self.lanes: dict[str, MoneyLane] = {lane.lane_id: lane for lane in lanes or default_money_lanes()}
        self.no_fantasy = NoFantasyFilter()
        self.source_scores: dict[str, float] = {}

    def score_signal(self, signal: RevenueSignal) -> ScoredOpportunity:
        lane = self.lanes[signal.money_lane_id]
        buyer_seller_clarity = 1.0 if signal.named_buyer and signal.named_seller else 0.7 if any([signal.named_buyer, signal.named_seller, signal.decision_maker]) else 0.0
        repeatability = lane.repeatability
        legal_risk = max(signal.legal_access_risk, lane.legal_access_risk)
        score = (
            signal.commercial_value * 25
            + signal.urgency * 20
            + buyer_seller_clarity * 20
            + signal.contactability * 15
            + signal.confidence * 10
            + repeatability * 10
            - signal.execution_difficulty * 15
            - legal_risk * 20
            - signal.time_delay * 10
        )
        rejection_reasons = self.no_fantasy.evaluate(signal)
        return ScoredOpportunity(
            signal_id=signal.id,
            lane_id=lane.lane_id,
            score=round(score, 4),
            actionable=not rejection_reasons,
            rejection_reasons=rejection_reasons,
            next_action=lane.first_48_hour_action if not rejection_reasons else None,
        )

    def package_offer(self, signal: RevenueSignal, scored: ScoredOpportunity) -> PackagedOffer:
        if not scored.actionable:
            raise ValueError(f"Cannot package rejected opportunity: {scored.rejection_reasons}")
        lane = self.lanes[signal.money_lane_id]
        contact = signal.decision_maker or signal.named_buyer or signal.named_seller or "target decision-maker"
        script = (
            f"I found a live signal relevant to {lane.buyer_type}: {signal.raw_signal}. "
            f"I can package this into a {lane.packaged_offer} with source links, priority score, "
            "recommended next actions, and a 48-hour validation path. Would you want to see a small sample?"
        )
        follow_up = (
            f"Following up on the {lane.packaged_offer}. The useful part is not the research; "
            "it is the named targets, evidence, and next actions that can be tested quickly."
        )
        return PackagedOffer(
            opportunity_id=scored.id,
            title=f"{lane.title}: {signal.raw_signal[:90]}",
            offer_name=lane.packaged_offer,
            buyer_type=lane.buyer_type,
            target_contact=contact,
            price_low=lane.price_low,
            price_high=lane.price_high,
            evidence_refs=signal.evidence_refs,
            outreach_script=script,
            follow_up_script=follow_up,
            approval_required=True,
        )

    def create_experiment(self, lane_id: str, *, price: float | None = None) -> RevenueExperiment:
        lane = self.lanes[lane_id]
        return RevenueExperiment(
            lane_id=lane_id,
            hypothesis=f"{lane.buyer_type} will pay for {lane.packaged_offer} when public signals show urgent movement.",
            buyer_type=lane.buyer_type,
            offer=lane.packaged_offer,
            price=price if price is not None else lane.price_low,
            outreach_target=30,
            success_reply_threshold=3,
            success_paid_threshold=1,
            kill_after_outreach=50,
        )

    def evaluate_experiment(
        self,
        experiment: RevenueExperiment,
        *,
        outreach_sent: int,
        replies: int,
        meetings: int,
        paid_conversions: int,
        revenue: float,
        operator_hours: float,
    ) -> RevenueExperimentResult:
        if paid_conversions >= experiment.success_paid_threshold or replies >= experiment.success_reply_threshold:
            decision = ExperimentDecision.SCALE if paid_conversions else ExperimentDecision.MODIFY
            lesson = "Buyer response proved the lane deserves more testing."
        elif outreach_sent >= experiment.kill_after_outreach:
            decision = ExperimentDecision.KILL
            lesson = "Kill or radically reframe: outreach threshold passed without enough response."
        else:
            decision = ExperimentDecision.CONTINUE
            lesson = "Insufficient data; continue until success or kill threshold."
        return RevenueExperimentResult(
            experiment.id,
            outreach_sent,
            replies,
            meetings,
            paid_conversions,
            revenue,
            operator_hours,
            decision,
            lesson,
        )

    def apply_outcome_learning(
        self,
        lane_id: str,
        source_id: str,
        *,
        revenue: float,
        reply: bool,
        legal_risk: float,
        operator_hours: float,
    ) -> MoneyLane:
        lane = self.lanes[lane_id]
        reward = min(0.15, revenue / max(lane.price_high, 1.0) * 0.10)
        reply_reward = 0.03 if reply else -0.02
        cost_penalty = min(0.08, operator_hours * 0.01)
        risk_penalty = min(0.20, legal_risk * 0.15)
        delta = reward + reply_reward - cost_penalty - risk_penalty
        updated_priority = max(0.0, min(1.0, lane.priority_score + delta))
        updated = replace(lane, priority_score=round(updated_priority, 4))
        self.lanes[lane_id] = updated
        previous_source = self.source_scores.get(source_id, 0.5)
        self.source_scores[source_id] = round(max(0.0, min(1.0, previous_source + delta)), 4)
        return updated


def default_money_lanes() -> list[MoneyLane]:
    return [
        MoneyLane(
            lane_id="high_intent_lead_pack",
            title="High-intent lead pack",
            opportunity_class=OpportunityClass.HIGH_INTENT_LEAD,
            packaged_offer="High-Intent Lead Pack",
            buyer_type="B2B service provider, agency, consultant, or founder selling into a defined market",
            seller_or_target_type="Companies or people publicly showing buying intent, pain, expansion, or urgent need",
            source_targets=["search results", "forums", "LinkedIn/manual capture", "review platforms", "founder communities"],
            search_queries=["looking for recommendations supplier urgent", "need help with vendor", "switching from alternative to"],
            first_48_hour_action="Build 25 sourced leads, identify decision-makers, draft offer-specific outreach, and ask whether the buyer wants the full pack.",
            price_low=150,
            price_high=500,
            repeatability=0.9,
            fulfillment_difficulty=0.25,
            time_to_cash_days=2,
            automation_readiness=AutomationReadiness.SEMI_AUTOMATED,
            priority_score=0.9,
        ),
        MoneyLane(
            lane_id="buyer_seller_match_sprint",
            title="Buyer/seller match sprint",
            opportunity_class=OpportunityClass.BUYER_SELLER_MATCH,
            packaged_offer="Buyer/Seller Match Sprint",
            buyer_type="Broker, seller, operator, asset owner, investor, or distributor",
            seller_or_target_type="Known buyer or seller with asset, inventory, service, company, or demand",
            source_targets=["marketplaces", "auction sites", "business-for-sale listings", "procurement posts", "industry directories"],
            search_queries=["for sale equipment closing", "wanted supplier buyer", "liquidating assets buyer needed"],
            first_48_hour_action="Verify the asset or demand, identify 20 likely counterparties, and queue controlled intro outreach for approval.",
            price_low=500,
            price_high=2500,
            repeatability=0.8,
            fulfillment_difficulty=0.45,
            time_to_cash_days=7,
            automation_readiness=AutomationReadiness.AUTOMATE_AFTER_PROOF,
            priority_score=0.85,
        ),
        MoneyLane(
            lane_id="procurement_rfp_match",
            title="Procurement/RFP match",
            opportunity_class=OpportunityClass.PROCUREMENT_MATCH,
            packaged_offer="Procurement / RFP Match Pack",
            buyer_type="Vendor, consultant, agency, contractor, or service provider eligible to bid",
            seller_or_target_type="Government, institution, nonprofit, or company publishing a buying requirement",
            source_targets=["government procurement portals", "municipal tenders", "school boards", "hospital procurement", "corporate supplier portals"],
            search_queries=["RFP vendor deadline", "tender services supplier", "request for proposal qualified vendors"],
            first_48_hour_action="Extract requirements, find 10 qualified vendors, and pitch the opportunity brief or bid-support intro.",
            price_low=250,
            price_high=1500,
            repeatability=0.85,
            fulfillment_difficulty=0.35,
            time_to_cash_days=5,
            automation_readiness=AutomationReadiness.SEMI_AUTOMATED,
            priority_score=0.82,
        ),
    ]
