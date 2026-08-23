from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(slots=True)
class CognitiveEdge:
    source: str
    target: str
    relation: str
    weight: float
    evidence_refs: list[str]
    quarantined: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class PlasticityEvent:
    edge_id: UUID
    previous_weight: float
    new_weight: float
    reason: str
    evidence_refs: list[str]
    reversible: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class RewireProposal:
    edge_id: UUID
    proposed_weight: float
    rationale: str
    evidence_refs: list[str]
    status: str = "proposed"
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class PruningDecision:
    edge_id: UUID
    action: str
    reason: str
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class RollbackRecord:
    event_id: UUID
    edge_id: UUID
    restored_weight: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass
class PlasticityService:
    edges: dict[UUID, CognitiveEdge] = field(default_factory=dict)
    events: list[PlasticityEvent] = field(default_factory=list)
    proposals: list[RewireProposal] = field(default_factory=list)
    pruning: list[PruningDecision] = field(default_factory=list)
    rollbacks: list[RollbackRecord] = field(default_factory=list)

    def create_edge(
        self,
        *,
        source: str,
        target: str,
        relation: str,
        weight: float,
        evidence_refs: list[str],
    ) -> CognitiveEdge:
        if not evidence_refs:
            raise ValueError("edge_requires_evidence")
        edge = CognitiveEdge(source, target, relation, clamp(weight), list(evidence_refs))
        self.edges[edge.id] = edge
        return edge

    def propose_rewire(
        self,
        edge: CognitiveEdge,
        *,
        proposed_weight: float,
        rationale: str,
        evidence_refs: list[str],
    ) -> RewireProposal:
        if not evidence_refs:
            raise ValueError("rewire_requires_evidence")
        proposal = RewireProposal(edge.id, clamp(proposed_weight), rationale, list(evidence_refs))
        self.proposals.append(proposal)
        return proposal

    def apply_reward(self, edge: CognitiveEdge, *, reward: float, evidence_refs: list[str]) -> PlasticityEvent:
        if not evidence_refs:
            raise ValueError("reward_rewire_requires_evidence")
        previous = edge.weight
        edge.weight = clamp(edge.weight + max(reward, 0.0))
        event = PlasticityEvent(edge.id, previous, edge.weight, "reward_strengthened", list(evidence_refs))
        self.events.append(event)
        return event

    def apply_pain(self, edge: CognitiveEdge, *, pain: float, evidence_refs: list[str]) -> PlasticityEvent:
        if not evidence_refs:
            raise ValueError("pain_rewire_requires_evidence")
        previous = edge.weight
        edge.weight = clamp(edge.weight - max(pain, 0.0))
        event = PlasticityEvent(edge.id, previous, edge.weight, "pain_weakened", list(evidence_refs))
        self.events.append(event)
        return event

    def prune_or_quarantine(
        self,
        edge: CognitiveEdge,
        *,
        stale: bool,
        contradiction: bool,
        evidence_refs: list[str],
    ) -> PruningDecision:
        if not evidence_refs:
            raise ValueError("pruning_requires_evidence")
        if contradiction:
            edge.quarantined = True
            decision = PruningDecision(edge.id, "quarantine", "contradiction", list(evidence_refs))
        elif stale and edge.weight < 0.1:
            decision = PruningDecision(edge.id, "prune", "stale_low_weight", list(evidence_refs))
        else:
            decision = PruningDecision(edge.id, "preserve", "insufficient_pruning_basis", list(evidence_refs))
        self.pruning.append(decision)
        return decision

    def rollback(self, event: PlasticityEvent, *, evidence_refs: list[str]) -> RollbackRecord:
        if not evidence_refs:
            raise ValueError("rollback_requires_evidence")
        edge = self.edges[event.edge_id]
        edge.weight = event.previous_weight
        record = RollbackRecord(event.id, edge.id, event.previous_weight, list(evidence_refs))
        self.rollbacks.append(record)
        return record
