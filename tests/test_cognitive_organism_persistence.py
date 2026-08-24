from brain.adapters.cognition import InMemoryCognitiveOrganismStore
from brain.cognitive_organism import CognitiveOrganism


def test_cognitive_organism_checkpoint_round_trip_and_audit():
    organism = CognitiveOrganism()
    organism.run_functional_cycle(
        ["memory:distress"],
        ["signal:buyer_intent", "signal:permit", "signal:auction"],
        ["distress", "buyer intent", "auction"],
    )
    store = InMemoryCognitiveOrganismStore()
    store.save_checkpoint("organism_runtime", {"cockpit": organism.cockpit()})

    checkpoint = store.load_checkpoint("organism_runtime")
    assert checkpoint is not None
    assert checkpoint["cockpit"]["autonomy_boundary"] == "tiers_0_to_4_only_tier_5_hold_tier_6_prohibited"
    assert store.list_audit_events()[0]["event_type"] == "COGNITIVE_ORGANISM_CHECKPOINT_SAVED"


def test_cognitive_organism_persistence_does_not_execute_actions():
    organism = CognitiveOrganism()
    cycle = organism.run_functional_cycle(
        ["memory:source_weight"],
        ["signal:rfp", "signal:permit", "signal:job_post"],
        ["rfp", "permit", "job"],
    )
    store = InMemoryCognitiveOrganismStore()
    store.save_checkpoint("organism_runtime", {"action": cycle["agency_action"]})
    checkpoint = store.load_checkpoint("organism_runtime")

    assert checkpoint["action"]["state"] == "approval_required"
    assert checkpoint["action"]["executed_at"] is None
