import pytest

from brain.formulas import default_formula_registry


def test_formula_registry_has_required_formulas():
    registry = default_formula_registry()
    required = {
        "source_priority_score",
        "attention_score",
        "bayesian_belief_update",
        "brier_score",
        "reward_score",
        "pain_score",
        "graph_weight_update",
        "fractional_kelly_exposure",
        "trust_adjusted_value",
    }
    assert required <= set(registry.formulas)


def test_formula_owner_input_output_and_decision_trace():
    registry = default_formula_registry()
    result = registry.evaluate(
        "attention_score",
        {
            "commercial_upside": 0.9,
            "novelty": 0.8,
            "urgency": 0.6,
            "contradiction_value": 0.3,
            "source_quality": 0.95,
            "learning_value": 0.7,
            "noise_probability": 0.1,
            "operator_load_penalty": 0.2,
        },
        owner_object_id="signal-1",
        owner_object_type="Signal",
    )
    assert result.owner_object_id == "signal-1"
    assert result.service == "AttentionAllocatorService"
    assert result.table_store == "formula_runs"
    assert result.dashboard == "Perception Inbox"
    assert result.decision_consequence
    assert result.audit_evidence["formula_id"] == "attention_score"
    assert result.output > 0


def test_bayesian_update_and_brier_score_are_bounded():
    registry = default_formula_registry()
    belief = registry.evaluate(
        "bayesian_belief_update",
        {"prior": 0.5, "likelihood": 0.9, "false_likelihood": 0.2},
        owner_object_id="belief-1",
        owner_object_type="Belief",
    )
    brier = registry.evaluate(
        "brier_score",
        {"forecast_probability": 0.7, "actual_outcome": 1.0},
        owner_object_id="prediction-1",
        owner_object_type="Prediction",
    )
    assert 0.0 <= belief.output <= 1.0
    assert belief.output > 0.5
    assert 0.0 <= brier.output <= 1.0


def test_missing_formula_inputs_fail():
    registry = default_formula_registry()
    with pytest.raises(ValueError):
        registry.evaluate(
            "trust_adjusted_value",
            {"action_expected_utility": 10.0},
            owner_object_id="action-1",
            owner_object_type="CandidateAction",
        )
