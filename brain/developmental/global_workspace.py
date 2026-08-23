from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class WorkspaceItem:
    content_ref: str
    priority: float
    evidence_refs: list[str]
    proposing_module: str
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class BroadcastRecord:
    winner_id: UUID
    consumer_modules: list[str]
    suppressed_item_ids: list[UUID]
    evidence_refs: list[str]
    consciousness_claim: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class WorkspaceCycle:
    candidate_ids: list[UUID]
    winner_id: UUID
    suppressed_item_ids: list[UUID]
    broadcast_id: UUID
    id: UUID = field(default_factory=uuid4)


@dataclass
class GlobalWorkspaceService:
    items: list[WorkspaceItem] = field(default_factory=list)
    broadcasts: list[BroadcastRecord] = field(default_factory=list)
    cycles: list[WorkspaceCycle] = field(default_factory=list)

    def propose_item(
        self,
        *,
        content_ref: str,
        priority: float,
        evidence_refs: list[str],
        proposing_module: str,
    ) -> WorkspaceItem:
        if not evidence_refs:
            raise ValueError("workspace_item_requires_evidence")
        item = WorkspaceItem(
            content_ref=content_ref,
            priority=priority,
            evidence_refs=list(evidence_refs),
            proposing_module=proposing_module,
        )
        self.items.append(item)
        return item

    def compete_and_broadcast(self, *, consumer_modules: list[str]) -> WorkspaceCycle:
        if not self.items:
            raise ValueError("workspace_requires_candidates")
        if not consumer_modules:
            raise ValueError("broadcast_requires_consumers")
        winner = max(self.items, key=lambda item: item.priority)
        suppressed = [item.id for item in self.items if item.id != winner.id]
        broadcast = BroadcastRecord(
            winner_id=winner.id,
            consumer_modules=list(consumer_modules),
            suppressed_item_ids=suppressed,
            evidence_refs=list(winner.evidence_refs),
            consciousness_claim=False,
        )
        cycle = WorkspaceCycle(
            candidate_ids=[item.id for item in self.items],
            winner_id=winner.id,
            suppressed_item_ids=suppressed,
            broadcast_id=broadcast.id,
        )
        self.broadcasts.append(broadcast)
        self.cycles.append(cycle)
        self.items.clear()
        return cycle
