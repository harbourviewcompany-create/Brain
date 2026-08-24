from brain.agency import AgencyState
from brain.cognitive_organism import CognitiveOrganism


def test_cognitive_organism_v1_full_acceptance_path():
    organism = CognitiveOrganism()
    result = organism.run_functional_cycle(
        memory_refs=["memory:source_win", "memory:buyer_reply", "memory:permit_pattern"],
        signal_refs=["signal:distress", "signal:buyer_intent", "signal:local_movement"],
        signals=["distress", "buyer intent", "local movement"],
    )
    cockpit = organism.cockpit()

    assert result["self_state"].current_focus_summary == "Cross-domain opportunity structure"
    assert cockpit["conscious_focus"]["active_focus"]
    assert cockpit["goal_pressure"]["dominant_goal"]
    assert cockpit["curiosity_queue"]
    assert cockpit["original_ideas"]
    assert cockpit["dream_insights"]
    assert cockpit["internal_debates"]
    assert result["agency_action"].state == AgencyState.APPROVAL_REQUIRED
    assert "subjective" not in result["self_state"].self_assessment.lower()
