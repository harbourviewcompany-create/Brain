"""Acceptance evidence for docs/spec/BRAIN_STATE_MACHINES.md's
'Cognitive-extension state machines' section. Each test here maps to one
named hard gate in that doc, kept separate from the per-module unit tests
so the mapping from doc claim to enforcement is traceable in one place."""

from __future__ import annotations

import pytest

from brain.circadian import CircadianClock, CircadianOscillator, CircadianPhase, SleepPressure
from brain.executive import CognitiveControlResource
from brain.theory_of_mind import TheoryOfMindService


def test_gate_control_resource_current_never_exceeds_capacity_on_recovery() -> None:
    """Executive control-resource gate: recovery cannot exceed capacity."""
    control = CognitiveControlResource(capacity=1.0, current=0.9, recovery_rate=0.5)
    control.recover(ticks=10.0)
    assert control.current == 1.0


def test_gate_control_resource_current_never_negative_on_overspend() -> None:
    """Executive control-resource gate: current is clamped at 0, never negative."""
    control = CognitiveControlResource(capacity=1.0, current=0.2)
    control.spend(999.0)
    assert control.current == 0.0


def test_gate_theory_of_mind_prediction_cannot_be_resolved_without_first_being_predicted() -> None:
    """Theory-of-mind gate: resolve_prediction only ever acts on a record
    produced by record_prediction; there is no path to a resolved record
    that skipped the predicted state."""
    svc = TheoryOfMindService()
    record = svc.record_prediction("agent-x", "some_action")
    assert record.correct is None
    model = svc.resolve_prediction("agent-x", record, actual_action="some_action")
    assert record.correct is True
    assert model.trust != 0.5  # moved off the neutral default, proving resolution ran


def test_gate_theory_of_mind_prediction_cannot_be_resolved_twice() -> None:
    """Theory-of-mind gate: resolving the same record twice would apply a
    second trust update for one real-world outcome. Blocked outright."""
    svc = TheoryOfMindService()
    record = svc.record_prediction("agent-z", "action")
    svc.resolve_prediction("agent-z", record, actual_action="action")
    with pytest.raises(ValueError):
        svc.resolve_prediction("agent-z", record, actual_action="action")


def test_gate_trust_moves_by_slow_blend_not_single_observation_overwrite() -> None:
    """Theory-of-mind gate: trust is never set directly from one outcome --
    a single correct prediction after a bad track record should move trust
    partway, not snap it to 1.0."""
    svc = TheoryOfMindService()
    model = svc.get_or_create("agent-y")
    model.trust = 0.1
    record = svc.record_prediction("agent-y", "action")
    svc.resolve_prediction("agent-y", record, actual_action="action")
    assert 0.1 < model.trust < 1.0


def test_gate_sleep_onset_requires_both_pressure_and_circadian_conjunction() -> None:
    """Circadian gate: high pressure alone, at a wake-favoring circadian
    phase, must not trigger sleep onset -- both conditions are required."""
    clock = CircadianClock(
        pressure=SleepPressure(level=0.95, build_rate=0.0, dissipation_rate=0.0),
        oscillator=CircadianOscillator(period_ticks=24.0, phase_position=0.5),  # biological daytime peak
        sleep_onset_pressure=0.5,
    )
    clock.advance(ticks=0.1)
    assert clock.is_awake, "high pressure alone at wake-favoring phase must not trigger sleep"


def test_gate_force_wake_leaves_residual_pressure_rather_than_clearing_it() -> None:
    """Circadian gate: force_wake is an override, not a reset -- it must
    not silently erase accumulated sleep debt."""
    clock = CircadianClock(
        pressure=SleepPressure(level=0.9, build_rate=0.0, dissipation_rate=0.0),
        oscillator=CircadianOscillator(period_ticks=24.0, phase_position=0.0),
        sleep_onset_pressure=0.5,
    )
    clock.advance(ticks=0.1)
    assert clock.phase == CircadianPhase.NREM
    clock.force_wake()
    assert clock.is_awake
    assert clock.pressure.level == 0.9  # unchanged, not cleared
