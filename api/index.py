from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

backend = (os.environ.get("BRAIN_STORAGE_BACKEND") or "").strip().lower()
if backend not in {"turso", "libsql"}:
    raise RuntimeError(
        "Vercel Brain API requires BRAIN_STORAGE_BACKEND=turso; "
        "legacy PostgreSQL/Railway is not a serverless production dependency"
    )

# Prevent stale Railway variables from binding apps.api.main to PostgreSQL at
# import time, and guarantee the serverless process never starts a daemon loop.
os.environ["BRAIN_INLINE_COGNITION"] = "0"
os.environ.pop("DATABASE_URL", None)
os.environ.pop("BRAIN_WORKER_DATABASE_URL", None)

from apps.api import main as api_module  # noqa: E402
from apps.api.turso_runtime import configure_api_module  # noqa: E402

_store = configure_api_module(api_module)
app = FastAPI(title="Brain Serverless API", version="0.8.2-zero-cost")


def _health_payload() -> dict:
    storage = _store.storage_health()
    database_ok = bool(storage.get("reachable"))
    try:
        heartbeat = api_module._cognition_status()
    except Exception:
        heartbeat = {}
    checkpoint = _store.db.fetchone(
        "SELECT projection_name,last_event_id,event_count,updated_at "
        "FROM projection_checkpoints ORDER BY updated_at DESC LIMIT 1"
    )
    compaction = _store.db.fetchone(
        "SELECT segment_id,event_count,sha256,created_at "
        "FROM brain_event_segments ORDER BY created_at DESC LIMIT 1"
    )
    return {
        "status": "ok" if database_ok else "degraded",
        "version": "0.8.2-zero-cost",
        "database": "connected" if database_ok else "unavailable",
        "persistence": "turso",
        "migration_version": "turso-v1",
        "bounded_cognition": True,
        "continuous_daemon": False,
        "storage": storage,
        "last_checkpoint": checkpoint,
        "last_compaction": compaction,
        "heartbeat": {
            "ticks": heartbeat.get("ticks", 0),
            "total_processed": heartbeat.get("total_processed", 0),
            "inbox": heartbeat.get("inbox", {}),
            "working_memory_size": heartbeat.get(
                "working_memory_size", heartbeat.get("belief_cache_size", 0)
            ),
        },
    }


@app.get("/api/health")
def health():
    payload = _health_payload()
    if payload["status"] != "ok":
        return JSONResponse(status_code=503, content=payload)
    return payload


@app.get("/api/ready")
def ready():
    payload = _health_payload()
    if payload["status"] != "ok":
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": payload["database"]},
        )
    return {"status": "ready", "database": "connected", "persistence": "turso"}


# All existing API/BFF routes keep their original paths after the /api mount.
# The existing API-key and CORS middleware continue to execute inside this app.
app.mount("/api", api_module.app)
