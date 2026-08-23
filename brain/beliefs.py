from __future__ import annotations

from dataclasses import replace

from .domain import Belief, BeliefState, Evidence, utcnow


class BeliefEngine:
    """Updates beliefs without erasing evidence provenance."""

    def __init__(self, max_delta: float = 0.20):
        self.max_delta = max_delta

    def apply_evidence(self, belief: Belief, evidence: Evidence, supports: bool) -> Belief:
        reliability = max(0.0, min(1.0, evidence.reliability))
        raw_delta = (reliability * 0.25) * (1 if supports else -1)
        delta = max(-self.max_delta, min(self.max_delta, raw_delta))
        confidence = max(0.0, min(1.0, belief.confidence + delta))

        supporting = set(belief.supporting_evidence)
        contradicting = set(belief.contradicting_evidence)
        (supporting if supports else contradicting).add(evidence.id)

        state = belief.state
        if supporting and contradicting:
            state = BeliefState.CONTESTED
        elif confidence >= 0.85:
            state = BeliefState.ESTABLISHED
        elif confidence >= 0.65:
            state = BeliefState.PROVISIONAL
        elif confidence <= 0.15:
            state = BeliefState.REJECTED

        return replace(
            belief,
            confidence=confidence,
            state=state,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            updated_at=utcnow(),
            version=belief.version + 1,
        )

    def decay(self, belief: Belief, rate: float = 0.02) -> Belief:
        target = 0.5
        confidence = belief.confidence + (target - belief.confidence) * max(0.0, rate)
        return replace(belief, confidence=confidence, updated_at=utcnow(), version=belief.version + 1)
