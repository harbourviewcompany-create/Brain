import pytest

from brain.developmental.immune import CognitiveImmuneService


def test_approval_bypass_is_quarantined() -> None:
    service = CognitiveImmuneService()
    quarantine = service.detect_approval_bypass(
        action_ref="action:send-outreach-without-approval",
        evidence_refs=["audit:approval-missing"],
    )

    assert quarantine.reason == "external_action_without_approval"
    assert service.alerts[0].alert_type == "approval_bypass"


def test_contaminated_source_is_blocked() -> None:
    service = CognitiveImmuneService()
    quarantine = service.detect_contaminated_source(
        source_ref="source:unlicensed-feed",
        evidence_refs=["rights:prohibited"],
    )

    assert quarantine.reason == "unsafe_or_unlicensed_source"
    assert quarantine.recoverable is True


def test_overconfidence_triggers_alert() -> None:
    service = CognitiveImmuneService()
    alert = service.detect_overconfidence(
        claim_ref="claim:brain-complete",
        confidence=0.97,
        evidence_count=1,
        evidence_refs=["report:partial"],
    )

    assert alert is not None
    assert alert.alert_type == "overconfidence"


def test_recovery_requires_evidence() -> None:
    service = CognitiveImmuneService()
    quarantine = service.detect_contaminated_source(
        source_ref="source:x",
        evidence_refs=["rights:hold"],
    )
    with pytest.raises(ValueError, match="recovery_requires_evidence"):
        service.create_recovery_plan(quarantine, required_evidence_refs=[], steps=["review"])

    plan = service.create_recovery_plan(
        quarantine,
        required_evidence_refs=["rights:permissioned"],
        steps=["verify license", "rerun fixture"],
    )
    assert plan.status == "planned"
    assert plan.required_evidence_refs == ["rights:permissioned"]
