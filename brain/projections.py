from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import UUID

from .events import BrainEvent


Projector = Callable[[BrainEvent, dict], None]


@dataclass
class ProjectionEngine:
    """Rebuilds disposable current state from immutable cognitive history.

    Supports full replay and incremental apply for checkpointed projections.
    """

    projectors: dict[str, Projector] = field(default_factory=dict)

    def register(self, event_type: str, projector: Projector) -> None:
        self.projectors[event_type] = projector

    def empty_state(self) -> dict[str, Any]:
        return {
            "beliefs": {},
            "edges": {},
            "predictions": {},
            "working_memory": [],
            "attributions": [],
            "event_count": 0,
            "last_event_id": None,
            "last_occurred_at": None,
        }

    def apply(self, event: BrainEvent, state: dict[str, Any]) -> dict[str, Any]:
        projector = self.projectors.get(event.event_type)
        if projector:
            projector(event, state)
        state["event_count"] = int(state.get("event_count", 0)) + 1
        state["last_event_id"] = event.id
        state["last_occurred_at"] = event.occurred_at
        return state

    def replay(self, events: list[BrainEvent], *, state: dict[str, Any] | None = None) -> dict[str, Any]:
        current = state if state is not None else self.empty_state()
        for event in sorted(events, key=lambda e: (e.occurred_at, str(e.id))):
            self.apply(event, current)
        return current

    def apply_many(self, events: list[BrainEvent], state: dict[str, Any]) -> dict[str, Any]:
        ordered = sorted(events, key=lambda e: (e.occurred_at, str(e.id)))
        for event in ordered:
            self.apply(event, state)
        return state


def default_projection_engine() -> ProjectionEngine:
    engine = ProjectionEngine()

    def belief_created(event: BrainEvent, state: dict) -> None:
        state["beliefs"][event.aggregate_id] = dict(event.payload)

    def belief_updated(event: BrainEvent, state: dict) -> None:
        belief = state["beliefs"].setdefault(event.aggregate_id, {})
        belief.update(event.payload)

    def working_stored(event: BrainEvent, state: dict) -> None:
        slots = state.setdefault("working_memory", [])
        slots.append({
            "id": str(event.aggregate_id),
            "content": event.payload.get("content"),
            "salience": event.payload.get("salience"),
            "source_event_id": event.payload.get("source_event_id"),
        })
        capacity = int(event.payload.get("capacity", 7))
        if len(slots) > capacity:
            del slots[0 : len(slots) - capacity]

    def working_evicted(event: BrainEvent, state: dict) -> None:
        slots = state.setdefault("working_memory", [])
        evicted_id = str(event.payload.get("slot_id", event.aggregate_id))
        state["working_memory"] = [s for s in slots if str(s.get("id")) != evicted_id]

    def edge_rewired(event: BrainEvent, state: dict) -> None:
        edges = state.setdefault("edges", {})
        edge = edges.setdefault(str(event.aggregate_id), {})
        edge.update(event.payload.get("current") or {})
        edge["operation"] = event.payload.get("operation")
        edge["reason"] = event.payload.get("reason")

    def prediction_created(event: BrainEvent, state: dict) -> None:
        state.setdefault("predictions", {})[str(event.aggregate_id)] = dict(event.payload)

    def prediction_resolved(event: BrainEvent, state: dict) -> None:
        pred = state.setdefault("predictions", {}).setdefault(str(event.aggregate_id), {})
        pred.update(event.payload)

    def attribution_recorded(event: BrainEvent, state: dict) -> None:
        state.setdefault("attributions", []).append(dict(event.payload))

    engine.register("belief.created", belief_created)
    engine.register("belief.updated", belief_updated)
    engine.register("memory.working_stored", working_stored)
    engine.register("memory.working_evicted", working_evicted)
    engine.register("graph.edge_rewired", edge_rewired)
    engine.register("prediction.created", prediction_created)
    engine.register("prediction.resolved", prediction_resolved)
    engine.register("learning.attribution_recorded", attribution_recorded)
    return engine


def incremental_checkpoint(
    engine: ProjectionEngine,
    event_store: Any,
    checkpoint_store: Any,
    *,
    projection_name: str = "brain.current",
) -> dict[str, Any]:
    """Load last checkpoint, apply only events after it, save updated state."""
    prior = None
    if hasattr(checkpoint_store, "get"):
        prior = checkpoint_store.get(projection_name)

    if prior and prior.get("state") is not None and prior.get("last_event_id"):
        state = dict(prior["state"])
        base = engine.empty_state()
        for key, value in base.items():
            state.setdefault(key, value if not isinstance(value, (dict, list)) else type(value)())

        last_id = prior["last_event_id"]
        if isinstance(last_id, str):
            last_id = UUID(last_id)

        last_occurred = state.get("last_occurred_at")
        if last_occurred is not None and hasattr(event_store, "read_after"):
            new_events = event_store.read_after(last_occurred, last_id)
        else:
            all_events = event_store.read_all()
            seen = False
            new_events = []
            for event in all_events:
                if seen:
                    new_events.append(event)
                elif event.id == last_id:
                    seen = True
        engine.apply_many(new_events, state)
    else:
        events = event_store.read_all()
        state = engine.replay(events)

    checkpoint_store.save(
        projection_name,
        last_event_id=state.get("last_event_id"),
        event_count=int(state.get("event_count", 0)),
        state=state,
    )
    return state
