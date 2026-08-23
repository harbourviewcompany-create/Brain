from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from .domain import Edge, Outcome, RewireEvent, utcnow
from .prediction import Prediction, PredictionEngine, PredictionResolution
from .reward import RewardSystem
from .rewiring import RewiringEngine


@dataclass(slots=True)
class AttributionRecord:
    """Links an outcome back to the edges / sources / prediction that caused it."""

    outcome_id: UUID
    prediction_id: UUID | None
    edge_ids: list[UUID]
    source_keys: list[str]
    reward_score: float
    prediction_error: float
    edge_deltas: dict[str, float] = field(default_factory=dict)
    source_deltas: dict[str, float] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: Any = field(default_factory=utcnow)
    rationale: list[str] = field(default_factory=list)


@dataclass(slots=True)
class LearningResult:
    attribution: AttributionRecord
    resolution: PredictionResolution | None
    updated_edges: list[Edge]
    rewire_events: list[RewireEvent]
    pruned_edge_ids: list[UUID]


class OutcomeAttribution:
    """Close the learning loop: Outcome → score → edge rewiring with provenance.

    Every major graph weight change cites the outcome (and optional prediction).
    Positive reward reinforces cited edges; negative reward weakens them.
    """

    def __init__(
        self,
        *,
        reward: RewardSystem | None = None,
        rewiring: RewiringEngine | None = None,
        predictions: PredictionEngine | None = None,
        edge_learn_rate: float = 0.08,
    ) -> None:
        self.reward = reward or RewardSystem()
        self.rewiring = rewiring or RewiringEngine()
        self.predictions = predictions or PredictionEngine()
        self.edge_learn_rate = edge_learn_rate

    def attribute(
        self,
        outcome: Outcome,
        *,
        edges: list[Edge],
        prediction: Prediction | None = None,
        source_keys: list[str] | None = None,
        evidence_id: UUID | None = None,
    ) -> LearningResult:
        resolution: PredictionResolution | None = None
        prediction_error = 0.0
        reward_score = self.reward.score(outcome)

        if prediction is not None:
            resolution = self.predictions.resolve(prediction, outcome)
            prediction_error = resolution.error
            reward_score = 0.7 * reward_score + 0.3 * resolution.reward_signal

        edge_ids = [e.id for e in edges]
        if prediction is not None:
            for eid in prediction.edge_ids:
                if eid not in edge_ids:
                    edge_ids.append(eid)
            sources = list(dict.fromkeys([*(source_keys or []), *prediction.source_keys]))
        else:
            sources = list(source_keys or [])

        amount = min(self.edge_learn_rate, abs(reward_score) * self.edge_learn_rate)
        updated_edges: list[Edge] = []
        rewire_events: list[RewireEvent] = []
        pruned: list[UUID] = []
        edge_deltas: dict[str, float] = {}

        edge_map = {e.id: e for e in edges}

        for edge_id in edge_ids:
            edge = edge_map.get(edge_id)
            if edge is None:
                continue
            prev = edge.weight
            if reward_score >= 0:
                eid = evidence_id or outcome.id
                new_edge, event = self.rewiring.reinforce(edge, eid, amount)
                event = RewireEvent(
                    operation=event.operation,
                    reason=f"Outcome attribution reinforced pathway (reward={reward_score:.3f}).",
                    target_id=event.target_id,
                    previous=event.previous,
                    current=event.current,
                    evidence_ids=list(event.evidence_ids) + ([outcome.id]),
                )
                updated_edges.append(new_edge)
                rewire_events.append(event)
                edge_deltas[str(edge_id)] = new_edge.weight - prev
            else:
                new_edge, event = self.rewiring.weaken(edge, amount)
                event = RewireEvent(
                    operation=event.operation,
                    reason=f"Outcome attribution weakened pathway (reward={reward_score:.3f}).",
                    target_id=event.target_id,
                    previous=event.previous,
                    current=event.current,
                    evidence_ids=[outcome.id],
                )
                rewire_events.append(event)
                if new_edge is None:
                    pruned.append(edge_id)
                    edge_deltas[str(edge_id)] = -prev
                else:
                    updated_edges.append(new_edge)
                    edge_deltas[str(edge_id)] = new_edge.weight - prev

        source_deltas: dict[str, float] = {}
        source_step = max(-0.05, min(0.05, reward_score * 0.05))
        for key in sources:
            source_deltas[key] = source_step

        rationale = [
            f"reward_score={reward_score:.4f}",
            f"prediction_error={prediction_error:.4f}",
            f"edges_touched={len(edge_deltas)}",
            f"sources_touched={len(source_deltas)}",
        ]
        if resolution is not None:
            rationale.append(f"signed_prediction_error={resolution.signed_error:.4f}")

        attribution = AttributionRecord(
            outcome_id=outcome.id,
            prediction_id=prediction.id if prediction else None,
            edge_ids=list(edge_ids),
            source_keys=sources,
            reward_score=reward_score,
            prediction_error=prediction_error,
            edge_deltas=edge_deltas,
            source_deltas=source_deltas,
            rationale=rationale,
        )
        return LearningResult(
            attribution=attribution,
            resolution=resolution,
            updated_edges=updated_edges,
            rewire_events=rewire_events,
            pruned_edge_ids=pruned,
        )
