"""A non-matching bearer token must not mask a valid Brain API key.

The Observatory BFF forwards a platform identity token in `authorization`
alongside the Brain API key in `X-Brain-Api-Key`. When the middleware treated
the bearer header as authoritative, every proxied request from Vercel failed
authentication even though the correct key was present.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from brain.security import ApiKeyAuthenticator, SecurityConfig, credential_candidates
from tests.conftest import TEST_API_KEY

# Reuse the shared `app` singleton and the shared key, as every other
# apps/api test file does. Setting a different BRAIN_API_KEY here would
# rebind the env var the middleware reads at request time and break the
# other files' clients.
client = TestClient(app)


def test_bearer_token_does_not_mask_a_valid_api_key():
    response = client.get(
        "/beliefs",
        headers={
            "authorization": "Bearer unrelated.platform.identity",
            "X-Brain-Api-Key": TEST_API_KEY,
        },
    )
    assert response.status_code == 200


def test_api_key_alone_still_authorizes():
    assert client.get("/beliefs", headers={"X-Brain-Api-Key": TEST_API_KEY}).status_code == 200


def test_bearer_key_alone_still_authorizes():
    assert client.get("/beliefs", headers={"authorization": f"Bearer {TEST_API_KEY}"}).status_code == 200


def test_wrong_credentials_in_every_header_are_still_rejected():
    response = client.get(
        "/beliefs",
        headers={
            "authorization": "Bearer wrong",
            "X-Brain-Api-Key": "also-wrong",
            "X-Api-Key": "wrong-too",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_or_missing_api_key"


def test_no_credentials_are_rejected():
    assert client.get("/beliefs").status_code == 401


@pytest.mark.parametrize(
    "headers,expected",
    [
        ({}, []),
        ({"x-api-key": "  "}, []),
        ({"authorization": "Basic abc"}, []),
        ({"authorization": "bearer tok"}, ["tok"]),
        ({"X-Brain-Api-Key": "a", "authorization": "Bearer b"}, ["a", "b"]),
    ],
)
def test_credential_candidates_collects_every_presented_value(headers, expected):
    assert sorted(credential_candidates(headers)) == sorted(expected)


def test_authenticator_accepts_either_header():
    auth = ApiKeyAuthenticator(
        SecurityConfig(
            environment="production",
            api_key="secret",
            cors_origins=("https://example.test",),
            external_actions_enabled=False,
        )
    )
    assert auth.authorized(authorization="Bearer nonsense", x_api_key="secret")
    assert auth.authorized(authorization="Bearer secret", x_api_key=None)
    assert not auth.authorized(authorization="Bearer nonsense", x_api_key="nonsense")
