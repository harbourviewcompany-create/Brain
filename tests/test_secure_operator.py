import pytest
from fastapi.testclient import TestClient

from apps.operator import secure_main


def _development_operator(monkeypatch, *, api_key: str | None):
    monkeypatch.setenv("BRAIN_ENV", "development")
    monkeypatch.setenv("BRAIN_TENANT_MODE", "disabled")
    monkeypatch.delenv("BRAIN_TENANT_CONTEXT_SECRET", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    if api_key is None:
        monkeypatch.delenv("BRAIN_API_KEY", raising=False)
    else:
        monkeypatch.setenv("BRAIN_API_KEY", api_key)
    return secure_main.create_app()


def test_health_and_readiness_remain_public(monkeypatch):
    app = _development_operator(monkeypatch, api_key=None)
    client = TestClient(app)

    health = client.get("/health")
    ready = client.get("/ready")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert ready.status_code == 200
    assert ready.json()["durable"] is False


def test_operator_routes_fail_closed_when_api_key_is_unconfigured(monkeypatch):
    app = _development_operator(monkeypatch, api_key=None)
    response = TestClient(app).get("/operator")

    assert response.status_code == 503
    assert "BRAIN_API_KEY" in response.json()["detail"]


def test_operator_routes_require_valid_api_key(monkeypatch):
    app = _development_operator(monkeypatch, api_key="operator-secret")
    client = TestClient(app)

    denied = client.get("/operator")
    allowed = client.get("/operator", headers={"X-Brain-Api-Key": "operator-secret"})
    bearer = client.get(
        "/operator/organism",
        headers={"Authorization": "Bearer operator-secret"},
    )

    assert denied.status_code == 401
    assert allowed.status_code == 200
    assert bearer.status_code == 200
    assert "autonomy_boundary" in bearer.json()


def test_production_operator_requires_durable_database(monkeypatch):
    monkeypatch.setenv("BRAIN_ENV", "production")
    monkeypatch.setenv("BRAIN_API_KEY", "operator-secret")
    monkeypatch.setenv("BRAIN_TENANT_MODE", "required")
    monkeypatch.setenv("BRAIN_TENANT_CONTEXT_SECRET", "tenant-secret")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        secure_main.create_app()


def test_production_operator_requires_tenant_mode(monkeypatch):
    monkeypatch.setenv("BRAIN_ENV", "production")
    monkeypatch.setenv("BRAIN_API_KEY", "operator-secret")
    monkeypatch.setenv("BRAIN_TENANT_MODE", "disabled")
    monkeypatch.setenv("DATABASE_URL", "postgresql://not-opened-before-guard")

    with pytest.raises(RuntimeError, match="BRAIN_TENANT_MODE=required"):
        secure_main.create_app()


def test_required_tenant_mode_cannot_run_without_membership_database(monkeypatch):
    monkeypatch.setenv("BRAIN_ENV", "development")
    monkeypatch.setenv("BRAIN_API_KEY", "operator-secret")
    monkeypatch.setenv("BRAIN_TENANT_MODE", "required")
    monkeypatch.setenv("BRAIN_TENANT_CONTEXT_SECRET", "tenant-secret")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="operator tenant mode is required"):
        secure_main.create_app()
