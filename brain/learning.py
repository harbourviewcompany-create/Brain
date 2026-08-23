from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from .attribution import LearningResult, OutcomeAttribution
from .domain import Edge, Outcome, utcnow
from .events import BrainEvent
from .prediction import Prediction, PredictionEngine, PredictionStatus


class EventAppender(Protocol):
    def append(self, event: BrainEvent) -> None: ...


class PredictionRepository(Protocol):
    def save(self, prediction: Prediction) -> None: ...
    def get(self, prediction_id: UUID) -> Prediction | None: ...


class EdgeRepository(Protocol):
    def get_edge(self, edge_id: UUID) -> Edge | None: ...
    def upsert_edge(self, edge: Edge) -> None: ...
    def delete_edge(self, edge_id: UUID) -> None: ...


class AttributionRepository(Protocol):
    def save_attribution(self, result: LearningResult) -> None: ...


class SourceRepository(Protocol):
    def apply_reliability_delta(self, source_key: str, delta: float) -> None: ...


def _prediction_payload(prediction: Prediction) -> dict[str, Any]:
    return {
        "statement": prediction.statement,
        "expected_value": prediction.expected_value,
        "confidence": prediction.confidence,
        "horizon_seconds": int(prediction.horizon.total_seconds()),
        "belief_id": str(prediction.belief_id) if prediction.belief_id else None,
        "action_id": str(prediction.action_id) if prediction.action_id else None,
        "edge_ids": [str(e) for e in prediction.edge_ids],
        "source_keys": list(prediction.source_keys),
        "status": str(prediction.status),
        "resolve_by": prediction.resolve_by.isoformat() if prediction.resolve_by else None,
        "resolved_at": prediction.resolved_at.isoformat() if prediction.resolved_at else None,
        "metadata": dict(prediction.metadata),
    }


class LearningService:
    """Orchestrates prediction lifecycle, outcome attribution, ledger events, and persistence."""

    def __init__(
        self,
        event_store: EventAppender,
        *,
        predictions: PredictionRepository | None = None,
        edges: EdgeRepository | None = None,
        attributions: AttributionRepository | None = None,
        sources: SourceRepository | None = None,
        attribution_engine: OutcomeAttribution | None = None,
        prediction_engine: PredictionEngine | None = None,
    ) -> None:
        self.event_store = event_store
        self.predictions = predictions
        self.edges = edges
        self.attributions = attributions
        self.sources = sources
        self.attribution_engine = attribution_engine or OutcomeAttribution()
        self.prediction_engine = prediction_engine or PredictionEngine()

    def create_prediction(self, prediction: Prediction) -> Prediction:
        if self.predictions is not None:
            self.predictions.save(prediction)
        self.event_store.append(
            BrainEvent("prediction.created", "prediction", prediction.id, _prediction_payload(prediction))
        )
        return prediction

    def record_outcome(
        self,
        outcome: Outcome,
        *,
        edge_ids: list[UUID] | None = None,
        prediction_id: UUID | None = None,
        source_keys: list[str] | None = None,
        evidence_id: UUID | None = None,
    ) -> LearningResult:
        resolved_prediction: Prediction | None = None
        pid = prediction_id or outcome.prediction_id
        if pid is not None and self.predictions is not None:
            resolved_prediction = self.predictions.get(pid)
            if resolved_prediction is None:
                raise KeyError(f"prediction_not_found:{pid}")
            if resolved_prediction.status is not PredictionStatus.OPEN:
                raise ValueError(f"prediction_not_open:{pid}")

        ids = list(edge_ids or outcome.edge_ids or [])
        if resolved_prediction is not None:
            for eid in resolved_prediction.edge_ids:
                if eid not in ids:
                    ids.append(eid)

        edge_objs: list[Edge] = []
        if self.edges is not None:
            for eid in ids:
                edge = self.edges.get_edge(eid)
                if edge is not None:
                    edge_objs.append(edge)

        result = self.attribution_engine.attribute(
            outcome,
            edges=edge_objs,
            prediction=resolved_prediction,
            source_keys=source_keys or outcome.source_keys or None,
            evidence_id=evidence_id,
        )

        if result.resolution is not None and self.predictions is not None:
            self.predictions.save(result.resolution.prediction)

        if self.edges is not None:
            for edge in result.updated_edges:
                self.edges.upsert_edge(edge)
            for pruned_id in result.pruned_edge_ids:
                self.edges.delete_edge(pruned_id)

        if self.attributions is not None:
            self.attributions.save_attribution(result)

        if self.sources is not None:
            for key, delta in result.attribution.source_deltas.items():
                self.sources.apply_reliability_delta(key, delta)

        self._emit_learning_events(outcome, result)
        return result

    def expire_due_predictions(self, *, now=None) -> list[Prediction]:
        """Mark open predictions past resolve_by as expired; emit events and persist."""
        now = now or utcnow()
        expired: list[Prediction] = []
        if self.predictions is None or not hasattr(self.predictions, "list_open"):
            return expired
        for pred in self.predictions.list_open():  # type: ignore[attr-defined]
            updated = self.prediction_engine.expire(pred, now=now)
            if updated.status is PredictionStatus.EXPIRED and pred.status is PredictionStatus.OPEN:
                self.predictions.save(updated)
                self.event_store.append(
                    BrainEvent(
                        "prediction.expired",
                        "prediction",
                        updated.id,
                        _prediction_payload(updated),
                    )
                )
                expired.append(updated)
        return expired

    def _emit_learning_events(self, outcome: Outcome, result: LearningResult) -> None:
        self.event_store.append(
            BrainEvent(
                "outcome.recorded",
                "outcome",
                outcome.id,
                {
                    "action_id": str(outcome.action_id),
                    "value_created": outcome.value_created,
                    "operator_time_cost": outcome.operator_time_cost,
                    "prediction_accuracy": outcome.prediction_accuracy,
                    "trust_impact": outcome.trust_impact,
                    "legal_risk": outcome.legal_risk,
                    "prediction_id": str(outcome.prediction_id) if outcome.prediction_id else None,
                    "edge_ids": [str(e) for e in outcome.edge_ids],
                    "source_keys": list(outcome.source_keys),
                },
            )
        )

        if result.resolution is not None:
            pred = result.resolution.prediction
            self.event_store.append(
                BrainEvent(
                    "prediction.resolved",
                    "prediction",
                    pred.id,
                    {
                        **_prediction_payload(pred),
                        "error": result.resolution.error,
                        "signed_error": result.resolution.signed_error,
                        "reward_signal": result.resolution.reward_signal,
                        "outcome_id": str(outcome.id),
                    },
                )
            )

        for event in result.rewire_events:
            self.event_store.append(
                BrainEvent(
                    "graph.edge_rewired",
                    "edge",
                    event.target_id,
                    {
                        "operation": str(event.operation),
                        "reason": event.reason,
                        "previous": event.previous,
                        "current": event.current,
                        "evidence_ids": [str(e) for e in event.evidence_ids],
                        "rewire_event_id": str(event.id),
                    },
                )
            )

        attr = result.attribution
        self.event_store.append(
            BrainEvent(
                "learning.attribution_recorded",
                "attribution",
                attr.id,
                {
                    "outcome_id": str(attr.outcome_id),
                    "prediction_id": str(attr.prediction_id) if attr.prediction_id else None,
                    "edge_ids": [str(e) for e in attr.edge_ids],
                    "source_keys": list(attr.source_keys),
                    "reward_score": attr.reward_score,
                    "prediction_error": attr.prediction_error,
                    "edge_deltas": dict(attr.edge_deltas),
                    "source_deltas": dict(attr.source_deltas),
                    "rationale": list(attr.rationale),
                    "pruned_edge_ids": [str(e) for e in result.pruned_edge_ids],
                },
            )
        )
