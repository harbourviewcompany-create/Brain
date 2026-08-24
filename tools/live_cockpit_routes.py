from __future__ import annotations

from datetime import UTC, datetime
import logging
import os
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from fastapi.responses import JSONResponse

from apps.api.main import app, runtime, _learning_store
from brain.attention import AttentionMarket, AttentionSignal
from tools.vercel_oidc import VercelOidcVerifier


_logger = logging.getLogger(__name__)
_attention_market = AttentionMarket()


def _iso(value: Any | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _stable_uuid(namespace: str, key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"brain:{namespace}:{key}"))


def _list_response(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"items": items, "total": len(items), "source": "api"}


def _number(payload: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(payload.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _signal_item_from_event(event: Any) -> dict[str, Any]:
    """Build the compatibility Signal shape from a durable signal.enqueued event."""
    event_payload = dict(getattr(event, "payload", {}) or {})
    signal_payload = dict(event_payload.get("payload") or {})

    commercial_upside = _number(signal_payload, "commercial_upside")
    novelty = _number(signal_payload, "novelty", 0.5)
    urgency = _number(signal_payload, "urgency")
    contradiction_value = _number(signal_payload, "contradiction_value")
    source_quality = _number(signal_payload, "source_reliability", 0.5)
    uncertainty_reduction = _number(signal_payload, "uncertainty_reduction", 0.5)
    noise_probability = _number(signal_payload, "noise_probability", 0.2)
    operator_burden = _number(signal_payload, "operator_burden")
    attention_score = _attention_market.score(
        AttentionSignal(
            commercial_upside=commercial_upside,
            novelty=novelty,
            urgency=urgency,
            contradiction_value=contradiction_value,
            source_quality=source_quality,
            uncertainty_reduction=uncertainty_reduction,
            noise_probability=noise_probability,
            operator_burden=operator_burden,
        )
    )

    occurred_at = getattr(event, "occurred_at", None)
    metadata = dict(signal_payload.get("metadata") or {})
    metadata.update(
        {
            "content": str(event_payload.get("content") or ""),
            "claim": str(event_payload.get("claim") or ""),
            "source_key": str(event_payload.get("source_key") or "unknown"),
        }
    )

    return {
        "id": str(getattr(event, "aggregate_id")),
        "created_at": _iso(occurred_at),
        "updated_at": _iso(occurred_at),
        "source_id": str(event_payload.get("source_key") or "unknown"),
        "evidence_ids": [],
        "novelty": novelty,
        "urgency": urgency,
        "commercial_upside": commercial_upside,
        "attention_score": attention_score,
        "formula_run_id": None,
        "metadata": metadata,
    }


@app.get("/signals")
def list_signals():
    """Read signals from the canonical durable signal.enqueued event stream.

    In production ``runtime.store.read_all()`` is backed by PostgresBrainStore and
    therefore reads public.brain_events. This deliberately avoids the disposable
    in-process ``runtime.store.evidence`` projection that can lag durable writes.
    """
    items = [
        _signal_item_from_event(event)
        for event in runtime.store.read_all()
        if getattr(event, "event_type", None) == "signal.enqueued"
    ]
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return _list_response(items)


@app.get("/contradictions")
def list_contradictions():
    """Live contradiction read model derived from contested beliefs."""
    items: list[dict[str, Any]] = []
    for belief in runtime.store.beliefs.values():
        supporting = [str(e) for e in getattr(belief, "supporting_evidence", set())]
        contradicting = [str(e) for e in getattr(belief, "contradicting_evidence", set())]
        state = str(getattr(belief, "state", ""))
        if not contradicting and state != "contested":
            continue
        items.append(
            {
                "id": _stable_uuid("contradiction", str(belief.id)),
                "created_at": _iso(getattr(belief, "updated_at", None)),
                "updated_at": _iso(getattr(belief, "updated_at", None)),
                "belief_ids": [str(belief.id)],
                "supporting_evidence_ids": supporting,
                "contradicting_evidence_ids": contradicting,
                "status": "open",
                "resolution_note": None,
                "investigation_pressure": 1.0 if contradicting else 0.5,
            }
        )
    return _list_response(items)


@app.get("/curiosity")
def list_curiosity_tasks():
    """Live curiosity read model derived from belief unknowns."""
    items: list[dict[str, Any]] = []
    for belief in runtime.store.beliefs.values():
        for index, unknown in enumerate(getattr(belief, "unknowns", []) or []):
            items.append(
                {
                    "id": _stable_uuid("curiosity", f"{belief.id}:{index}:{unknown}"),
                    "created_at": _iso(getattr(belief, "updated_at", None)),
                    "updated_at": _iso(getattr(belief, "updated_at", None)),
                    "title": str(unknown),
                    "linked_object_type": "belief",
                    "linked_object_id": str(belief.id),
                    "priority": 0.5,
                    "status": "open",
                    "suggested_action": "collect_evidence",
                }
            )
    return _list_response(items)


@app.get("/sources")
def list_sources():
    """Live source read model from evidence and source reliability scores."""
    source_ids = {str(e.source_id) for e in runtime.store.evidence.values()}
    source_scores = getattr(_learning_store, "source_scores", {}) or {}
    source_ids.update(str(key) for key in source_scores.keys())

    items: list[dict[str, Any]] = []
    for source_id in sorted(source_ids):
        trust_score = float(source_scores.get(source_id, 0.5) or 0.5)
        now = datetime.now(UTC).isoformat()
        items.append(
            {
                "id": _stable_uuid("source", source_id),
                "created_at": now,
                "updated_at": now,
                "name": source_id,
                "kind": "observed",
                "trust_score": trust_score,
                "status": "quarantined" if trust_score < 0.2 else "active",
                "quarantine_reason": "low_trust_score" if trust_score < 0.2 else None,
            }
        )
    return _list_response(items)


@app.get("/approvals")
def list_approvals():
    return _list_response([])


@app.get("/opportunities")
def list_opportunities():
    return _list_response([])


@app.get("/outcomes")
def list_outcomes():
    return _list_response([])


@app.get("/formula-runs")
def list_formula_runs():
    return _list_response([])


@app.get("/acceptance-reports")
def list_acceptance_reports():
    return _list_response([])


class VercelOidcAuthBridge:
    """ASGI wrapper for the Railway-only deployment identity path.

    The wrapped FastAPI application and its existing authentication middleware
    remain unchanged. A valid Vercel deployment token is verified outside the
    FastAPI middleware stack and exchanged only inside Railway for the local
    BRAIN_API_KEY already stored in this service.
    """

    def __init__(self, inner_app) -> None:
        self.inner_app = inner_app
        self.verifier = VercelOidcVerifier.from_env()

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.inner_app(scope, receive, send)
            return

        headers = list(scope.get("headers", []))
        authorization = next(
            (
                value.decode("latin-1")
                for name, value in headers
                if name.lower() == b"authorization"
            ),
            "",
        )

        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
            verified, reason = self.verifier.verify(token)
            if verified:
                local_key = (os.environ.get("BRAIN_API_KEY") or "").strip()
                if not local_key:
                    response = JSONResponse(
                        status_code=503,
                        content={"detail": "brain_local_api_key_not_configured"},
                    )
                    await response(scope, receive, send)
                    return

                blocked = {b"authorization", b"x-api-key", b"x-brain-api-key"}
                scope = dict(scope)
                scope["headers"] = [
                    (name, value) for name, value in headers if name.lower() not in blocked
                ] + [(b"x-brain-api-key", local_key.encode("utf-8"))]
            elif reason != "vercel_oidc_not_configured":
                _logger.info("vercel_oidc_auth_rejected reason=%s", reason)

        await self.inner_app(scope, receive, send)


# Uvicorn imports this module-level name. Cockpit routes remain registered on the
# original FastAPI object above; only the Railway entrypoint is wrapped.
app = VercelOidcAuthBridge(app)
