from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from .domain import Belief, Edge, Evidence, Node, RewireEvent
from .events import BrainEvent
from .prediction import Prediction


@dataclass
class InMemoryBrainStore:
    beliefs: dict[UUID, Belief] = field(default_factory=dict)
    evidence: dict[UUID, Evidence] = field(default_factory=dict)
    nodes: dict[UUID, Node] = field(default_factory=dict)
    edges: dict[UUID, Edge] = field(default_factory=dict)
    predictions: dict[UUID, Prediction] = field(default_factory=dict)
    rewires: list[RewireEvent] = field(default_factory=list)
    events: list[BrainEvent] = field(default_factory=list)

    def append(self, event: BrainEvent) -> None:
        self.events.append(event)

    def read_all(self, *, limit: int | None = None) -> list[BrainEvent]:
        if limit is None:
            return list(self.events)
        if limit <= 0:
            return []
        return list(self.events[:limit])

    def read_recent(
        self,
        *,
        event_types: Iterable[str],
        limit: int = 200,
    ) -> list[BrainEvent]:
        if limit <= 0:
            return []
        wanted = {str(value).strip() for value in event_types if str(value).strip()}
        if not wanted:
            return []
        events = [event for event in self.events if event.event_type in wanted]
        events.sort(key=lambda event: (event.occurred_at, str(event.id)), reverse=True)
        return events[:limit]

    def read_after(self, occurred_at: datetime, event_id: UUID) -> list[BrainEvent]:
        """Return events strictly after the given cursor.

        Prefers log order (append sequence) when the cursor id is present so
        same-timestamp events remain deterministic. Falls back to
        (occurred_at, id) ordering for externally supplied cursors.
        """
        out: list[BrainEvent] = []
        seen = False
        found = False
        for event in self.events:
            if event.id == event_id:
                found = True
                seen = True
                continue
            if seen:
                out.append(event)
        if found:
            return out
        for event in self.events:
            if (event.occurred_at, str(event.id)) > (occurred_at, str(event_id)):
                out.append(event)
        return out

    def get(self, item_id: UUID):
        return (
            self.beliefs.get(item_id)
            or self.evidence.get(item_id)
            or self.predictions.get(item_id)
        )

    def save(self, item) -> None:
        if isinstance(item, Belief):
            self.beliefs[item.id] = item
        elif isinstance(item, Evidence):
            self.evidence[item.id] = item
        elif isinstance(item, Prediction):
            self.predictions[item.id] = item
        else:
            raise TypeError(type(item))

    def upsert_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def upsert_edge(self, edge: Edge) -> None:
        self.edges[edge.id] = edge

    def get_edge(self, edge_id: UUID) -> Edge | None:
        return self.edges.get(edge_id)

    def log_rewire(self, event: RewireEvent) -> None:
        self.rewires.append(event)
