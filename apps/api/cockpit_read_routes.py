"""Cockpit read-model routes for the canonical Brain API image.

These GET routes project existing durable Brain state for operator interfaces.
They do not introduce a second cognitive store or change write semantics.

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

_LEARNING_EVENT_TYPES = {
    "learning.attribution_recorded",
    "graph.edge_rewired",
    "prediction.resolved",
    "outcome.recorded",
    "belief.created",
    "belief.updated",
    "memory.working_stored",
    "memory.working_evicted",
    "attention.scored",
    "cycle.completed",
    "dream.night_phase",
}


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


def _event_store(api_module: Any) -> Any:
    """Resolve the canonical durable event store behind the active runtime."""
    store = api_module.runtime.store
    candidate = getattr(store, "event_store", None)
    if candidate is not None and (
        hasattr(candidate, "read_recent") or hasattr(candidate, "read_all")
    ):
        return candidate
    return store


def _read_events(
    api_module: Any,
    *,
    event_types: set[str],
    limit: int,
) -> list[Any]:
    """Return a bounded newest-first event slice for cockpit projections.

    Production Postgres uses ``read_recent`` so each event type walks the
    ``brain_events_type_idx`` index backward and stops at a finite limit. This
    avoids the historical `/signals` full-ledger sort that exhausted PostgreSQL
    temporary disk. Small in-memory/test stores retain a safe fallback.
    """
    if limit <= 0 or not event_types:
        return []
    store = _event_store(api_module)
    recent = getattr(store, "read_recent", None)
    if callable(recent):
        return list(recent(event_types=event_types, limit=limit))

    reader = getattr(store, "read_all", None)
    if not callable(reader):
        return []
    events = [
        event
        for event in reader()
        if getattr(event, "event_type", None) in event_types
    ]
    events.sort(
        key=lambda event: (getattr(event, "occurred_at", datetime.min.replace(tzinfo=UTC)), str(getattr(event, "id", ""))),
        reverse=True,
    )
    return events[:limit]


def _refresh_projection(api_module: Any) -> None:
    refresh = getattr(api_module, "_refresh_reads", None)
    if callable(refresh):
        refresh()


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
        "evidence_ids": [str(value) for value in getattr(edge, "evidence_ids", set())],
        "created_at": _iso(updated_at),
        "updated_at": _iso(updated_at),
    }


def _outcome_item_from_event(event: Any) -> dict[str, Any]:
    payload = dict(getattr(event, "payload", {}) or {})
    occurred_at = getattr(event, "occurred_at", None)
    return {
        "id": str(getattr(event, "aggregate_id")),
        "created_at": _iso(occurred_at),
        "updated_at": _iso(occurred_at),
        "action_id": str(payload.get("action_id") or ""),
        "value_created": _number(payload, "value_created"),
        "prediction_accuracy": _number(payload, "prediction_accuracy"),
        "operator_time_cost": _number(payload, "operator_time_cost"),
        "trust_impact": _number(payload, "trust_impact"),
        "legal_risk": _number(payload, "legal_risk"),
        "prediction_id": str(payload["prediction_id"]) if payload.get("prediction_id") else None,
        "metadata": {
            "edge_ids": [str(value) for value in payload.get("edge_ids", []) or []],
            "source_keys": [str(value) for value in payload.get("source_keys", []) or []],
            "correlation_id": str(getattr(event, "correlation_id", "") or "") or None,
        },
    }


def _learning_event_item(event: Any) -> dict[str, Any]:
    return {
        "id": str(getattr(event, "id")),
        "event_type": str(getattr(event, "event_type", "unknown")),
        "aggregate_type": str(getattr(event, "aggregate_type", "unknown")),
        "aggregate_id": str(getattr(event, "aggregate_id", "")),
        "occurred_at": _iso(getattr(event, "occurred_at", None)),
        "correlation_id": str(getattr(event, "correlation_id", "") or "") or None,
        "payload": dict(getattr(event, "payload", {}) or {}),
    }


def register_cockpit_read_routes(app: Any, *, api_module: Any) -> None:
    """Register the cockpit read model on the canonical FastAPI app."""

    @app.get("/signals")
    def list_signals():
        """Read the latest durable signals without a full-ledger scan."""
        items = [
            _signal_item_from_event(event)
            for event in _read_events(
                api_module,
                event_types={"signal.enqueued"},
                limit=500,
            )
        ]
        return _list_response(items)

    @app.get("/evidence")
    def list_evidence():
        """Expose persisted evidence and its real belief relationships."""
        _refresh_projection(api_module)
        store = api_module.runtime.store
        relationships: dict[str, dict[str, Any]] = {}
        for belief in store.beliefs.values():
            for evidence_id in getattr(belief, "supporting_evidence", set()):
                entry = relationships.setdefault(str(evidence_id), {"supports": set(), "contradicts": set()})
                entry["supports"].add(str(belief.id))
            for evidence_id in getattr(belief, "contradicting_evidence", set()):
                entry = relationships.setdefault(str(evidence_id), {"supports": set(), "contradicts": set()})
                entry["contradicts"].add(str(belief.id))

        items: list[dict[str, Any]] = []
        for evidence in store.evidence.values():
            relation = relationships.get(str(evidence.id), {"supports": set(), "contradicts": set()})
            supporting = sorted(relation["supports"])
            contradicting = sorted(relation["contradicts"])
            supports: bool | None = None
            if supporting and not contradicting:
                supports = True
            elif contradicting and not supporting:
                supports = False
            items.append(
                {
                    "id": str(evidence.id),
                    "created_at": _iso(getattr(evidence, "created_at", None)),
                    "updated_at": _iso(getattr(evidence, "created_at", None)),
                    "claim": str(getattr(evidence, "claim", "")),
                    "source_id": str(getattr(evidence, "source_id", "unknown")),
                    "reliability": float(getattr(evidence, "reliability", 0.0) or 0.0),
                    "observation_id": str(evidence.observation_id) if getattr(evidence, "observation_id", None) else None,
                    "supports": supports,
                    "belief_ids": sorted(set(supporting + contradicting)),
                    "metadata": {
                        **dict(getattr(evidence, "metadata", {}) or {}),
                        "supporting_belief_ids": supporting,
                        "contradicting_belief_ids": contradicting,
                    },
                }
            )
        items.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
        return _list_response(items)

    @app.get("/edges")
    def list_edges():
        """Read graph edges from the configured learning edge store."""
        edge_store = api_module.learning.edges or api_module._learning_store
        items = [_edge_item(edge) for edge in edge_store.list_edges()]
        return _list_response(items)

    @app.get("/contradictions")
    def list_contradictions():
        """Live contradiction read model derived from contested beliefs."""
        _refresh_projection(api_module)
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
        _refresh_projection(api_module)
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
        _refresh_projection(api_module)
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

    @app.get("/outcomes")
    def list_outcomes():
        """Project recent real outcome.recorded events into the Outcome contract."""
        items = [
            _outcome_item_from_event(event)
            for event in _read_events(
                api_module,
                event_types={"outcome.recorded"},
                limit=200,
            )
        ]
        return _list_response(items)

    @app.get("/learning-events")
    def list_learning_events():
        """Expose bounded durable cognitive evolution history used by the UI."""
        items = [
            _learning_event_item(event)
            for event in _read_events(
                api_module,
                event_types=_LEARNING_EVENT_TYPES,
                limit=200,
            )
        ]
        return _list_response(items)

    @app.get("/working-memory")
    def get_working_memory():
        """Report the latest durable observation of active working-memory size.

        This is an observation from completed cognition, not a claim that the API
        process owns the worker's in-memory buffer. Capacity is taken only from a
        real memory.working_stored event when available.
        """
        events = _read_events(
            api_module,
            event_types={"cycle.completed", "memory.working_stored"},
            limit=50,
        )
        completed = next(
            (event for event in events if getattr(event, "event_type", None) == "cycle.completed"),
            None,
        )
        stored = next(
            (event for event in events if getattr(event, "event_type", None) == "memory.working_stored"),
            None,
        )
        if completed is None:
            return {
                "observed_at": None,
                "size": None,
                "capacity": None,
                "cycle_id": None,
                "source": "unobserved",
                "evicted_count": 0,
                "last_slot_id": None,
            }
        payload = dict(getattr(completed, "payload", {}) or {})
        stored_payload = dict(getattr(stored, "payload", {}) or {}) if stored is not None else {}
        return {
            "observed_at": _iso(getattr(completed, "occurred_at", None)),
            "size": int(payload["working_memory_size"]) if payload.get("working_memory_size") is not None else None,
            "capacity": int(stored_payload["capacity"]) if stored_payload.get("capacity") is not None else None,
            "cycle_id": str(getattr(completed, "correlation_id", "") or getattr(completed, "aggregate_id", "") or "") or None,
            "source": "cycle.completed",
            "evicted_count": int(payload.get("evicted_count") or 0),
            "last_slot_id": str(stored_payload.get("slot_id") or "") or None,
        }

    # Surfaces the Observatory queries but the runtime does not yet populate.
    # They answer with an empty collection rather than 404 so the cockpit can
    # render its real empty state instead of an error.
    @app.get("/approvals")
    def list_approvals():
        return _list_response([])

    @app.get("/opportunities")
    def list_opportunities():
        return _list_response([])

    @app.get("/formula-runs")
    def list_formula_runs():
        return _list_response([])

    @app.get("/acceptance-reports")
    def list_acceptance_reports():
        return _list_response([])
