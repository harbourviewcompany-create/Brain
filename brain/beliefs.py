from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Mapping
from uuid import UUID

from .domain import Belief, BeliefState, Evidence, utcnow

SUPPORTS_PREFIX = "supports:"
CONTRADICTS_PREFIX = "contradicts:"


def evidence_fingerprint(evidence: Evidence, supports: bool) -> str:
    """Identify what an item of evidence actually asserts.

    Two records that carry the same claim from the same source on the same side
    are the same assertion no matter how many times they are submitted, so they
    share a fingerprint. Confidence may move for the first one and must not move
    again for the repeats.
    """

    stance = SUPPORTS_PREFIX if supports else CONTRADICTS_PREFIX
    source = (evidence.source_id or "unknown").strip().lower()
    claim = " ".join((evidence.claim or "").split()).lower()
    return f"{stance}{source}|{claim}"


def _count_side(fingerprints: Iterable[str], supports: bool) -> int:
    prefix = SUPPORTS_PREFIX if supports else CONTRADICTS_PREFIX
    return sum(1 for item in fingerprints if item.startswith(prefix))


def rebuild_fingerprints(
    belief: Belief,
    evidence_index: Mapping[UUID, Evidence],
) -> Belief:
    """Recompute a belief's fingerprint set from its linked evidence.

    Fingerprints are derived state, not a new column: stores reconstruct them on
    hydrate from the evidence rows they already hold, so deduplication survives a
    process restart without a schema change.
    """

    fingerprints: set[str] = set()
    for evidence_id in belief.supporting_evidence:
        record = evidence_index.get(evidence_id)
        if record is not None:
            fingerprints.add(evidence_fingerprint(record, True))
    for evidence_id in belief.contradicting_evidence:
        record = evidence_index.get(evidence_id)
        if record is not None:
            fingerprints.add(evidence_fingerprint(record, False))
    belief.evidence_fingerprints = fingerprints
    return belief


class BeliefEngine:
    """Updates beliefs without erasing evidence provenance."""

    #: Largest confidence move a single item of evidence may cause.
    def __init__(self, max_delta: float = 0.20, contested_ratio: float = 3.0):
        self.max_delta = max_delta
        # A belief is contested while the minority side holds at least
        # 1/contested_ratio of the majority's distinct assertions.
        self.contested_ratio = contested_ratio

    def apply_evidence(self, belief: Belief, evidence: Evidence, supports: bool) -> Belief:
        supporting = set(belief.supporting_evidence)
        contradicting = set(belief.contradicting_evidence)
        fingerprints = set(belief.evidence_fingerprints)

        fingerprint = evidence_fingerprint(evidence, supports)
        already_asserted = fingerprint in fingerprints

        # Provenance always records the submission, even a repeat: the ledger
        # should show that a source said this again.
        (supporting if supports else contradicting).add(evidence.id)

        if already_asserted:
            # Restating a claim is not new information. Attach it and stop.
            delta = 0.0
        else:
            reliability = max(0.0, min(1.0, evidence.reliability))
            # Diminishing returns per side: the tenth independent corroboration
            # moves a belief far less than the first, so confidence tracks the
            # breadth of evidence rather than its raw volume.
            prior_on_side = _count_side(fingerprints, supports)
            raw_delta = (reliability * 0.25) / (1 + prior_on_side)
            delta = min(self.max_delta, raw_delta) * (1 if supports else -1)
            fingerprints.add(fingerprint)

        confidence = max(0.0, min(1.0, belief.confidence + delta))
        state = self._classify(
            belief,
            confidence=confidence,
            supporting=_count_side(fingerprints, True),
            contradicting=_count_side(fingerprints, False),
        )

        return replace(
            belief,
            confidence=confidence,
            state=state,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            evidence_fingerprints=fingerprints,
            updated_at=utcnow(),
            version=belief.version + 1,
        )

    def _classify(
        self,
        belief: Belief,
        *,
        confidence: float,
        supporting: int,
        contradicting: int,
    ) -> BeliefState:
        """Derive state from the evidence a belief currently holds.

        State is recomputed from the present balance rather than latched. A
        single stale objection used to pin a belief to CONTESTED permanently,
        because evidence sets only ever grow and the contested branch was
        checked before every confidence threshold -- so a belief with one
        contradiction and twenty strong corroborations reported as contested at
        confidence 1.0, and could never be REJECTED either.
        """

        if supporting and contradicting:
            weaker = min(supporting, contradicting)
            stronger = max(supporting, contradicting)
            if weaker * self.contested_ratio >= stronger:
                return BeliefState.CONTESTED

        if confidence >= 0.85:
            return BeliefState.ESTABLISHED
        if confidence >= 0.65:
            return BeliefState.PROVISIONAL
        if confidence <= 0.15:
            return BeliefState.REJECTED

        # Mid-range and no longer contested: fall back to the prior state, but
        # never re-latch CONTESTED after the balance has moved past it.
        if belief.state is BeliefState.CONTESTED:
            return BeliefState.HYPOTHESIS
        return belief.state

    def decay(self, belief: Belief, rate: float = 0.02) -> Belief:
        target = 0.5
        confidence = belief.confidence + (target - belief.confidence) * max(0.0, rate)
        return replace(belief, confidence=confidence, updated_at=utcnow(), version=belief.version + 1)
