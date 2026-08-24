from brain.debate import CognitiveDebateSociety


def test_internal_debate_preserves_role_arguments():
    debate = CognitiveDebateSociety().debate(
        topic="permit-triggered buyer lane",
        proposal="Test buyer outreach after permit and distress signals align.",
        evidence_refs=["signal:permit", "signal:distress"],
        risk=0.2,
    )

    roles = {argument.role for argument in debate.arguments}
    assert "Skeptic" in roles
    assert "ImmuneSystem" in roles
    assert len(debate.arguments) >= 5
    assert debate.verdict == "advance_to_agency_review"


def test_skeptic_can_route_to_quarantine():
    debate = CognitiveDebateSociety().debate(
        topic="unsupported idea",
        proposal="Act without source evidence.",
        evidence_refs=[],
        risk=0.2,
    )

    assert debate.verdict == "quarantine_for_missing_evidence"
