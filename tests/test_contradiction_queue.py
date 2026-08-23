import pytest

from brain.contradiction_queue import ContradictionReviewService, ContradictionStatus


def test_contradictions_are_preserved():
    service = ContradictionReviewService()
    item = service.create_review_item(
        belief_id="belief-1",
        supporting_claim="Company A is expanding.",
        contradicting_claim="Company A has shut down the facility.",
        source_ids=["source-1", "source-2"],
        severity=0.9,
    )
    assert item.supporting_claim
    assert item.contradicting_claim
    assert item.source_ids == ["source-1", "source-2"]
    assert item.status == ContradictionStatus.OPEN


def test_conflicts_require_review_status():
    service = ContradictionReviewService()
    item = service.create_review_item(
        belief_id="belief-2",
        supporting_claim="Signal supports opportunity.",
        contradicting_claim="New evidence weakens opportunity.",
        source_ids=["source-1"],
        severity=0.7,
    )
    updated = service.require_user_decision(item.id)
    assert updated.status == ContradictionStatus.USER_DECISION_REQUIRED
    assert service.unresolved()[0].id == item.id


def test_no_silent_resolution_by_agent_preference():
    service = ContradictionReviewService()
    item = service.create_review_item(
        belief_id="belief-3",
        supporting_claim="Commercial Brain scope matters.",
        contradicting_claim="Digital organism scope also matters.",
        source_ids=["manual"],
        severity=1.0,
    )
    with pytest.raises(ValueError):
        service.resolve(
            item.id,
            resolution="Delete one side.",
            resolution_source="agent_preference",
        )
