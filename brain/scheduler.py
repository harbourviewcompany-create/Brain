from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from uuid import UUID, uuid4

from .cognitive_state import NeuromodulatorState


@dataclass(order=True, slots=True)
class CognitiveTask:
    sort_index: float = field(init=False, repr=False)
    utility: float
    urgency: float
    novelty: float
    uncertainty_reduction: float
    cost: float
    name: str = field(compare=False)
    payload: dict = field(default_factory=dict, compare=False)
    id: UUID = field(default_factory=uuid4, compare=False)

    def __post_init__(self) -> None:
        self.sort_index = 0.0


class CognitiveScheduler:
    """A finite cognitive-budget scheduler. Tasks compete rather than run indiscriminately."""

    def priority(self, task: CognitiveTask, modulation: NeuromodulatorState) -> float:
        reward_weight = 0.8 + modulation.dopamine
        urgency_weight = 0.8 + modulation.norepinephrine
        learning_weight = 0.6 + modulation.acetylcholine
        exploration_weight = max(0.2, 1.2 - modulation.stress)
        return (
            task.utility * reward_weight
            + task.urgency * urgency_weight
            + task.uncertainty_reduction * learning_weight
            + task.novelty * exploration_weight
            - task.cost * (0.8 + modulation.stress)
        )

    def select(
        self,
        tasks: list[CognitiveTask],
        modulation: NeuromodulatorState,
        budget: int,
    ) -> list[CognitiveTask]:
        heap: list[tuple[float, str, CognitiveTask]] = []
        for task in tasks:
            p = self.priority(task, modulation)
            heappush(heap, (-p, str(task.id), task))
        return [heappop(heap)[2] for _ in range(min(budget, len(heap)))]
