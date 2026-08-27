"""Cockpit read-model routes for the canonical Brain API image.

These GET routes previously existed only in ``tools/live_cockpit_routes.py``,
which is served by ``Dockerfile.railway`` -- the image its own first line calls
the "Legacy Railway cockpit compatibility image". The repository default
(``railway.toml``) and both Docker CI jobs build ``Dockerfile`` instead, which
runs ``apps.api.tenant_app`` over ``apps/api/main.py`` and registered none of
them. The Observatory's client calls all nine, so CI was proving out an image
the cockpit would 404 against while the deprecated image carried the real read
surface.

Registering them here puts one route set behind one canonical image.

``api_module`` attributes are resolved per request rather than captured at
import time, because ``apps.api.tenant_app`` rebinds ``runtime``, ``learning``
and ``_learning_store`` to tenant-scoped proxies after this module is imported.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from brain.attention import AttentionMarket, AttentionSignal

_attention_market = AttentionMarket()


def _list_response(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"items": items, "total": len(items), "source": "api"}


def _iso(value: Any | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _stable_uuid(namespace: str, key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"brain:{namespace}:{key}"))


def _number(payload: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(payload.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _signal_item_from_event(event: Any) -> dict[str, Any]:
    """Build the cockpit Signal shape from a durable signal.enqueued event."""
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


def register_cockpit_read_routes(app: Any, *, api_module: Any) -> None:
    """Register the cockpit read model on the canonical FastAPI app."""

    @app.get("/signals")
    def list_signals():
        """Read signals from the canonical durable signal.enqueued event stream."""
        items = [
            _signal_item_from_event(event)
            for event in api_module.runtime.store.read_all()
            if getattr(event, "event_type", None) == "signal.enqueued"
        ]
        items.sort(key=lambda item: item["created_at"], reverse=True)
        return _list_response(items)

    @app.get("/edges")
    def list_edges():
        """Read graph edges from the configured learning edge store.

        Production resolves ``learning.edges`` to ``PostgresEdgeStore`` so this
        reads ``public.graph_edges`` durably. Local and test mode use the
        matching in-memory implementation. The POST /edges contract is owned by
        apps.api.main and is unchanged.
        """
        edge_store = api_module.learning.edges or api_module._learning_store
        items = [_edge_item(edge) for edge in edge_store.list_edges()]
        return _list_response(items)

    @app.get("/contradictions")
    def list_contradictions():
        """Live contradiction read model derived from contested beliefs."""
        items: list[dict[str, Any]] = []
        for belief in api_module.runtime.store.beliefs.values():
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
        for belief in api_module.runtime.store.beliefs.values():
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
        source_ids = {str(e.source_id) for e in api_module.runtime.store.evidence.values()}
        source_scores = getattr(api_module._learning_store, "source_scores", {}) or {}
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

    # Surfaces the Observatory queries but the runtime does not yet populate.
    # They answer with an empty collection rather than 404 so the cockpit can
    # render its real empty state instead of an error.
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
