from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from uuid import UUID, uuid4

from ..domain import utcnow


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class CognitiveEdge:
    source: str
    target: str
    relation: str
    weight: float = 0.5
    confidence: float = 0.5
    evidence_refs: list[str] = field(default_factory=list)
    age_cycles: int = 0
    quarantined: bool = False
    pruned: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class RewireProposal:
    edge_id: UUID
    delta: float
    reason: str
    evidence_refs: list[str]
    proposed_weight: float
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class PlasticityEvent:
    edge_id: UUID
    previous_weight: float
    new_weight: float
    reason: str
    evidence_refs: list[str]
    proposal_id: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class RollbackRecord:
    edge_id: UUID
    event_id: UUID
    restore_weight: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class PruningDecision:
    edge_id: UUID
    prune: bool
    quarantine: bool
    reason: str
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class PlasticityService:
    """Propose evidence-bound weight changes from attributed outcomes."""

    def propose(
        self,
        edge: CognitiveEdge,
        *,
        reward: float = 0.0,
        pain: float = 0.0,
        contradiction: float = 0.0,
        reliability: float = 0.5,
        evidence_refs: list[str] | None = None,
    ) -> RewireProposal:
        evidence = list(evidence_refs or edge.evidence_refs)
        if not evidence:
            raise ValueError("rewire proposal requires evidence")
        positive = max(0.0, float(reward)) * _clamp01(reliability)
        negative = max(0.0, float(pain)) + max(0.0, float(contradiction)) * 0.5
        delta = max(-0.25, min(0.25, (positive - negative) * 0.1))
        reason = "reward" if delta > 0 else "pain_or_contradiction" if delta < 0 else "no_change"
        return RewireProposal(
            edge_id=edge.id,
            delta=delta,
            reason=reason,
            evidence_refs=evidence,
            proposed_weight=_clamp01(edge.weight + delta),
        )


class GraphRewireService:
    """Apply and roll back explicit rewire proposals."""

    def apply(
        self, edge: CognitiveEdge, proposal: RewireProposal
    ) -> tuple[CognitiveEdge, PlasticityEvent, RollbackRecord]:
        if proposal.edge_id != edge.id:
            raise ValueError("proposal targets another edge")
        if not proposal.evidence_refs:
            raise ValueError("rewire cannot be applied without evidence")
        previous = edge.weight
        updated = replace(
            edge,
            weight=_clamp01(proposal.proposed_weight),
            evidence_refs=sorted(set(edge.evidence_refs + proposal.evidence_refs)),
        )
        event = PlasticityEvent(
            edge_id=edge.id,
            previous_weight=previous,
            new_weight=updated.weight,
            reason=proposal.reason,
            evidence_refs=list(proposal.evidence_refs),
            proposal_id=proposal.id,
        )
        rollback = RollbackRecord(
            edge_id=edge.id,
            event_id=event.id,
            restore_weight=previous,
            evidence_refs=list(proposal.evidence_refs),
        )
        return updated, event, rollback

    def rollback(self, edge: CognitiveEdge, rollback: RollbackRecord) -> CognitiveEdge:
        if rollback.edge_id != edge.id:
            raise ValueError("rollback targets another edge")
        if not rollback.evidence_refs:
            raise ValueError("rollback requires provenance")
        return replace(edge, weight=_clamp01(rollback.restore_weight))


class PruningService:
    """Quarantine or prune weak, stale edges only with auditable evidence."""

    def decide(
        self,
        edge: CognitiveEdge,
        *,
        evidence_refs: list[str],
        minimum_weight: float = 0.08,
        minimum_confidence: float = 0.15,
        stale_after_cycles: int = 500,
    ) -> PruningDecision:
        if not evidence_refs:
            raise ValueError("pruning requires evidence")
        weak = edge.weight < minimum_weight
        uncertain = edge.confidence < minimum_confidence
        stale = edge.age_cycles >= stale_after_cycles
        prune = weak and (uncertain or stale)
        quarantine = not prune and (weak or uncertain)
        if prune:
            reason = "weak_and_unreliable_or_stale"
        elif quarantine:
            reason = "weak_or_uncertain_requires_review"
        else:
            reason = "retain"
        return PruningDecision(
            edge_id=edge.id,
            prune=prune,
            quarantine=quarantine,
            reason=reason,
            evidence_refs=list(evidence_refs),
        )

    def apply(self, edge: CognitiveEdge, decision: PruningDecision) -> CognitiveEdge:
        if decision.edge_id != edge.id:
            raise ValueError("pruning decision targets another edge")
        if not decision.evidence_refs:
            raise ValueError("pruning decision has no evidence")
        return replace(edge, pruned=decision.prune, quarantined=decision.quarantine)
