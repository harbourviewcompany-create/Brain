from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from .domain import Edge, RewireEvent, RewireOperation, utcnow


class RewiringEngine:
    def __init__(self, max_edge_delta: float = 0.10, prune_threshold: float = 0.05):
        self.max_edge_delta = max_edge_delta
        self.prune_threshold = prune_threshold

    def reinforce(self, edge: Edge, evidence_id: UUID, amount: float) -> tuple[Edge, RewireEvent]:
        delta = min(abs(amount), self.max_edge_delta)
        previous = edge.weight
        updated = replace(
            edge,
            weight=min(1.0, edge.weight + delta),
            evidence_ids=set(edge.evidence_ids) | {evidence_id},
            updated_at=utcnow(),
        )
        event = RewireEvent(
            operation=RewireOperation.STRENGTHEN_EDGE,
            reason="Supporting evidence reinforced this pathway.",
            target_id=edge.id,
            previous={"weight": previous},
            current={"weight": updated.weight},
            evidence_ids=[evidence_id],
        )
        return updated, event

    def weaken(self, edge: Edge, amount: float) -> tuple[Edge | None, RewireEvent]:
        delta = min(abs(amount), self.max_edge_delta)
        new_weight = max(0.0, edge.weight - delta)
        operation = RewireOperation.PRUNE_EDGE if new_weight <= self.prune_threshold else RewireOperation.WEAKEN_EDGE
        updated = None if operation is RewireOperation.PRUNE_EDGE else replace(edge, weight=new_weight, updated_at=utcnow())
        event = RewireEvent(
            operation=operation,
            reason="Contradiction, decay, or negative outcome weakened this pathway.",
            target_id=edge.id,
            previous={"weight": edge.weight},
            current={"weight": 0.0 if updated is None else updated.weight},
        )
        return updated, event
