from __future__ import annotations

import pytest
from pydantic import ValidationError

from brain.schemas import CANONICAL_SCHEMAS, validate_object

COGNITIVE_EXTENSION_SCHEMA_NAMES = {
    "EmotionalState",
    "Mood",
    "ResponseCandidate",
    "ExecutiveDecision",
    "CircadianState",
    "AttributedBelief",
    "AgentPredictionRecord",
    "RewardPredictionError",
    "PainSignal",
    "Percept",
    "MotorExecutionResult",
}


def test_all_cognitive_extension_schemas_are_registered() -> None:
    assert COGNITIVE_EXTENSION_SCHEMA_NAMES <= set(CANONICAL_SCHEMAS)


def test_emotional_state_schema_enforces_bounds_and_label_enum() -> None:
    valid = validate_object(
        "EmotionalState",
        {"valence": 0.5, "arousal": 0.6, "dominance": 0.7, "label": "joy", "intensity": 0.5},
    )
    assert valid.label == "joy"
    with pytest.raises(ValidationError):
        validate_object(
            "EmotionalState",
            {"valence": 5.0, "arousal": 0.6, "dominance": 0.7, "label": "joy", "intensity": 0.5},
        )
    with pytest.raises(ValidationError):
        validate_object(
            "EmotionalState",
            {"valence": 0.5, "arousal": 0.6, "dominance": 0.7, "label": "ecstatic", "intensity": 0.5},
        )


def test_circadian_state_schema_enforces_phase_enum() -> None:
    valid = validate_object(
        "CircadianState",
        {"phase": "nrem", "pressure_ratio": 0.8, "oscillator_wake_drive": 0.1, "cycles_completed_this_sleep": 2},
    )
    assert valid.phase == "nrem"
    with pytest.raises(ValidationError):
        validate_object(
            "CircadianState",
            {"phase": "drowsy", "pressure_ratio": 0.8, "oscillator_wake_drive": 0.1, "cycles_completed_this_sleep": 2},
        )


def test_response_candidate_schema_enforces_source_enum() -> None:
    with pytest.raises(ValidationError):
        validate_object(
            "ResponseCandidate",
            {"action": "x", "source": "reflex", "prepotency": 0.5, "goal_alignment": 0.0, "expected_value": 1.0},
        )


def test_percept_schema_enforces_modality_enum_and_novelty_bounds() -> None:
    valid = validate_object(
        "Percept",
        {"modality": "text", "raw_ref": "ref1", "features": {"length": 5.0}, "novelty": 1.0},
    )
    assert valid.modality == "text"
    with pytest.raises(ValidationError):
        validate_object(
            "Percept",
            {"modality": "smell", "raw_ref": "ref1", "features": {}, "novelty": 1.0},
        )


def test_motor_execution_result_schema_carries_signed_error() -> None:
    valid = validate_object(
        "MotorExecutionResult",
        {
            "action_description": "send outreach",
            "effector_name": "email",
            "expected_outcome": 10.0,
            "actual_outcome": 8.0,
            "succeeded": False,
            "error": -2.0,
        },
    )
    assert valid.error == -2.0


def test_pain_signal_schema_rejects_out_of_range_intensity() -> None:
    with pytest.raises(ValidationError):
        validate_object(
            "PainSignal",
            {"intensity": 1.5, "source": "x", "withdrawal_urgency": 0.5},
        )
