from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from .adapters.cognitive_object_store import InMemoryCognitiveObjectStore


def utcnow() -> datetime:
    return datetime.now(UTC)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class KnowledgeGapType(StrEnum):
    UNKNOWN = "UNKNOWN"
    UNCERTAIN = "UNCERTAIN"
    UNDEROBSERVED = "UNDEROBSERVED"
    CONTRADICTED = "CONTRADICTED"
    UNTESTED = "UNTESTED"
    UNEXPLAINED = "UNEXPLAINED"
    UNCALIBRATED = "UNCALIBRATED"
    MODEL_GAP = "MODEL_GAP"
    MECHANISM_UNKNOWN = "MECHANISM_UNKNOWN"


class ProjectionState(StrEnum):
    INTERNAL = "internal"
    CANDIDATE = "candidate"
    DELIBERATED = "deliberated"
    GOVERNANCE_PENDING = "governance_pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXTERNALIZED = "externalized"
    CLOSED = "closed"


@dataclass(slots=True)
class EpistemicState:
    confidence: float | None = None
    uncertainty: float | None = None
    evidence_strength: float | None = None
    evidence_diversity: float | None = None
    source_reliability: float | None = None
    contradiction: float | None = None
    recency: float | None = None
    causal_support: float | None = None
    prediction_performance: float | None = None
    calibration: float | None = None
    stability: float | None = None
    novelty: float | None = None

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if value is not None:
                setattr(self, name, clamp01(value))


@dataclass(slots=True)
class ProvenanceEdge:
    from_id: str
    to_id: str
    edge_type: str
    source_refs: list[str]
    confidence: float | None = None
    formula_run_id: str | None = None
    actor: str = "brain"
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not self.source_refs:
            raise ValueError("provenance edge requires source/evidence references")
        if self.confidence is not None:
            self.confidence = clamp01(self.confidence)


@dataclass(slots=True)
class KnowledgeGap:
    gap_type: KnowledgeGapType
    description: str
    target_refs: list[str]
    evidence_refs: list[str]
    epistemic_state: EpistemicState
    importance: float = 0.5
    expected_information_gain: float = 0.5
    downstream_dependency_count: int = 0
    investigation_cost: float = 0.5
    lifecycle_state: str = "detected"
    id: UUID = field(default_factory=uuid4)
    detected_at: datetime = field(default_factory=utcnow)
    curiosity_task_refs: list[str] = field(default_factory=list)

    @property
    def priority_score(self) -> float:
        uncertainty = self.epistemic_state.uncertainty
        if uncertainty is None:
            uncertainty = 0.5
        dependency = min(max(self.downstream_dependency_count, 0) / 10.0, 1.0)
        score = (
            clamp01(self.importance) * 0.30
            + clamp01(self.expected_information_gain) * 0.30
            + clamp01(uncertainty) * 0.20
            + dependency * 0.15
            + (1.0 - clamp01(self.investigation_cost)) * 0.05
        )
        return clamp01(score)


@dataclass(slots=True)
class CognitiveAffordance:
    kind: str
    target_refs: list[str]
    rationale: str
    evidence_refs: list[str]
    expected_utility: float = 0.5
    expected_information_gain: float = 0.0
    uncertainty_reduction: float = 0.0
    risk: float = 0.0
    resource_cost: float = 0.0
    reversibility: float = 1.0
    novelty: float = 0.0
    time_sensitivity: float = 0.0
    governance_requirement: str = "internal"
    lifecycle_state: str = "detected"
    goal_refs: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)

    @property
    def evaluation_score(self) -> float:
        return clamp01(
            clamp01(self.expected_utility) * 0.30
            + clamp01(self.expected_information_gain) * 0.20
            + clamp01(self.uncertainty_reduction) * 0.15
            + (1.0 - clamp01(self.risk)) * 0.15
            + (1.0 - clamp01(self.resource_cost)) * 0.10
            + clamp01(self.reversibility) * 0.05
            + clamp01(self.time_sensitivity) * 0.05
        )


@dataclass(slots=True)
class ProjectionDecision:
    object_refs: list[str]
    target: str
    source_refs: list[str]
    state: ProjectionState = ProjectionState.INTERNAL
    consequential: bool = False
    approved_by: str | None = None
    reason: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)

    @property
    def may_externalize(self) -> bool:
        if self.consequential:
            return self.state == ProjectionState.APPROVED and self.approved_by is not None
        return self.state == ProjectionState.APPROVED


@dataclass(slots=True)
class LearningEvent:
    outcome_refs: list[str]
    action_refs: list[str]
    prediction_refs: list[str]
    attribution_refs: list[str]
    evidence_refs: list[str]
    expected_vs_actual: str
    utility_delta: float
    information_gain: float
    proposed_updates: dict[str, Any]
    lifecycle_state: str = "attribution_pending"
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class DevelopmentalPlasticityDelta:
    target_kind: str
    target_id: str
    trigger_learning_event_ids: list[str]
    before_state_ref: str
    proposed_after_state: dict[str, Any]
    mechanism_class: str
    evidence_refs: list[str]
    expected_benefit: float
    regression_risk: float
    rollback_plan_ref: str
    benchmark_refs: list[str] = field(default_factory=list)
    lifecycle_state: str = "proposed"
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    applied_at: datetime | None = None


@dataclass(slots=True)
class ReplayBundle:
    scope: str
    object_refs: list[str]
    provenance_edge_ids: list[str]
    epistemic_object_refs: list[str]
    transition_refs: list[str]
    affordance_refs: list[str]
    projection_refs: list[str]
    outcome_refs: list[str]
    learning_event_refs: list[str]
    unresolved_gap_refs: list[str]
    unresolved_conflict_refs: list[str]
    source_refs: list[str]
    software_version: str | None = None
    external_actions_executed: int = 0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if self.external_actions_executed != 0:
            raise ValueError("cognitive replay must never execute external actions")
        if not self.source_refs:
            raise ValueError("replay bundle requires source/provenance references")


class CognitiveProtocolService:
    """Shared cross-organ protocol persisted through the existing cognitive-object store."""

    def __init__(self, store: InMemoryCognitiveObjectStore | None = None) -> None:
        self.store = store or InMemoryCognitiveObjectStore()
        self.provenance_edges: dict[UUID, ProvenanceEdge] = {}
        self.gaps: dict[UUID, KnowledgeGap] = {}
        self.affordances: dict[UUID, CognitiveAffordance] = {}
        self.projections: dict[UUID, ProjectionDecision] = {}
        self.learning_events: dict[UUID, LearningEvent] = {}
        self.plasticity_deltas: dict[UUID, DevelopmentalPlasticityDelta] = {}
        self.replays: dict[UUID, ReplayBundle] = {}

    def _save(self, kind: str, object_id: UUID, payload: Any, source_refs: list[str]) -> None:
        if not source_refs:
            raise ValueError(f"{kind} requires provenance")
        self.store.save(kind, object_id, payload, source_refs=source_refs)

    def add_provenance_edge(self, edge: ProvenanceEdge) -> ProvenanceEdge:
        self.provenance_edges[edge.id] = edge
        self._save("provenance_edge", edge.id, edge, edge.source_refs)
        return edge

    def detect_gap(self, gap: KnowledgeGap) -> KnowledgeGap:
        if not gap.evidence_refs:
            raise ValueError("knowledge gap requires evidence/provenance references")
        self.gaps[gap.id] = gap
        self._save("knowledge_gap", gap.id, gap, gap.evidence_refs)
        return gap

    def affordance_from_gap(self, gap_id: UUID, *, kind: str = "investigate") -> CognitiveAffordance:
        gap = self.gaps[gap_id]
        affordance = CognitiveAffordance(
            kind=kind,
            target_refs=[str(gap.id), *gap.target_refs],
            rationale=f"Resolve {gap.gap_type.value}: {gap.description}",
            evidence_refs=list(gap.evidence_refs),
            expected_information_gain=gap.expected_information_gain,
            uncertainty_reduction=gap.epistemic_state.uncertainty or 0.5,
            resource_cost=gap.investigation_cost,
            governance_requirement="internal",
        )
        self.affordances[affordance.id] = affordance
        self._save("cognitive_affordance", affordance.id, affordance, affordance.evidence_refs)
        return affordance

    def evaluate_projection(
        self,
        projection: ProjectionDecision,
        *,
        approve: bool = False,
        approver: str | None = None,
    ) -> ProjectionDecision:
        if not projection.source_refs:
            raise ValueError("projection requires provenance")
        if projection.consequential and (not approve or not approver):
            projection.state = ProjectionState.GOVERNANCE_PENDING
            projection.reason = "consequential externalization requires explicit approval"
        elif approve:
            projection.state = ProjectionState.APPROVED
            projection.approved_by = approver or "brain-governance"
        else:
            projection.state = ProjectionState.DELIBERATED
        self.projections[projection.id] = projection
        self._save("projection_decision", projection.id, projection, projection.source_refs)
        return projection

    def record_learning(self, event: LearningEvent) -> LearningEvent:
        if not event.outcome_refs or not event.attribution_refs or not event.evidence_refs:
            raise ValueError("learning requires outcome, attribution and evidence provenance")
        event.lifecycle_state = "supported"
        self.learning_events[event.id] = event
        self._save("learning_event", event.id, event, event.evidence_refs)
        return event

    def propose_plasticity(self, delta: DevelopmentalPlasticityDelta) -> DevelopmentalPlasticityDelta:
        if not delta.trigger_learning_event_ids or not delta.rollback_plan_ref or not delta.evidence_refs:
            raise ValueError("plasticity requires learning trigger, evidence and rollback plan")
        self.plasticity_deltas[delta.id] = delta
        self._save("developmental_plasticity_delta", delta.id, delta, delta.evidence_refs)
        return delta

    def build_replay(self, bundle: ReplayBundle) -> ReplayBundle:
        self.replays[bundle.id] = bundle
        self._save("cognitive_replay", bundle.id, bundle, bundle.source_refs)
        return bundle

    def snapshot(self) -> dict[str, int]:
        return {
            "provenance_edges": len(self.provenance_edges),
            "knowledge_gaps": len(self.gaps),
            "cognitive_affordances": len(self.affordances),
            "projection_decisions": len(self.projections),
            "learning_events": len(self.learning_events),
            "plasticity_deltas": len(self.plasticity_deltas),
            "replay_bundles": len(self.replays),
        }
