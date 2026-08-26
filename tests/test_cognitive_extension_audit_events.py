"""Tests for the standalone to_event() constructors that let code using
brain/affect.py, executive.py, circadian.py, theory_of_mind.py, hedonic.py,
perception.py, and motor.py directly -- outside CognitiveCycle's own
wiring -- still produce a properly-shaped BrainEvent for their own
persistence. Closes the audit-event gap named in
TRACE-BRAIN-COGNITIVE-EXTENSIONS's unresolved_gaps."""

from __future__ import annotations

from uuid import uuid4

import httpx

from brain.affect import AffectAppraisalService, AppraisalInput, emotional_state_to_event
from brain.circadian import CircadianPhase, circadian_forced_wake_event, circadian_phase_changed_event
from brain.cognitive_state import NeuromodulatorState
from brain.domain import CandidateAction
from brain.executive import (
    CognitiveControlResource,
    ConflictMonitor,
    ExecutiveControlService,
    ResponseCandidate,
    ResponseSource,
    executive_decision_to_event,
)
from brain.hedonic import HedonicSystem, pain_signal_to_event, reward_prediction_error_to_event
from brain.motor import HttpEffector, MotorExecutionService, motor_execution_result_to_event
from brain.perception import Modality, PerceptionService, TextPerceptionEncoder, percept_to_event
from brain.theory_of_mind import TheoryOfMindService, attributed_belief_to_event


def test_emotional_state_to_event_shape():
    svc = AffectAppraisalService()
    emotion = svc.appraise(
        AppraisalInput(goal_congruence=0.5, novelty=0.2, urgency=0.2, controllability=0.9, certainty=0.9)
    )
    aggregate_id = uuid4()
    event = emotional_state_to_event(emotion, aggregate_type="observation", aggregate_id=aggregate_id)
    assert event.event_type == "affect.appraised"
    assert event.aggregate_type == "observation"
    assert event.aggregate_id == aggregate_id
    assert event.payload["label"] == str(emotion.label)
    assert "mood_valence" not in event.payload  # optional, omitted when not passed


def test_emotional_state_to_event_includes_mood_when_provided():
    svc = AffectAppraisalService()
    emotion = svc.appraise(
        AppraisalInput(goal_congruence=0.5, novelty=0.2, urgency=0.2, controllability=0.9, certainty=0.9)
    )
    event = emotional_state_to_event(
        emotion, aggregate_type="observation", aggregate_id=uuid4(), mood_valence=svc.mood.valence,
    )
    assert event.payload["mood_valence"] == svc.mood.valence


def test_executive_decision_to_event_shape():
    candidates = [
        ResponseCandidate(action="a", source=ResponseSource.HABITUAL, prepotency=0.9, goal_alignment=-0.7, expected_value=0.5),
        ResponseCandidate(action="b", source=ResponseSource.DELIBERATE, prepotency=0.2, goal_alignment=0.8, expected_value=0.5),
    ]
    svc = ExecutiveControlService(conflict_monitor=ConflictMonitor())
    control = CognitiveControlResource(capacity=1.0, current=1.0)
    decision = svc.arbitrate(
        candidates, goals=None, control=control,
        modulation=NeuromodulatorState(dopamine=0.5, norepinephrine=0.5, serotonin=0.5, acetylcholine=0.7, stress=0.1),
    )
    aggregate_id = uuid4()
    event = executive_decision_to_event(
        decision, aggregate_type="cognitive_cycle", aggregate_id=aggregate_id, control_remaining=control.current,
    )
    assert event.event_type == "executive.arbitrated"
    assert event.payload["chosen"] == decision.chosen.action
    assert event.payload["control_remaining"] == control.current


def test_circadian_phase_changed_event_shape():
    event = circadian_phase_changed_event(
        previous_phase=CircadianPhase.WAKE,
        new_phase=CircadianPhase.NREM,
        pressure_ratio=0.7,
        aggregate_type="cognitive_cycle",
        aggregate_id=uuid4(),
    )
    assert event.event_type == "circadian.phase_changed"
    assert event.payload["previous_phase"] == "wake"
    assert event.payload["new_phase"] == "nrem"


def test_circadian_forced_wake_event_shape():
    event = circadian_forced_wake_event(
        previous_phase=CircadianPhase.REM, urgency=0.95, aggregate_type="cognitive_cycle", aggregate_id=uuid4(),
    )
    assert event.event_type == "circadian.forced_wake"
    assert event.payload["previous_phase"] == "rem"
    assert event.payload["urgency"] == 0.95


def test_attributed_belief_to_event_shape():
    svc = TheoryOfMindService()
    belief = svc.attribute_belief("agent-x", statement="the deal closed", confidence=0.8, evidence_refs=["e1"])
    event = attributed_belief_to_event(
        belief, agent_id="agent-x", aggregate_type="observation", aggregate_id=uuid4(),
    )
    assert event.event_type == "theory_of_mind.belief_attributed"
    assert event.payload["agent_id"] == "agent-x"
    assert event.payload["statement"] == "the deal closed"


def test_reward_prediction_error_to_event_shape():
    system = HedonicSystem()
    rpe = system.register_outcome(expected_value=0.2, actual_value=0.8)
    event = reward_prediction_error_to_event(rpe, aggregate_type="belief", aggregate_id=uuid4())
    assert event.event_type == "hedonic.outcome_registered"
    assert event.payload["delta"] == rpe.delta


def test_pain_signal_to_event_shape():
    system = HedonicSystem()
    pain = system.register_pain(intensity=0.6, source="contradiction")
    event = pain_signal_to_event(pain, aggregate_type="belief", aggregate_id=uuid4())
    assert event.event_type == "hedonic.pain_registered"
    assert event.payload["intensity"] == 0.6
    assert event.payload["source"] == "contradiction"


def test_percept_to_event_shape():
    svc = PerceptionService()
    svc.register(TextPerceptionEncoder())
    percept = svc.perceive(Modality.TEXT, "ref1", "growth and success")
    event = percept_to_event(percept, aggregate_type="observation", aggregate_id=uuid4())
    assert event.event_type == "perception.encoded"
    assert event.payload["modality"] == "text"
    assert event.payload["novelty"] == percept.novelty


def test_motor_execution_result_to_event_shape():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"outcome": 9.0})

    effector = HttpEffector("https://example.test/webhook", transport=httpx.MockTransport(handler))
    svc = MotorExecutionService()
    action = CandidateAction(description="notify", expected_value=0.5, uncertainty=0.1, external=False)
    _, result = svc.execute(action, effector_name="webhook", effector=effector, raw_expected_outcome=10.0)

    event = motor_execution_result_to_event(
        result, effector_name="webhook", aggregate_type="cognitive_cycle", aggregate_id=uuid4(),
    )
    assert event.event_type == "motor.executed"
    assert event.payload["effector_name"] == "webhook"
    assert event.payload["actual_outcome"] == 9.0
