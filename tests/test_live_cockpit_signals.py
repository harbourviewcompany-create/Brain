from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

import apps.api.main as api
from apps.api.cockpit_read_routes import _signal_item_from_event
from brain.events import BrainEvent
from tests.conftest import TEST_API_KEY

# The cockpit read model moved from tools/live_cockpit_routes.py, which only the
# deprecated Dockerfile.railway image serves, onto the canonical app in
# apps/api/main.py. Exercise it there, through the real HTTP surface, so the
# test proves the route the production image actually exposes.
client = TestClient(api.app, headers={"x-api-key": TEST_API_KEY})


def _signal_event(*, token: str = "durable-probe") -> BrainEvent:
    return BrainEvent(
        "signal.enqueued",
        "sensory_inbox",
        uuid4(),
        {
            "source_key": "production_smoke",
            "content": f"[{token}] durable signal",
            "claim": "durable signals are readable",
            "payload": {
                "source_reliability": 1.0,
                "novelty": 0.2,
                "urgency": 0.3,
                "commercial_upside": 0.4,
                "contradiction_value": 0.0,
                "uncertainty_reduction": 0.5,
                "noise_probability": 0.1,
                "operator_burden": 0.0,
                "metadata": {"token": token},
            },
        },
        occurred_at=datetime(2026, 8, 24, 15, 0, tzinfo=UTC),
    )


def test_signal_item_preserves_durable_signal_identity_and_payload() -> None:
    event = _signal_event()

    item = _signal_item_from_event(event)

    assert item["id"] == str(event.aggregate_id)
    assert item["source_id"] == "production_smoke"
    assert item["novelty"] == 0.2
    assert item["urgency"] == 0.3
    assert item["commercial_upside"] == 0.4
    assert item["created_at"] == "2026-08-24T15:00:00+00:00"
    assert item["metadata"]["token"] == "durable-probe"
    assert item["metadata"]["content"] == "[durable-probe] durable signal"
    assert item["metadata"]["claim"] == "durable signals are readable"


def test_list_signals_reads_event_stream_not_evidence_projection(monkeypatch) -> None:
    event = _signal_event(token="stream-only")

    class EventStreamOnlyStore:
        evidence = {}

        def read_all(self):
            return [
                BrainEvent("unrelated.event", "test", uuid4(), {}),
                event,
            ]

    monkeypatch.setattr(api.runtime, "store", EventStreamOnlyStore())

    response = client.get("/signals").json()

    assert response["total"] == 1
    assert response["source"] == "api"
    assert response["items"][0]["id"] == str(event.aggregate_id)
    assert response["items"][0]["metadata"]["token"] == "stream-only"
