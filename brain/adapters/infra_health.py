"""Aggregate health checks for Postgres, Neo4j, Temporal, and object storage."""

from __future__ import annotations

import os
import socket
from typing import Any


def _tcp_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_postgres(dsn: str | None = None) -> dict[str, Any]:
    dsn = dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        return {"configured": False, "healthy": True, "detail": "not_configured"}
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=3) as conn:
            row = conn.execute("select 1").fetchone()
            ok = bool(row and row[0] == 1)
        return {"configured": True, "healthy": ok, "detail": "connected" if ok else "failed"}
    except Exception as exc:
        return {"configured": True, "healthy": False, "detail": str(exc)[:200]}


def check_neo4j() -> dict[str, Any]:
    if not os.environ.get("NEO4J_URI"):
        return {"configured": False, "healthy": True, "detail": "not_configured"}
    try:
        from .neo4j_projection import Neo4jProjection

        proj = Neo4jProjection.from_env()
        if proj is None:
            return {"configured": False, "healthy": True, "detail": "disabled"}
        ok = proj.healthy()
        proj.close()
        return {"configured": True, "healthy": ok, "detail": "connected" if ok else "unavailable"}
    except Exception as exc:
        return {"configured": True, "healthy": False, "detail": str(exc)[:200]}


def check_temporal() -> dict[str, Any]:
    address = os.environ.get("TEMPORAL_ADDRESS", "").strip()
    if not address:
        return {"configured": False, "healthy": True, "detail": "not_configured"}
    host, _, port_s = address.partition(":")
    port = int(port_s or "7233")
    if not _tcp_open(host, port):
        return {"configured": True, "healthy": False, "detail": "tcp_unreachable"}
    return {
        "configured": True,
        "healthy": True,
        "detail": "tcp_open",
        "namespace": os.environ.get("TEMPORAL_NAMESPACE", "default"),
        "task_queue": os.environ.get("BRAIN_TEMPORAL_TASK_QUEUE", "brain-cognition"),
    }


def check_object_storage() -> dict[str, Any]:
    if not os.environ.get("OBJECT_STORAGE_BUCKET"):
        return {"configured": False, "healthy": True, "detail": "not_configured"}
    try:
        from .object_storage import ObjectStorage

        store = ObjectStorage.from_env()
        if store is None:
            return {"configured": False, "healthy": True, "detail": "not_configured"}
        ok = store.healthy()
        return {
            "configured": True,
            "healthy": ok,
            "detail": "reachable" if ok else "unavailable",
            "bucket": store.config.bucket,
        }
    except Exception as exc:
        return {"configured": True, "healthy": False, "detail": str(exc)[:200]}


def infrastructure_status() -> dict[str, Any]:
    components = {
        "postgres": check_postgres(),
        "neo4j": check_neo4j(),
        "temporal": check_temporal(),
        "object_storage": check_object_storage(),
    }
    configured = [name for name, st in components.items() if st.get("configured")]
    unhealthy = [
        name
        for name, st in components.items()
        if st.get("configured") and not st.get("healthy")
    ]
    return {
        "components": components,
        "configured": configured,
        "unhealthy": unhealthy,
        "all_configured_healthy": len(unhealthy) == 0,
    }
