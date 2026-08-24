from __future__ import annotations

"""Motor execution and error-driven adaptation.

``brain/governance.py`` decides whether an action is *allowed* to run.
Nothing decides how it actually runs, or learns from how well it worked.
A real motor system doesn't just fire-and-forget a command: it holds a
forward-model prediction of the expected outcome, compares that to what
actually happened, and adjusts an internal gain/calibration parameter
from the error -- this is cerebellar motor learning, the same mechanism
behind prism adaptation (people re-aim correctly within ~20 throws when
wearing displacing prism goggles, purely from error feedback, with no
explicit reasoning about the prism).

This is distinct from ``brain/hedonic.py``'s reward-prediction-error: that
tracks whether an outcome was *good*; this tracks whether an outcome
matched what was *expected to physically happen*, independent of whether
the result was desirable. A perfectly-executed action with a bad outcome
should not degrade motor calibration; a badly-executed action with a
lucky good outcome should.
"""

from dataclasses import dataclass, field
from typing import Callable
from uuid import UUID, uuid4

from .domain import CandidateAction, utcnow
from .governance import GovernanceDecision, GovernanceGovernor


@dataclass(slots=True)
class MotorPrediction:
    """The forward-model's expectation before the action is executed --
    e.g. 'this outreach should reach the counterparty within 2 hours.'
    Expressed as a single scalar the actuator's domain defines (time,
    magnitude, whatever the action's own units are), kept deliberately
    generic so this works for any effector."""

    expected_outcome: float
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class MotorExecutionResult:
    action: CandidateAction
    prediction: MotorPrediction
    actual_outcome: float
    succeeded: bool
    error: float = field(init=False)
    id: UUID = field(default_factory=uuid4)
    executed_at: object = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        self.error = self.actual_outcome - self.prediction.expected_outcome


@dataclass(slots=True)
class MotorCalibration:
    """A per-effector gain the way cerebellar adaptation adjusts reach
    amplitude/direction. Starts at 1.0 (no correction); drifts based on
    the sign and size of repeated execution error, capped so a single
    wild outlier can't blow out calibration -- real adaptation is
    incremental across trials, not a single-shot correction."""

    gain: float = 1.0
    learning_rate: float = 0.1
    max_step: float = 0.15

    def update(self, result: MotorExecutionResult) -> MotorCalibration:
        if result.prediction.expected_outcome == 0:
            return self
        relative_error = result.error / max(1e-6, abs(result.prediction.expected_outcome))
        # Negative feedback, same direction real closed-loop motor
        # adaptation moves in: if the effector overshot the commanded
        # amplitude (positive error), reduce gain so the next command is
        # smaller; if it undershot, increase gain. A positive-feedback
        # sign here would make calibration diverge instead of converge.
        step = max(-self.max_step, min(self.max_step, -self.learning_rate * relative_error))
        self.gain = max(0.1, min(3.0, self.gain + step))
        return self


Effector = Callable[[CandidateAction, float], float]
"""A concrete effector: takes the action and the calibrated expected
outcome, executes it in the world, and returns the actual outcome. This
is the only place real-world side effects happen -- everything else in
this module is prediction/comparison/adaptation."""


@dataclass
class MotorExecutionService:
    """Wires governance approval -> calibrated prediction -> execution ->
    error-driven recalibration into one loop, per named effector so
    different action types (email outreach vs. API call vs. whatever)
    maintain independent calibration the way different muscle groups do.
    """

    governor: GovernanceGovernor = field(default_factory=GovernanceGovernor)
    calibrations: dict[str, MotorCalibration] = field(default_factory=dict)
    history: list[MotorExecutionResult] = field(default_factory=list)
    max_history: int = 500

    def _calibration_for(self, effector_name: str) -> MotorCalibration:
        if effector_name not in self.calibrations:
            self.calibrations[effector_name] = MotorCalibration()
        return self.calibrations[effector_name]

    def execute(
        self,
        action: CandidateAction,
        *,
        effector_name: str,
        effector: Effector,
        raw_expected_outcome: float,
        external_actions_enabled: bool = False,
        success_predicate: Callable[[float, float], bool] | None = None,
    ) -> tuple[GovernanceDecision, MotorExecutionResult | None]:
        """Returns (governance_decision, result). result is None if
        governance blocked execution -- an ungoverned action never
        touches the effector, full stop."""
        decision = self.governor.evaluate(action, external_actions_enabled=external_actions_enabled)
        if not decision.allowed:
            return decision, None

        calibration = self._calibration_for(effector_name)
        calibrated_expected = raw_expected_outcome * calibration.gain
        prediction = MotorPrediction(expected_outcome=calibrated_expected)

        actual = effector(action, calibrated_expected)

        predicate = success_predicate or (lambda expected, actual_: abs(actual_ - expected) <= 0.1 * max(1.0, abs(expected)))
        succeeded = predicate(calibrated_expected, actual)

        result = MotorExecutionResult(
            action=action, prediction=prediction, actual_outcome=actual, succeeded=succeeded,
        )
        calibration.update(result)

        self.history.append(result)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        return decision, result
