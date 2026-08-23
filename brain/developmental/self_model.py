from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from ..domain import utcnow


@dataclass(slots=True)
class CapabilityRecord:
    name: str
    confidence: float
    evidence_refs: list[str]
    fixture_refs: list[str] = field(default_factory=list)
    test_refs: list[str] = field(default_factory=list)
    acceptance_refs: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class LimitationRecord:
    description: str
    evidence_refs: list[str]
    active: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class LearningDebt:
    topic: str
    severity: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class EvidenceGap:
    topic: str
    missing_evidence: list[str]
    severity: float
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class SelfModel:
    capabilities: dict[str, CapabilityRecord] = field(default_factory=dict)
    limitations: list[LimitationRecord] = field(default_factory=list)
    learning_debt: list[LearningDebt] = field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = field(default_factory=list)
    fatigue: float = 0.0
    load: float = 0.0
    updated_at: datetime = field(default_factory=utcnow)


class CapabilityLedgerService:
    def register(self, record: CapabilityRecord) -> CapabilityRecord:
        if not record.evidence_refs:
            raise ValueError("capability claim requires evidence")
        if not record.test_refs or not record.fixture_refs or not record.acceptance_refs:
            raise ValueError("capability claim requires fixture, test and acceptance evidence")
        record.confidence = max(0.0, min(1.0, record.confidence))
        return record

    @staticmethod
    def claimable(record: CapabilityRecord) -> bool:
        return bool(
            record.evidence_refs
            and record.fixture_refs
            and record.test_refs
            and record.acceptance_refs
            and record.confidence >= 0.5
        )


class SelfModelService:
    def __init__(self, model: SelfModel | None = None) -> None:
        self.model = model or SelfModel()
        self.ledger = CapabilityLedgerService()

    def add_capability(self, record: CapabilityRecord) -> CapabilityRecord:
        record = self.ledger.register(record)
        self.model.capabilities[record.name] = record
        self.model.updated_at = utcnow()
        return record

    def add_limitation(self, limitation: LimitationRecord) -> None:
        if not limitation.evidence_refs:
            raise ValueError("limitation record requires evidence")
        self.model.limitations.append(limitation)
        self.model.updated_at = utcnow()

    def add_learning_debt(self, debt: LearningDebt) -> None:
        if not debt.evidence_refs:
            raise ValueError("learning debt requires evidence")
        debt.severity = max(0.0, min(1.0, debt.severity))
        self.model.learning_debt.append(debt)
        self.model.updated_at = utcnow()

    def add_evidence_gap(self, gap: EvidenceGap) -> None:
        gap.severity = max(0.0, min(1.0, gap.severity))
        self.model.evidence_gaps.append(gap)
        self.model.updated_at = utcnow()

    def learning_priority(self, topic: str) -> float:
        debt = max((item.severity for item in self.model.learning_debt if item.topic == topic), default=0.0)
        gap = max((item.severity for item in self.model.evidence_gaps if item.topic == topic), default=0.0)
        return max(0.0, min(1.0, debt * 0.6 + gap * 0.4))

    def can_claim(self, capability_name: str) -> bool:
        record = self.model.capabilities.get(capability_name)
        if record is None or not self.ledger.claimable(record):
            return False
        blocked = any(
            limitation.active and capability_name.lower() in limitation.description.lower()
            for limitation in self.model.limitations
        )
        return not blocked
