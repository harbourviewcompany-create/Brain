from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from ..domain import utcnow


class TheoryStatus(StrEnum):
    SPECULATIVE = "speculative"
    SUPPORTED = "supported"
    DISPUTED = "disputed"
    REJECTED = "rejected"


@dataclass(slots=True)
class UnknownMechanism:
    name: str
    description: str
    evidence_refs: list[str]
    tests_needed: list[str] = field(default_factory=list)
    open: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class TheoryRecord:
    name: str
    explanation: str
    evidence_refs: list[str]
    status: TheoryStatus = TheoryStatus.SPECULATIVE
    confidence: float = 0.0
    falsification_tests: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class TheoryCompetition:
    question: str
    theory_ids: list[UUID]
    evidence_refs: list[str]
    leading_theory_id: UUID | None = None
    unresolved: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class OpenQuestion:
    question: str
    mechanism_ids: list[UUID] = field(default_factory=list)
    theory_ids: list[UUID] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)


class UnknownMechanismRegistryService:
    def __init__(self) -> None:
        self.items: dict[UUID, UnknownMechanism] = {}

    def register(self, item: UnknownMechanism) -> UnknownMechanism:
        if not item.name.strip() or not item.description.strip():
            raise ValueError("unknown mechanism requires name and description")
        self.items[item.id] = item
        return item

    def close(self, item_id: UUID, *, evidence_refs: list[str]) -> UnknownMechanism:
        if not evidence_refs:
            raise ValueError("unknown mechanism cannot be closed without evidence")
        item = self.items[item_id]
        item.evidence_refs = sorted(set(item.evidence_refs + evidence_refs))
        item.open = False
        return item


class TheoryRegistryService:
    def __init__(self) -> None:
        self.theories: dict[UUID, TheoryRecord] = {}

    def register(self, theory: TheoryRecord) -> TheoryRecord:
        theory.confidence = max(0.0, min(1.0, theory.confidence))
        self.theories[theory.id] = theory
        return theory

    def promote(self, theory_id: UUID, *, evidence_refs: list[str], confidence: float) -> TheoryRecord:
        if not evidence_refs:
            raise ValueError("theory promotion requires new evidence")
        theory = self.theories[theory_id]
        theory.evidence_refs = sorted(set(theory.evidence_refs + evidence_refs))
        theory.confidence = max(0.0, min(1.0, confidence))
        theory.status = TheoryStatus.SUPPORTED if theory.confidence >= 0.6 else TheoryStatus.SPECULATIVE
        return theory

    def reject(self, theory_id: UUID, *, evidence_refs: list[str]) -> TheoryRecord:
        if not evidence_refs:
            raise ValueError("theory rejection requires falsifying evidence")
        theory = self.theories[theory_id]
        theory.evidence_refs = sorted(set(theory.evidence_refs + evidence_refs))
        theory.status = TheoryStatus.REJECTED
        return theory


class TheoryCompetitionService:
    def compete(
        self,
        question: str,
        theories: list[TheoryRecord],
        *,
        evidence_refs: list[str],
    ) -> TheoryCompetition:
        if len(theories) < 2:
            raise ValueError("theory competition requires alternatives")
        if not evidence_refs:
            raise ValueError("theory competition requires evidence")
        eligible = [theory for theory in theories if theory.status is not TheoryStatus.REJECTED]
        leading = max(eligible, key=lambda theory: theory.confidence, default=None)
        if leading is not None:
            tied = [theory for theory in eligible if abs(theory.confidence - leading.confidence) < 0.05]
            unresolved = len(tied) > 1 or leading.confidence < 0.75
        else:
            unresolved = True
        return TheoryCompetition(
            question=question,
            theory_ids=[theory.id for theory in theories],
            evidence_refs=list(evidence_refs),
            leading_theory_id=leading.id if leading else None,
            unresolved=unresolved,
        )
