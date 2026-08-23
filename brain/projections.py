from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .events import BrainEvent


Projector = Callable[[BrainEvent, dict], None]


@dataclass
class ProjectionEngine:
    """Rebuilds disposable current state from immutable cognitive history."""

    projectors: dict[str, Projector] = field(default_factory=dict)

    def register(self, event_type: str, projector: Projector) -> None:
        self.projectors[event_type] = projector

    def replay(self, events: list[BrainEvent]) -> dict:
        state: dict = {
            "beliefs": {},
            "event_count": 0,
            "last_event_id": None,
        }
        for event in sorted(events, key=lambda e: (e.occurred_at, str(e.id))):
            projector = self.projectors.get(event.event_type)
            if projector:
                projector(event, state)
            state["event_count"] += 1
            state["last_event_id"] = event.id
        return state


def default_projection_engine() -> ProjectionEngine:
    engine = ProjectionEngine()

    def belief_created(event: BrainEvent, state: dict) -> None:
        state["beliefs"][event.aggregate_id] = dict(event.payload)

    def belief_updated(event: BrainEvent, state: dict) -> None:
        belief = state["beliefs"].setdefault(event.aggregate_id, {})
        belief.update(event.payload)

    engine.register("belief.created", belief_created)
    engine.register("belief.updated", belief_updated)
    return engine
