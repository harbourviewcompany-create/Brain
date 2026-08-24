from __future__ import annotations

from brain.domain import CandidateAction
from brain.motor import MotorExecutionService


def _action(external: bool = False) -> CandidateAction:
    return CandidateAction(description="send outreach", expected_value=0.5, uncertainty=0.2, external=external)


def test_internal_action_executes_and_updates_calibration() -> None:
    svc = MotorExecutionService()

    def effector(action: CandidateAction, expected: float) -> float:
        return expected  # perfect execution

    decision, result = svc.execute(
        _action(external=False),
        effector_name="email",
        effector=effector,
        raw_expected_outcome=10.0,
    )
    assert decision.allowed
    assert result is not None
    assert result.succeeded
    assert result.error == 0.0


def test_external_action_blocked_without_approval_never_touches_effector() -> None:
    svc = MotorExecutionService()
    called = {"count": 0}

    def effector(action: CandidateAction, expected: float) -> float:
        called["count"] += 1
        return expected

    decision, result = svc.execute(
        _action(external=True),
        effector_name="api_call",
        effector=effector,
        raw_expected_outcome=10.0,
        external_actions_enabled=False,
    )
    assert not decision.allowed
    assert result is None
    assert called["count"] == 0


def test_repeated_overshoot_increases_gain_correction_downward() -> None:
    svc = MotorExecutionService()

    def overshooting_effector(action: CandidateAction, expected: float) -> float:
        return expected * 1.5  # consistently overshoots by 50%

    gains = []
    for _ in range(10):
        _, result = svc.execute(
            _action(),
            effector_name="reach",
            effector=overshooting_effector,
            raw_expected_outcome=10.0,
        )
        gains.append(svc.calibrations["reach"].gain)

    # Gain should trend downward over repeated trials as the system learns
    # the effector overshoots and reduces its own predicted (and via the
    # calibrated_expected feedback loop, effective) amplitude.
    assert gains[-1] < gains[0]


def test_calibrations_are_independent_per_effector() -> None:
    svc = MotorExecutionService()

    def overshoot(action: CandidateAction, expected: float) -> float:
        return expected * 1.5

    def undershoot(action: CandidateAction, expected: float) -> float:
        return expected * 0.5

    for _ in range(5):
        svc.execute(_action(), effector_name="a", effector=overshoot, raw_expected_outcome=10.0)
        svc.execute(_action(), effector_name="b", effector=undershoot, raw_expected_outcome=10.0)

    assert svc.calibrations["a"].gain != svc.calibrations["b"].gain
    assert svc.calibrations["a"].gain < 1.0  # overshooting effector -> command scaled down
    assert svc.calibrations["b"].gain > 1.0  # undershooting effector -> command scaled up


def test_single_wild_outlier_is_capped_by_max_step() -> None:
    svc = MotorExecutionService()

    def wild(action: CandidateAction, expected: float) -> float:
        return expected * 100

    svc.execute(_action(), effector_name="x", effector=wild, raw_expected_outcome=10.0)
    calibration = svc.calibrations["x"]
    assert abs(calibration.gain - 1.0) <= calibration.max_step + 1e-9


def test_custom_success_predicate_is_respected() -> None:
    svc = MotorExecutionService()

    def effector(action: CandidateAction, expected: float) -> float:
        return expected - 5.0  # always off by a fixed amount

    _, result = svc.execute(
        _action(),
        effector_name="strict",
        effector=effector,
        raw_expected_outcome=10.0,
        success_predicate=lambda expected, actual: actual == expected,
    )
    assert not result.succeeded

    _, result2 = svc.execute(
        _action(),
        effector_name="lenient",
        effector=effector,
        raw_expected_outcome=10.0,
        success_predicate=lambda expected, actual: True,
    )
    assert result2.succeeded
