"""Revenue execution spine API: queue -> approve -> log -> outcome.

This is the HTTP surface that was previously missing entirely — the class
existed (brain.money_spine.RevenueExecutionSpine) but had no route. These
tests exercise the full approval-gated loop end to end, including that
skipping a required step (e.g. logging before approval) is rejected.
"""

from fastapi.testclient import TestClient

from apps.api.main import app
from tests.conftest import TEST_API_KEY

client = TestClient(app, headers={"x-api-key": TEST_API_KEY})

_SIGNAL = {
    "raw_signal": "Company posted urgent request for vendor recommendations",
    "source_id": "manual-test-source",
    "money_lane_id": "high_intent_lead_pack",
    "evidence_refs": ["https://example.test/signal"],
    "named_buyer": "Example Co",
    "decision_maker": "Operations Lead",
    "visible_pain": "Urgent vendor search",
    "urgency_reason": "Public urgent request",
    "payment_path": "Sell lead pack to relevant vendors",
    "contact_channel": "email",
    "commercial_value": 0.8,
    "confidence": 0.8,
    "urgency": 0.9,
    "contactability": 0.8,
    "execution_difficulty": 0.2,
}


def _queue_action() -> dict:
    response = client.post("/revenue-actions/queue", json={"signal": _SIGNAL})
    assert response.status_code == 200
    return response.json()


def test_queue_revenue_action_starts_approval_required():
    payload = _queue_action()
    assert payload["action"]["state"] == "approval_required"
    assert payload["offer"]["offer_name"] == "High-Intent Lead Pack"


def test_log_manual_action_before_approval_is_rejected():
    payload = _queue_action()
    action_id = payload["action"]["id"]
    response = client.post(
        f"/revenue-actions/{action_id}/log-manual",
        json={"manual_proof_ref": "screenshot://premature"},
    )
    assert response.status_code == 409


def test_full_approval_gated_lifecycle_records_outcome_and_updates_snapshot():
    payload = _queue_action()
    action_id = payload["action"]["id"]

    approve = client.post(
        f"/revenue-actions/{action_id}/approve",
        json={"approved_by": "tyler"},
    )
    assert approve.status_code == 200
    assert approve.json()["state"] == "approved"
    assert approve.json()["approved_by"] == "tyler"

    logged = client.post(
        f"/revenue-actions/{action_id}/log-manual",
        json={"manual_proof_ref": "screenshot://sent-outreach"},
    )
    assert logged.status_code == 200
    assert logged.json()["state"] == "manual_action_logged"

    followup = client.post(
        f"/revenue-actions/{action_id}/follow-up",
        json={"script": "Checking in on the lead pack", "delay_hours": 48},
    )
    assert followup.status_code == 200
    assert followup.json()["action_id"] == action_id

    outcome = client.post(
        f"/revenue-actions/{action_id}/outcome",
        json={
            "outcome_type": "paid_conversion",
            "revenue": 250.0,
            "reply": True,
            "meeting_booked": True,
            "paid_conversion": True,
            "legal_risk": 0.0,
            "operator_hours": 1.5,
            "lesson": "Fast response rate on this lane",
        },
    )
    assert outcome.status_code == 200
    assert outcome.json()["revenue"] == 250.0

    fetched = client.get(f"/revenue-actions/{action_id}")
    assert fetched.status_code == 200
    assert fetched.json()["state"] == "outcome_logged"

    snapshot = client.get("/revenue-actions")
    assert snapshot.status_code == 200
    body = snapshot.json()
    assert body["outcomes"] >= 1
    assert body["revenue"] >= 250.0
    assert body["autonomy_boundary"] == "queues_only_no_send_no_spend_no_tier5_autonomy"


def test_approve_unknown_action_returns_404():
    response = client.post(
        "/revenue-actions/00000000-0000-0000-0000-000000000000/approve",
        json={"approved_by": "tyler"},
    )
    assert response.status_code == 404


def test_queue_revenue_action_unknown_lane_returns_404():
    bad_signal = dict(_SIGNAL, money_lane_id="not_a_real_lane")
    response = client.post("/revenue-actions/queue", json={"signal": bad_signal})
    assert response.status_code == 404
