from __future__ import annotations

import httpx
import pytest

from brain.domain import CandidateAction
from brain.motor import HttpEffector, MissingEffectorCredentialsError, MotorExecutionService


def _action() -> CandidateAction:
    return CandidateAction(description="notify ops channel", expected_value=0.5, uncertainty=0.1, external=False)


def test_http_effector_extracts_numeric_outcome_field():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return httpx.Response(200, json={"outcome": 7.5})

    transport = httpx.MockTransport(handler)
    effector = HttpEffector("https://example.test/webhook", transport=transport)
    result = effector(_action(), 10.0)
    assert result == 7.5


def test_http_effector_falls_back_to_binary_success_when_no_outcome_field():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "sent"})

    transport = httpx.MockTransport(handler)
    effector = HttpEffector("https://example.test/webhook", transport=transport)
    result = effector(_action(), 10.0)
    assert result == 1.0


def test_http_effector_sends_expected_payload_shape():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json
        captured["body"] = json.loads(request.content)
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json={"outcome": 1.0})

    transport = httpx.MockTransport(handler)
    effector = HttpEffector("https://example.test/webhook", transport=transport)
    action = _action()
    effector(action, 42.0)

    assert captured["body"]["action_id"] == str(action.id)
    assert captured["body"]["action_description"] == action.description
    assert captured["body"]["expected_outcome"] == 42.0


def test_http_effector_raises_on_missing_credentials(monkeypatch):
    monkeypatch.delenv("TEST_EFFECTOR_API_KEY", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should never reach the network without credentials")

    transport = httpx.MockTransport(handler)
    effector = HttpEffector(
        "https://example.test/webhook", api_key_env_var="TEST_EFFECTOR_API_KEY", transport=transport,
    )
    with pytest.raises(MissingEffectorCredentialsError):
        effector(_action(), 10.0)


def test_http_effector_sends_bearer_token_when_credentials_present(monkeypatch):
    monkeypatch.setenv("TEST_EFFECTOR_API_KEY", "secret-123")
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"outcome": 1.0})

    transport = httpx.MockTransport(handler)
    effector = HttpEffector(
        "https://example.test/webhook", api_key_env_var="TEST_EFFECTOR_API_KEY", transport=transport,
    )
    effector(_action(), 10.0)
    assert captured["auth"] == "Bearer secret-123"


def test_http_effector_raises_on_http_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server exploded"})

    transport = httpx.MockTransport(handler)
    effector = HttpEffector("https://example.test/webhook", transport=transport)
    with pytest.raises(httpx.HTTPStatusError):
        effector(_action(), 10.0)


def test_http_effector_integrates_with_motor_execution_service_governance():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"outcome": 9.5})

    transport = httpx.MockTransport(handler)
    effector = HttpEffector("https://example.test/webhook", transport=transport)
    svc = MotorExecutionService()

    decision, result = svc.execute(
        _action(),
        effector_name="ops_webhook",
        effector=effector,
        raw_expected_outcome=10.0,
    )
    assert decision.allowed
    assert result is not None
    assert result.actual_outcome == 9.5


def test_http_effector_blocked_external_action_never_reaches_transport():
    called = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called["count"] += 1
        return httpx.Response(200, json={"outcome": 1.0})

    transport = httpx.MockTransport(handler)
    effector = HttpEffector("https://example.test/webhook", transport=transport)
    svc = MotorExecutionService()

    external_action = CandidateAction(description="send external email", expected_value=0.5, uncertainty=0.1, external=True)
    decision, result = svc.execute(
        external_action,
        effector_name="ops_webhook",
        effector=effector,
        raw_expected_outcome=10.0,
        external_actions_enabled=False,
    )
    assert not decision.allowed
    assert result is None
    assert called["count"] == 0
