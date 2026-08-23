from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class CognitiveScale(StrEnum):
    MOLECULAR = "molecular"
    CELLULAR = "cellular"
    CIRCUIT = "circuit"
    REGION = "region"
    SYSTEM = "system"
    BEHAVIOR = "behavior"
    COMMERCIAL = "commercial"
    SOCIAL = "social"
    SELF_MODEL = "self_model"


class DevelopmentalStage(StrEnum):
    REFLEX = "reflex"
    PERCEPTUAL = "perceptual"
    ASSOCIATIVE = "associative"
    PREDICTIVE = "predictive"
    STRATEGIC = "strategic"
    METACOGNITIVE = "metacognitive"
    SELF_REPAIRING = "self_repairing"
    CONSOLIDATED = "consolidated"


@dataclass(slots=True)
class ScaleNode:
    name: str
    scale: CognitiveScale
    source_refs: list[str]
    description: str = ""
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ScaleLink:
    parent_node_id: UUID
    child_node_id: UUID
    relation: str
    evidence_refs: list[str]
    confidence: float = 0.5
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class BrainRegionMapping:
    region_name: str
    functional_claim: str
    brain_module: str
    implementation_module: str
    analogy_status: str
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)

    def requires_boundary_label(self) -> bool:
        return self.analogy_status not in {"implemented", "direct_runtime"}


@dataclass(slots=True)
class CausalHypothesis:
    cause_ref: str
    effect_ref: str
    mechanism: str
    evidence_refs: list[str]
    confidence: float
    alternative_hypotheses: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class CurriculumTask:
    target_capability: str
    reason: str
    evidence_refs: list[str]
    expected_learning_value: float
    risk: float
    priority: float
    external_action: bool = False
    status: str = "proposed"
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class BenchmarkRecord:
    benchmark_name: str
    capability: str
    score: float
    baseline_score: float
    evidence_refs: list[str]
    claim_allowed: bool = False
    id: UUID = field(default_factory=uuid4)

    @property
    def improvement(self) -> float:
        return self.score - self.baseline_score


@dataclass(slots=True)
class DevelopmentalStageRecord:
    stage: DevelopmentalStage
    entered_because: str
    evidence_refs: list[str]
    capabilities_unlocked: list[str]
    blocked_claims: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


class HigherOrderCognitionService:
    """Controlled higher-order cognition layer.

    This service gives the Brain multi-scale organization, brain-region analogy mapping,
    causal world-model hypotheses, curriculum self-design, benchmark metacognition and
    developmental staging without allowing unsupported capability claims or external action.
    """

    def __init__(self) -> None:
        self.nodes: dict[UUID, ScaleNode] = {}
        self.links: dict[UUID, ScaleLink] = {}
        self.region_mappings: dict[UUID, BrainRegionMapping] = {}
        self.causal_hypotheses: dict[UUID, CausalHypothesis] = {}
        self.curriculum_tasks: dict[UUID, CurriculumTask] = {}
        self.benchmarks: dict[UUID, BenchmarkRecord] = {}
        self.stage_records: dict[UUID, DevelopmentalStageRecord] = {}

    def add_scale_node(self, node: ScaleNode) -> ScaleNode:
        if not node.source_refs:
            raise ValueError("scale_node_requires_source_refs")
        self.nodes[node.id] = node
        return node

    def link_scales(self, link: ScaleLink) -> ScaleLink:
        if link.parent_node_id not in self.nodes or link.child_node_id not in self.nodes:
            raise ValueError("scale_link_requires_existing_nodes")
        if not link.evidence_refs:
            raise ValueError("scale_link_requires_evidence")
        link.confidence = clamp(link.confidence)
        self.links[link.id] = link
        return link

    def map_brain_region(self, mapping: BrainRegionMapping) -> BrainRegionMapping:
        if not mapping.evidence_refs:
            raise ValueError("brain_region_mapping_requires_evidence")
        if mapping.analogy_status == "neuroscience_claim_without_runtime":
            raise ValueError("unsupported_neuroscience_claim")
        self.region_mappings[mapping.id] = mapping
        return mapping

    def register_causal_hypothesis(self, hypothesis: CausalHypothesis) -> CausalHypothesis:
        if not hypothesis.evidence_refs:
            raise ValueError("causal_hypothesis_requires_evidence")
        if not hypothesis.alternative_hypotheses:
            raise ValueError("causal_hypothesis_requires_alternatives")
        hypothesis.confidence = clamp(hypothesis.confidence)
        self.causal_hypotheses[hypothesis.id] = hypothesis
        return hypothesis

    def design_curriculum_task(self, task: CurriculumTask) -> CurriculumTask:
        if task.external_action:
            raise ValueError("curriculum_task_cannot_execute_external_action")
        if not task.evidence_refs:
            raise ValueError("curriculum_task_requires_evidence")
        task.priority = clamp(task.expected_learning_value - task.risk)
        self.curriculum_tasks[task.id] = task
        return task

    def record_benchmark(self, record: BenchmarkRecord) -> BenchmarkRecord:
        if not record.evidence_refs:
            raise ValueError("benchmark_requires_evidence")
        record.claim_allowed = record.score > record.baseline_score and bool(record.evidence_refs)
        self.benchmarks[record.id] = record
        return record

    def enter_developmental_stage(self, record: DevelopmentalStageRecord) -> DevelopmentalStageRecord:
        if not record.evidence_refs:
            raise ValueError("developmental_stage_requires_evidence")
        if record.stage in {DevelopmentalStage.METACOGNITIVE, DevelopmentalStage.SELF_REPAIRING}:
            if not record.capabilities_unlocked:
                raise ValueError("advanced_stage_requires_capability_evidence")
        self.stage_records[record.id] = record
        return record

    def claim_boundary_report(self) -> dict[str, list[str]]:
        blocked = [
            "full_brain_completion",
            "superior_intelligence_without_benchmarks",
            "consciousness_claim",
            "external_action_without_approval",
            "neuroscience_equivalence_claim",
        ]
        allowed = [
            "multi_scale_runtime_mapping",
            "brain_region_translation_as_analogy_or_runtime_mapping",
            "causal_hypothesis_tracking",
            "curriculum_proposal_generation",
            "benchmark_bound_metacognition",
            "evidence_bound_developmental_stage_tracking",
        ]
        return {"allowed": allowed, "blocked": blocked}
