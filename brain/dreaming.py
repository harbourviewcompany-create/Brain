from __future__ import annotations

from dataclasses import dataclass

from .domain import Belief


@dataclass(slots=True)
class DreamHypothesis:
    statement: str
    reason: str
    confidence: float


class DreamEngine:
    """Offline recombination. It proposes; it never silently converts a dream into fact."""

    def recombine(self, beliefs: list[Belief]) -> list[DreamHypothesis]:
        active = [b for b in beliefs if b.confidence >= 0.55]
        active.sort(key=lambda b: b.confidence, reverse=True)
        hypotheses: list[DreamHypothesis] = []
        for left, right in zip(active, active[1:]):
            hypotheses.append(
                DreamHypothesis(
                    statement=f"Possible relationship between [{left.statement}] and [{right.statement}]",
                    reason="High-confidence beliefs were adjacent during offline recombination.",
                    confidence=min(left.confidence, right.confidence) * 0.5,
                )
            )
        return hypotheses
