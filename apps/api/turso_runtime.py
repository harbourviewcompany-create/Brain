from __future__ import annotations

import os
from typing import Any

from brain.adapters.turso import TursoDatabase
from brain.adapters.turso_brain_store import TursoBrainStore
from brain.adapters.turso_learning_store import (
    TursoAttributionStore,
    TursoEdgeStore,
    TursoPredictionStore,
    TursoSourceStore,
)
from brain.adapters.turso_revenue_store import TursoRevenueStore
from brain.heartbeat import HeartbeatService
from brain.learning import LearningService
from brain.money_spine import MoneySpineService, RevenueExecutionSpine
from brain.runtime import BrainRuntime


class UnsupportedZeroCostTenantMode(RuntimeError):
    pass


def _tenant_mode_requested() -> bool:
    value = (os.environ.get("BRAIN_TENANT_MODE") or "").strip().lower()
    return value not in {"", "0", "false", "off", "disabled"}


def configure_api_module(api_module: Any) -> TursoBrainStore:
    """Rebind the existing API route module to Turso-backed durable stores.

    PostgreSQL tenant/RLS mode intentionally remains a separate security
    topology. libSQL has no equivalent of the existing PostgreSQL RLS policy
    boundary, so a request to combine tenant mode with this runtime fails closed.
    """

    if _tenant_mode_requested():
        raise UnsupportedZeroCostTenantMode(
            "BRAIN_TENANT_MODE requires the audited PostgreSQL RLS runtime; "
            "the Turso zero-cost runtime will not emulate or weaken that boundary"
        )

    db = TursoDatabase.from_env()
    store = TursoBrainStore(db=db)
    prediction_store = TursoPredictionStore(db)
    edge_store = TursoEdgeStore(db)
    attribution_store = TursoAttributionStore(db)
    source_store = TursoSourceStore(db)
    revenue_store = TursoRevenueStore(db)

    api_module._brain_store = store
    api_module.runtime = BrainRuntime(store=store)
    api_module.learning = LearningService(
        store.event_store,
        predictions=prediction_store,
        edges=edge_store,
        attributions=attribution_store,
        sources=source_store,
    )
    api_module.heartbeat = HeartbeatService(event_store=store.event_store, learning=api_module.learning)
    api_module.money_spine = MoneySpineService(store=revenue_store)
    api_module.revenue_spine = RevenueExecutionSpine(
        money=api_module.money_spine,
        store=revenue_store,
    )
    # Some existing route code keeps this fallback global for non-Postgres
    # learning reads. Point it at a durable facade rather than stale memory.
    api_module._learning_store = prediction_store
    return store
