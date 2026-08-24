from brain.agency import AgencyState, AgencyTier, GovernedAgency


def test_agency_blocks_unapproved_external_action():
    agency = GovernedAgency()
    action = agency.propose(
        action_type="outreach",
        proposal="Send outreach to validate buyer demand.",
        tier=AgencyTier.TIER_4_ACT_WITH_APPROVAL,
        source_refs=["signal:buyer_intent"],
    )

    assert action.state == AgencyState.APPROVAL_REQUIRED
    assert action.approval_status == "approval_required"


def test_agency_allows_internal_thinking_action():
    action = GovernedAgency().propose(
        action_type="think",
        proposal="Generate hypotheses from stored signals.",
        tier=AgencyTier.TIER_1_THINK,
        source_refs=["memory:signals"],
    )

    assert action.state == AgencyState.THOUGHT


def test_tier_5_hold_and_tier_6_prohibited():
    agency = GovernedAgency()
    hold = agency.propose(
        action_type="autonomous_outreach",
        proposal="Act without approval.",
        tier=AgencyTier.TIER_5_LIMITED_AUTONOMY,
        source_refs=["signal:x"],
    )
    prohibited = agency.propose(
        action_type="deception",
        proposal="Do not do this.",
        tier=AgencyTier.TIER_6_PROHIBITED,
        source_refs=["signal:x"],
    )

    assert hold.state == AgencyState.HOLD
    assert prohibited.state == AgencyState.PROHIBITED
