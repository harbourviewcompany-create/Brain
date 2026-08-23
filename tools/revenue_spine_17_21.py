from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from brain.money_spine import DailyRevenueReport, MoneySpineService, RevenueSignal

REGISTRY_TARGET_COUNT = 10_000
FAST_CASH_COUNT = 500
REQUIRED_COLUMNS = [
    "lane_id", "lane_domain", "signal_family", "signal_to_watch", "source_categories",
    "likely_buyer", "likely_seller_target", "monetization_path", "first_48_hour_action",
    "time_to_cash_days", "automation_potential", "risk_level", "priority_score", "scale_trigger",
]
DOMAINS = ["distressed_assets", "buyer_intent", "procurement", "hiring_expansion", "local_gaps", "underpriced_assets", "paid_intelligence", "vendor_replacement", "capital_need", "market_entry"]
SIGNALS = ["buying_request", "seller_distress", "deadline", "expansion", "complaint", "mispricing", "regulatory_opening", "leadership_change", "inventory_movement", "supplier_gap"]


class AccessStatus(StrEnum):
    PUBLIC = "public"
    PERMISSIONED = "permissioned"
    REVIEW_REQUIRED = "review_required"
    PROHIBITED = "prohibited"


class ConnectorKind(StrEnum):
    MANUAL_TEXT = "manual_text"
    JOB_BOARD = "job_board"
    PROCUREMENT = "procurement"
    AUCTION = "auction"


class ApprovalStatus(StrEnum):
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"
    SENT = "sent"
    WON = "won"
    LOST = "lost"


@dataclass(slots=True)
class OpportunityRegistryRow:
    lane_id: str
    lane_domain: str
    signal_family: str
    signal_to_watch: str
    source_categories: list[str]
    likely_buyer: str
    likely_seller_target: str
    monetization_path: str
    first_48_hour_action: str
    time_to_cash_days: float
    automation_potential: float
    risk_level: float
    priority_score: float
    scale_trigger: str


@dataclass(slots=True)
class SourceConnectorInput:
    connector_kind: ConnectorKind
    source_id: str
    content: str
    evidence_ref: str
    access_status: AccessStatus = AccessStatus.PUBLIC
    extraction_method: str = "fixture"
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RevenueSignalCandidate:
    raw_signal: str
    source_id: str
    money_lane_id: str
    evidence_refs: list[str]
    named_buyer: str | None
    named_seller: str | None
    decision_maker: str | None
    visible_pain: str | None
    urgency_reason: str | None
    payment_path: str | None
    contact_channel: str | None
    legal_access_risk: float
    extraction_method: str
    access_status: AccessStatus
    content_hash: str

    def to_revenue_signal(self) -> RevenueSignal:
        allowed = self.legal_access_risk < 0.75
        return RevenueSignal(
            raw_signal=self.raw_signal,
            source_id=self.source_id,
            money_lane_id=self.money_lane_id,
            evidence_refs=list(self.evidence_refs),
            named_buyer=self.named_buyer,
            named_seller=self.named_seller,
            decision_maker=self.decision_maker,
            visible_pain=self.visible_pain,
            urgency_reason=self.urgency_reason,
            payment_path=self.payment_path,
            contact_channel=self.contact_channel,
            commercial_value=0.8 if allowed else 0,
            confidence=0.78 if allowed else 0,
            urgency=0.82 if allowed else 0,
            contactability=0.72 if self.contact_channel else 0,
            execution_difficulty=0.28 if allowed else 1,
            legal_access_risk=self.legal_access_risk,
            time_delay=0.1 if allowed else 1,
            metadata={"access_status": str(self.access_status), "extraction_method": self.extraction_method, "content_hash": self.content_hash},
        )


@dataclass(slots=True)
class MoneyHypothesis:
    evidence_for: list[str]
    evidence_against: list[str]
    fastest_validation_action: str
    falsification_rule: str
    confidence: float


@dataclass(slots=True)
class CortexResult:
    signal: RevenueSignal
    hypotheses: list[MoneyHypothesis]
    objections: list[str]
    approval_required: bool = True


@dataclass(slots=True)
class CockpitAction:
    offer_id: UUID
    status: ApprovalStatus = ApprovalStatus.APPROVAL_REQUIRED
    approved_by: str | None = None
    sent: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class CockpitOutcome:
    action_id: UUID
    source_id: str
    lane_id: str
    replies: int
    meetings: int
    paid_conversions: int
    revenue: float
    operator_hours: float
    false_positive: bool
    legal_access_issue: bool
    lesson: str


def generate_opportunity_registry(count: int = REGISTRY_TARGET_COUNT) -> list[OpportunityRegistryRow]:
    if count <= 0:
        raise ValueError("registry count must be positive")
    rows: list[OpportunityRegistryRow] = []
    for index in range(count):
        days = 1 + index % 14
        auto = round(0.35 + ((index * 17) % 60) / 100, 4)
        risk = round(0.05 + ((index * 11) % 45) / 100, 4)
        priority = round(max(0, min(1, 0.35 + ((15 - days) / 15) * 0.35 + auto * 0.15 - risk * 0.10)), 4)
        domain = DOMAINS[index % len(DOMAINS)]
        signal = SIGNALS[(index // len(DOMAINS)) % len(SIGNALS)]
        rows.append(OpportunityRegistryRow(f"opp-{index + 1:05d}", domain, signal, f"{signal} in {domain}", ["manual_url", "public_web"], "B2B buyer", "seller or target", "lead pack", "Capture 25 signals and queue approval-gated outreach.", float(days), auto, risk, priority, "scale after 2 paid conversions or 5 replies"))
    return rows


def validate_registry_row(row: OpportunityRegistryRow | dict) -> OpportunityRegistryRow:
    if isinstance(row, dict):
        missing = [column for column in REQUIRED_COLUMNS if column not in row]
        if missing:
            raise ValueError(f"missing required columns: {missing}")
        row = OpportunityRegistryRow(**{column: row[column] for column in REQUIRED_COLUMNS})
    if not row.source_categories:
        raise ValueError("source_categories required")
    if not 0 <= row.priority_score <= 1 or not 0 <= row.risk_level <= 1:
        raise ValueError("scores must be between 0 and 1")
    return row


def first_500_fast_cash(rows: list[OpportunityRegistryRow]) -> list[OpportunityRegistryRow]:
    clean = [validate_registry_row(row) for row in rows]
    return sorted(clean, key=lambda row: (-row.priority_score, row.time_to_cash_days, row.risk_level, row.lane_id))[:FAST_CASH_COUNT]


def registry_summary(rows: list[OpportunityRegistryRow]) -> dict[str, object]:
    clean = [validate_registry_row(row) for row in rows]
    return {"row_count": len(clean), "first_500_count": len(first_500_fast_cash(clean)), "domains": sorted({row.lane_domain for row in clean})}


class FixtureConnectorRunner:
    def ingest(self, item: SourceConnectorInput) -> list[RevenueSignalCandidate]:
        risk = 1 if item.access_status == AccessStatus.PROHIBITED else 0.55 if item.access_status == AccessStatus.REVIEW_REQUIRED else 0
        if risk >= 0.55 or not item.evidence_ref:
            return [RevenueSignalCandidate("BLOCKED: source access or evidence review failed", item.source_id, "high_intent_lead_pack", [item.evidence_ref] if item.evidence_ref else [], None, None, None, None, None, None, None, 1, item.extraction_method, item.access_status, sha256(item.content.encode()).hexdigest())]
        lane = "procurement_rfp_match" if item.connector_kind == ConnectorKind.PROCUREMENT else "buyer_seller_match_sprint" if item.connector_kind == ConnectorKind.AUCTION else "high_intent_lead_pack"
        buyer = item.metadata.get("buyer") or item.metadata.get("company") or "named buyer"
        seller = item.metadata.get("seller") or ("eligible vendor pool" if item.connector_kind == ConnectorKind.PROCUREMENT else None)
        return [RevenueSignalCandidate(item.content.strip(), item.source_id, lane, [item.evidence_ref], buyer, seller, buyer, item.metadata.get("pain", "visible commercial pain"), item.metadata.get("urgency", "deadline detected"), item.metadata.get("payment_path", "sell opportunity pack"), item.metadata.get("contact_channel", "public contact"), risk, item.extraction_method, item.access_status, sha256(item.content.encode()).hexdigest())]


class DeterministicModelCortex:
    def analyze(self, item: SourceConnectorInput) -> CortexResult:
        objections = []
        if not item.evidence_ref:
            objections.append("missing_provenance")
        if item.access_status in {AccessStatus.REVIEW_REQUIRED, AccessStatus.PROHIBITED}:
            objections.append("access_status_blocks_or_requires_review")
        if not item.metadata.get("buyer") and not item.metadata.get("company"):
            objections.append("buyer_not_named")
        if "urgent" not in item.content.lower() and "deadline" not in item.content.lower():
            objections.append("urgency_not_explicit")
        signal = FixtureConnectorRunner().ingest(item)[0].to_revenue_signal()
        hypothesis = MoneyHypothesis([item.evidence_ref] if item.evidence_ref else [], list(objections), "Send approval-gated sample request.", "Kill if 30 targeted outreaches produce zero replies.", 0.8 if not objections else 0.45)
        return CortexResult(signal, [hypothesis], objections)


class RevenueCockpit:
    def __init__(self, service: MoneySpineService | None = None):
        self.service = service or MoneySpineService()
        self.signals: list[RevenueSignal] = []
        self.offers: list[object] = []
        self.actions: dict[UUID, CockpitAction] = {}
        self.backlog: list[str] = []
        self.outcomes: list[CockpitOutcome] = []

    def ingest_signal(self, signal: RevenueSignal) -> UUID | None:
        self.signals.append(signal)
        scored = self.service.score_signal(signal)
        if not scored.actionable:
            self.backlog.extend(scored.rejection_reasons)
            return None
        offer = self.service.package_offer(signal, scored)
        self.offers.append(offer)
        self.actions[offer.id] = CockpitAction(offer.id)
        return offer.id

    def approve_offer(self, offer_id: UUID, approved_by: str) -> CockpitAction:
        self.actions[offer_id].status = ApprovalStatus.APPROVED
        self.actions[offer_id].approved_by = approved_by
        return self.actions[offer_id]

    def mark_sent(self, offer_id: UUID) -> CockpitAction:
        action = self.actions[offer_id]
        if action.status != ApprovalStatus.APPROVED:
            raise PermissionError("outreach_requires_operator_approval")
        action.status = ApprovalStatus.SENT
        action.sent = True
        return action

    def log_outcome(self, offer_id: UUID, outcome: CockpitOutcome) -> CockpitOutcome:
        if not self.actions[offer_id].sent:
            raise PermissionError("cannot_log_outcome_before_approved_outreach")
        self.outcomes.append(outcome)
        self.service.apply_outcome_learning(outcome.lane_id, outcome.source_id, revenue=outcome.revenue, reply=outcome.replies > 0, legal_risk=1 if outcome.legal_access_issue else 0, operator_hours=outcome.operator_hours)
        self.actions[offer_id].status = ApprovalStatus.WON if outcome.paid_conversions else ApprovalStatus.LOST
        return outcome

    def daily_report(self) -> DailyRevenueReport:
        sent = sum(1 for action in self.actions.values() if action.sent)
        return DailyRevenueReport(len(self.signals), len(self.signals), len(self.offers), len(self.offers), sent, len(self.offers), len([outcome for outcome in self.outcomes if outcome.lesson]))

    def snapshot(self) -> dict[str, object]:
        report = self.daily_report()
        return {"signal_inbox": len(self.signals), "today_revenue_queue": len(self.offers), "research_backlog": list(self.backlog), "outreach_approval_queue": [str(action.offer_id) for action in self.actions.values() if action.status == ApprovalStatus.APPROVAL_REQUIRED], "source_scores": dict(self.service.source_scores), "daily_revenue_report": {"passed": report.passed, "gaps": report.gaps}}


def reconcile_go_hold(issues: list[dict], reports: list[dict]) -> list[str]:
    by_number = {int(issue["issue_number"]): issue for issue in issues}
    failures = []
    for report in reports:
        if report.get("verdict") != "GO":
            continue
        for number in report.get("issue_numbers", []):
            issue = by_number[int(number)]
            if issue.get("issue_state") != "closed" and not issue.get("explicit_open_reason"):
                failures.append(f"GO report {report['report_id']} references open issue #{number}")
            if not issue.get("evidence_refs") or not report.get("evidence_refs"):
                failures.append(f"GO report {report['report_id']} or issue #{number} lacks evidence")
    return failures


def load_go_hold_reconciliation(path: str | Path) -> list[str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return reconcile_go_hold(data["issues"], data["reports"])
