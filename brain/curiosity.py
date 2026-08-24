from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class CuriosityState(StrEnum):
    GENERATED = "generated"
    PRIORITIZED = "prioritized"
    INVESTIGATING = "investigating"
    ANSWERED = "answered"
    UNRESOLVED = "unresolved"
    CONVERTED_TO_HYPOTHESIS = "converted_to_hypothesis"
    ARCHIVED = "archived"


@dataclass(slots=True)
class CuriosityTask:
    question: str
    expected_uncertainty_reduction: float
    expected_value: float
    research_cost: float
    id: UUID = field(default_factory=uuid4)
    trigger_type: str = "unknown"
    trigger_refs: list[str] = field(default_factory=list)
    falsification_condition: str | None = None
    state: CuriosityState = CuriosityState.GENERATED

    @property
    def priority(self) -> float:
        return _clamp((self.expected_uncertainty_reduction * self.expected_value) - self.research_cost)


class CuriosityEngine:
    def __init__(self) -> None:
        self.tasks: list[CuriosityTask] = []

    def from_unknown(self, unknown: str, value: float = 0.5) -> CuriosityTask:
        task = CuriosityTask(
            question=f"Resolve: {unknown}",
            expected_uncertainty_reduction=0.7,
            expected_value=value,
            research_cost=0.15,
            trigger_type="unknown",
            falsification_condition=f"No actionable evidence resolves {unknown}",
            state=CuriosityState.PRIORITIZED,
        )
        self.tasks.append(task)
        return task

    def generate(
        self,
        trigger_type: str,
        trigger_refs: list[str],
        question: str,
        *,
        expected_value: float = 0.5,
        uncertainty: float = 0.7,
        cost: float = 0.15,
        falsification_condition: str | None = None,
    ) -> CuriosityTask:
        task = CuriosityTask(
            question=question,
            expected_uncertainty_reduction=_clamp(uncertainty),
            expected_value=_clamp(expected_value),
            research_cost=_clamp(cost),
            trigger_type=trigger_type,
            trigger_refs=list(trigger_refs),
            falsification_condition=falsification_condition or "Contradictory source found or no evidence after bounded search",
            state=CuriosityState.PRIORITIZED if expected_value * uncertainty > cost else CuriosityState.GENERATED,
        )
        self.tasks.append(task)
        return task
