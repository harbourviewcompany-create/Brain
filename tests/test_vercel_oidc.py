from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

import tools.live_cockpit_routes as live_cockpit
from tools.vercel_oidc import VercelOidcConfig, VercelOidcVerifier


class _SigningKey:
    def __init__(self, key) -> None:
        self.key = key


class _StaticJwksClient:
    def __init__(self, key) -> None:
        self._key = key

    def get_signing_key_from_jwt(self, _token: str):
        return _SigningKey(self._key)


def _config() -> VercelOidcConfig:
    return VercelOidcConfig(
        team_slug="harbourview",
        project="brain",
        environment="production",
    )


def _token(private_key, **overrides) -> str:
    config = _config()
    now = datetime.now(UTC)
    payload = {
        "iss": f"https://oidc.vercel.com/{config.team_slug}",
        "sub": config.subject,
        "aud": config.audience,
        "iat": int(now.timestamp()),
        "nbf": int((now - timedelta(seconds=1)).timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    payload.update(overrides)
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test"})


def _verifier():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = VercelOidcVerifier(
        _config(),
        jwks_client=_StaticJwksClient(private_key.public_key()),
    )
    return verifier, private_key


def test_accepts_exact_production_vercel_identity() -> None:
    verifier, private_key = _verifier()
    assert verifier.verify(_token(private_key)) == (True, "vercel_oidc_verified")


def test_accepts_global_vercel_issuer_mode() -> None:
    verifier, private_key = _verifier()
    assert verifier.verify(_token(private_key, iss="https://oidc.vercel.com")) == (
        True,
        "vercel_oidc_verified",
    )


def test_rejects_wrong_project_subject() -> None:
    verifier, private_key = _verifier()
    ok, reason = verifier.verify(
        _token(
            private_key,
            sub="owner:harbourview:project:other:environment:production",
        )
    )
    assert not ok
    assert reason == "vercel_oidc_subject_rejected"


def test_rejects_wrong_audience() -> None:
    verifier, private_key = _verifier()
    ok, reason = verifier.verify(_token(private_key, aud="https://vercel.com/other"))
    assert not ok
    assert reason == "vercel_oidc_invalid_token"


def test_rejects_expired_token() -> None:
    verifier, private_key = _verifier()
    expired = int((datetime.now(UTC) - timedelta(minutes=5)).timestamp())
    ok, reason = verifier.verify(_token(private_key, exp=expired))
    assert not ok
    assert reason == "vercel_oidc_invalid_token"


def test_disabled_without_explicit_identity_scope() -> None:
    verifier = VercelOidcVerifier(VercelOidcConfig("", "", ""))
    assert verifier.verify("anything") == (False, "vercel_oidc_not_configured")


def test_legacy_oidc_bridge_requires_flag_and_disabled_tenant_mode(monkeypatch) -> None:
    monkeypatch.setattr(
        live_cockpit.tenant_api,
        "tenant_security",
        SimpleNamespace(mode="disabled"),
    )
    monkeypatch.delenv("BRAIN_OBSERVATORY_LEGACY_OIDC_BRIDGE", raising=False)
    assert not live_cockpit._legacy_oidc_bridge_enabled()

    monkeypatch.setenv("BRAIN_OBSERVATORY_LEGACY_OIDC_BRIDGE", "true")
    assert live_cockpit._legacy_oidc_bridge_enabled()

    monkeypatch.setattr(
        live_cockpit.tenant_api,
        "tenant_security",
        SimpleNamespace(mode="required"),
    )
    assert not live_cockpit._legacy_oidc_bridge_enabled()
