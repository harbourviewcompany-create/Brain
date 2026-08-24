from fastapi.testclient import TestClient

from apps.api.main import app
from tests.conftest import TEST_API_KEY


def test_cognitive_organism_api_persistence_checkpoint_and_audit():
    client = TestClient(app, headers={"x-api-key": TEST_API_KEY})

    status = client.get("/organism/persistence/status")
    assert status.status_code == 200
    assert status.json()["autonomy_boundary"] == "persistence_only_no_external_action"

    update = client.post(
        "/organism/self-state/update",
        json={
            "current_focus_summary": "Persistence checkpoint test",
            "belief_count": 1,
            "event_count": 2,
            "prediction_count": 1,
            "opportunity_count": 1,
            "source_event_ids": ["test:persistence"],
        },
    )
    assert update.status_code == 200

    checkpoint = client.get("/organism/persistence/checkpoint")
    assert checkpoint.status_code == 200
    assert checkpoint.json()["checkpoint"]["counts"]["self_state_snapshots"] >= 1

    rehydrate = client.post("/organism/persistence/rehydrate")
    assert rehydrate.status_code == 200
    assert rehydrate.json()["rehydrated"] is True

    audit = client.get("/organism/audit-events")
    assert audit.status_code == 200
    event_types = {item["event_type"] for item in audit.json()["items"]}
    assert "COGNITIVE_ORGANISM_CHECKPOINT_SAVED" in event_types
