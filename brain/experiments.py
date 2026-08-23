from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from .events import BrainEvent
from .projections import ProjectionEngine


@dataclass(slots=True)
class CognitiveExperiment:
    name: str
    policy_name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ExperimentResult:
    experiment_id: UUID
    score: float
    metrics: dict[str, float]
    final_state: dict[str, Any]


class ExperimentHarness:
    """Replay the same cognitive history under alternate policies and compare outcomes."""

    def run(
        self,
        experiment: CognitiveExperiment,
        events: list[BrainEvent],
        projection: ProjectionEngine,
        evaluator: Callable[[dict], tuple[float, dict[str, float]]],
    ) -> ExperimentResult:
        state = projection.replay(events)
        score, metrics = evaluator(state)
        return ExperimentResult(experiment.id, score, metrics, state)
