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

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable
from uuid import UUID, uuid4

import httpx

from .domain import CandidateAction, utcnow
from .events import BrainEvent
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


class MissingEffectorCredentialsError(RuntimeError):
    """Raised when an HttpEffector is called but its configured
    credential environment variable is unset. Deliberately loud rather
    than silently sending an unauthenticated request or silently no-op'ing
    -- a motor command that can't actually execute should fail visibly,
    not report a fabricated outcome."""


class HttpEffector:
    """A real, wireable ``Effector``: POSTs the action to a configured
    HTTP endpoint and extracts a numeric outcome from the JSON response.

    This is intentionally vendor-neutral -- point ``endpoint_url`` at
    Resend, a Slack webhook, an internal API, whatever the deployment
    actually has credentials for. Nothing in ``brain/motor.py`` should
    hardcode a specific vendor; that decision belongs to whoever wires
    this up in a given deployment, not to this module.

    Credentials are read from an environment variable *by name*, resolved
    at call time rather than construction time, so rotating a secret
    doesn't require restarting the process and so no credential is ever
    held in a dataclass field where it could leak into logs/repr.

    ``transport`` is an optional ``httpx`` transport override purely for
    testing (``httpx.MockTransport``) -- production callers leave it
    unset and get real network I/O.
    """

    def __init__(
        self,
        endpoint_url: str,
        *,
        api_key_env_var: str | None = None,
        timeout_seconds: float = 10.0,
        response_outcome_field: str = "outcome",
        transport: object | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.api_key_env_var = api_key_env_var
        self.timeout_seconds = timeout_seconds
        self.response_outcome_field = response_outcome_field
        self._transport = transport

    def __call__(self, action: CandidateAction, expected_outcome: float) -> float:
        headers: dict[str, str] = {}
        if self.api_key_env_var:
            api_key = os.environ.get(self.api_key_env_var)
            if not api_key:
                raise MissingEffectorCredentialsError(
                    f"environment variable {self.api_key_env_var!r} is not set"
                )
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "action_id": str(action.id),
            "action_description": action.description,
            "expected_outcome": expected_outcome,
        }

        client_kwargs: dict[str, object] = {"timeout": self.timeout_seconds}
        if self._transport is not None:
            client_kwargs["transport"] = self._transport

        with httpx.Client(**client_kwargs) as client:
            response = client.post(self.endpoint_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        if self.response_outcome_field in data:
            return float(data[self.response_outcome_field])
        # The endpoint's response contract doesn't include a numeric
        # outcome field -- treat a successful HTTP response as a binary
        # "it happened" outcome rather than fabricating a magnitude.
        return 1.0


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


def motor_execution_result_to_event(
    result: MotorExecutionResult,
    *,
    effector_name: str,
    aggregate_type: str,
    aggregate_id: UUID,
    correlation_id: UUID | None = None,
) -> BrainEvent:
    """Audit-event constructor for a completed ``MotorExecutionResult``.
    Not currently called by anything -- ``MotorExecutionService`` is not
    yet wired into ``CognitiveCycle`` at all (it has no default effector
    to safely call automatically), so this exists for whoever wires a
    concrete ``Effector`` into a cycle or standalone workflow next, per
    ``docs/spec/BRAIN_STATE_MACHINES.md``'s motor-execution state
    machine."""
    return BrainEvent(
        "motor.executed",
        aggregate_type,
        aggregate_id,
        {
            "effector_name": effector_name,
            "expected_outcome": result.prediction.expected_outcome,
            "actual_outcome": result.actual_outcome,
            "succeeded": result.succeeded,
            "error": result.error,
        },
        correlation_id=correlation_id,
    )
