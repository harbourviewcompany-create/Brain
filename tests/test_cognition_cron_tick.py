"""Lease-aware external cognition tick used by free Cloudflare cron."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.cognition_cron_routes import register_cognition_cron_routes

REPO_ROOT = Path(__file__).resolve().parents[1]
CF_DIR = REPO_ROOT / "deploy" / "cloudflare-cognition-cron"


@pytest.fixture
def cron_client(monkeypatch):
    monkeypatch.setenv("BRAIN_API_KEY", "test-cron-key")
    # Force the in-memory path (no DATABASE_URL) so ticks run without Postgres.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("BRAIN_WORKER_DATABASE_URL", raising=False)

    app = FastAPI()
    heartbeat = MagicMock()
    heartbeat.tick.return_value = {"processed_this_call": 0, "ticks": 1}

    class ApiMod:
        pass

    api_mod = ApiMod()
    api_mod.heartbeat = heartbeat

    @app.middleware("http")
    async def _auth(request, call_next):
        if request.headers.get("x-brain-api-key") != "test-cron-key":
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=401, content={"detail": "invalid_or_missing_api_key"})
        return await call_next(request)

    register_cognition_cron_routes(app, api_module=api_mod)
    return TestClient(app), heartbeat


def test_external_tick_requires_api_key(cron_client):
    client, _ = cron_client
    assert client.post("/internal/cognition/tick").status_code == 401


def test_external_tick_without_database_runs(cron_client):
    client, heartbeat = cron_client
    response = client.post(
        "/internal/cognition/tick",
        headers={"X-Brain-Api-Key": "test-cron-key"},
        json={"max_items": 1, "max_ticks": 2},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ticked"
    assert body["lease"] == "not_configured"
    assert body["ticks"] == 2
    assert heartbeat.tick.call_count == 2


def test_external_tick_lease_held_elsewhere(cron_client, monkeypatch):
    client, heartbeat = cron_client
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused/unused")

    with patch("apps.api.cognition_cron_routes.CognitionLease") as lease_cls:
        lease = MagicMock()
        lease.acquire.return_value = False
        lease_cls.return_value = lease

        response = client.post(
            "/internal/cognition/tick",
            headers={"X-Brain-Api-Key": "test-cron-key"},
            json={},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "lease_held_elsewhere"
    assert body["ticks"] == 0
    heartbeat.tick.assert_not_called()
    lease.release.assert_not_called()


def test_external_tick_acquires_and_releases(cron_client, monkeypatch):
    client, heartbeat = cron_client
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused/unused")

    with patch("apps.api.cognition_cron_routes.CognitionLease") as lease_cls:
        lease = MagicMock()
        lease.acquire.return_value = True
        lease_cls.return_value = lease

        response = client.post(
            "/internal/cognition/tick",
            headers={"X-Brain-Api-Key": "test-cron-key"},
            json={"max_ticks": 1},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ticked"
    assert body["lease"] == "acquired_and_released"
    heartbeat.tick.assert_called_once()
    lease.release.assert_called_once()


def test_cloudflare_worker_package_is_present():
    assert (CF_DIR / "wrangler.toml").is_file()
    assert (CF_DIR / "src" / "index.js").is_file()
    wrangler = (CF_DIR / "wrangler.toml").read_text(encoding="utf-8")
    assert "* * * * *" in wrangler
    worker = (CF_DIR / "src" / "index.js").read_text(encoding="utf-8")
    assert "/internal/cognition/tick" in worker
    assert "X-Brain-Api-Key" in worker
