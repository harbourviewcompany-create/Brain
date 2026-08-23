from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from apps.api.main import app, runtime, _learning_store


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


@app.get("/signals")
def list_signals():
    """Live attention-market read model derived from stored evidence.

    The Brain does not yet have a dedicated persistent Signal service. This
    endpoint exposes real evidence as live attention signals instead of returning
    cockpit fixture data.
    """
    items: list[dict[str, Any]] = []
    for evidence in runtime.store.evidence.values():
        reliability = float(getattr(evidence, "reliability", 0.5) or 0.5)
        metadata = getattr(evidence, "metadata", {}) or {}
        items.append(
            {
                "id": _stable_uuid("signal", str(evidence.id)),
                "created_at": _iso(getattr(evidence, "created_at", None)),
                "updated_at": _iso(getattr(evidence, "created_at", None)),
                "source_id": str(evidence.source_id),
                "evidence_ids": [str(evidence.id)],
                "novelty": reliability,
                "urgency": float(metadata.get("urgency", 0.0) or 0.0),
                "commercial_upside": float(metadata.get("commercial_upside", 0.0) or 0.0),
                "attention_score": reliability,
                "formula_run_id": None,
            }
        )
    items.sort(key=lambda item: item["attention_score"], reverse=True)
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
