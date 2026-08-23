from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from .domain import Belief, Edge, Evidence, Node, RewireEvent
from .events import BrainEvent


@dataclass
class InMemoryBrainStore:
    beliefs: dict[UUID, Belief] = field(default_factory=dict)
    evidence: dict[UUID, Evidence] = field(default_factory=dict)
    nodes: dict[UUID, Node] = field(default_factory=dict)
    edges: dict[UUID, Edge] = field(default_factory=dict)
    rewires: list[RewireEvent] = field(default_factory=list)
    events: list[BrainEvent] = field(default_factory=list)

    def append(self, event: BrainEvent) -> None:
        self.events.append(event)

    def get(self, item_id: UUID):
        return self.beliefs.get(item_id) or self.evidence.get(item_id)

    def save(self, item) -> None:
        if isinstance(item, Belief):
            self.beliefs[item.id] = item
        elif isinstance(item, Evidence):
            self.evidence[item.id] = item
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
