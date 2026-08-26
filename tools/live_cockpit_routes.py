from __future__ import annotations

from datetime import UTC, datetime
import logging
import os
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi.responses import JSONResponse

import apps.api.tenant_app as tenant_api
from brain.attention import AttentionMarket, AttentionSignal
from brain.tenant_auth import TenantRole
from brain.tenant_context import TenantScopeViolation, trusted_tenant_context
from brain.tenant_runtime import tenant_context_scope
from tools.vercel_oidc import VercelOidcVerifier

# Railway's cockpit compatibility surface is registered on the same tenant-aware
# FastAPI object used by the canonical production API. This preserves the live
# read-model routes while ensuring forced-RLS startup and request membership
# checks cannot be bypassed by the compatibility entrypoint.
brain_api = tenant_api.base
app = tenant_api.app
runtime = brain_api.runtime
_learning_store = brain_api._learning_store

_logger = logging.getLogger(__name__)
_attention_market = AttentionMarket()

# This identifier is inert unless the explicit Observatory compatibility release
# SQL has created the tenant + durable membership. Canonical migrations 019-022
# deliberately leave pre-tenant NULL ownership quarantined.
_DEFAULT_OBSERVATORY_TENANT_ID = UUID("7d4427c4-8b8d-4f4a-9f75-b46cedc2f126")
_OBSERVATORY_ACTOR_ID = "brain-observatory-bff"


def _observatory_identity_context():
    raw = (os.environ.get("BRAIN_OBSERVATORY_TENANT_ID") or "").strip()
    try:
        tenant_id = UUID(raw) if raw else _DEFAULT_OBSERVATORY_TENANT_ID
    except ValueError:
        return None
    return trusted_tenant_context(
        tenant_id=tenant_id,
        actor_id=_OBSERVATORY_ACTOR_ID,
        roles=(),
    )


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


def _edge_item(edge: Any) -> dict[str, Any]:
    updated_at = getattr(edge, "updated_at", None)
    return {
        "id": str(edge.id),
        "source": str(edge.source),
        "target": str(edge.target),
        "source_node_id": str(edge.source),
        "target_node_id": str(edge.target),
        "relation": str(edge.relation),
        "weight": float(edge.weight),
        "confidence": float(edge.confidence),
        "created_at": _iso(updated_at),
        "updated_at": _iso(updated_at),
    }


@app.get("/signals")
def list_signals():
    """Read signals from the canonical durable signal.enqueued event stream."""
    items = [
        _signal_item_from_event(event)
        for event in runtime.store.read_all()
        if getattr(event, "event_type", None) == "signal.enqueued"
    ]
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return _list_response(items)


@app.get("/edges")
def list_edges():
    """Read graph edges from the configured learning edge store.

    Production resolves ``brain_api.learning.edges`` to ``PostgresEdgeStore`` so
    this reads ``public.graph_edges`` durably. Local/test mode uses the matching
    in-memory store implementation. The existing POST /edges contract is owned by
    apps.api.main and remains unchanged.
    """
    edge_store = brain_api.learning.edges or brain_api._learning_store
    items = [_edge_item(edge) for edge in edge_store.list_edges()]
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
    """Railway deployment-identity bridge with durable tenant membership.

    A verified Vercel deployment token is exchanged for the local API key and
    bound to a server-owned tenant/actor identity. The actor's role is resolved
    from tenant_memberships before the request runs. Neither API key, tenant, role,
    nor service context is accepted from untrusted request headers through this
    bridge. Canonical legacy ownership remains quarantined until the separate
    Observatory compatibility release action has been explicitly applied.
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

                identity_context = _observatory_identity_context()
                if identity_context is None:
                    response = JSONResponse(
                        status_code=503,
                        content={"detail": "brain_observatory_tenant_invalid"},
                    )
                    await response(scope, receive, send)
                    return
                if tenant_api._membership_resolver is None:
                    response = JSONResponse(
                        status_code=503,
                        content={"detail": "tenant_membership_store_unavailable"},
                    )
                    await response(scope, receive, send)
                    return

                try:
                    context = tenant_api._membership_resolver.resolve(identity_context)
                    if str(scope.get("method", "GET")).upper() not in {
                        "GET",
                        "HEAD",
                        "OPTIONS",
                    }:
                        context.require_role(
                            TenantRole.OWNER,
                            TenantRole.ADMIN,
                            TenantRole.OPERATOR,
                        )
                except TenantScopeViolation:
                    response = JSONResponse(
                        status_code=403,
                        content={"detail": "brain_observatory_membership_or_role_required"},
                    )
                    await response(scope, receive, send)
                    return
                except Exception:
                    response = JSONResponse(
                        status_code=503,
                        content={"detail": "tenant_membership_lookup_failed"},
                    )
                    await response(scope, receive, send)
                    return

                blocked = {
                    b"authorization",
                    b"x-api-key",
                    b"x-brain-api-key",
                    b"x-brain-tenant-id",
                    b"x-brain-actor-id",
                    b"x-brain-tenant-timestamp",
                    b"x-brain-tenant-signature",
                    b"x-brain-roles",
                    b"x-brain-service-context",
                }
                scope = dict(scope)
                scope["headers"] = [
                    (name, value) for name, value in headers if name.lower() not in blocked
                ] + [(b"x-brain-api-key", local_key.encode("utf-8"))]

                with tenant_context_scope(context):
                    await self.inner_app(scope, receive, send)
                return
            if reason != "vercel_oidc_not_configured":
                _logger.info("vercel_oidc_auth_rejected reason=%s", reason)

        await self.inner_app(scope, receive, send)


# Uvicorn imports this module-level name. Cockpit routes remain registered on the
# tenant-aware FastAPI object above; only the Railway entrypoint is wrapped.
app = VercelOidcAuthBridge(app)
