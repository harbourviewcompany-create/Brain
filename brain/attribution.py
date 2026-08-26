from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from .domain import Edge, Outcome, RewireEvent, utcnow
from .generalization import GeneralizationEngine
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
    generalized_edge_ids: list[str] = field(default_factory=list)


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
        generalization: GeneralizationEngine | None = None,
        edge_learn_rate: float = 0.08,
        min_learn_rate: float = 0.02,
        max_learn_rate: float = 0.24,
        volatility_window: int = 20,
    ) -> None:
        self.reward = reward or RewardSystem()
        self.rewiring = rewiring or RewiringEngine()
        self.predictions = predictions or PredictionEngine()
        self.generalization = generalization or GeneralizationEngine()
        # Meta-plasticity: base_edge_learn_rate is the rate absent any error
        # history; effective_edge_learn_rate below scales it by how volatile
        # recent prediction error has actually been. This mirrors why
        # acetylcholine already gates learning_weight in CognitiveScheduler
        # (Yu & Dayan-style expected/unexpected uncertainty) -- a brain
        # that's been consistently right should stop moving its weights so
        # hard on every new data point; one that's been consistently
        # surprised should move them faster, not at a rate fixed forever.
        self.base_edge_learn_rate = edge_learn_rate
        self.min_learn_rate = min_learn_rate
        self.max_learn_rate = max_learn_rate
        self._recent_errors: deque[float] = deque(maxlen=volatility_window)

    @property
    def edge_learn_rate(self) -> float:
        """Backward-compatible alias -- existing callers that read
        .edge_learn_rate directly still see a sane value."""
        return self.effective_edge_learn_rate

    @property
    def effective_edge_learn_rate(self) -> float:
        if len(self._recent_errors) < 2:
            return self.base_edge_learn_rate
        volatility = statistics.pstdev(self._recent_errors)
        scaled = self.base_edge_learn_rate * (1.0 + 3.0 * volatility)
        return max(self.min_learn_rate, min(self.max_learn_rate, scaled))

    def attribute(
        self,
        outcome: Outcome,
        *,
        edges: list[Edge],
        prediction: Prediction | None = None,
        source_keys: list[str] | None = None,
        evidence_id: UUID | None = None,
        candidate_edges: list[Edge] | None = None,
    ) -> LearningResult:
        resolution: PredictionResolution | None = None
        prediction_error = 0.0
        reward_score = self.reward.score(outcome)

        # Meta-plasticity rate for *this* update is drawn from error history
        # *prior* to this outcome -- using this outcome's own error to set
        # its own rate would be circular. The new error (if any) is folded
        # in afterward, below, so it's available for the next call.
        effective_rate = self.effective_edge_learn_rate

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

        amount = min(effective_rate, abs(reward_score) * effective_rate)
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

        # Generalization: partial transfer to structurally similar edges
        # that weren't themselves cited by this prediction/outcome. Only
        # runs when the caller actually supplies a candidate pool -- no
        # pool, no propagation, fully backward compatible.
        generalized_edge_ids: list[str] = []
        if candidate_edges:
            already_touched = set(edge_ids)
            eid = evidence_id or outcome.id
            for edge_id in edge_ids:
                delta = edge_deltas.get(str(edge_id))
                edge = edge_map.get(edge_id)
                if edge is None or delta is None or abs(delta) < 1e-9:
                    continue
                gen_result = self.generalization.propagate(
                    edge, delta, candidate_edges, self.rewiring, eid, exclude_ids=already_touched
                )
                updated_edges.extend(gen_result.updated_edges)
                rewire_events.extend(gen_result.rewire_events)
                pruned.extend(gen_result.pruned_edge_ids)
                for key, gen_delta in gen_result.edge_deltas.items():
                    edge_deltas[key] = edge_deltas.get(key, 0.0) + gen_delta
                    generalized_edge_ids.append(key)
                already_touched.update(e.id for e in gen_result.updated_edges)
                already_touched.update(gen_result.pruned_edge_ids)

        source_deltas: dict[str, float] = {}
        source_step = max(-0.05, min(0.05, reward_score * 0.05))
        for key in sources:
            source_deltas[key] = source_step

        rationale = [
            f"reward_score={reward_score:.4f}",
            f"prediction_error={prediction_error:.4f}",
            f"edges_touched={len(edge_deltas)}",
            f"sources_touched={len(source_deltas)}",
            f"effective_edge_learn_rate={effective_rate:.4f}",
        ]
        if resolution is not None:
            rationale.append(f"signed_prediction_error={resolution.signed_error:.4f}")
        if generalized_edge_ids:
            rationale.append(f"generalized_to={len(set(generalized_edge_ids))}_edges")

        # Fold this outcome's error into volatility history *after* using
        # the prior history to set this update's rate.
        if resolution is not None:
            self._recent_errors.append(abs(resolution.signed_error))

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
            generalized_edge_ids=sorted(set(generalized_edge_ids)),
        )
