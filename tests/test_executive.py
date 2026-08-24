from brain.cognitive_state import CognitiveDrive, NeuromodulatorState
from brain.executive import (
    CognitiveControlResource,
    ConflictMonitor,
    ExecutiveControlService,
    ResponseCandidate,
    ResponseSource,
)


def _cand(
    action: str,
    *,
    source: ResponseSource = ResponseSource.DELIBERATE,
    prepotency: float = 0.5,
    goal_alignment: float = 0.5,
    expected_value: float = 0.5,
) -> ResponseCandidate:
    return ResponseCandidate(
        action=action,
        source=source,
        prepotency=prepotency,
        goal_alignment=goal_alignment,
        expected_value=expected_value,
    )


def test_conflict_monitor_zero_when_same_candidate():
    c = _cand("go", prepotency=0.9, goal_alignment=0.9)
    signal = ConflictMonitor().evaluate([c])
    assert signal.magnitude == 0.0
    assert signal.prepotent.id == signal.goal_best.id


def test_conflict_monitor_detects_disagreement():
    habit = _cand("grab", source=ResponseSource.HABITUAL, prepotency=0.95, goal_alignment=0.1)
    deliberate = _cand("wait", source=ResponseSource.DELIBERATE, prepotency=0.2, goal_alignment=0.95)
    signal = ConflictMonitor().evaluate([habit, deliberate])
    assert signal.magnitude > 0.0
    assert signal.prepotent.action == "grab"
    assert signal.goal_best.action == "wait"


def test_override_succeeds_when_resource_available():
    svc = ExecutiveControlService()
    habit = _cand("grab", source=ResponseSource.HABITUAL, prepotency=0.95, goal_alignment=0.1)
    deliberate = _cand("wait", source=ResponseSource.DELIBERATE, prepotency=0.2, goal_alignment=0.95)
    control = CognitiveControlResource(capacity=1.0, current=1.0)
    modulation = NeuromodulatorState(acetylcholine=0.8, stress=0.1, norepinephrine=0.4)
    decision = svc.arbitrate(
        [habit, deliberate],
        goals=[CognitiveDrive(name="patience", target=1.0, current=0.2, priority=1.0)],
        control=control,
        modulation=modulation,
    )
    assert decision.override_attempted is True
    assert decision.override_succeeded is True
    assert decision.chosen.action == "wait"
    assert control.current < 1.0


def test_override_fails_when_resource_exhausted():
    svc = ExecutiveControlService()
    habit = _cand("grab", source=ResponseSource.HABITUAL, prepotency=0.95, goal_alignment=0.1)
    deliberate = _cand("wait", source=ResponseSource.DELIBERATE, prepotency=0.2, goal_alignment=0.95)
    control = CognitiveControlResource(capacity=1.0, current=0.01)
    modulation = NeuromodulatorState(acetylcholine=0.2, stress=0.8, norepinephrine=0.9)
    decision = svc.arbitrate(
        [habit, deliberate],
        goals=[CognitiveDrive(name="patience", target=1.0, current=0.2, priority=1.0)],
        control=control,
        modulation=modulation,
    )
    assert decision.override_attempted is True
    assert decision.override_succeeded is False
    assert decision.chosen.action == "grab"


def test_no_conflict_no_spend():
    svc = ExecutiveControlService()
    c = _cand("go", prepotency=0.8, goal_alignment=0.9)
    control = CognitiveControlResource(capacity=1.0, current=1.0)
    modulation = NeuromodulatorState()
    decision = svc.arbitrate([c], goals=None, control=control, modulation=modulation)
    assert decision.override_attempted is False
    assert control.current == 1.0


def test_resource_recovers():
    control = CognitiveControlResource(capacity=1.0, current=0.2, recovery_rate=0.1)
    control.recover(ticks=3)
    assert control.current == 0.5


def test_empty_candidates_raises():
    try:
        ConflictMonitor().evaluate([])
        assert False, "expected ValueError"
    except ValueError:
        pass
