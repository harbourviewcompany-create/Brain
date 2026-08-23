from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(slots=True)
class CuriosityTask:
    question: str
    expected_uncertainty_reduction: float
    expected_value: float
    research_cost: float
    id: UUID = field(default_factory=uuid4)

    @property
    def priority(self) -> float:
        return (self.expected_uncertainty_reduction * self.expected_value) - self.research_cost


class CuriosityEngine:
    def from_unknown(self, unknown: str, value: float = 0.5) -> CuriosityTask:
        return CuriosityTask(
            question=f"Resolve: {unknown}",
            expected_uncertainty_reduction=0.7,
            expected_value=value,
            research_cost=0.15,
        )
