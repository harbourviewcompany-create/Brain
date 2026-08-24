"""Cycle-level learning helpers.

This module preserves the `brain.cycle` import boundary while delegating the
actual prediction and attribution helpers to `brain.learning`. It keeps the
in-process learning hook additive and backward-compatible.
"""

from __future__ import annotations

from .learning import (
    attribute_capital_or_result_outcome,
    emit_predictions_for_selected_tasks,
    prediction_for_task,
)

__all__ = [
    "attribute_capital_or_result_outcome",
    "emit_predictions_for_selected_tasks",
    "prediction_for_task",
]
