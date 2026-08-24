from __future__ import annotations

import pytest

from brain.theory_of_mind import TheoryOfMindService


def test_attributed_belief_requires_evidence() -> None:
    svc = TheoryOfMindService()
    with pytest.raises(ValueError):
        svc.attribute_belief("alice", statement="the box is empty", confidence=0.8, evidence_refs=[])


def test_false_belief_detection_diverges_from_ground_truth() -> None:
    svc = TheoryOfMindService()
    # Sally-Anne: Alice believes the marble is in the basket, but it was
    # actually moved to the box while she was out of the room.
    svc.attribute_belief(
        "alice",
        statement="marble is in the basket",
        confidence=0.9,
        evidence_refs=["alice_saw_it_placed_in_basket"],
    )
    result = svc.check_false_belief("alice", "marble is in the basket", ground_truth=False)
    assert result.agent_believes is True
    assert result.ground_truth is False
    assert result.is_false_belief is True


def test_true_belief_is_not_flagged_as_false() -> None:
    svc = TheoryOfMindService()
    svc.attribute_belief(
        "bob", statement="the deal closed", confidence=0.9, evidence_refs=["bob_signed_it"],
    )
    result = svc.check_false_belief("bob", "the deal closed", ground_truth=True)
    assert result.is_false_belief is False


def test_predict_action_uses_attributed_goals_not_ground_truth() -> None:
    svc = TheoryOfMindService()
    svc.infer_goal(
        "carol", statement="maximize quarterly revenue", confidence=0.9,
        evidence_refs=["carol_said_targets_matter"],
    )
    predicted, confidence = svc.predict_action(
        "carol", ["cut costs to hit margin", "maximize quarterly revenue push", "take a vacation"]
    )
    assert predicted == "maximize quarterly revenue push"
    assert confidence > 0


def test_predict_action_without_any_goals_is_low_confidence_default() -> None:
    svc = TheoryOfMindService()
    predicted, confidence = svc.predict_action("stranger", ["option_a", "option_b"])
    assert predicted == "option_a"
    assert confidence < 0.2


def test_trust_increases_after_correct_prediction_and_decreases_after_wrong() -> None:
    svc = TheoryOfMindService()
    svc.infer_goal("dave", statement="close the deal", confidence=0.8, evidence_refs=["e1"])

    record = svc.record_prediction("dave", "close the deal fast")
    model = svc.resolve_prediction("dave", record, actual_action="close the deal fast")
    assert model.trust > 0.5

    trust_after_correct = model.trust
    record2 = svc.record_prediction("dave", "close the deal fast")
    model = svc.resolve_prediction("dave", record2, actual_action="walked away entirely")
    assert model.trust < trust_after_correct


def test_prediction_accuracy_reflects_track_record() -> None:
    svc = TheoryOfMindService()
    model = svc.get_or_create("erin")
    r1 = svc.record_prediction("erin", "a")
    svc.resolve_prediction("erin", r1, actual_action="a")
    r2 = svc.record_prediction("erin", "b")
    svc.resolve_prediction("erin", r2, actual_action="c")
    assert model.prediction_accuracy == 0.5


def test_low_trust_agent_model_reports_lower_prediction_confidence() -> None:
    svc = TheoryOfMindService()
    svc.infer_goal("frank", statement="expand internationally", confidence=0.9, evidence_refs=["e"])
    model = svc.get_or_create("frank")
    model.trust = 0.1
    _, low_trust_confidence = svc.predict_action(
        "frank", ["expand internationally now", "stay local"]
    )

    svc.infer_goal("grace", statement="expand internationally", confidence=0.9, evidence_refs=["e"])
    model2 = svc.get_or_create("grace")
    model2.trust = 0.9
    _, high_trust_confidence = svc.predict_action(
        "grace", ["expand internationally now", "stay local"]
    )
    assert low_trust_confidence < high_trust_confidence
