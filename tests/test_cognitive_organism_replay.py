from brain.agency import AgencyState
from brain.cognitive_organism import CognitiveOrganism


def test_replay_proves_organism_cycle_is_deterministic_enough_for_v1():
    organism = CognitiveOrganism()
    result = organism.run_functional_cycle(
        memory_refs=["memory:permit", "memory:buyer", "memory:distress"],
        signal_refs=["signal:permit", "signal:buyer", "signal:distress"],
        signals=["permits", "buyer intent", "distress"],
    )

    assert result["workspace_item"].state.value == "active_focus"
    assert result["curiosity_task"].priority > 0
    assert len(result["original_idea"].source_signal_refs + result["original_idea"].memory_refs) >= 6
    assert result["debate"].verdict == "advance_to_agency_review"
    assert result["quarantine"] is None
    assert result["agency_action"].state == AgencyState.APPROVAL_REQUIRED
    assert organism.cockpit()["autonomy_boundary"] == "tiers_0_to_4_only_tier_5_hold_tier_6_prohibited"
