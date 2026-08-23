from __future__ import annotations

import os
from dataclasses import asdict
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from brain.adapters.developmental_store import InMemoryDevelopmentalStore
from brain.adapters.learning_store import InMemoryLearningStore
from brain.developmental.runtime import DevelopmentalRuntime
from brain.domain import Edge, Evidence, Node, Outcome
from brain.learning import LearningService
from brain.memory import InMemoryBrainStore
from brain.money_spine import DailyRevenueReport, MoneySpineService, RevenueSignal
from brain.prediction import PredictionEngine
from brain.runtime import BrainRuntime
from brain.security import ApiKeyAuthenticator, SecurityConfig

_security = SecurityConfig.from_env()
_authenticator = ApiKeyAuthenticator(_security)

app = FastAPI(title="Brain Runtime API", version="0.7.1")

_origins = _security.allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Brain-Api-Key", "X-Request-Id"],
)

_PUBLIC_PATHS = frozenset({"/health", "/ready"})


@app.middleware("http")
async def production_authentication(request: Request, call_next):
    if request.url.path not in _PUBLIC_PATHS and not _authenticator.authorized(
        authorization=request.headers.get("authorization"),
        x_api_key=request.headers.get("x-brain-api-key"),
    ):
        return JSONResponse(status_code=401, content={"detail": "brain_authentication_required"})
    return await call_next(request)


_brain_store: InMemoryBrainStore = InMemoryBrainStore()
_learning_store = InMemoryLearningStore()
_developmental_store = InMemoryDevelopmentalStore()
runtime = BrainRuntime(store=_brain_store)
learning = LearningService(
    _brain_store,
    predictions=_learning_store,
    edges=_learning_store,
    attributions=_learning_store,
    sources=_learning_store,
)
development = DevelopmentalRuntime(_developmental_store)
money_spine = MoneySpineService()


def _configure_from_env() -> None:
    global _brain_store, runtime, learning, development
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return
    from brain.adapters.brain_store import PostgresBrainStore
    from brain.adapters.developmental_store import PostgresDevelopmentalStore
    from brain.adapters.learning_store import (
        PostgresAttributionStore,
        PostgresEdgeStore,
        PostgresPredictionStore,
        PostgresSourceStore,
    )

    store = PostgresBrainStore(dsn)
    _brain_store = store
    store.hydrate()
    runtime = BrainRuntime(store=store)
    learning = LearningService(
        store.event_store,
        predictions=PostgresPredictionStore(store.pool),
        edges=PostgresEdgeStore(store.pool),
        attributions=PostgresAttributionStore(store.pool),
        sources=PostgresSourceStore(store.pool),
    )
    development = DevelopmentalRuntime(PostgresDevelopmentalStore(dsn, pool=store.pool))


_configure_from_env()


class CreateBeliefRequest(BaseModel):
    statement: str
    confidence: float = Field(default=0.5, ge=0, le=1)


class LearnRequest(BaseModel):
    belief_id: str
    claim: str
    source_id: str
    reliability: float = Field(ge=0, le=1)
    supports: bool


class CreatePredictionRequest(BaseModel):
    statement: str
    expected_value: float
    confidence: float = Field(default=0.5, ge=0, le=1)
    horizon_seconds: int = Field(default=7 * 24 * 3600, ge=1)
    belief_id: str | None = None
    action_id: str | None = None
    edge_ids: list[str] = Field(default_factory=list)
    source_keys: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpsertEdgeRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    relation: str
    weight: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0.5, ge=0, le=1)
    edge_id: str | None = None


class RecordOutcomeRequest(BaseModel):
    action_id: str
    value_created: float
    operator_time_cost: float = 0.0
    prediction_accuracy: float = Field(default=0.0, ge=0, le=1)
    trust_impact: float = 0.0
    legal_risk: float = Field(default=0.0, ge=0, le=1)
    prediction_id: str | None = None
    edge_ids: list[str] = Field(default_factory=list)
    source_keys: list[str] = Field(default_factory=list)


class RevenueSignalRequest(BaseModel):
    raw_signal: str
    source_id: str
    money_lane_id: str
    evidence_refs: list[str] = Field(default_factory=list)
    named_buyer: str | None = None
    named_seller: str | None = None
    decision_maker: str | None = None
    visible_pain: str | None = None
    urgency_reason: str | None = None
    payment_path: str | None = None
    contact_channel: str | None = None
    commercial_value: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0.5, ge=0, le=1)
    urgency: float = Field(default=0.0, ge=0, le=1)
    contactability: float = Field(default=0.0, ge=0, le=1)
    execution_difficulty: float = Field(default=0.5, ge=0, le=1)
    legal_access_risk: float = Field(default=0.0, ge=0, le=1)
    time_delay: float = Field(default=0.0, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentResultRequest(BaseModel):
    lane_id: str
    outreach_sent: int = Field(ge=0)
    replies: int = Field(ge=0)
    meetings: int = Field(ge=0)
    paid_conversions: int = Field(ge=0)
    revenue: float = Field(ge=0)
    operator_hours: float = Field(ge=0)
    price: float | None = Field(default=None, ge=0)


class DailyRevenueReportRequest(BaseModel):
    raw_signals_reviewed: int = Field(ge=0)
    signals_logged: int = Field(ge=0)
    qualified_opportunities: int = Field(ge=0)
    prioritized_opportunities: int = Field(ge=0)
    direct_revenue_actions: int = Field(ge=0)
    sellable_assets_created: int = Field(ge=0)
    lessons_recorded: int = Field(ge=0)


def _serialize_prediction(p) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "statement": p.statement,
        "expected_value": p.expected_value,
        "confidence": p.confidence,
        "horizon_seconds": int(p.horizon.total_seconds()),
        "belief_id": str(p.belief_id) if p.belief_id else None,
        "action_id": str(p.action_id) if p.action_id else None,
        "edge_ids": [str(e) for e in p.edge_ids],
        "source_keys": list(p.source_keys),
        "status": str(p.status),
        "resolve_by": p.resolve_by.isoformat() if p.resolve_by else None,
        "resolved_at": p.resolved_at.isoformat() if p.resolved_at else None,
        "metadata": dict(p.metadata),
    }


def _serialize_learning(result) -> dict[str, Any]:
    attr = result.attribution
    return {
        "attribution_id": str(attr.id),
        "outcome_id": str(attr.outcome_id),
        "prediction_id": str(attr.prediction_id) if attr.prediction_id else None,
        "reward_score": attr.reward_score,
        "prediction_error": attr.prediction_error,
        "edge_deltas": attr.edge_deltas,
        "source_deltas": attr.source_deltas,
        "rationale": attr.rationale,
        "updated_edges": [
            {"id": str(e.id), "weight": e.weight, "confidence": e.confidence, "relation": e.relation}
            for e in result.updated_edges
        ],
        "pruned_edge_ids": [str(e) for e in result.pruned_edge_ids],
        "rewire_operations": [str(r.operation) for r in result.rewire_events],
    }


def _database_ready() -> tuple[bool, str]:
    if not os.environ.get("DATABASE_URL"):
        return True, "not_configured"
    checker = getattr(_brain_store, "database_healthy", None)
    if checker is None:
        return False, "configured_without_durable_store"
    return (True, "connected") if checker() else (False, "unavailable")


@app.get("/health")
def health():
    database_ok, database_status = _database_ready()
    # Avoid full event-ledger scan on every health probe
    event_count = len(getattr(runtime.store, "events", []) or [])
    payload = {
        "status": "ok" if database_ok else "degraded",
        "version": "0.7.1",
        "database": database_status,
        "persistence": "postgres" if os.environ.get("DATABASE_URL") else "in_memory",
        "beliefs": len(runtime.store.beliefs),
        "events": event_count,
        "predictions": len(getattr(_learning_store, "predictions", {})),
        "money_lanes": len(money_spine.lanes),
    }
    if not database_ok:
        return JSONResponse(status_code=503, content=payload)
    return payload


@app.get("/ready")
def ready():
    database_ok, database_status = _database_ready()
    if not database_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": database_status},
        )
    return {"status": "ready", "database": database_status}


@app.get("/beliefs")
def list_beliefs():
    items = []
    for belief in runtime.store.beliefs.values():
        items.append(
            {
                "id": str(belief.id),
                "statement": belief.statement,
                "confidence": belief.confidence,
                "state": str(belief.state),
                "version": getattr(belief, "version", 1),
                "created_at": None,
                "updated_at": belief.updated_at.isoformat()
                if getattr(belief, "updated_at", None)
                else None,
            }
        )
    source = (
        "postgres"
        if os.environ.get("DATABASE_URL") and getattr(_brain_store, "pool", None) is not None
        else "memory"
    )
    return {"items": items, "total": len(items), "source": source}


@app.get("/beliefs/{belief_id}")
def get_belief(belief_id: str):
    belief = runtime.store.beliefs.get(UUID(belief_id))
    if belief is None:
        raise HTTPException(status_code=404, detail="belief_not_found")
    return {
        "id": str(belief.id),
        "statement": belief.statement,
        "confidence": belief.confidence,
        "state": str(belief.state),
        "version": getattr(belief, "version", 1),
    }


@app.get("/predictions")
def list_predictions():
    store = learning.predictions if learning.predictions is not None else _learning_store
    if hasattr(store, "predictions"):
        predictions = list(store.predictions.values())
    elif hasattr(store, "list_open"):
        predictions = store.list_open()
    else:
        predictions = []
    items = [_serialize_prediction(prediction) for prediction in predictions]
    return {"items": items, "total": len(items)}


@app.get("/development/pressures")
def list_development_pressures():
    return {"items": development.store.list("development_pressure")}


@app.post("/beliefs")
def create_belief(body: CreateBeliefRequest):
    belief = runtime.create_belief(body.statement, body.confidence)
    return {
        "id": str(belief.id),
        "statement": belief.statement,
        "confidence": belief.confidence,
        "state": str(belief.state),
    }


@app.post("/learn")
def learn(body: LearnRequest):
    belief = runtime.store.beliefs.get(UUID(body.belief_id))
    if belief is None:
        raise HTTPException(status_code=404, detail="belief_not_found")
    evidence = Evidence(claim=body.claim, source_id=body.source_id, reliability=body.reliability)
    updated = runtime.learn(belief, evidence, body.supports)
    return {
        "id": str(updated.id),
        "statement": updated.statement,
        "confidence": updated.confidence,
        "state": str(updated.state),
        "version": updated.version,
    }


@app.post("/edges")
def upsert_edge(body: UpsertEdgeRequest):
    edge_id = UUID(body.edge_id) if body.edge_id else uuid4()
    edge = Edge(
        source=UUID(body.source_node_id),
        target=UUID(body.target_node_id),
        relation=body.relation,
        weight=body.weight,
        confidence=body.confidence,
        id=edge_id,
    )
    runtime.store.upsert_node(Node("entity", str(edge.source), id=edge.source))
    runtime.store.upsert_node(Node("entity", str(edge.target), id=edge.target))
    if learning.edges is not None:
        learning.edges.upsert_edge(edge)
    else:
        _learning_store.upsert_edge(edge)
    runtime.store.upsert_edge(edge)
    return {
        "id": str(edge.id),
        "source": str(edge.source),
        "target": str(edge.target),
        "relation": edge.relation,
        "weight": edge.weight,
    }


@app.post("/predictions")
def create_prediction(body: CreatePredictionRequest):
    prediction = PredictionEngine().create(
        body.statement,
        expected_value=body.expected_value,
        confidence=body.confidence,
        horizon=timedelta(seconds=body.horizon_seconds),
        belief_id=UUID(body.belief_id) if body.belief_id else None,
        action_id=UUID(body.action_id) if body.action_id else None,
        edge_ids=[UUID(e) for e in body.edge_ids],
        source_keys=list(body.source_keys),
        metadata=dict(body.metadata),
    )
    learning.create_prediction(prediction)
    return _serialize_prediction(prediction)


@app.get("/predictions/{prediction_id}")
def get_prediction(prediction_id: str):
    if learning.predictions is None:
        raise HTTPException(status_code=501, detail="predictions_store_unavailable")
    pred = learning.predictions.get(UUID(prediction_id))
    if pred is None:
        raise HTTPException(status_code=404, detail="prediction_not_found")
    return _serialize_prediction(pred)


@app.post("/outcomes")
def record_outcome(body: RecordOutcomeRequest):
    outcome = Outcome(
        action_id=UUID(body.action_id),
        value_created=body.value_created,
        operator_time_cost=body.operator_time_cost,
        prediction_accuracy=body.prediction_accuracy,
        trust_impact=body.trust_impact,
        legal_risk=body.legal_risk,
        prediction_id=UUID(body.prediction_id) if body.prediction_id else None,
        edge_ids=[UUID(e) for e in body.edge_ids],
        source_keys=list(body.source_keys),
    )
    try:
        result = learning.record_outcome(
            outcome,
            edge_ids=[UUID(e) for e in body.edge_ids] or None,
            prediction_id=UUID(body.prediction_id) if body.prediction_id else None,
            source_keys=list(body.source_keys) or None,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    pressure = development.ingest_learning_signal(
        outcome_id=outcome.id,
        prediction_id=result.attribution.prediction_id,
        prediction_error=result.attribution.prediction_error,
        reward_score=result.attribution.reward_score,
        evidence_refs=[
            f"outcome:{outcome.id}",
            f"attribution:{result.attribution.id}",
        ],
    )
    payload = _serialize_learning(result)
    payload["development_pressure"] = {
        "id": str(pressure.id),
        "pressure": pressure.pressure,
        "learning_priority": pressure.learning_priority,
        "reasons": pressure.reasons,
    }
    return payload


@app.get("/money-lanes")
def list_money_lanes():
    return [asdict(lane) for lane in money_spine.lanes.values()]


@app.post("/revenue-signals/score")
def score_revenue_signal(body: RevenueSignalRequest):
    signal = RevenueSignal(**body.model_dump())
    try:
        scored = money_spine.score_signal(signal)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="money_lane_not_found") from exc
    return asdict(scored)


@app.post("/revenue-signals/package")
def package_revenue_signal(body: RevenueSignalRequest):
    signal = RevenueSignal(**body.model_dump())
    try:
        scored = money_spine.score_signal(signal)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="money_lane_not_found") from exc
    if not scored.actionable:
        return {"error": "opportunity_rejected", "score": asdict(scored)}
    offer = money_spine.package_offer(signal, scored)
    return {"score": asdict(scored), "offer": asdict(offer)}


@app.post("/revenue-experiments/evaluate")
def evaluate_revenue_experiment(body: ExperimentResultRequest):
    try:
        experiment = money_spine.create_experiment(body.lane_id, price=body.price)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="money_lane_not_found") from exc
    result = money_spine.evaluate_experiment(
        experiment,
        outreach_sent=body.outreach_sent,
        replies=body.replies,
        meetings=body.meetings,
        paid_conversions=body.paid_conversions,
        revenue=body.revenue,
        operator_hours=body.operator_hours,
    )
    return {"experiment": asdict(experiment), "result": asdict(result)}


@app.post("/daily-revenue-report")
def daily_revenue_report(body: DailyRevenueReportRequest):
    report = DailyRevenueReport(**body.model_dump())
    return {
        "passed": report.passed,
        "gaps": report.gaps,
        "report": asdict(report),
    }
