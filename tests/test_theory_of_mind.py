from brain.theory_of_mind import TheoryOfMindService


def test_attribute_belief_requires_evidence():
    svc = TheoryOfMindService()
    try:
        svc.attribute_belief("agent-a", statement="box is empty", confidence=0.9, evidence_refs=[])
        assert False, "expected ValueError"
    except ValueError as e:
        assert "evidence" in str(e)


def test_attribute_belief_and_false_belief_detection():
    svc = TheoryOfMindService()
    svc.attribute_belief(
        "sally",
        statement="marble is in the basket",
        confidence=0.95,
        evidence_refs=["obs-1"],
    )
    # Brain ground truth: marble was moved to the box
    result = svc.check_false_belief("sally", "marble is in the basket", ground_truth=False)
    assert result.agent_believes is True
    assert result.ground_truth is False
    assert result.is_false_belief is True


def test_true_belief_is_not_false_belief():
    svc = TheoryOfMindService()
    svc.attribute_belief(
        "anne",
        statement="marble is in the box",
        confidence=0.9,
        evidence_refs=["obs-2"],
    )
    result = svc.check_false_belief("anne", "marble is in the box", ground_truth=True)
    assert result.is_false_belief is False


def test_predict_action_uses_attributed_goals_not_ground_truth():
    svc = TheoryOfMindService()
    svc.infer_goal(
        "buyer",
        statement="secure cheap inventory",
        confidence=0.8,
        evidence_refs=["msg-1"],
    )
    action, confidence = svc.predict_action(
        "buyer",
        ["pay premium for scarce stock", "negotiate for cheaper inventory", "walk away"],
    )
    assert action == "negotiate for cheaper inventory"
    assert 0.0 <= confidence <= 1.0


def test_predict_action_requires_candidates():
    svc = TheoryOfMindService()
    try:
        svc.predict_action("x", [])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_trust_updates_from_prediction_outcomes():
    svc = TheoryOfMindService()
    model = svc.get_or_create("partner")
    assert model.trust == 0.5
    rec = svc.record_prediction("partner", "accept offer")
    svc.resolve_prediction("partner", rec, actual_action="accept offer")
    assert svc.agents["partner"].trust > 0.5
    rec2 = svc.record_prediction("partner", "accept offer")
    svc.resolve_prediction("partner", rec2, actual_action="reject offer")
    # one miss should not collapse trust
    assert svc.agents["partner"].trust > 0.3


def test_prediction_accuracy_property():
    svc = TheoryOfMindService()
    rec = svc.record_prediction("a", "go left")
    svc.resolve_prediction("a", rec, actual_action="go left")
    rec2 = svc.record_prediction("a", "go left")
    svc.resolve_prediction("a", rec2, actual_action="go right")
    assert svc.agents["a"].prediction_accuracy == 0.5


def test_confidence_scaled_by_trust():
    svc = TheoryOfMindService()
    svc.infer_goal("x", statement="win auction", confidence=1.0, evidence_refs=["e"])
    # degrade trust
    for _ in range(5):
        rec = svc.record_prediction("x", "bid high")
        svc.resolve_prediction("x", rec, actual_action="bid low")
    _, low_conf = svc.predict_action("x", ["bid high", "bid low"])
    # reset a high-trust agent
    svc2 = TheoryOfMindService()
    svc2.infer_goal("y", statement="win auction", confidence=1.0, evidence_refs=["e"])
    for _ in range(5):
        rec = svc2.record_prediction("y", "bid high")
        svc2.resolve_prediction("y", rec, actual_action="bid high")
    _, high_conf = svc2.predict_action("y", ["bid high", "bid low"])
    assert high_conf > low_conf
