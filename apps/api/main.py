from __future__ import annotations

import os
from dataclasses import asdict
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from brain.adapters.belief_store import PostgresBeliefStore, serialize_belief
from brain.adapters.learning_store import InMemoryLearningStore
from brain.domain import Edge, Evidence, Node, Outcome
from brain.learning import LearningService
from brain.memory import InMemoryBrainStore
from brain.money_spine import DailyRevenueReport, MoneySpineService, RevenueSignal
from brain.prediction import PredictionEngine
from brain.runtime import BrainRuntime

app = FastAPI(title="Brain Runtime API", version="0.5.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_memory_store = InMemoryBrainStore()
_learning_store = InMemoryLearningStore()
_event_store: Any = None
_belief_store: PostgresBeliefStore | None = None
_durable = False

runtime = BrainRuntime(store=_memory_store)
learning = LearningService(
    _memory_store,
    predictions=_learning_store,
    edges=_learning_store,
    attributions=_learning_store,
    sources=_learning_store,
)
money_spine = MoneySpineService()


def _configure_from_env() -> None:
    global learning, runtime, _event_store, _belief_store, _durable
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return
    try:
        from brain.adapters.learning_store import (
            PostgresAttributionStore,
            PostgresEdgeStore,
            PostgresPredictionStore,
            PostgresSourceStore,
        )
        from brain.adapters.postgres import PostgresEventStore
    except ImportError:
        return

    event_store = PostgresEventStore(dsn)
    _event_store = event_store
    _belief_store = PostgresBeliefStore(event_store.pool)
    _durable = True

    # Dual-write: in-memory working set + durable event ledger + belief projection
    runtime = BrainRuntime(
        store=_memory_store,
        event_store=event_store,
        belief_projection=_belief_store,
    )

    # Hydrate working set from projection (fast path)
    try:
        loaded = _belief_store.load_into(_memory_store.beliefs)
    except Exception:
        loaded = 0

    # If projection empty, try event replay via hydrate helper
    if loaded == 0:
        try:
            from brain.hydrate import hydrate_belief_cache

            hydrate_belief_cache(_memory_store.beliefs, event_store, from_checkpoint=False)
            for b in _memory_store.beliefs.values():
                try:
                    _belief_store.upsert(b)
                except Exception:
                    pass
        except Exception:
            pass

    learning = LearningService(
        event_store,
        predictions=PostgresPredictionStore(event_store.pool),
        edges=PostgresEdgeStore(event_store.pool),
        attributions=PostgresAttributionStore(event_store.pool),
        sources=PostgresSourceStore(event_store.pool),
    )


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


@app.get("/health")
def health():
    event_count = len(getattr(_memory_store, "events", []) or [])
    try:
        if _event_store is not None and hasattr(_event_store, "read_all"):
            event_count = len(_event_store.read_all())
    except Exception:
        pass
    belief_count = len(runtime.store.beliefs)
    if _belief_store is not None:
        try:
            belief_count = max(belief_count, len(_belief_store.list_all()))
        except Exception:
            pass
    return {
        "status": "ok",
        "version": "0.5.1",
        "durable": _durable,
        "beliefs": belief_count,
        "events": event_count,
        "predictions": len(getattr(_learning_store, "predictions", {})),
        "money_lanes": len(money_spine.lanes),
    }


@app.get("/beliefs")
def list_beliefs():
    # Prefer durable projection when available
    if _belief_store is not None:
        try:
            items = [serialize_belief(b) for b in _belief_store.list_all()]
            return {"items": items, "total": len(items), "source": "postgres"}
        except Exception:
            pass
    items = [serialize_belief(b) for b in runtime.store.beliefs.values()]
    return {"items": items, "total": len(items), "source": "memory"}


@app.get("/beliefs/{belief_id}")
def get_belief(belief_id: str):
    bid = UUID(belief_id)
    if _belief_store is not None:
        try:
            belief = _belief_store.get(bid)
            if belief is not None:
                return serialize_belief(belief)
        except Exception:
            pass
    belief = runtime.store.beliefs.get(bid)
    if belief is None:
        raise HTTPException(status_code=404, detail="belief_not_found")
    return serialize_belief(belief)


@app.get("/predictions")
def list_predictions():
    store = learning.predictions if learning.predictions is not None else _learning_store
    preds = getattr(store, "predictions", {}) or {}
    items = [_serialize_prediction(p) for p in preds.values()]
    return {"items": items, "total": len(items)}


@app.post("/beliefs")
def create_belief(body: CreateBeliefRequest):
    belief = runtime.create_belief(body.statement, body.confidence)
    return serialize_belief(belief)


@app.post("/learn")
def learn(body: LearnRequest):
    bid = UUID(body.belief_id)
    belief = runtime.store.beliefs.get(bid)
    if belief is None and _belief_store is not None:
        belief = _belief_store.get(bid)
        if belief is not None:
            runtime.store.beliefs[bid] = belief
    if belief is None:
        raise HTTPException(status_code=404, detail="belief_not_found")
    evidence = Evidence(claim=body.claim, source_id=body.source_id, reliability=body.reliability)
    updated = runtime.learn(belief, evidence, body.supports)
    return serialize_belief(updated)


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
    return _serialize_learning(result)


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
