from __future__ import annotations

import os
import sys
import threading
from contextlib import asynccontextmanager
from dataclasses import asdict
from math import isfinite
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from apps.api.cockpit_read_routes import register_cockpit_read_routes
from apps.api.inline_cognition import InlineCognition, start_inline_cognition
from brain.logging_config import get_logger
from apps.api.cognitive_organism_routes import register_cognitive_organism_routes
from brain.adapters.learning_store import InMemoryLearningStore
from brain.domain import Edge, Evidence, Node, Outcome
from brain.heartbeat import HeartbeatService
from brain.learning import LearningService
from brain.memory import InMemoryBrainStore
from brain.money_spine import (
    DailyRevenueReport,
    MoneySpineService,
    RevenueExecutionSpine,
    RevenueOutcomeType,
    RevenueSignal,
)
from brain.prediction import PredictionEngine
from brain.runtime import BrainRuntime
from brain.security import SecurityConfig, presented_credentials

_security = SecurityConfig.from_env()

_inline_cognition: InlineCognition | None = None

#: One writer at a time inside this process. The cognition lease keeps two
#: *processes* from thinking at once, but it says nothing about this one: the
#: inline thread and any request calling POST /tick (or /signals with
#: process_now) both drive the same HeartbeatService, whose cycle, inbox and
#: belief cache are plain unguarded dicts. FastAPI runs sync routes in a thread
#: pool, so without this an operator tick could interleave with a background
#: cycle mid-mutation.
_tick_lock = threading.Lock()


def tick_once(*, max_items: int = 1) -> dict[str, Any]:
    """Run cognition cycles as the only writer in this process."""

    with _tick_lock:
        return heartbeat.tick(max_items=max_items)


def _resume_durable_beliefs() -> None:
    """Load what the Brain already believes into the cycle it will think with.

    bootstrap_mind() seeds foundational beliefs into the cycle's cache and
    nothing else, so a cycle started cold reasons as though the lattice were
    empty -- re-deriving beliefs the database already holds and contradicting
    none of them, because it cannot see them. apps/worker/main.build_runner()
    registers the durable projection first for exactly this reason; the inline
    path has to do the same or restarting the API amounts to amnesia.
    """

    cycle = getattr(heartbeat, "_cycle", None)
    register = getattr(cycle, "register_belief", None)
    if register is None:
        return
    beliefs = getattr(_brain_store, "beliefs", {}) or {}
    for belief in list(beliefs.values()):
        try:
            register(belief)
        except Exception:
            log.exception("durable belief could not be resumed", extra={"belief_id": str(belief.id)})
    log.info("inline cognition resumed durable beliefs", extra={"beliefs": len(beliefs)})


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Drive cognition from this process when nothing else is driving it.

    Deliberately a lifespan handler and not import-time work: no test in this
    suite enters TestClient as a context manager, so none of them start a
    cognition thread, while every deployed entrypoint runs the app as ASGI and
    so does. The Vercel OIDC bridge in tools/live_cockpit_routes passes
    non-HTTP scopes straight through to the inner app, so the lifespan reaches
    this handler through that wrapper too.
    """

    global _inline_cognition
    _inline_cognition = start_inline_cognition(
        lambda: tick_once(max_items=1), on_start=_resume_durable_beliefs
    )
    try:
        yield
    finally:
        engine, _inline_cognition = _inline_cognition, None
        if engine is not None:
            engine.stop()


app = FastAPI(title="Brain Runtime API", version="0.8.1", lifespan=_lifespan)

_origins = _security.allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Api-Key",
        "X-Brain-Api-Key",
        "X-Request-Id",
    ],
)

_API_KEY_ENV_VAR = "BRAIN_API_KEY"
log = get_logger("api")

_PUBLIC_PATHS = frozenset({"/health", "/ready"})


#: Routes answered from the cached projection rather than from PostgreSQL
#: directly. Wiring the refresh into three handlers left the rest -- the
#: cockpit's /contradictions, /curiosity and /sources among them -- serving the
#: boot snapshot indefinitely, and the Observatory polls them all in parallel,
#: so which routes happened to be fresh depended on request ordering. One
#: boundary is easier to keep honest than a call in every handler.
_PROJECTION_EXEMPT_PATHS = frozenset({"/health", "/ready"})


@app.middleware("http")
async def refresh_projection_reads(request: Request, call_next):
    # /health and /ready are exempt: they answer whether the database is
    # reachable at all, and must keep failing fast when it is not rather than
    # waiting on a read they already know will not work. /health refreshes
    # itself once readiness passes.
    if request.method in {"GET", "HEAD"} and request.url.path not in _PROJECTION_EXEMPT_PATHS:
        _refresh_reads()
    return await call_next(request)


@app.middleware("http")
async def brain_authentication(request: Request, call_next):
    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)

    configured_key = os.environ.get(_API_KEY_ENV_VAR)
    if not configured_key:
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    f"{_API_KEY_ENV_VAR} is not configured on this deployment; "
                    "refusing all requests until it is set"
                )
            },
        )

    if not presented_credentials(request.headers, configured_key):
        return JSONResponse(
            status_code=401,
            content={"detail": "invalid_or_missing_api_key"},
        )
    return await call_next(request)


_brain_store: InMemoryBrainStore = InMemoryBrainStore()
_learning_store = InMemoryLearningStore()
runtime = BrainRuntime(store=_brain_store)
learning = LearningService(
    _brain_store,
    predictions=_learning_store,
    edges=_learning_store,
    attributions=_learning_store,
    sources=_learning_store,
)
money_spine = MoneySpineService()
# The approval-gated action loop on top of money_spine. Queues, approves,
# logs, and records outcomes for revenue actions. It never sends or
# spends anything itself — see RevenueExecutionSpine docstring.
revenue_spine = RevenueExecutionSpine(money=money_spine)
heartbeat = HeartbeatService(event_store=_brain_store, learning=learning)


def _configure_from_env() -> None:
    global _brain_store, runtime, learning, heartbeat, money_spine, revenue_spine
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return

    from brain.adapters.brain_store import PostgresBrainStore
    from brain.adapters.learning_store import (
        PostgresAttributionStore,
        PostgresEdgeStore,
        PostgresPredictionStore,
        PostgresSourceStore,
    )
    from brain.adapters.revenue_store import PostgresRevenueStore

    store = PostgresBrainStore(dsn)
    _brain_store = store
    runtime = BrainRuntime(store=store)
    learning = LearningService(
        store.event_store,
        predictions=PostgresPredictionStore(store.pool),
        edges=PostgresEdgeStore(store.pool),
        attributions=PostgresAttributionStore(store.pool),
        sources=PostgresSourceStore(store.pool),
    )
    # The store, not store.event_store. PostgresEventStore can append to the
    # ledger but has no save(), and CognitiveCycle._persist_belief() looks for
    # exactly that method -- so a cycle driven through the event store wrote
    # belief.created events while never touching the beliefs table the cockpit
    # reads. Harmless while apps/api ran no cognition; the moment it does, it
    # would climb CYCLE against a lattice that stays permanently UNFORMED.
    # apps/worker/main.build_runner() passes the store for the same reason.
    heartbeat = HeartbeatService(event_store=store, learning=learning)

    revenue_store = PostgresRevenueStore(pool=store.pool)
    money_spine = MoneySpineService(store=revenue_store)
    revenue_spine = RevenueExecutionSpine(money=money_spine, store=revenue_store)


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


class QueueRevenueActionRequest(BaseModel):
    signal: RevenueSignalRequest
    action_type: str = "outreach_draft"


class ApproveRevenueActionRequest(BaseModel):
    approved_by: str


class LogManualRevenueActionRequest(BaseModel):
    manual_proof_ref: str


class ScheduleFollowUpRequest(BaseModel):
    script: str
    delay_hours: int = Field(default=48, ge=0)


class RecordRevenueOutcomeRequest(BaseModel):
    outcome_type: RevenueOutcomeType
    revenue: float = Field(default=0.0, ge=0)
    reply: bool = False
    meeting_booked: bool = False
    paid_conversion: bool = False
    legal_risk: float = Field(default=0.0, ge=0, le=1)
    operator_hours: float = Field(default=0.0, ge=0)
    lesson: str = ""


class PerceiveRequest(BaseModel):
    content: str
    claim: str
    source_key: str = "operator"
    source_reliability: float = Field(default=0.7, ge=0, le=1)
    supports: bool = True
    belief_statement: str | None = None
    belief_confidence: float = Field(default=0.5, ge=0, le=1)
    novelty: float = Field(default=0.5, ge=0, le=1)
    urgency: float = Field(default=0.3, ge=0, le=1)
    commercial_upside: float = Field(default=0.0, ge=0, le=1)
    contradiction_value: float = Field(default=0.0, ge=0, le=1)
    uncertainty_reduction: float = Field(default=0.5, ge=0, le=1)
    noise_probability: float = Field(default=0.2, ge=0, le=1)
    operator_burden: float = Field(default=0.0, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    process_now: bool = False


class TickRequest(BaseModel):
    max_items: int = Field(default=1, ge=1, le=50)


def _serialize_prediction(prediction) -> dict[str, Any]:
    return {
        "id": str(prediction.id),
        "statement": prediction.statement,
        "expected_value": prediction.expected_value,
        "confidence": prediction.confidence,
        "horizon_seconds": int(prediction.horizon.total_seconds()),
        "belief_id": str(prediction.belief_id) if prediction.belief_id else None,
        "action_id": str(prediction.action_id) if prediction.action_id else None,
        "edge_ids": [str(edge_id) for edge_id in prediction.edge_ids],
        "source_keys": list(prediction.source_keys),
        "status": str(prediction.status),
        "resolve_by": prediction.resolve_by.isoformat() if prediction.resolve_by else None,
        "resolved_at": prediction.resolved_at.isoformat() if prediction.resolved_at else None,
        "metadata": dict(prediction.metadata),
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
            {
                "id": str(edge.id),
                "weight": edge.weight,
                "confidence": edge.confidence,
                "relation": edge.relation,
            }
            for edge in result.updated_edges
        ],
        "pruned_edge_ids": [str(edge_id) for edge_id in result.pruned_edge_ids],
        "rewire_operations": [str(rewire.operation) for rewire in result.rewire_events],
    }


#: How long a cached belief/graph projection may serve reads before the API
#: re-reads it. The Observatory polls every 5s; matching that keeps the cockpit
#: live at roughly one hydrate per poll interval. 0 refreshes every read; a
#: negative value disables refreshing and restores the boot-snapshot behavior.
def _read_refresh_seconds() -> float:
    raw = (os.environ.get("BRAIN_READ_REFRESH_SECONDS") or "").strip()
    if not raw:
        return 5.0
    try:
        parsed = float(raw)
    except ValueError:
        return 5.0
    # float() accepts "nan" and "inf". Neither takes the garbage-value
    # fallback on its own, and both break the TTL rather than tuning it: NaN
    # fails every age comparison and hydrates on every single request, while
    # Infinity makes the boot snapshot fresh forever -- restoring exactly the
    # stale-read bug the TTL exists to fix.
    if not isfinite(parsed):
        log.warning(
            "ignoring non-finite BRAIN_READ_REFRESH_SECONDS", extra={"value": raw}
        )
        return 5.0
    return parsed


def _refresh_reads() -> None:
    """Let read routes see what the worker wrote.

    PostgresBrainStore.hydrate() runs once in the constructor, so a long-lived
    API process answered every read from the snapshot it booted with. The
    worker writes beliefs and evidence to the same database from another
    process, and none of it appeared until the API restarted.
    """
    refresh = getattr(_brain_store, "refresh_if_stale", None)
    if refresh is None:
        return
    try:
        refresh(_read_refresh_seconds())
    except Exception:
        log.exception("belief projection refresh failed; serving cached projection")


def _cognition_status() -> dict[str, Any]:
    """Heartbeat status describing the system, not this process.

    apps/api runs no cognition loop: `heartbeat` here is an untouched
    HeartbeatService whose counters are structurally always zero, while every
    tick happens in apps/worker against a different instance. The cockpit read
    those zeros and rendered CYCLE 0 no matter how much work the worker had
    done. Durable counts from the shared event stream replace them; the local
    values remain as the fallback when no database is configured.
    """
    status = dict(heartbeat.status())
    counters = getattr(_brain_store, "cognition_counters", None)
    if counters is None:
        return status
    try:
        counts = counters(_read_refresh_seconds())
    except Exception:
        log.exception("durable cognition counters unavailable; reporting process-local heartbeat")
        return status

    status["ticks"] = counts.get("cycle.completed", status.get("ticks", 0))
    # observation.received or nothing. signal.enqueued is emitted when a signal
    # is *queued*, before any cognition touches it, so falling back to it would
    # report every waiting signal as processed -- loudest in precisely the case
    # this endpoint exists to expose, a stalled loop with a full inbox.
    status["total_processed"] = counts.get("observation.received", 0)
    status["signals_enqueued"] = counts.get("signal.enqueued", 0)
    status["beliefs_created"] = counts.get("belief.created", 0)
    status["beliefs_updated"] = counts.get("belief.updated", 0)
    status["source"] = "durable"
    return status


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
    # Both of these open pooled connections with no timeout of their own, so
    # each can wait out the pool's 30s default. _database_ready() is
    # deliberately bounded to ~3s (#75) precisely so a dead database fails
    # fast; running them anyway would turn an already-known 503 into a
    # minute-long hang and time out every monitor watching this endpoint.
    if database_ok:
        _refresh_reads()
    hb = _cognition_status() if database_ok else dict(heartbeat.status())
    payload = {
        "status": "ok" if database_ok else "degraded",
        "version": "0.8.1",
        "database": database_status,
        "persistence": "postgres" if os.environ.get("DATABASE_URL") else "in_memory",
        "beliefs": len(runtime.store.beliefs),
        "money_lanes": len(money_spine.lanes),
        "heartbeat": {
            "ticks": hb.get("ticks", 0),
            "total_processed": hb.get("total_processed", 0),
            "inbox": hb.get("inbox", {}),
            "working_memory_size": hb.get(
                "working_memory_size",
                hb.get("belief_cache_size", 0),
            ),
        },
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


@app.post("/signals")
def enqueue_signal(body: PerceiveRequest):
    item = heartbeat.perceive(
        content=body.content,
        claim=body.claim,
        source_key=body.source_key,
        source_reliability=body.source_reliability,
        supports=body.supports,
        belief_statement=body.belief_statement,
        belief_confidence=body.belief_confidence,
        novelty=body.novelty,
        urgency=body.urgency,
        commercial_upside=body.commercial_upside,
        contradiction_value=body.contradiction_value,
        uncertainty_reduction=body.uncertainty_reduction,
        noise_probability=body.noise_probability,
        operator_burden=body.operator_burden,
        metadata=body.metadata,
    )
    tick_result = tick_once(max_items=1) if body.process_now else None
    return {
        "id": str(item.id),
        "source_key": item.source_key,
        "content": item.content,
        "claim": item.claim,
        "status": item.status,
        "tick": tick_result,
    }


@app.post("/tick")
def run_heartbeat_tick(body: TickRequest | None = None):
    max_items = body.max_items if body is not None else 1
    return tick_once(max_items=max_items)


@app.get("/runner/status")
def runner_status():
    _refresh_reads()
    return _cognition_status()


@app.get("/beliefs")
def list_beliefs():
    _refresh_reads()
    items = [
        {
            "id": str(belief.id),
            "statement": belief.statement,
            "confidence": belief.confidence,
            "state": str(belief.state),
            "version": getattr(belief, "version", 1),
            "updated_at": belief.updated_at.isoformat()
            if getattr(belief, "updated_at", None)
            else None,
        }
        for belief in runtime.store.beliefs.values()
    ]
    return {
        "items": items,
        "total": len(items),
        "source": "postgres" if os.environ.get("DATABASE_URL") else "memory",
    }


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
        edge_ids=[UUID(edge_id) for edge_id in body.edge_ids],
        source_keys=list(body.source_keys),
        metadata=dict(body.metadata),
    )
    learning.create_prediction(prediction)
    return _serialize_prediction(prediction)


@app.get("/predictions/{prediction_id}")
def get_prediction(prediction_id: str):
    if learning.predictions is None:
        raise HTTPException(status_code=501, detail="predictions_store_unavailable")
    prediction = learning.predictions.get(UUID(prediction_id))
    if prediction is None:
        raise HTTPException(status_code=404, detail="prediction_not_found")
    return _serialize_prediction(prediction)


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
        edge_ids=[UUID(edge_id) for edge_id in body.edge_ids],
        source_keys=list(body.source_keys),
    )
    try:
        result = learning.record_outcome(
            outcome,
            edge_ids=[UUID(edge_id) for edge_id in body.edge_ids] or None,
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
    return {"passed": report.passed, "gaps": report.gaps, "report": asdict(report)}


# --- Revenue execution spine: the approval-gated action loop -------------
# score/package (above) tell you whether a signal is worth acting on.
# These routes are what actually closes the loop: queue a candidate
# action, require a named human to approve it, log manual proof of
# execution (this system never sends or spends on its own), and record
# the real-world outcome, which feeds straight back into
# MoneySpineService.apply_outcome_learning.

@app.post("/revenue-actions/queue")
def queue_revenue_action(body: QueueRevenueActionRequest):
    signal = RevenueSignal(**body.signal.model_dump())
    try:
        scored, offer, action = revenue_spine.queue_action_from_signal(
            signal, action_type=body.action_type
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="money_lane_not_found") from exc
    return {"score": asdict(scored), "offer": asdict(offer), "action": asdict(action)}


@app.get("/revenue-actions")
def list_revenue_actions():
    return revenue_spine.snapshot()


@app.get("/revenue-actions/{action_id}")
def get_revenue_action(action_id: UUID):
    try:
        return asdict(revenue_spine.actions[action_id])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="revenue_action_not_found") from exc


@app.post("/revenue-actions/{action_id}/approve")
def approve_revenue_action(action_id: UUID, body: ApproveRevenueActionRequest):
    try:
        action = revenue_spine.approve_action(action_id, approved_by=body.approved_by)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="revenue_action_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return asdict(action)


@app.post("/revenue-actions/{action_id}/log-manual")
def log_manual_revenue_action(action_id: UUID, body: LogManualRevenueActionRequest):
    try:
        action = revenue_spine.log_manual_action(
            action_id, manual_proof_ref=body.manual_proof_ref
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="revenue_action_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return asdict(action)


@app.post("/revenue-actions/{action_id}/follow-up")
def schedule_revenue_follow_up(action_id: UUID, body: ScheduleFollowUpRequest):
    try:
        followup = revenue_spine.schedule_follow_up(
            action_id, script=body.script, delay_hours=body.delay_hours
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="revenue_action_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return asdict(followup)


@app.post("/revenue-actions/{action_id}/outcome")
def record_revenue_outcome(action_id: UUID, body: RecordRevenueOutcomeRequest):
    try:
        entry = revenue_spine.record_outcome(
            action_id,
            outcome_type=body.outcome_type,
            revenue=body.revenue,
            reply=body.reply,
            meeting_booked=body.meeting_booked,
            paid_conversion=body.paid_conversion,
            legal_risk=body.legal_risk,
            operator_hours=body.operator_hours,
            lesson=body.lesson,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="revenue_action_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return asdict(entry)


register_cognitive_organism_routes(app)

# The cockpit read model lives on the canonical image, not only on the
# deprecated Dockerfile.railway compatibility entrypoint.
register_cockpit_read_routes(app, api_module=sys.modules[__name__])
