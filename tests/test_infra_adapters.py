"""Unit tests for infrastructure adapters (no live cloud required)."""

from __future__ import annotations

from uuid import uuid4

from brain.adapters.neo4j_projection import Neo4jConfig, _neo4j_value
from brain.adapters.object_storage import ObjectStorageConfig
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
