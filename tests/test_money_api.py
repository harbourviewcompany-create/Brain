from fastapi.testclient import TestClient

from apps.api.main import app
from tests.conftest import TEST_API_KEY


client = TestClient(app, headers={"x-api-key": TEST_API_KEY})


def test_money_lanes_endpoint_returns_seed_lanes():
    response = client.get("/money-lanes")
    assert response.status_code == 200
    lanes = response.json()
    assert any(lane["lane_id"] == "high_intent_lead_pack" for lane in lanes)


def test_package_revenue_signal_endpoint_returns_offer():
    response = client.post(
        "/revenue-signals/package",
        json={
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
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["score"]["actionable"] is True
    assert payload["offer"]["offer_name"] == "High-Intent Lead Pack"


def test_daily_revenue_report_endpoint_blocks_passive_day():
    response = client.post(
        "/daily-revenue-report",
        json={
            "raw_signals_reviewed": 50,
            "signals_logged": 20,
            "qualified_opportunities": 10,
            "prioritized_opportunities": 5,
            "direct_revenue_actions": 0,
            "sellable_assets_created": 1,
            "lessons_recorded": 1,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["passed"] is False
    assert "direct_revenue_actions" in payload["gaps"]
