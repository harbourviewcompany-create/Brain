from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class CapabilityClaim:
    name: str
    confidence: float
    evidence_refs: list[str]
    test_refs: list[str]
    acceptance_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class LimitationRecord:
    limitation: str
    effect: str
    preserved: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class LearningDebt:
    area: str
    severity: float
    evidence_gap: str
    priority: float
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class SelfAssessment:
    capability_count: int
    limitation_count: int
    learning_debt_priority: float
    overclaim_blocked: bool
    id: UUID = field(default_factory=uuid4)


@dataclass
class SelfModelService:
    capabilities: list[CapabilityClaim] = field(default_factory=list)
    limitations: list[LimitationRecord] = field(default_factory=list)
    debts: list[LearningDebt] = field(default_factory=list)
    assessments: list[SelfAssessment] = field(default_factory=list)

    def claim_capability(
        self,
        *,
        name: str,
        confidence: float,
        evidence_refs: list[str],
        test_refs: list[str],
        acceptance_refs: list[str],
    ) -> CapabilityClaim:
        if not evidence_refs or not test_refs or not acceptance_refs:
            raise ValueError("capability_claim_requires_evidence_tests_acceptance")
        claim = CapabilityClaim(
            name=name,
            confidence=min(1.0, max(0.0, confidence)),
            evidence_refs=list(evidence_refs),
            test_refs=list(test_refs),
            acceptance_refs=list(acceptance_refs),
        )
        self.capabilities.append(claim)
        return claim

    def record_limitation(self, *, limitation: str, effect: str) -> LimitationRecord:
        record = LimitationRecord(limitation=limitation, effect=effect, preserved=True)
        self.limitations.append(record)
        return record

    def add_learning_debt(self, *, area: str, severity: float, evidence_gap: str) -> LearningDebt:
        priority = min(1.0, max(0.0, severity))
        debt = LearningDebt(area=area, severity=severity, evidence_gap=evidence_gap, priority=priority)
        self.debts.append(debt)
        return debt

    def assess(self) -> SelfAssessment:
        debt_priority = max((debt.priority for debt in self.debts), default=0.0)
        overclaim_blocked = any(limit.preserved for limit in self.limitations)
        assessment = SelfAssessment(
            capability_count=len(self.capabilities),
            limitation_count=len(self.limitations),
            learning_debt_priority=debt_priority,
            overclaim_blocked=overclaim_blocked,
        )
        self.assessments.append(assessment)
        return assessment

    def can_claim(self, capability_name: str) -> bool:
        return any(claim.name == capability_name for claim in self.capabilities)
