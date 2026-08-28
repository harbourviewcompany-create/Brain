"""External cognition ticks for free serverless schedulers.

Cloudflare Workers (and similar free cron hosts) cannot run the Python worker.
They can HTTP-trigger a short, lease-aware unit of work on the Brain API.

This path deliberately acquires the cognition lease with ``blocking=False``,
runs at most a few heartbeat ticks, and releases. If inline cognition (#168)
or a dedicated worker already holds the lease, the call returns 200 with
``status=lease_held_elsewhere`` and does no work -- never a second writer.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from fastapi import APIRouter
from pydantic import BaseModel, Field

from apps.api.inline_cognition import cognition_dsn
from brain.cognition_lease import CognitionLease
from brain.logging_config import get_logger

log = get_logger("cognition_cron")

router = APIRouter(tags=["cognition-cron"])


class ExternalTickRequest(BaseModel):
    max_items: int = Field(default=1, ge=1, le=5)
    max_ticks: int = Field(default=1, ge=1, le=5)


def _tick_fn_from_module(api_module: Any) -> Callable[..., Any]:
    heartbeat = getattr(api_module, "heartbeat")

    def _tick(max_items: int) -> Any:
        return heartbeat.tick(max_items=max_items)

    return _tick


def register_cognition_cron_routes(app: Any, *, api_module: Any) -> None:
    """Mount lease-aware external tick routes on the given FastAPI app."""

    tick_fn = _tick_fn_from_module(api_module)

    @router.post("/internal/cognition/tick")
    def external_cognition_tick(body: ExternalTickRequest | None = None) -> dict[str, Any]:
        req = body or ExternalTickRequest()
        dsn = cognition_dsn()
        if not dsn:
            # In-memory deployments have no shared lease; still allow a tick so
            # local/dev cron probes do something observable.
            results = [tick_fn(req.max_items) for _ in range(req.max_ticks)]
            return {
                "status": "ticked",
                "lease": "not_configured",
                "ticks": len(results),
                "results": results,
            }

        lease = CognitionLease(dsn)
        if not lease.acquire(blocking=False):
            return {
                "status": "lease_held_elsewhere",
                "lease": "not_acquired",
                "ticks": 0,
                "results": [],
                "detail": (
                    "another process holds the cognition lease; "
                    "no work performed (single-writer preserved)"
                ),
            }

        results: list[Any] = []
        try:
            for _ in range(req.max_ticks):
                results.append(tick_fn(req.max_items))
        except Exception:
            log.exception("external cognition tick failed")
            raise
        finally:
            # Always drop the request-scoped lease so inline/worker can reclaim.
            lease.release()

        return {
            "status": "ticked",
            "lease": "acquired_and_released",
            "ticks": len(results),
            "results": results,
        }

    app.include_router(router)
