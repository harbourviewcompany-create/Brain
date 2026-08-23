from brain.developmental.global_workspace import GlobalWorkspaceService


def test_workspace_winner_has_evidence() -> None:
    service = GlobalWorkspaceService()
    low = service.propose_item(
        content_ref="belief:watch",
        priority=0.2,
        evidence_refs=["evidence:weak"],
        proposing_module="belief",
    )
    high = service.propose_item(
        content_ref="action:approval-needed",
        priority=0.9,
        evidence_refs=["evidence:urgent"],
        proposing_module="approval",
    )
    cycle = service.compete_and_broadcast(consumer_modules=["memory", "planning"])

    assert cycle.winner_id == high.id
    assert low.id in cycle.suppressed_item_ids
    assert service.broadcasts[0].evidence_refs == ["evidence:urgent"]


def test_suppressed_items_are_logged() -> None:
    service = GlobalWorkspaceService()
    first = service.propose_item(
        content_ref="signal:a",
        priority=0.3,
        evidence_refs=["evidence:a"],
        proposing_module="perception",
    )
    second = service.propose_item(
        content_ref="signal:b",
        priority=0.4,
        evidence_refs=["evidence:b"],
        proposing_module="perception",
    )
    cycle = service.compete_and_broadcast(consumer_modules=["belief"])

    assert first.id in cycle.suppressed_item_ids
    assert second.id == cycle.winner_id


def test_broadcast_records_consumers() -> None:
    service = GlobalWorkspaceService()
    service.propose_item(
        content_ref="memory:compress",
        priority=0.8,
        evidence_refs=["evidence:memory"],
        proposing_module="memory",
    )
    service.compete_and_broadcast(consumer_modules=["planning", "self_model", "immune"])

    assert service.broadcasts[0].consumer_modules == ["planning", "self_model", "immune"]


def test_broadcast_does_not_claim_consciousness() -> None:
    service = GlobalWorkspaceService()
    service.propose_item(
        content_ref="attention:winner",
        priority=1.0,
        evidence_refs=["evidence:x"],
        proposing_module="attention",
    )
    service.compete_and_broadcast(consumer_modules=["planner"])

    assert service.broadcasts[0].consciousness_claim is False
