from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from brain.money_spine import (
    RevenueActionState,
    RevenueExecutionSpine,
    RevenueOutcomeType,
    RevenueSignal,
)


def actionable_signal() -> RevenueSignal:
    return RevenueSignal(
        raw_signal="Municipal deadline creates urgent vendor demand for bid support.",
        source_id="source:rfp:test",
        money_lane_id="procurement_rfp_match",
        evidence_refs=["https://example.test/rfp"],
        named_buyer="eligible local vendors",
        decision_maker="procurement lead",
        visible_pain="deadline pressure",
        urgency_reason="bid due in 72 hours",
        payment_path="paid opportunity brief",
        contact_channel="email",
        commercial_value=0.9,
        confidence=0.8,
        urgency=0.9,
        contactability=0.8,
        execution_difficulty=0.25,
    )


def test_revenue_execution_queues_action_without_external_send():
    spine = RevenueExecutionSpine()
    score, offer, action = spine.queue_action_from_signal(actionable_signal())

    assert score.actionable is True
    assert offer.approval_required is True
    assert action.state == RevenueActionState.APPROVAL_REQUIRED
    assert action.approved_by is None
    assert spine.snapshot()["autonomy_boundary"] == "queues_only_no_send_no_spend_no_tier5_autonomy"


def test_revenue_execution_blocks_manual_action_before_approval():
    spine = RevenueExecutionSpine()
    _, _, action = spine.queue_action_from_signal(actionable_signal())

    with pytest.raises(PermissionError):
        spine.log_manual_action(action.id, manual_proof_ref="operator:sent:1")

    approved = spine.approve_action(action.id, approved_by="operator")
    assert approved.state == RevenueActionState.APPROVED
    logged = spine.log_manual_action(action.id, manual_proof_ref="operator:sent:1")
    assert logged.state == RevenueActionState.MANUAL_ACTION_LOGGED


def test_revenue_execution_followups_and_outcomes_update_learning():
    spine = RevenueExecutionSpine()
    _, _, action = spine.queue_action_from_signal(actionable_signal())
    spine.approve_action(action.id, approved_by="operator")
    spine.log_manual_action(action.id, manual_proof_ref="operator:sent:1")

    followup = spine.schedule_follow_up(action.id, script="Following up on the RFP pack.", delay_hours=1)
    due = spine.due_followups(now=datetime.now(timezone.utc) + timedelta(hours=2))
    assert followup in due

    before = spine.money.lanes[action.lane_id].priority_score
    outcome = spine.record_outcome(
        action.id,
        outcome_type=RevenueOutcomeType.PAID_CONVERSION,
        revenue=500,
        reply=True,
        meeting_booked=True,
        paid_conversion=True,
        legal_risk=0.0,
        operator_hours=1.5,
        lesson="RFP deadline briefs convert when vendors are named.",
    )

    assert outcome.revenue == 500
    assert spine.actions[action.id].state == RevenueActionState.OUTCOME_LOGGED
    assert spine.money.lanes[action.lane_id].priority_score > before
    assert spine.money.source_scores[action.source_id] > 0.5
    assert spine.snapshot()["revenue"] == 500
