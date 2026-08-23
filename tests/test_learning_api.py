from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.main import app, learning
from brain.domain import Edge, Node, Outcome
from brain.learning import LearningService
from brain.memory import InMemoryBrainStore
from brain.prediction import PredictionEngine, PredictionStatus

client = TestClient(app)


def test_create_prediction_emits_event_and_persists():
    edge_id = str(uuid4())
    resp = client.post(
        "/predictions",
        json={
            "statement": "Market expands",
            "expected_value": 0.8,
            "confidence": 0.7,
            "horizon_seconds": 3600,
            "edge_ids": [edge_id],
            "source_keys": ["regulator"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["statement"] == "Market expands"
    assert data["status"] == "open"
    pred_id = data["id"]

    got = client.get(f"/predictions/{pred_id}")
    assert got.status_code == 200
    assert got.json()["id"] == pred_id

    events = learning.event_store.read_all() if hasattr(learning.event_store, "read_all") else []
    assert any(e.event_type == "prediction.created" for e in events)


def test_outcome_attribution_emits_learning_events():
    store = InMemoryBrainStore()
    mem = __import__("brain.adapters.learning_store", fromlist=["InMemoryLearningStore"]).InMemoryLearningStore()
    a = Node("entity", "a")
    b = Node("entity", "b")
    edge = Edge(a.id, b.id, "related_to", weight=0.5)
    mem.upsert_edge(edge)
    svc = LearningService(
        store,
        predictions=mem,
        edges=mem,
        attributions=mem,
        sources=mem,
    )
    pred = PredictionEngine().create(
        "Deal closes",
        expected_value=0.5,
        confidence=0.8,
        horizon=timedelta(hours=1),
        edge_ids=[edge.id],
        source_keys=["crm"],
    )
    svc.create_prediction(pred)

    outcome = Outcome(
        action_id=uuid4(),
        value_created=1.0,
        operator_time_cost=0.1,
        prediction_accuracy=1.0,
        prediction_id=pred.id,
        edge_ids=[edge.id],
        source_keys=["crm"],
    )
    result = svc.record_outcome(outcome, prediction_id=pred.id, edge_ids=[edge.id])
    assert result.attribution.reward_score != 0
    assert result.updated_edges[0].weight > 0.5

    kinds = [e.event_type for e in store.events]
    assert "prediction.created" in kinds
    assert "outcome.recorded" in kinds
    assert "prediction.resolved" in kinds
    assert "graph.edge_rewired" in kinds
    assert "learning.attribution_recorded" in kinds

    saved = mem.get(pred.id)
    assert saved is not None
    assert saved.status is PredictionStatus.RESOLVED
    assert len(mem.attributions) == 1
    assert "crm" in mem.source_scores


def test_api_outcome_with_edge_reinforcement():
    n1, n2 = str(uuid4()), str(uuid4())
    edge_resp = client.post(
        "/edges",
        json={
            "source_node_id": n1,
            "target_node_id": n2,
            "relation": "supplies",
            "weight": 0.4,
        },
    )
    assert edge_resp.status_code == 200
    edge_id = edge_resp.json()["id"]

    pred_resp = client.post(
        "/predictions",
        json={
            "statement": "Supply link holds",
            "expected_value": 0.6,
            "confidence": 0.9,
            "edge_ids": [edge_id],
            "source_keys": ["ops"],
        },
    )
    pred_id = pred_resp.json()["id"]

    out_resp = client.post(
        "/outcomes",
        json={
            "action_id": str(uuid4()),
            "value_created": 1.0,
            "operator_time_cost": 0.05,
            "prediction_accuracy": 1.0,
            "prediction_id": pred_id,
            "edge_ids": [edge_id],
            "source_keys": ["ops"],
        },
    )
    assert out_resp.status_code == 200
    body = out_resp.json()
    assert body["reward_score"] > 0
    assert body["updated_edges"]
    assert body["updated_edges"][0]["weight"] > 0.4
    assert body["prediction_id"] == pred_id
