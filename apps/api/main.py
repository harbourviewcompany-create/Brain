from __future__ import annotations

import hmac
import os
from dataclasses import asdict
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from apps.api.cognitive_organism_routes import register_cognitive_organism_routes
from brain.adapters.learning_store import InMemoryLearningStore
from brain.domain import Edge, Evidence, Node, Outcome
from brain.heartbeat import HeartbeatService
from brain.learning import LearningService
from brain.memory import InMemoryBrainStore
from brain.money_spine import DailyRevenueReport, MoneySpineService, RevenueSignal
from brain.prediction import PredictionEngine
from brain.runtime import BrainRuntime
from brain.security import SecurityConfig

_security = SecurityConfig.from_env()

app = FastAPI(title="Brain Runtime API", version="0.8.1")

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
_PUBLIC_PATHS = frozenset({"/health", "/ready"})


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

    authorization = request.headers.get("authorization")
    candidate = (
        request.headers.get("x-brain-api-key")
        or request.headers.get("x-api-key")
        or ""
    )
    if authorization and authorization.lower().startswith("bearer "):
        candidate = authorization[7:].strip()

    if not candidate or not hmac.compare_digest(candidate, configured_key):
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
heartbeat = HeartbeatService(event_store=_brain_store, learning=learning)


def _configure_from_env() -> None:
    global _brain_store, runtime, learning, heartbeat
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
    heartbeat = HeartbeatService(event_store=store.event_store, learning=learning)


_configure_from_env()
