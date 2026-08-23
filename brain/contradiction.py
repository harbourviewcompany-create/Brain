from dataclasses import dataclass
from uuid import UUID

from .domain import Belief, Evidence


@dataclass(slots=True)
class Contradiction:
    belief_id: UUID
    evidence_id: UUID
    severity: float
    question: str


class ContradictionEngine:
    def inspect(self, belief: Belief, evidence: Evidence, supports: bool) -> Contradiction | None:
        if supports:
            return None
        severity = evidence.reliability * max(0.1, belief.confidence)
        return Contradiction(
            belief_id=belief.id,
            evidence_id=evidence.id,
            severity=min(1.0, severity),
            question=f"What observation would resolve the contradiction around: {belief.statement}?",
        )
