from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

import apps.worker.main as worker_main
import brain.adapters.object_storage as object_storage_module
from brain.adapters.neo4j_projection import Neo4jConfig, Neo4jProjection
from brain.adapters.object_storage import S3ObjectStorage
from brain.domain import Edge, Node


TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")
NODE_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
NODE_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
EDGE = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")


class _Result:
    def consume(self):
        return self


class _Session:
    def __init__(self, calls):
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def run(self, query, **params):
        self.calls.append((" ".join(query.split()), params))
        return _Result()


class _Driver:
    def __init__(self):
        self.calls = []
        self.closed = False

    def session(self, *, database):
        self.calls.append(("database", database))
        return _Session(self.calls)

    def verify_connectivity(self):
        return None

    def close(self):
        self.closed = True


def _projection() -> tuple[Neo4jProjection, _Driver]:
    driver = _Driver()
    return (
        Neo4jProjection(
            Neo4jConfig("neo4j://example", "neo4j", "secret"),
            driver=driver,
        ),
        driver,
    )


def test_neo4j_node_replace_is_tenant_scoped_and_removes_stale_properties():
    projection, driver = _projection()
    node = Node(id=NODE_A, kind="concept", key="alpha", properties={"old": "value"})
    projection.upsert_node(node, scope=TENANT_A)

    query, params = next(
        (query, params)
        for query, params in driver.calls
        if isinstance(query, str) and "MERGE (n:BrainNode" in query
    )
    assert "SET n = $props" in query
    assert params["projection_id"] == f"{TENANT_A}:{NODE_A}"
    assert params["props"]["tenant_scope"] == str(TENANT_A)
    assert params["props"]["p_old"] == "value"


def test_neo4j_edge_move_deletes_same_logical_edge_before_recreate():
    projection, driver = _projection()
    edge = Edge(
        id=EDGE,
        source=NODE_A,
        target=NODE_B,
        relation="supports",
        weight=0.7,
        confidence=0.8,
        updated_at=datetime(2026, 8, 26, tzinfo=UTC),
    )
    projection.upsert_edge(edge, scope=TENANT_A)

    queries = [call for call in driver.calls if isinstance(call[0], str)]
    assert "DELETE old" in queries[0][0]
    assert queries[0][1]["projection_id"] == f"{TENANT_A}:{EDGE}"
    assert "CREATE (s)-[r:BRAIN_REL]->(t)" in queries[1][0]
    assert queries[1][1]["source_projection_id"] == f"{TENANT_A}:{NODE_A}"
    assert queries[1][1]["target_projection_id"] == f"{TENANT_A}:{NODE_B}"


def test_neo4j_rebuild_deletes_only_requested_tenant_scope():
    projection, driver = _projection()
    projection.rebuild([], [], scope=TENANT_B)

    queries = [
        (query, params)
        for query, params in driver.calls
        if isinstance(query, str) and "DELETE" in query
    ]
    assert queries
    assert all(params.get("tenant_scope") == str(TENANT_B) for _, params in queries)
    assert all("MATCH (n:BrainNode) DETACH DELETE n" not in query for query, _ in queries)


class _Precondition(Exception):
    def __init__(self):
        self.response = {"Error": {"Code": "PreconditionFailed"}}


class _S3:
    def __init__(self):
        self.objects = {}
        self.put_bodies = []

    def put_object(self, *, Bucket, Key, Body, Metadata, IfNoneMatch):
        assert IfNoneMatch == "*"
        if Key in self.objects:
            raise _Precondition()
        data = Body if isinstance(Body, bytes) else Body.read()
        self.put_bodies.append(type(Body))
        self.objects[Key] = {"data": data, "Metadata": dict(Metadata)}
        return {}

    def head_object(self, *, Bucket, Key):
        if Key not in self.objects:
            exc = Exception("not found")
            exc.response = {"Error": {"Code": "404"}}
            raise exc
        return {"Metadata": self.objects[Key]["Metadata"]}

    def get_object(self, *, Bucket, Key):
        class Body:
            def __init__(self, data):
                self.data = data

            def read(self):
                return self.data

        return {"Body": Body(self.objects[Key]["data"])}

    def delete_object(self, *, Bucket, Key):
        self.objects.pop(Key, None)


def test_object_storage_is_write_once_and_same_digest_is_idempotent():
    client = _S3()
    storage = S3ObjectStorage("brain", client=client)

    first = storage.put_bytes(b"alpha", key="fixed")
    second = storage.put_bytes(b"alpha", key="fixed")
    assert first == second

    with pytest.raises(RuntimeError, match="different digest"):
        storage.put_bytes(b"beta", key="fixed")


def test_put_file_streams_a_file_handle(tmp_path: Path):
    client = _S3()
    storage = S3ObjectStorage("brain", client=client)
    source = tmp_path / "large.bin"
    expected = b"x" * (2 * 1024 * 1024 + 7)
    source.write_bytes(expected)

    result = storage.put_file(source, key="files/large.bin")
    assert result.bytes == len(expected)
    assert client.objects["files/large.bin"]["data"] == expected
    assert client.put_bodies[-1] is not bytes


class _Boto3:
    def __init__(self):
        self.calls = []
        self.client_instance = _S3()

    def client(self, service, **kwargs):
        self.calls.append((service, kwargs))
        return self.client_instance


def test_object_storage_uses_standard_provider_chain_without_explicit_keys(monkeypatch):
    fake = _Boto3()
    monkeypatch.setattr(object_storage_module, "boto3", fake)
    monkeypatch.setenv("OBJECT_STORAGE_BUCKET", "brain")
    monkeypatch.setenv("OBJECT_STORAGE_REGION", "ca-central-1")
    monkeypatch.delenv("OBJECT_STORAGE_ENDPOINT", raising=False)
    monkeypatch.delenv("OBJECT_STORAGE_ACCESS_KEY", raising=False)
    monkeypatch.delenv("OBJECT_STORAGE_SECRET_KEY", raising=False)
    monkeypatch.delenv("OBJECT_STORAGE_SESSION_TOKEN", raising=False)

    storage = S3ObjectStorage.from_env()
    assert storage is not None
    _, kwargs = fake.calls[-1]
    assert kwargs == {"region_name": "ca-central-1"}


def test_object_storage_passes_temporary_session_token(monkeypatch):
    fake = _Boto3()
    monkeypatch.setattr(object_storage_module, "boto3", fake)
    monkeypatch.setenv("OBJECT_STORAGE_BUCKET", "brain")
    monkeypatch.setenv("OBJECT_STORAGE_ACCESS_KEY", "access")
    monkeypatch.setenv("OBJECT_STORAGE_SECRET_KEY", "secret")
    monkeypatch.setenv("OBJECT_STORAGE_SESSION_TOKEN", "token")

    storage = S3ObjectStorage.from_env()
    assert storage is not None
    _, kwargs = fake.calls[-1]
    assert kwargs["aws_access_key_id"] == "access"
    assert kwargs["aws_secret_access_key"] == "secret"
    assert kwargs["aws_session_token"] == "token"


def test_neo4j_config_requires_password_when_configured(monkeypatch):
    monkeypatch.setenv("NEO4J_URI", "neo4j://example")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="NEO4J_USER and NEO4J_PASSWORD"):
        Neo4jConfig.from_env()


def test_temporal_worker_passes_api_key_and_tls(monkeypatch):
    calls = {}

    class _Client:
        @staticmethod
        async def connect(address, **kwargs):
            calls["connect"] = (address, kwargs)
            return object()

    class _Worker:
        def __init__(self, client, **kwargs):
            calls["worker"] = (client, kwargs)

        async def run(self):
            calls["ran"] = True

    monkeypatch.setattr(worker_main, "Client", _Client)
    monkeypatch.setattr(worker_main, "Worker", _Worker)
    monkeypatch.setenv("TEMPORAL_ADDRESS", "tenant.tmprl.cloud:7233")
    monkeypatch.setenv("TEMPORAL_NAMESPACE", "tenant.account")
    monkeypatch.setenv("TEMPORAL_API_KEY", "api-key")
    monkeypatch.setenv("TEMPORAL_TLS", "true")
    monkeypatch.setenv("BRAIN_TEMPORAL_AUTOSTART", "false")

    asyncio.run(worker_main.run_temporal_worker())

    address, kwargs = calls["connect"]
    assert address == "tenant.tmprl.cloud:7233"
    assert kwargs["namespace"] == "tenant.account"
    assert kwargs["api_key"] == "api-key"
    assert kwargs["tls"] is True
    assert calls["ran"] is True
