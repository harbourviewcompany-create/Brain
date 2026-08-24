from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import pytest

from brain.tenant_auth import TenantRole
from brain.tenant_runtime import active_tenant_context
from tools import apply_migrations
from tools.live_cockpit_routes import (
    VercelOidcAuthBridge,
    _DEFAULT_OBSERVATORY_TENANT_ID,
)


class _AllowVerifier:
    def verify(self, token: str):
        return token == "valid-vercel-token", "ok"


def test_migration_dsn_prefers_privileged_split_role(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://runtime")
    monkeypatch.setenv("BRAIN_MIGRATION_DATABASE_URL", "postgresql://migration")
    assert apply_migrations._migration_dsn() == "postgresql://migration"


def test_migration_dsn_keeps_legacy_fallback(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://legacy")
    monkeypatch.delenv("BRAIN_MIGRATION_DATABASE_URL", raising=False)
    assert apply_migrations._migration_dsn() == "postgresql://legacy"


def test_migration_dsn_requires_a_connection(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("BRAIN_MIGRATION_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="BRAIN_MIGRATION_DATABASE_URL or DATABASE_URL"):
        apply_migrations._migration_dsn()


def test_verified_oidc_binds_server_owned_observatory_tenant_and_strips_spoofed_headers(
    monkeypatch,
):
    monkeypatch.setenv("BRAIN_API_KEY", "local-server-key")
    monkeypatch.delenv("BRAIN_OBSERVATORY_TENANT_ID", raising=False)

    inner = FastAPI()

    @inner.get("/probe")
    def probe(request: Request):
        context = active_tenant_context()
        return {
            "tenant_id": str(context.tenant_id) if context else None,
            "actor_id": context.actor_id if context else None,
            "roles": [str(role) for role in context.roles] if context else [],
            "authorization": request.headers.get("authorization"),
            "api_key": request.headers.get("x-brain-api-key"),
            "spoofed_tenant": request.headers.get("x-brain-tenant-id"),
            "spoofed_roles": request.headers.get("x-brain-roles"),
            "spoofed_service": request.headers.get("x-brain-service-context"),
        }

    bridge = VercelOidcAuthBridge(inner)
    bridge.verifier = _AllowVerifier()

    response = TestClient(bridge).get(
        "/probe",
        headers={
            "Authorization": "Bearer valid-vercel-token",
            "X-Brain-Tenant-Id": "11111111-1111-1111-1111-111111111111",
            "X-Brain-Roles": "owner",
            "X-Brain-Service-Context": "true",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == str(_DEFAULT_OBSERVATORY_TENANT_ID)
    assert body["actor_id"] == "brain-observatory-bff"
    assert TenantRole.OPERATOR.value in body["roles"]
    assert body["authorization"] is None
    assert body["api_key"] == "local-server-key"
    assert body["spoofed_tenant"] is None
    assert body["spoofed_roles"] is None
    assert body["spoofed_service"] is None
    assert active_tenant_context() is None


def test_verified_oidc_fails_closed_for_invalid_server_tenant(monkeypatch):
    monkeypatch.setenv("BRAIN_API_KEY", "local-server-key")
    monkeypatch.setenv("BRAIN_OBSERVATORY_TENANT_ID", "not-a-uuid")

    inner = FastAPI()

    @inner.get("/probe")
    def probe():
        return {"unexpected": True}

    bridge = VercelOidcAuthBridge(inner)
    bridge.verifier = _AllowVerifier()

    response = TestClient(bridge).get(
        "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "brain_observatory_tenant_invalid"}
