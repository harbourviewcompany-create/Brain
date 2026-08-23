from pathlib import Path

from brain.replay import ReplayHarness

FIXTURES = Path("tests/fixtures/brain")


def test_source_to_signal_replay():
    result = ReplayHarness().run_fixture(FIXTURES / "source_signal_evidence_belief.json")
    assert result.passed is True
    assert "observation.received" in result.event_types
    assert "belief.updated" in result.event_types
    assert result.go_hold == "GO"


def test_replay_is_deterministic():
    harness = ReplayHarness()
    first = harness.run_fixture(FIXTURES / "source_signal_evidence_belief.json")
    second = harness.run_fixture(FIXTURES / "source_signal_evidence_belief.json")
    assert first.deterministic_signature() == second.deterministic_signature()


def test_approval_gate_blocks_external_action():
    result = ReplayHarness().run_fixture(FIXTURES / "approval_gate_external_action.json")
    assert result.passed is True
    assert "approval.blocked" in result.event_types


def test_reward_pain_reallocation_replay():
    result = ReplayHarness().run_fixture(FIXTURES / "outcome_reward_pain_learning.json")
    assert result.passed is True
    assert [run["formula_id"] for run in result.formula_runs] == [
        "reward_score",
        "pain_score",
        "graph_weight_update",
    ]


def test_contradiction_fixture_preserves_both_sides():
    result = ReplayHarness().run_fixture(FIXTURES / "contradiction_review.json")
    assert result.passed is True
    assert "contradiction.review_required" in result.event_types


def test_formula_fixture_emits_audit_trace():
    result = ReplayHarness().run_fixture(FIXTURES / "formula_run_attention_reward.json")
    assert result.passed is True
    assert all(run["audit_evidence"] for run in result.formula_runs)
