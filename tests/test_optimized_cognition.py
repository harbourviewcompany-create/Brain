from __future__ import annotations

import pytest

from brain.model_cortex import ModelCortexRouter, ModelOutput, ModelProfile
from brain.observability import CognitiveTelemetry
from brain.planning import CausalEdge, CausalGraph, CounterfactualPlanner, Intervention, PlanAction, PlanCandidate
from brain.security import ApiKeyAuthenticator, SecurityConfig


def test_production_security_requires_key_and_constant_time_auth(monkeypatch):
    monkeypatch.setenv("BRAIN_ENV", "production")
    monkeypatch.delenv("BRAIN_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        SecurityConfig.from_env()
    monkeypatch.setenv("BRAIN_API_KEY", "secret")
    monkeypatch.setenv("BRAIN_CORS_ORIGINS", "https://brain.example")
    config = SecurityConfig.from_env()
    auth = ApiKeyAuthenticator(config)
    assert config.allowed_origins() == ["https://brain.example"]
    assert auth.authorized(authorization="Bearer secret", x_api_key=None)
    assert not auth.authorized(authorization="Bearer wrong", x_api_key=None)


def test_external_actions_fail_closed_without_explicit_approval_mode(monkeypatch):
    monkeypatch.setenv("BRAIN_ENV", "production")
    monkeypatch.setenv("BRAIN_API_KEY", "secret")
    monkeypatch.setenv("BRAIN_EXTERNAL_ACTIONS_ENABLED", "true")
    monkeypatch.delenv("BRAIN_EXTERNAL_ACTION_APPROVAL_MODE", raising=False)
    with pytest.raises(RuntimeError):
        SecurityConfig.from_env()
    monkeypatch.setenv("BRAIN_EXTERNAL_ACTION_APPROVAL_MODE", "explicit")
    assert SecurityConfig.from_env().external_actions_enabled is True


def test_model_cortex_routes_by_measured_performance_and_detects_disagreement():
    router = ModelCortexRouter()
    strong = router.register(
        ModelProfile(
            "provider-a",
            "reasoner",
            {"planning": 0.95},
            calibration=0.9,
            historical_accuracy=0.9,
            cost_score=0.5,
            latency_score=0.5,
        )
    )
    weak = router.register(
        ModelProfile(
            "provider-b",
            "cheap",
            {"planning": 0.3},
            calibration=0.5,
            historical_accuracy=0.5,
            cost_score=1.0,
            latency_score=1.0,
        )
    )
    route = router.route("planning")
    assert route.model_id == strong.id
    assessment = router.assess_ensemble(
        [
            ModelOutput(strong.id, "buy", 0.9, ["evidence:a"]),
            ModelOutput(weak.id, "wait", 0.4, ["evidence:b"]),
        ]
    )
    assert assessment.requires_adversarial_review is True


def test_counterfactual_planning_preserves_evidence_and_approval_gate():
    graph = CausalGraph()
    graph.add_edge(CausalEdge("price", "demand", -0.5, 0.8, ["study:elasticity"]))
    plan = PlanCandidate(
        actions=[
            PlanAction(
                "raise price",
                Intervention("price", 0.2, ["experiment:pricing"]),
                cost=0.05,
                risk=0.2,
                reversible=False,
                external=True,
                approval_required=True,
            )
        ],
        target_variable="demand",
        target_value=-0.08,
        evidence_refs=["strategy:pricing"],
    )
    result = CounterfactualPlanner(graph).simulate(plan, {"demand": 0.0})
    assert result.requires_approval is True
    assert "study:elasticity" in result.evidence_refs
    assert result.predicted_state["demand"] == pytest.approx(-0.08)


def test_cognitive_telemetry_traces_and_exports_json_lines():
    telemetry = CognitiveTelemetry()
    span = telemetry.start_span("belief.update", "learning", attributes={"belief": "b1"})
    span.finish()
    telemetry.metric("prediction_error", 0.4, module="learning")
    snapshot = telemetry.snapshot()
    assert snapshot["spans"][0]["status"] == "ok"
    assert snapshot["metrics"][0]["name"] == "prediction_error"
    assert "belief.update" in telemetry.json_lines()
