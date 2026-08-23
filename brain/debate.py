from __future__ import annotations

from dataclasses import dataclass

from .domain import Belief, CandidateAction


@dataclass(slots=True)
class DebateVerdict:
    recommendation: str
    arguments_for: list[str]
    arguments_against: list[str]
    confidence: float


class DebateChamber:
    """Deterministic shell for later multi-model / multi-agent evaluators."""

    def judge(self, belief: Belief, action: CandidateAction) -> DebateVerdict:
        pros = [f"Belief confidence={belief.confidence:.2f}", f"Expected value={action.expected_value:.2f}"]
        cons = [f"Action uncertainty={action.uncertainty:.2f}"]
        score = belief.confidence * action.expected_value - action.uncertainty
        recommendation = "advance" if score > 0.25 else "research_more" if score > 0 else "hold"
        return DebateVerdict(recommendation, pros, cons, max(0.0, min(1.0, 0.5 + score / 2)))
