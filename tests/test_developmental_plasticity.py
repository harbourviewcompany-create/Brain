import pytest

from brain.developmental.plasticity import PlasticityService


def test_reward_strengthens_edge() -> None:
    service = PlasticityService()
    edge = service.create_edge(
        source="source:registry",
        target="belief:license-expansion",
        relation="supports",
        weight=0.4,
        evidence_refs=["evidence:initial"],
    )
    event = service.apply_reward(edge, reward=0.3, evidence_refs=["outcome:validated"])

    assert edge.weight == pytest.approx(0.7)
    assert event.previous_weight == pytest.approx(0.4)
    assert event.new_weight == pytest.approx(0.7)


def test_pain_weakens_edge() -> None:
    service = PlasticityService()
    edge = service.create_edge(
        source="source:social-post",
        target="belief:buyer-intent",
        relation="weak_support",
        weight=0.6,
        evidence_refs=["evidence:post"],
    )
    event = service.apply_pain(edge, pain=0.5, evidence_refs=["outcome:false-positive"])

    assert edge.weight == pytest.approx(0.1)
    assert event.reason == "pain_weakened"


def test_pruning_requires_evidence() -> None:
    service = PlasticityService()
    edge = service.create_edge(
        source="a",
        target="b",
        relation="stale",
        weight=0.05,
        evidence_refs=["evidence:old"],
    )
    with pytest.raises(ValueError, match="pruning_requires_evidence"):
        service.prune_or_quarantine(edge, stale=True, contradiction=False, evidence_refs=[])

    decision = service.prune_or_quarantine(
        edge,
        stale=True,
        contradiction=False,
        evidence_refs=["evidence:age-decay"],
    )
    assert decision.action == "prune"


def test_rewire_is_replayable_and_reversible() -> None:
    service = PlasticityService()
    edge = service.create_edge(
        source="source:x",
        target="belief:y",
        relation="supports",
        weight=0.5,
        evidence_refs=["evidence:x"],
    )
    proposal = service.propose_rewire(
        edge,
        proposed_weight=0.9,
        rationale="validated high-yield path",
        evidence_refs=["outcome:won"],
    )
    event = service.apply_reward(edge, reward=0.4, evidence_refs=["outcome:won"])
    rollback = service.rollback(event, evidence_refs=["audit:rollback-approved"])

    assert proposal.status == "proposed"
    assert edge.weight == pytest.approx(0.5)
    assert rollback.restored_weight == pytest.approx(0.5)
