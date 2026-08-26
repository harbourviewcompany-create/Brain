from fastapi.testclient import TestClient

from apps.api.main import app

# Imported at module scope, before any request is served, because that is how
# production loads it: uvicorn imports the module at process start. Importing
# it inside a test instead makes the file pass only when some earlier test file
# happened to import it first -- Starlette refuses to add middleware once the
# app has handled a request, so `tenant_app`'s membership middleware raises
# "Cannot add middleware after an application has started".
import tools.live_cockpit_routes  # noqa: E402,F401  (registers cockpit routes on `app`)
from tests.conftest import TEST_API_KEY  # noqa: E402

# Deliberately reuse the same `app` singleton every other apps/api test file
# uses. Reloading the module here would rebind apps.api.main's globals
# (learning, runtime, ...) out from under every other test file's route
# handlers, since those handlers resolve module globals by name at call
# time, not at import time - a real cross-test state-corruption bug caught
# while writing this file.
client = TestClient(app)


def test_health_is_exempt_from_auth():
    response = client.get("/health")
    assert response.status_code == 200


def test_request_without_key_is_rejected():
    response = client.get("/beliefs", headers={"x-api-key": ""})
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_or_missing_api_key"


def test_request_with_wrong_key_is_rejected():
    response = client.get("/beliefs", headers={"x-api-key": "wrong-key"})
    assert response.status_code == 401


def test_request_with_correct_key_is_accepted():
    response = client.get("/beliefs", headers={"x-api-key": TEST_API_KEY})
    assert response.status_code == 200


def test_unconfigured_key_fails_closed_not_open(monkeypatch):
    """If BRAIN_API_KEY is unset, every non-exempt request must be rejected -
    an unconfigured key must never silently mean 'no auth required'.
    monkeypatch restores the env var automatically after this test."""
    monkeypatch.delenv("BRAIN_API_KEY", raising=False)
    response = client.get("/beliefs", headers={"x-api-key": "anything"})
    assert response.status_code == 503


def test_write_endpoint_requires_key():
    response = client.post(
        "/beliefs",
        json={"statement": "auth test belief - should be rejected", "confidence": 0.5},
        headers={"x-api-key": "wrong-key"},
    )
    assert response.status_code == 401


def test_cockpit_routes_are_covered_by_same_middleware():
    """live_cockpit_routes.py registers routes on the same `app` object at
    import time (see the module-scope import above), so it must inherit the
    same auth middleware without any per-route change in that file."""
    unauth = client.get("/signals", headers={"x-api-key": "wrong-key"})
    assert unauth.status_code == 401

    authed = client.get("/signals", headers={"x-api-key": TEST_API_KEY})
    assert authed.status_code == 200
