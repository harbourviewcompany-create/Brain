from brain.curiosity import CuriosityEngine, CuriosityState


def test_curiosity_generates_questions_from_uncertainty_and_contradiction():
    engine = CuriosityEngine()
    task = engine.generate(
        "contradiction",
        ["belief:a", "signal:b"],
        "What source would disprove the buyer demand hypothesis?",
        expected_value=0.8,
        uncertainty=0.8,
    )

    assert task.priority > 0
    assert task.state == CuriosityState.PRIORITIZED
    assert task.falsification_condition
    assert engine.from_unknown("missing buyer").question == "Resolve: missing buyer"
