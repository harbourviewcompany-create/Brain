from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from ..domain import utcnow


class ImmuneSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(slots=True)
class ImmuneAlert:
    alert_type: str
    severity: ImmuneSeverity
    reason: str
    evidence_refs: list[str]
    target_id: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class QuarantineRecord:
    target_id: str
    alert_id: UUID
    reason: str
    active: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ContaminationTrace:
    source_id: str
    contamination_type: str
    evidence_refs: list[str]
    blocked: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class RecoveryPlan:
    target_id: str
    remediation_steps: list[str]
    evidence_refs: list[str]
    verified: bool = False
    id: UUID = field(default_factory=uuid4)


class CognitiveImmuneService:
    """Fail-closed detectors for unsafe cognition and unsafe development."""

    def scan(
        self,
        *,
        target_id: str,
        approval_required: bool = False,
        approval_present: bool = False,
        source_contaminated: bool = False,
        confidence: float = 0.0,
        evidence_count: int = 0,
        stale_evidence: bool = False,
        circular_reinforcement: bool = False,
        reward_hacking_signal: bool = False,
        evidence_refs: list[str] | None = None,
    ) -> list[ImmuneAlert]:
        refs = list(evidence_refs or [])
        alerts: list[ImmuneAlert] = []
        if approval_required and not approval_present:
            alerts.append(
                ImmuneAlert(
                    "approval_bypass",
                    ImmuneSeverity.CRITICAL,
                    "consequential transition lacks required approval",
                    refs,
                    target_id,
                )
            )
        if source_contaminated:
            alerts.append(
                ImmuneAlert(
                    "source_contamination",
                    ImmuneSeverity.CRITICAL,
                    "source is marked contaminated or prohibited",
                    refs,
                    target_id,
                )
            )
        if confidence >= 0.9 and evidence_count == 0:
            alerts.append(
                ImmuneAlert(
                    "unsupported_overconfidence",
                    ImmuneSeverity.HIGH,
                    "high confidence has no supporting evidence",
                    refs,
                    target_id,
                )
            )
        if stale_evidence:
            alerts.append(
                ImmuneAlert(
                    "stale_evidence",
                    ImmuneSeverity.WARNING,
                    "decision relies on stale evidence",
                    refs,
                    target_id,
                )
            )
        if circular_reinforcement:
            alerts.append(
                ImmuneAlert(
                    "circular_reinforcement",
                    ImmuneSeverity.HIGH,
                    "derived claims are recursively reinforcing their own source chain",
                    refs,
                    target_id,
                )
            )
        if reward_hacking_signal:
            alerts.append(
                ImmuneAlert(
                    "reward_hacking",
                    ImmuneSeverity.CRITICAL,
                    "optimization signal appears to bypass protected objectives",
                    refs,
                    target_id,
                )
            )
        return alerts

    @staticmethod
    def should_block(alerts: list[ImmuneAlert]) -> bool:
        return any(alert.severity in {ImmuneSeverity.HIGH, ImmuneSeverity.CRITICAL} for alert in alerts)


class QuarantineService:
    def quarantine(self, target_id: str, alert: ImmuneAlert) -> QuarantineRecord:
        if alert.target_id not in {None, target_id}:
            raise ValueError("alert targets another object")
        return QuarantineRecord(
            target_id=target_id,
            alert_id=alert.id,
            reason=alert.reason,
            active=True,
        )

    def contamination_trace(
        self, source_id: str, contamination_type: str, evidence_refs: list[str]
    ) -> ContaminationTrace:
        if not evidence_refs:
            raise ValueError("contamination trace requires evidence")
        return ContaminationTrace(
            source_id=source_id,
            contamination_type=contamination_type,
            evidence_refs=list(evidence_refs),
            blocked=True,
        )


class RecoveryService:
    def plan(self, target_id: str, remediation_steps: list[str], evidence_refs: list[str]) -> RecoveryPlan:
        if not remediation_steps:
            raise ValueError("recovery requires remediation steps")
        return RecoveryPlan(target_id, list(remediation_steps), list(evidence_refs), False)

    def verify(self, plan: RecoveryPlan, verification_evidence: list[str]) -> RecoveryPlan:
        if not verification_evidence:
            raise ValueError("recovery cannot complete without evidence")
        plan.evidence_refs = sorted(set(plan.evidence_refs + verification_evidence))
        plan.verified = True
        return plan
