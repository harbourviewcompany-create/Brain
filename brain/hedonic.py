from __future__ import annotations

"""Generic reward and pain.

``brain/reward.py`` is real but entirely business-scoped: it scores
``Outcome.value_created``, ``legal_risk``, ``operator_time_cost`` -- KPIs,
not hedonic experience. A real brain's dopaminergic reward system doesn't
know what a KPI is; it responds to prediction error against expected
value, the same circuitry whether the outcome is a business deal or
finding food. Nothing in this repo modeled that domain-neutral layer, so
anything outside the Capital Discovery Cortex had no reward signal to
learn from at all.

This models reward prediction error (the actual dopaminergic
mechanism -- Schultz's finding that dopamine neurons fire for *unexpected*
reward and for cues that predict it, not for expected reward itself,
and go *below* baseline when an expected reward fails to arrive) plus a
distinct nociceptive/pain pathway for punishment signals that isn't just
"negative reward" -- pain has its own urgency/withdrawal-driving character
that a symmetric reward scale doesn't capture.
"""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from .cognitive_state import NeuromodulatorState
from .domain import utcnow


@dataclass(slots=True)
class RewardPredictionError:
    """The actual unit of dopaminergic signaling: not the reward itself,
    but how much it deviated from what was expected. This is what makes
    reward learning possible at all -- a system that only registers
    absolute reward magnitude can't tell "as expected" from "surprisingly
    good," and both TD-learning and real dopamine neurons care about the
    delta, not the level.
    """

    expected_value: float
    actual_value: float
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)

    @property
    def delta(self) -> float:
        return self.actual_value - self.expected_value

    @property
    def is_positive_surprise(self) -> bool:
        return self.delta > 0

    @property
    def magnitude(self) -> float:
        return abs(self.delta)


@dataclass(slots=True)
class PainSignal:
    """Nociception, not just negative reward. Distinguished by an urgency/
    withdrawal component: real pain drives immediate avoidance behavior in
    a way that a merely-low-reward outcome doesn't, and it decays on its
    own timeline rather than being folded back into a single valence
    scalar the way brain/affect.py's EmotionalState already is (this
    module produces the raw nociceptive signal; affect appraisal is free
    to consume it as one input among several)."""

    intensity: float  # [0, 1]
    source: str
    withdrawal_urgency: float  # [0, 1]
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)


@dataclass
class HedonicSystem:
    """The domain-neutral reward/pain engine. Any organ -- economic or
    otherwise -- reports (expected, actual) value here and gets back a
    prediction-error-based signal plus a neuromodulator write, instead of
    routing everything through business-KPI scoring.

    baseline_dopamine tracks a slow-moving expectation level itself (tonic
    dopamine), separate from the phasic per-event delta, matching the
    tonic/phasic distinction in the real dopaminergic system.
    """

    baseline_dopamine: float = 0.5
    baseline_momentum: float = 0.95
    recent_errors: list[RewardPredictionError] = field(default_factory=list)
    recent_pain: list[PainSignal] = field(default_factory=list)
    max_history: int = 500

    def register_outcome(self, *, expected_value: float, actual_value: float) -> RewardPredictionError:
        rpe = RewardPredictionError(expected_value=expected_value, actual_value=actual_value)
        self.recent_errors.append(rpe)
        if len(self.recent_errors) > self.max_history:
            self.recent_errors.pop(0)

        # Tonic dopamine baseline drifts toward whatever's actually being
        # received, slowly -- this is what produces hedonic adaptation:
        # a reward that repeats stops producing positive prediction error
        # once it becomes the expectation.
        w = 1 - self.baseline_momentum
        normalized_actual = max(0.0, min(1.0, 0.5 + 0.5 * actual_value))
        self.baseline_dopamine = (
            self.baseline_momentum * self.baseline_dopamine + w * normalized_actual
        )
        self.baseline_dopamine = max(0.0, min(1.0, self.baseline_dopamine))
        return rpe

    def register_pain(self, *, intensity: float, source: str) -> PainSignal:
        intensity = max(0.0, min(1.0, intensity))
        signal = PainSignal(
            intensity=intensity,
            source=source,
            withdrawal_urgency=min(1.0, intensity * 1.3),
        )
        self.recent_pain.append(signal)
        if len(self.recent_pain) > self.max_history:
            self.recent_pain.pop(0)
        return signal

    def modulator_delta(
        self, rpe: RewardPredictionError | None = None, pain: PainSignal | None = None
    ) -> NeuromodulatorState:
        """Phasic dopamine tracks prediction error (up on positive
        surprise, dipping below baseline on a worse-than-expected/omitted
        reward -- the below-baseline dip on omission is a specific,
        well-established finding, not just "less positive"). Pain raises
        stress and norepinephrine independent of any dopamine effect.
        """
        dopamine = self.baseline_dopamine
        if rpe is not None:
            dopamine = self.baseline_dopamine + 0.5 * rpe.delta
        stress = 0.2
        norepinephrine = 0.4
        if pain is not None:
            stress = 0.2 + 0.7 * pain.intensity
            norepinephrine = 0.4 + 0.5 * pain.withdrawal_urgency
            dopamine -= 0.3 * pain.intensity

        return NeuromodulatorState(
            dopamine=dopamine,
            norepinephrine=norepinephrine,
            serotonin=0.5,
            acetylcholine=0.5,
            stress=stress,
        ).clamp()

    def hedonic_tone(self) -> float:
        """A single-number read of "how has it been going lately,"
        [-1, 1], from recent prediction errors net of recent pain --
        useful as an input to Mood in brain/affect.py without affect
        needing to know anything about outcomes/expectations itself."""
        if not self.recent_errors and not self.recent_pain:
            return 0.0
        reward_component = 0.0
        if self.recent_errors:
            window = self.recent_errors[-20:]
            reward_component = sum(e.delta for e in window) / len(window)
        pain_component = 0.0
        if self.recent_pain:
            window_p = self.recent_pain[-20:]
            pain_component = sum(p.intensity for p in window_p) / len(window_p)
        tone = reward_component - pain_component
        return max(-1.0, min(1.0, tone))
