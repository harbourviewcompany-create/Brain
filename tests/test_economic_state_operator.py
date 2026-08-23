from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.operator.main import app
from brain.economic_runtime import EconomicStateMachine, InMemoryEconomicStore


def test_economic_state_machine_blocks_illegal_transition() -> None:
    store = InMemoryEconomicStore()
    machine = EconomicStateMachine()
    with pytest.raises(ValueError, match="blocked_transition:pressure:hypothesized->active"):
        machine.transition(
            store,
            machine="pressure",
            object_id=uuid4(),
            from_state="hypothesized",
            to_state="active",
            trigger="attempted_skip",
        )
    assert store.transitions() == []


def test_economic_state_machine_records_allowed_transition_with_evidence() -> None:
    store = InMemoryEconomicStore()
    machine = EconomicStateMachine()
    object_id = uuid4()
    evidence_id = uuid4()
    record = machine.transition(
        store,
        machine="pressure",
        object_id=object_id,
        from_state="hypothesized",
        to_state="supported",
        trigger="evidence_threshold_met",
        evidence_ids=[evidence_id],
    )
    assert record.object_id == object_id
    assert record.evidence_ids == [evidence_id]
    assert store.transitions(object_id) == [record]


def test_operator_http_surface_is_readable_and_renders_ui() -> None:
    client = TestClient(app)
    health = client.get("/health")
    snapshot = client.get("/operator")
    ui = client.get("/operator/ui")

    assert health.status_code == 200
    assert health.json()["surface"] == "economic-operator"
    assert snapshot.status_code == 200
    assert {"act_now", "verify_first", "watch", "suppressed_count"} <= set(snapshot.json())
    assert ui.status_code == 200
    assert "Brain Economic Operator" in ui.text
    assert "ACT NOW" in ui.text


def test_operator_app_does_not_expose_consequential_write_routes() -> None:
    paths = {route.path for route in app.routes}
    assert all(not path.startswith("/execute") for path in paths)
    assert all(not path.startswith("/spend") for path in paths)
    assert all(not path.startswith("/outreach") for path in paths)
