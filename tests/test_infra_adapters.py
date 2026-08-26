"""Unit tests for infrastructure adapters (no live cloud required)."""

from __future__ import annotations

from io import BytesIO
from uuid import uuid4
from unittest.mock import MagicMock

from brain.adapters.neo4j_projection import Neo4jConfig, Neo4jProjection, _neo4j_value
from brain.adapters.object_storage import ObjectStorage, ObjectStorageConfig
from brain.domain import Edge, Node


def test_neo4j_config_from_env(monkeypatch):
    monkeypatch.delenv("NEO4J_URI", raising=False)
    assert Neo4jConfig.from_env() is None
    monkeypatch.setenv("NEO4J_URI", "neo4j://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "x")
    cfg = Neo4jConfig.from_env()
    assert cfg is not None
    assert cfg.uri.startswith("neo4j")


def test_object_storage_config_from_env(monkeypatch):
    monkeypatch.delenv("OBJECT_STORAGE_BUCKET", raising=False)
    assert ObjectStorageConfig.from_env() is None
    monkeypatch.setenv("OBJECT_STORAGE_BUCKET", "brain-artifacts")
    monkeypatch.setenv("OBJECT_STORAGE_ENDPOINT", "http://localhost:9000")
    cfg = ObjectStorageConfig.from_env()
    assert cfg is not None
    assert cfg.bucket == "brain-artifacts"
    assert cfg.endpoint_url.endswith("9000")


def test_neo4j_value_coercion():
    uid = uuid4()
    assert _neo4j_value(uid) == str(uid)
    assert _neo4j_value({"a": 1}) == str({"a": 1})
    assert _neo4j_value([1, uid]) == [1, str(uid)]


def test_domain_graph_objects_for_projection():
    n = Node(kind="entity", key="acme", properties={"sector": "saas"})
    e = Edge(source=n.id, target=uuid4(), relation="competes_with", weight=0.7)
    assert n.key == "acme"
    assert e.relation == "competes_with"


def test_neo4j_projection_upsert_node_with_mock_driver():
    cfg = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="x")
    session = MagicMock()
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = False
    proj = Neo4jProjection(cfg, driver=driver)
    node = Node(kind="entity", key="acme", properties={"sector": "saas"})
    proj.upsert_node(node)
    session.run.assert_called()
    cypher = session.run.call_args[0][0]
    assert "BrainNode" in cypher or "MERGE" in cypher.upper() or "CREATE" in cypher.upper()


def test_object_storage_put_get_with_mock_client():
    cfg = ObjectStorageConfig(bucket="brain-artifacts", prefix="brain/")
    client = MagicMock()
    store = ObjectStorage(cfg, client=client)
    meta = store.put_bytes(b"hello-evidence", content_type="text/plain", object_key="evidence/test.bin")
    assert meta["bucket"] == "brain-artifacts"
    assert meta["key"].startswith("brain/")
    assert meta["sha256"]
    client.put_object.assert_called_once()
    put_kwargs = client.put_object.call_args.kwargs
    assert put_kwargs["Bucket"] == "brain-artifacts"
    assert put_kwargs["Body"] == b"hello-evidence"

    client.get_object.return_value = {"Body": BytesIO(b"hello-evidence")}
    data = store.get_bytes(meta["key"])
    assert data == b"hello-evidence"

    client.head_object.return_value = {}
    assert store.exists(meta["key"]) is True
