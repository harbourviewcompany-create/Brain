from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class ImmuneAlert:
    target_ref: str
    alert_type: str
    severity: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class QuarantineRecord:
    target_ref: str
    reason: str
    alert_id: UUID
    recoverable: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class RecoveryPlan:
    quarantine_id: UUID
    required_evidence_refs: list[str]
    steps: list[str]
    status: str = "planned"
    id: UUID = field(default_factory=uuid4)


@dataclass
class CognitiveImmuneService:
    alerts: list[ImmuneAlert] = field(default_factory=list)
    quarantines: list[QuarantineRecord] = field(default_factory=list)
    recovery_plans: list[RecoveryPlan] = field(default_factory=list)

    def alert(self, *, target_ref: str, alert_type: str, severity: float, evidence_refs: list[str]) -> ImmuneAlert:
        if not evidence_refs:
            raise ValueError("immune_alert_requires_evidence")
        alert = ImmuneAlert(target_ref, alert_type, min(1.0, max(0.0, severity)), list(evidence_refs))
        self.alerts.append(alert)
        return alert

    def quarantine(self, alert: ImmuneAlert, *, reason: str) -> QuarantineRecord:
        record = QuarantineRecord(alert.target_ref, reason, alert.id, recoverable=True)
        self.quarantines.append(record)
        return record

    def detect_approval_bypass(self, *, action_ref: str, evidence_refs: list[str]) -> QuarantineRecord:
        alert = self.alert(
            target_ref=action_ref,
            alert_type="approval_bypass",
            severity=1.0,
            evidence_refs=evidence_refs,
        )
        return self.quarantine(alert, reason="external_action_without_approval")

    def detect_contaminated_source(self, *, source_ref: str, evidence_refs: list[str]) -> QuarantineRecord:
        alert = self.alert(
            target_ref=source_ref,
            alert_type="source_contamination",
            severity=0.95,
            evidence_refs=evidence_refs,
        )
        return self.quarantine(alert, reason="unsafe_or_unlicensed_source")

    def detect_overconfidence(
        self,
        *,
        claim_ref: str,
        confidence: float,
        evidence_count: int,
        evidence_refs: list[str],
    ) -> ImmuneAlert | None:
        if confidence >= 0.9 and evidence_count < 2:
            return self.alert(
                target_ref=claim_ref,
                alert_type="overconfidence",
                severity=confidence,
                evidence_refs=evidence_refs,
            )
        return None

    def create_recovery_plan(
        self,
        quarantine: QuarantineRecord,
        *,
        required_evidence_refs: list[str],
        steps: list[str],
    ) -> RecoveryPlan:
        if not required_evidence_refs:
            raise ValueError("recovery_requires_evidence")
        plan = RecoveryPlan(quarantine.id, list(required_evidence_refs), list(steps))
        self.recovery_plans.append(plan)
        return plan
