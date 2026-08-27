from __future__ import annotations

import apps.api.tenant_app as tenant_api
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from brain.tenant_auth import TenantRole
from brain.tenant_context import TenantScopeViolation, trusted_tenant_context
from brain.tenant_runtime import active_tenant_context
import tools.live_cockpit_routes as live_cockpit_routes
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


def _capture_logger_info(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def capture_info(message, *args, **kwargs):
        calls.append((str(message), kwargs))

    monkeypatch.setattr(live_cockpit_routes._logger, "info", capture_info)
    return calls


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


def test_verified_oidc_logs_only_non_secret_verified_identity_once(monkeypatch):
    bridge = _bridge_with_probe(monkeypatch, _OperatorResolver())
    client = TestClient(bridge)
    calls = _capture_logger_info(monkeypatch)

    first = client.get(
        "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
    )
    second = client.get(
        "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert live_cockpit_routes._logger.name == "brain.vercel_oidc_auth"
    assert calls == [
        (
            "vercel_oidc_auth_accepted",
            {
                "extra": {
                    "audience": "https://vercel.com/harbourviewcompany-create",
                    "environment": "production",
                    "event": "vercel_oidc_auth_accepted",
                    "project": "brain",
                    "subject": (
                        "owner:harbourviewcompany-create:project:brain:environment:production"
                    ),
                    "team_slug": "harbourviewcompany-create",
                }
            },
        )
    ]
    serialized = repr(calls)
    assert "valid-vercel-token" not in serialized
    assert "local-server-key" not in serialized


def test_verified_oidc_logs_legacy_acceptance_once_after_bridge_selection(monkeypatch):
    bridge = _bridge_with_probe(monkeypatch, _OperatorResolver())
    client = TestClient(bridge)
    calls = _capture_logger_info(monkeypatch)
    monkeypatch.setattr(live_cockpit_routes, "_legacy_oidc_bridge_enabled", lambda: True)

    first = client.get(
        "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
    )
    second = client.get(
        "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert [message for message, _ in calls] == ["vercel_oidc_auth_accepted"]
    assert bridge._verified_identity_logged is True


def test_verified_oidc_requires_durable_observatory_membership(monkeypatch):
    bridge = _bridge_with_probe(monkeypatch, _RejectResolver())
    calls = _capture_logger_info(monkeypatch)
    response = TestClient(bridge).get(
        "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "brain_observatory_membership_or_role_required"
    }
    assert calls == []
    assert bridge._verified_identity_logged is False


def test_verified_oidc_rejects_viewer_write(monkeypatch):
    bridge = _bridge_with_probe(monkeypatch, _ViewerResolver())
    calls = _capture_logger_info(monkeypatch)
    response = TestClient(bridge).post(
        "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "brain_observatory_membership_or_role_required"
    }
    assert calls == []
    assert bridge._verified_identity_logged is False


def test_verified_oidc_fails_closed_for_invalid_server_tenant(monkeypatch):
    monkeypatch.setenv("BRAIN_API_KEY", "local-server-key")
    monkeypatch.setenv("BRAIN_OBSERVATORY_TENANT_ID", "not-a-uuid")
    monkeypatch.setattr(tenant_api, "_membership_resolver", _OperatorResolver())

    inner = FastAPI()
    bridge = VercelOidcAuthBridge(inner)
    bridge.verifier = _AllowVerifier()
    calls = _capture_logger_info(monkeypatch)

    response = TestClient(bridge).get(
        "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "brain_observatory_tenant_invalid"}
    assert calls == []
    assert bridge._verified_identity_logged is False


def test_verified_oidc_does_not_log_when_membership_store_unavailable(monkeypatch):
    bridge = _bridge_with_probe(monkeypatch, None)
    calls = _capture_logger_info(monkeypatch)

    response = TestClient(bridge).get(
        "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "tenant_membership_store_unavailable"}
    assert calls == []
    assert bridge._verified_identity_logged is False


def test_verified_oidc_does_not_log_when_local_api_key_missing(monkeypatch):
    bridge = _bridge_with_probe(monkeypatch, _OperatorResolver())
    monkeypatch.delenv("BRAIN_API_KEY", raising=False)
    calls = _capture_logger_info(monkeypatch)

    response = TestClient(bridge).get(
        "/probe", headers={"Authorization": "Bearer valid-vercel-token"}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "brain_local_api_key_not_configured"}
    assert calls == []
    assert bridge._verified_identity_logged is False
