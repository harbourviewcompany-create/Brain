from brain.cognitive_immune import CognitiveImmuneSystem, QuarantineState


def test_immune_system_quarantines_unsupported_claims():
    immune = CognitiveImmuneSystem()
    item = immune.screen(
        item_type="idea",
        item_ref="idea:1",
        claims=["Guaranteed revenue without evidence"],
        evidence_refs=[],
        risk_score=0.8,
    )

    assert item is not None
    assert item.state == QuarantineState.QUARANTINED
    assert item.reason == "unsupported_claim"


def test_immune_system_allows_evidence_backed_low_risk_item():
    assert CognitiveImmuneSystem().screen(
        item_type="idea",
        item_ref="idea:2",
        claims=["Buyer intent appears in public RFP evidence."],
        evidence_refs=["source:rfp"],
        risk_score=0.1,
    ) is None
