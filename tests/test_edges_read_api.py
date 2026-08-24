"""Regression coverage for the authenticated durable Observatory edge read contract."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import apps.api.main as brain_api
import tools.live_cockpit_routes as live_routes
from brain.adapters.learning_store import InMemoryLearningStore, PostgresEdgeStore
from tests.conftest import TEST_API_KEY


client = TestClient(live_routes.app)
AUTH = {"x-api-key": TEST_API_KEY}


@pytest.fixture
def isolated_edge_store(monkeypatch):
    store = InMemoryLearningStore()
    monkeypatch.setattr(brain_api.learning, "edges", store)
    return store


def test_get_edges_requires_authentication(isolated_edge_store):
    response = client.get("/edges")
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_or_missing_api_key"


def test_get_edges_returns_empty_list_response(isolated_edge_store):
    response = client.get("/edges", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "source": "api"}


def test_posted_edge_is_read_back_by_get_edges(isolated_edge_store):
    source_id = uuid4()
    target_id = uuid4()
    edge_id = uuid4()

    created = client.post(
        "/edges",
        headers=AUTH,
        json={
            "edge_id": str(edge_id),
            "source_node_id": str(source_id),
            "target_node_id": str(target_id),
            "relation": "supports",
            "weight": 0.72,
            "confidence": 0.81,
        },
    )
    assert created.status_code == 200
    assert created.json()["id"] == str(edge_id)

    response = client.get("/edges", headers=AUTH)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    edge = payload["items"][0]
    assert edge["id"] == str(edge_id)
    assert edge["source"] == str(source_id)
    assert edge["target"] == str(target_id)
    assert edge["source_node_id"] == str(source_id)
    assert edge["target_node_id"] == str(target_id)
    assert edge["relation"] == "supports"
    assert edge["weight"] == pytest.approx(0.72)
    assert edge["confidence"] == pytest.approx(0.81)


class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.query = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.query = query
        return self

    def fetchall(self):
        return list(self.rows)


class _FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = _FakeCursor(rows)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, row_factory=None):
        return self.cursor_instance


class _FakeConnectionContext:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self, rows):
        self.connection_instance = _FakeConnection(rows)

    def connection(self):
        return _FakeConnectionContext(self.connection_instance)


def test_postgres_edge_store_lists_persisted_edges():
    edge_id = uuid4()
    source_id = uuid4()
    target_id = uuid4()
    updated_at = datetime(2026, 8, 24, 17, 30, tzinfo=UTC)
    pool = _FakePool(
        [
            {
                "id": edge_id,
                "source_id": source_id,
                "target_id": target_id,
                "relation": "predicts",
                "weight": 0.66,
                "confidence": 0.91,
                "evidence_ids": [],
                "updated_at": updated_at,
            }
        ]
    )

    edges = PostgresEdgeStore(pool).list_edges()

    assert len(edges) == 1
    edge = edges[0]
    assert edge.id == edge_id
    assert edge.source == source_id
    assert edge.target == target_id
    assert edge.relation == "predicts"
    assert edge.weight == pytest.approx(0.66)
    assert edge.confidence == pytest.approx(0.91)
    assert edge.updated_at == updated_at
    assert "from public.graph_edges" in pool.connection_instance.cursor_instance.query
