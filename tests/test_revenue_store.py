"""Revenue persistence: row<->object translation, and that
MoneySpineService/RevenueExecutionSpine actually write through to an
injected store on every mutation. No live Postgres needed — this
follows the same pattern as tests/test_postgres_adapter.py: pure
translation logic is unit tested directly; write-through wiring is
tested against a fake in-memory store standing in for
PostgresRevenueStore's interface.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from brain.adapters.revenue_store import PostgresRevenueStore
from brain.money_spine import (
    AutomationReadiness,
    MoneyLane,
    MoneySpineService,
    OpportunityClass,
    RevenueActionState,
    RevenueExecutionAction,
    RevenueExecutionSpine,
    RevenueOutcomeType,
    RevenueSignal,
)


# --- row <-> object translation -----------------------------------------

def test_row_to_lane_round_trip():
    row = {
        "lane_key": "high_intent_lead_pack",
        "title": "High-intent lead pack",
        "opportunity_class": "high_intent_lead",
        "packaged_offer": "High-Intent Lead Pack",
        "buyer_type": "agency",
        "seller_or_target_type": "companies",
        "first_48_hour_action": "Build 25 leads",
        "price_low": 150.0,
        "price_high": 500.0,
        "repeatability": 0.9,
        "fulfillment_difficulty": 0.25,
        "time_to_cash_days": 2.0,
        "automation_readiness": "semi_automated",
        "legal_access_risk": 0.0,
        "priority_score": 0.73,
    }
    lane = PostgresRevenueStore._row_to_lane(row)
    assert lane.lane_id == "high_intent_lead_pack"
    assert lane.opportunity_class == OpportunityClass.HIGH_INTENT_LEAD
    assert lane.automation_readiness == AutomationReadiness.SEMI_AUTOMATED
    assert lane.priority_score == 0.73


def test_row_to_action_round_trip():
    action_id = uuid4()
    now = datetime.now(UTC)
    row = {
        "id": action_id,
        "opportunity_id": uuid4(),
        "offer_id": uuid4(),
        "lane_id": "procurement_rfp_match",
        "source_id": "demo",
        "action_type": "outreach_draft",
        "target_contact": "Procurement Director",
        "proposal": "Draft outreach text",
        "evidence_refs": ["https://example.com/x"],
        "approval_required": True,
        "state": "approved",
        "approved_by": "tyler",
        "manual_proof_ref": None,
        "created_at": now,
        "updated_at": now,
    }
    action = PostgresRevenueStore._row_to_action(row)
    assert action.id == action_id
    assert action.state == RevenueActionState.APPROVED
    assert action.evidence_refs == ["https://example.com/x"]


def test_row_to_followup_round_trip():
    followup_id = uuid4()
    action_id = uuid4()
    due = datetime.now(UTC) + timedelta(hours=48)
    row = {
        "id": followup_id,
        "action_id": action_id,
        "due_at": due,
        "script": "Checking in",
        "state": "scheduled",
        "completed_at": None,
    }
    followup = PostgresRevenueStore._row_to_followup(row)
    assert followup.id == followup_id
    assert followup.due_at == due


def test_row_to_outcome_round_trip():
    entry_id = uuid4()
    action_id = uuid4()
    now = datetime.now(UTC)
    row = {
        "id": entry_id,
        "action_id": action_id,
        "lane_id": "high_intent_lead_pack",
        "source_id": "demo",
        "outcome_type": "paid_conversion",
        "revenue": 250,
        "reply": True,
        "meeting_booked": True,
        "paid_conversion": True,
        "legal_risk": 0,
        "operator_hours": 1.5,
        "lesson": "Fast response rate",
        "created_at": now,
    }
    entry = PostgresRevenueStore._row_to_outcome(row)
    assert entry.id == entry_id
    assert entry.outcome_type == RevenueOutcomeType.PAID_CONVERSION
    assert entry.revenue == 250.0


# --- write-through wiring, against a fake store --------------------------

class FakeRevenueStore:
    """Stands in for PostgresRevenueStore's public interface, in memory,
    so write-through calls can be asserted without a live database."""

    def __init__(self, lanes: dict[str, MoneyLane] | None = None,
                 source_scores: dict[str, float] | None = None) -> None:
        self._lanes = dict(lanes or {})
        self._source_scores = dict(source_scores or {})
        self.actions: dict = {}
        self.followups: dict = {}
        self.outcomes: dict = {}
        self.seed_calls = 0
        self.save_lane_priority_calls: list[MoneyLane] = []
        self.save_source_score_calls: list[tuple[str, float]] = []

    def load_lanes(self):
        return dict(self._lanes)

    def seed_lanes(self, lanes):
        self.seed_calls += 1
        self._lanes = {lane.lane_id: lane for lane in lanes}

    def save_lane_priority(self, lane):
        self.save_lane_priority_calls.append(lane)
        self._lanes[lane.lane_id] = lane

    def load_source_scores(self):
        return dict(self._source_scores)

    def save_source_score(self, source_id, score):
        self.save_source_score_calls.append((source_id, score))
        self._source_scores[source_id] = score

    def load_actions(self):
        return dict(self.actions)

    def save_action(self, action):
        self.actions[action.id] = action

    def load_followups(self):
        return dict(self.followups)

    def save_followup(self, followup):
        self.followups[followup.id] = followup

    def load_outcomes(self):
        return dict(self.outcomes)

    def save_outcome(self, entry):
        self.outcomes[entry.id] = entry


def test_money_spine_seeds_store_when_empty():
    store = FakeRevenueStore()
    service = MoneySpineService(store=store)
    assert store.seed_calls == 1
    assert set(service.lanes) == set(store.load_lanes())


def test_money_spine_hydrates_existing_lanes_without_reseeding():
    existing_lane = MoneyLane(
        lane_id="high_intent_lead_pack", title="Custom title",
        opportunity_class=OpportunityClass.HIGH_INTENT_LEAD, packaged_offer="Pack",
        buyer_type="agency", seller_or_target_type="companies", source_targets=[],
        search_queries=[], first_48_hour_action="Do it", price_low=100, price_high=200,
        repeatability=0.5, fulfillment_difficulty=0.5, time_to_cash_days=1,
        priority_score=0.81,
    )
    store = FakeRevenueStore(lanes={"high_intent_lead_pack": existing_lane}, source_scores={"demo": 0.62})
    service = MoneySpineService(store=store)
    assert store.seed_calls == 0
    assert service.lanes["high_intent_lead_pack"].priority_score == 0.81
    assert service.source_scores["demo"] == 0.62


def test_apply_outcome_learning_writes_through_lane_and_source_score():
    store = FakeRevenueStore()
    service = MoneySpineService(store=store)
    service.apply_outcome_learning(
        "high_intent_lead_pack", "demo-source",
        revenue=300.0, reply=True, legal_risk=0.0, operator_hours=1.0,
    )
    assert len(store.save_lane_priority_calls) == 1
    assert store.save_lane_priority_calls[0].lane_id == "high_intent_lead_pack"
    assert store.save_source_score_calls[-1][0] == "demo-source"


def test_money_spine_without_store_never_touches_none():
    # No store -> pure in-memory behavior, must not raise.
    service = MoneySpineService()
    service.apply_outcome_learning(
        "high_intent_lead_pack", "demo-source",
        revenue=100.0, reply=False, legal_risk=0.0, operator_hours=0.5,
    )
    assert "demo-source" in service.source_scores


_SIGNAL = RevenueSignal(
    raw_signal="Urgent vendor search",
    source_id="demo-source",
    money_lane_id="high_intent_lead_pack",
    evidence_refs=["https://example.test/signal"],
    named_buyer="Example Co",
    decision_maker="Ops Lead",
    visible_pain="Urgent vendor search",
    urgency_reason="Public urgent request",
    payment_path="Sell lead pack",
    contact_channel="email",
    commercial_value=0.8, confidence=0.8, urgency=0.9, contactability=0.8, execution_difficulty=0.2,
)


def test_revenue_execution_spine_hydrates_from_store():
    action = RevenueExecutionAction(
        opportunity_id=uuid4(), offer_id=uuid4(), lane_id="high_intent_lead_pack",
        source_id="demo", action_type="outreach_draft", target_contact="X",
        proposal="Y", evidence_refs=[],
    )
    store = FakeRevenueStore()
    store.actions[action.id] = action
    spine = RevenueExecutionSpine(store=store)
    assert action.id in spine.actions


def test_revenue_execution_spine_writes_through_full_lifecycle():
    money_store = FakeRevenueStore()
    money = MoneySpineService(store=money_store)
    spine = RevenueExecutionSpine(money=money, store=money_store)

    _, _, action = spine.queue_action_from_signal(_SIGNAL)
    assert action.id in money_store.actions

    spine.approve_action(action.id, approved_by="tyler")
    assert money_store.actions[action.id].state == RevenueActionState.APPROVED

    spine.log_manual_action(action.id, manual_proof_ref="proof://x")
    assert money_store.actions[action.id].state == RevenueActionState.MANUAL_ACTION_LOGGED

    followup = spine.schedule_follow_up(action.id, script="check in", delay_hours=24)
    assert followup.id in money_store.followups

    entry = spine.record_outcome(
        action.id, outcome_type=RevenueOutcomeType.PAID_CONVERSION, revenue=500.0,
        reply=True, meeting_booked=True, paid_conversion=True, legal_risk=0.0,
        operator_hours=1.0, lesson="worked",
    )
    assert entry.id in money_store.outcomes
    assert money_store.actions[action.id].state == RevenueActionState.OUTCOME_LOGGED
    # apply_outcome_learning ran through the shared money_store too.
    assert len(money_store.save_lane_priority_calls) == 1


def test_revenue_execution_spine_without_store_still_works():
    spine = RevenueExecutionSpine()
    _, _, action = spine.queue_action_from_signal(_SIGNAL)
    spine.approve_action(action.id, approved_by="tyler")
    spine.log_manual_action(action.id, manual_proof_ref="proof://x")
    entry = spine.record_outcome(
        action.id, outcome_type=RevenueOutcomeType.PAID_CONVERSION, revenue=100.0,
        reply=True, meeting_booked=False, paid_conversion=True, legal_risk=0.0,
        operator_hours=0.5, lesson="worked",
    )
    assert entry.revenue == 100.0
