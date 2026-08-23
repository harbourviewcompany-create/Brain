from __future__ import annotations

from brain.cognitive_state import CognitiveDrive, NeuromodulatorState
from brain.executive import (
    CognitiveControlResource,
    ConflictMonitor,
    ExecutiveControlService,
    ResponseCandidate,
    ResponseSource,
)


def _neutral_modulation() -> NeuromodulatorState:
    return NeuromodulatorState(
        dopamine=0.5, norepinephrine=0.5, serotonin=0.5, acetylcholine=0.7, stress=0.1
    )


def test_no_conflict_when_prepotent_and_goal_best_agree() -> None:
    good_habit = ResponseCandidate(
        action="do_the_right_thing", source=ResponseSource.HABITUAL,
        prepotency=0.9, goal_alignment=0.9, expected_value=0.8,
    )
    weak_alt = ResponseCandidate(
        action="alt", source=ResponseSource.DELIBERATE,
        prepotency=0.1, goal_alignment=0.2, expected_value=0.1,
    )
    signal = ConflictMonitor().evaluate([good_habit, weak_alt])
    assert signal.magnitude == 0.0
    assert signal.prepotent.id == signal.goal_best.id


def test_high_conflict_when_prepotent_is_goal_incongruent() -> None:
    impulsive = ResponseCandidate(
        action="eat_the_cookie", source=ResponseSource.HABITUAL,
        prepotency=0.95, goal_alignment=-0.8, expected_value=0.9,
    )
    deliberate = ResponseCandidate(
        action="stick_to_the_plan", source=ResponseSource.DELIBERATE,
        prepotency=0.2, goal_alignment=0.9, expected_value=0.6,
    )
    signal = ConflictMonitor().evaluate([impulsive, deliberate])
    assert signal.magnitude > 0.3
    assert signal.prepotent.action == "eat_the_cookie"
    assert signal.goal_best.action == "stick_to_the_plan"


def test_full_control_resource_overrides_prepotent_impulse() -> None:
    impulsive = ResponseCandidate(
        action="impulse", source=ResponseSource.HABITUAL,
        prepotency=0.9, goal_alignment=-0.7, expected_value=0.5,
    )
    deliberate = ResponseCandidate(
        action="plan", source=ResponseSource.DELIBERATE,
        prepotency=0.2, goal_alignment=0.8, expected_value=0.5,
    )
    control = CognitiveControlResource(capacity=1.0, current=1.0)
    decision = ExecutiveControlService().arbitrate(
        [impulsive, deliberate], goals=None, control=control, modulation=_neutral_modulation(),
    )
    assert decision.override_attempted and decision.override_succeeded
    assert decision.chosen.action == "plan"
    assert control.current < 1.0


def test_depleted_control_resource_falls_back_to_impulse() -> None:
    impulsive = ResponseCandidate(
        action="impulse", source=ResponseSource.HABITUAL,
        prepotency=0.9, goal_alignment=-0.7, expected_value=0.5,
    )
    deliberate = ResponseCandidate(
        action="plan", source=ResponseSource.DELIBERATE,
        prepotency=0.2, goal_alignment=0.8, expected_value=0.5,
    )
    control = CognitiveControlResource(capacity=1.0, current=0.0)
    decision = ExecutiveControlService().arbitrate(
        [impulsive, deliberate], goals=None, control=control, modulation=_neutral_modulation(),
    )
    assert decision.override_attempted and not decision.override_succeeded
    assert decision.chosen.action == "impulse"


def test_high_stress_reduces_effective_control_and_raises_override_cost() -> None:
    impulsive = ResponseCandidate(
        action="impulse", source=ResponseSource.HABITUAL,
        prepotency=0.9, goal_alignment=-0.7, expected_value=0.5,
    )
    deliberate = ResponseCandidate(
        action="plan", source=ResponseSource.DELIBERATE,
        prepotency=0.2, goal_alignment=0.8, expected_value=0.5,
    )
    calm = NeuromodulatorState(dopamine=0.5, norepinephrine=0.5, serotonin=0.5, acetylcholine=0.7, stress=0.1)
    stressed = NeuromodulatorState(dopamine=0.5, norepinephrine=0.5, serotonin=0.5, acetylcholine=0.7, stress=0.9)
    svc = ExecutiveControlService()
    calm_d = svc.arbitrate([impulsive, deliberate], goals=None, control=CognitiveControlResource(current=0.5), modulation=calm)
    stressed_d = svc.arbitrate([impulsive, deliberate], goals=None, control=CognitiveControlResource(current=0.5), modulation=stressed)
    assert stressed_d.effective_control < calm_d.effective_control
    assert stressed_d.control_cost > calm_d.control_cost


def test_goal_deficit_increases_pressure_to_override() -> None:
    impulsive = ResponseCandidate(
        action="impulse", source=ResponseSource.HABITUAL,
        prepotency=0.6, goal_alignment=-0.5, expected_value=0.5,
    )
    deliberate = ResponseCandidate(
        action="plan", source=ResponseSource.DELIBERATE,
        prepotency=0.3, goal_alignment=0.6, expected_value=0.5,
    )
    urgent = [CognitiveDrive(name="deadline", target=1.0, current=0.0, priority=1.0)]
    idle = [CognitiveDrive(name="deadline", target=1.0, current=1.0, priority=1.0)]
    svc = ExecutiveControlService()
    urgent_d = svc.arbitrate([impulsive, deliberate], goals=urgent, control=CognitiveControlResource(), modulation=_neutral_modulation())
    idle_d = svc.arbitrate([impulsive, deliberate], goals=idle, control=CognitiveControlResource(), modulation=_neutral_modulation())
    assert urgent_d.control_cost > idle_d.control_cost


def test_control_resource_recovers_with_rest() -> None:
    control = CognitiveControlResource(capacity=1.0, current=0.2, recovery_rate=0.1)
    control.recover(ticks=3.0)
    assert control.current == 0.5


def test_conflict_monitor_requires_candidates() -> None:
    try:
        ConflictMonitor().evaluate([])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
