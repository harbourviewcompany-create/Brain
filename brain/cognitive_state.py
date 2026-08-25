from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from .domain import utcnow


class MemoryKind(StrEnum):
    SENSORY = "sensory"
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PROSPECTIVE = "prospective"


@dataclass(slots=True)
class MemoryItem:
    kind: MemoryKind
    content: dict[str, Any]
    salience: float = 0.5
    strength: float = 0.5
    source_event_ids: list[UUID] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    last_accessed_at: datetime = field(default_factory=utcnow)
    access_count: int = 0


@dataclass(slots=True)
class BitemporalInterval:
    """Separates time in the world from time in the Brain's knowledge."""

    valid_from: datetime
    valid_to: datetime | None = None
    known_from: datetime = field(default_factory=utcnow)
    known_to: datetime | None = None


@dataclass(slots=True)
class NeuromodulatorState:
    """Global cognitive modulation; values are normalized to [0, 1]."""

    dopamine: float = 0.5
    norepinephrine: float = 0.5
    serotonin: float = 0.5
    acetylcholine: float = 0.5
    stress: float = 0.2

    def clamp(self) -> NeuromodulatorState:
        for name in ("dopamine", "norepinephrine", "serotonin", "acetylcholine", "stress"):
            setattr(self, name, max(0.0, min(1.0, float(getattr(self, name)))))
        return self


@dataclass(slots=True)
class HomeostaticState:
    compute_load: float = 0.0
    unresolved_uncertainty: float = 0.0
    memory_pressure: float = 0.0
    operator_load: float = 0.0
    budget_pressure: float = 0.0
    graph_density_pressure: float = 0.0
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def stress_index(self) -> float:
        # Capital pressure is hunger, not another equal dashboard signal.
        # A starving ledger must be able to dominate attention and scheduling
        # without needing artificial uncertainty/operator-load compounding.
        budget_weight = 12.0
        weighted_sum = (
            self.compute_load
            + self.unresolved_uncertainty
            + self.memory_pressure
            + self.operator_load
            + self.graph_density_pressure
            + (self.budget_pressure * budget_weight)
        )
        total_weight = 5.0 + budget_weight
        return max(0.0, min(1.0, weighted_sum / total_weight))


@dataclass(slots=True)
class CognitiveDrive:
    name: str
    target: float
    current: float
    priority: float = 0.5
    id: UUID = field(default_factory=uuid4)

    @property
    def deficit(self) -> float:
        return max(0.0, self.target - self.current) * self.priority
