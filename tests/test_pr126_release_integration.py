from __future__ import annotations

import json
import logging

import apps.api.tenant_app as tenant_api
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from brain.tenant_auth import TenantRole
from brain.tenant_context import TenantScopeViolation, trusted_tenant_context
from brain.tenant_runtime import active_tenant_context
from tools.live_cockpit_routes import (
    VercelOidcAuthBridge,
    _DEFAULT_OBSERVATORY_TENANT_ID,
)
from tools.vercel_oidc import VercelOidcConfig


class _AllowVerifier:
    config = VercelOidcConfig(
        team_slug="harbourviewcompany-create",
        project="brain",
        environment="production",
    )

    def verify(self, token: str):
        return token == "valid-vercel-token", "ok"


class _OperatorResolver:
    def resolve(self, identity_context):
        assert identity_context.roles == ()
        return trusted_tenant_context(
            tenant_id=identity_context.tenant_id,
            actor_id=identity_context.actor_id,
            roles=(TenantRole.OPERATOR,),
        )


class _ViewerResolver:
    def resolve(self, identity_context):
        return trusted_tenant_context(
            tenant_id=identity_context.tenant_id,
            actor_id=identity_context.actor_id,
            roles=(TenantRole.VIEWER,),
        )


class _RejectResolver:
    def resolve(self, identity_context):
        raise TenantScopeViolation("active_tenant_membership_required")


def _bridge_with_probe(monkeypatch, resolver):
    monkeypatch.setenv("BRAIN_API_KEY", "local-server-key")
    monkeypatch.delenv("BRAIN_OBSERVATORY_TENANT_ID", raising=False)
    monkeypatch.setattr(tenant_api, "_membership_resolver", resolver)

    inner = FastAPI()

    @inner.api_route("/probe", methods=["GET", "POST"])
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
    return bridge


def test_verified_oidc_uses_durable_membership_and_strips_spoofed_headers(monkeypatch):
    bridge = _bridge_with_probe(monkeypatch, _OperatorResolver())

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


def test_verified_oidc_logs_only_non_secret_verified_identity_once(monkeypatch, caplog):
    bridge = _bridge_with_probe(monkeypatch, _OperatorResolver())
    client = TestClient(bridge)

    with caplog.at_level(logging.INFO, logger="tools.live_cockpit_routes"):
        first = client.get(
            "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
        )
        second = client.get(
            "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
        )

    assert first.status_code == 200
    assert second.status_code == 200
    accepted = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "tools.live_cockpit_routes"
        and record.getMessage().startswith("{")
        and json.loads(record.getMessage()).get("event") == "vercel_oidc_auth_accepted"
    ]
    assert accepted == [
        {
            "audience": "https://vercel.com/harbourviewcompany-create",
            "environment": "production",
            "event": "vercel_oidc_auth_accepted",
            "project": "brain",
            "subject": (
                "owner:harbourviewcompany-create:project:brain:environment:production"
            ),
            "team_slug": "harbourviewcompany-create",
        }
    ]
    assert "valid-vercel-token" not in caplog.text
    assert "local-server-key" not in caplog.text


def test_verified_oidc_requires_durable_observatory_membership(monkeypatch):
    bridge = _bridge_with_probe(monkeypatch, _RejectResolver())
    response = TestClient(bridge).get(
        "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "brain_observatory_membership_or_role_required"
    }


def test_verified_oidc_rejects_viewer_write(monkeypatch):
    bridge = _bridge_with_probe(monkeypatch, _ViewerResolver())
    response = TestClient(bridge).post(
        "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "brain_observatory_membership_or_role_required"
    }


def test_verified_oidc_fails_closed_for_invalid_server_tenant(monkeypatch):
    monkeypatch.setenv("BRAIN_API_KEY", "local-server-key")
    monkeypatch.setenv("BRAIN_OBSERVATORY_TENANT_ID", "not-a-uuid")
    monkeypatch.setattr(tenant_api, "_membership_resolver", _OperatorResolver())

    inner = FastAPI()
    bridge = VercelOidcAuthBridge(inner)
    bridge.verifier = _AllowVerifier()

    response = TestClient(bridge).get(
        "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "brain_observatory_tenant_invalid"}
