"""Hooks that close the learning loop inside CognitiveCycle without API-only calls.

On cognitive_task.selected → create an open Prediction bound to the task/action.
When a capital/revenue result arrives on a later stimulus → record Outcome and
attribute through LearningService (edge rewiring + ledger events).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from .domain import Outcome
from .learning import LearningService
from .prediction import Prediction, PredictionEngine
from .scheduler import CognitiveTask


def prediction_for_task(
    task: CognitiveTask,
    *,
    belief_id: UUID | None,
    cycle_id: UUID,
    source_id: str,
    horizon: timedelta | None = None,
    engine: PredictionEngine | None = None,
) -> Prediction:
    """Build a forecast that this selected task will create positive value."""
    engine = engine or PredictionEngine()
    expected = float(max(0.0, min(1.0, task.utility)))
    confidence = float(max(0.05, min(0.95, 0.4 + 0.5 * task.utility)))
    return engine.create(
        f"Task {task.name} yields value",
        expected_value=expected,
        confidence=confidence,
        horizon=horizon or timedelta(hours=24),
        belief_id=belief_id,
        action_id=task.id,
        source_keys=[source_id] if source_id else [],
        metadata={
            "task_name": task.name,
            "cycle_id": str(cycle_id),
            "payload": dict(task.payload),
            "auto": True,
        },
    )


def emit_predictions_for_selected_tasks(
    learning: LearningService,
    selected: list[CognitiveTask],
    *,
    belief_id: UUID | None,
    cycle_id: UUID,
    source_id: str,
    engine: PredictionEngine | None = None,
) -> dict[UUID, UUID]:
    """Create and persist a prediction per selected task.

    Returns mapping action_id (task.id) → prediction_id for later attribution.
    """
    mapping: dict[UUID, UUID] = {}
    engine = engine or PredictionEngine()
    for task in selected:
        pred = prediction_for_task(
            task,
            belief_id=belief_id,
            cycle_id=cycle_id,
            source_id=source_id,
            engine=engine,
        )
        learning.create_prediction(pred)
        mapping[task.id] = pred.id
    return mapping


def attribute_capital_or_result_outcome(
    learning: LearningService,
    *,
    action_id: UUID,
    value_created: float,
    prediction_id: UUID | None = None,
    source_keys: list[str] | None = None,
    operator_time_cost: float = 0.0,
    prediction_accuracy: float | None = None,
    open_by_action: dict[UUID, UUID] | None = None,
) -> Any:
    """Close learning when a downstream capital/revenue/result arrives.

    If prediction_id is omitted, looks up open_by_action[action_id].
    """
    pid = prediction_id
    if pid is None and open_by_action is not None:
        pid = open_by_action.get(action_id)

    accuracy = prediction_accuracy
    if accuracy is None:
        accuracy = max(0.0, min(1.0, abs(float(value_created))))

    outcome = Outcome(
        action_id=action_id,
        value_created=float(value_created),
        operator_time_cost=float(operator_time_cost),
        prediction_accuracy=float(accuracy),
        prediction_id=pid,
        source_keys=list(source_keys or []),
    )
    return learning.record_outcome(
        outcome,
        prediction_id=pid,
        source_keys=list(source_keys or []) or None,
    )
