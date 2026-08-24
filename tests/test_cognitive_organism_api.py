from fastapi.testclient import TestClient

from apps.api.main import app
from tests.conftest import TEST_API_KEY


def test_cognitive_organism_api_returns_cockpit_snapshot():
    client = TestClient(app, headers={"x-api-key": TEST_API_KEY})

    initial = client.get("/organism/cockpit")
    assert initial.status_code == 200
    assert initial.json()["autonomy_boundary"] == "tiers_0_to_4_only_tier_5_hold_tier_6_prohibited"

    workspace = client.post(
        "/organism/workspace/admit",
        json={
            "title": "Live procurement anomaly",
            "content": "A deadline signal may reveal vendor demand.",
            "source_refs": ["signal:rfp"],
            "salience": 0.8,
            "novelty": 0.7,
            "urgency": 0.8,
            "goal_pressure": 0.7,
        },
    )
    assert workspace.status_code == 200
    assert workspace.json()["admitted"] is True

    idea = client.post(
        "/organism/original-ideas/generate",
        json={
            "title": "Procurement deadline vendor lane",
            "idea": "Fuse procurement deadlines, local permit data and buyer intent into a 48-hour revenue validation offer for named buyers.",
            "source_signal_refs": ["signal:rfp", "signal:permit"],
            "memory_refs": ["memory:buyer_intent"],
            "combination_method": "cross_domain_signal_fusion",
            "why_most_people_miss_it": "They monitor procurement and permits separately.",
            "fastest_test": "Run a 48-hour validation against 30 vendors.",
            "kill_condition": "Kill if no replies after 30 targeted messages.",
        },
    )
    assert idea.status_code == 200
    assert idea.json()["approval_status"] == "approval_required"

    action = client.post(
        "/organism/agency/propose",
        json={
            "action_type": "outreach",
            "proposal": "Ask vendors whether they want the procurement brief.",
            "tier": "tier_4_act_with_approval",
            "source_refs": ["signal:rfp"],
        },
    )
    assert action.status_code == 200
    assert action.json()["state"] == "approval_required"
