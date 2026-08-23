from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class UnknownMechanism:
    question: str
    context_refs: list[str]
    status: str = "unknown"
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class TheoryCandidate:
    mechanism_id: UUID
    name: str
    explanation: str
    status: str
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class TheoryCompetition:
    mechanism_id: UUID
    theory_ids: list[UUID]
    preserved_alternatives: bool
    id: UUID = field(default_factory=uuid4)


@dataclass
class TheoryRegistryService:
    unknowns: dict[UUID, UnknownMechanism] = field(default_factory=dict)
    theories: dict[UUID, TheoryCandidate] = field(default_factory=dict)
    competitions: list[TheoryCompetition] = field(default_factory=list)

    def register_unknown(self, *, question: str, context_refs: list[str]) -> UnknownMechanism:
        if not context_refs:
            raise ValueError("unknown_mechanism_requires_context")
        unknown = UnknownMechanism(question=question, context_refs=list(context_refs), status="unknown")
        self.unknowns[unknown.id] = unknown
        return unknown

    def add_theory(
        self,
        unknown: UnknownMechanism,
        *,
        name: str,
        explanation: str,
        speculative: bool,
        evidence_refs: list[str],
    ) -> TheoryCandidate:
        status = "speculative" if speculative else "candidate"
        theory = TheoryCandidate(
            mechanism_id=unknown.id,
            name=name,
            explanation=explanation,
            status=status,
            evidence_refs=list(evidence_refs),
        )
        self.theories[theory.id] = theory
        return theory

    def create_competition(self, unknown: UnknownMechanism, theory_ids: list[UUID]) -> TheoryCompetition:
        if len(theory_ids) < 2:
            raise ValueError("theory_competition_requires_alternatives")
        for theory_id in theory_ids:
            if theory_id not in self.theories:
                raise ValueError("theory_missing")
        competition = TheoryCompetition(
            mechanism_id=unknown.id,
            theory_ids=list(theory_ids),
            preserved_alternatives=True,
        )
        self.competitions.append(competition)
        return competition

    def promote_theory(self, theory: TheoryCandidate, *, evidence_refs: list[str]) -> TheoryCandidate:
        if len(evidence_refs) < 2:
            raise ValueError("theory_promotion_requires_evidence")
        theory.status = "supported"
        theory.evidence_refs = sorted(set(theory.evidence_refs + list(evidence_refs)))
        return theory
