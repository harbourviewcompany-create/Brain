"""Health checks for configured Brain infrastructure dependencies."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import psycopg
from temporalio.client import Client

from .neo4j_projection import Neo4jConfig, Neo4jProjection
from .object_storage import S3ObjectStorage


def _postgres() -> dict[str, Any]:
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        return {"configured": False, "ok": True}
    try:
        with psycopg.connect(dsn, connect_timeout=5) as conn:
            conn.execute("select 1")
        return {"configured": True, "ok": True}
    except Exception as exc:
        return {"configured": True, "ok": False, "error": str(exc)}


def _neo4j() -> dict[str, Any]:
    try:
        config = Neo4jConfig.from_env()
        if config is None:
            return {"configured": False, "ok": True}
        projection = Neo4jProjection(config)
        try:
            ok = projection.healthy()
        finally:
            projection.close()
        return {"configured": True, "ok": ok}
    except Exception as exc:
        return {"configured": True, "ok": False, "error": str(exc)}


async def _temporal_check() -> bool:
    """Verify Temporal reachability/authentication through the native SDK.

    ``Client.connect`` performs the SDK connection/authentication handshake.
    We intentionally do not call the generic gRPC health service afterward:
    Temporal Cloud API-key connections can reject that endpoint even when the
    authenticated namespace connection used by workers is healthy.
    """
    address = os.environ["TEMPORAL_ADDRESS"]
    namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
    api_key = os.environ.get("TEMPORAL_API_KEY", "").strip() or None
    tls_env = os.environ.get("TEMPORAL_TLS", "").strip().lower()
    tls = api_key is not None or tls_env in {"1", "true", "yes", "on"}
    client = await Client.connect(
        address,
        namespace=namespace,
        api_key=api_key,
        tls=tls,
    )
    return client is not None


def _temporal() -> dict[str, Any]:
    if not os.environ.get("TEMPORAL_ADDRESS", "").strip():
        return {"configured": False, "ok": True}
    try:
        return {"configured": True, "ok": asyncio.run(_temporal_check())}
    except Exception as exc:
        return {"configured": True, "ok": False, "error": str(exc)}


def _object_storage() -> dict[str, Any]:
    if not os.environ.get("OBJECT_STORAGE_BUCKET", "").strip():
        return {"configured": False, "ok": True}
    try:
        storage = S3ObjectStorage.from_env()
        assert storage is not None
        storage.client.head_bucket(Bucket=storage.bucket)
        return {"configured": True, "ok": True}
    except Exception as exc:
        return {"configured": True, "ok": False, "error": str(exc)}


def infrastructure_status() -> dict[str, Any]:
    services = {
        "postgres": _postgres(),
        "neo4j": _neo4j(),
        "temporal": _temporal(),
        "object_storage": _object_storage(),
    }
    configured = [value for value in services.values() if value["configured"]]
    return {
        **services,
        "all_configured_healthy": all(value["ok"] for value in configured),
    }
