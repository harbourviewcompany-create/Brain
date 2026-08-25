from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from .domain import utcnow


class BrainSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    source_refs: list[str] = Field(default_factory=list)
    provenance: list[ProvenanceRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProvenanceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_location: str | None = None
    excerpt_hash: str | None = None


class MemoryKind(StrEnum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    EMOTIONAL = "emotional"
    SOCIAL = "social"


class Source(BrainSchema):
    name: str
    kind: str
    trust_score: float = Field(ge=0.0, le=1.0)
    status: Literal["active", "monitor", "blocked", "retired"] = "active"


class Sensor(BrainSchema):
    source_id: str
    signal_types: list[str]
    priority: float = Field(ge=0.0, le=1.0)
    status: Literal["enabled", "disabled", "quarantined"] = "enabled"


class RawObservation(BrainSchema):
    source_id: str
    content: str
    observed_at: datetime = Field(default_factory=utcnow)
    sensor_id: str | None = None


class PerceptualEvent(BrainSchema):
    observation_id: str
    summary: str
    salience_score: float = Field(ge=0.0)
    attention_route: str


class EvidenceItem(BrainSchema):
    claim: str
    source_id: str
    reliability: float = Field(ge=0.0, le=1.0)
    supports: bool = True
    observation_id: str | None = None
    evidence_strength: float = Field(default=0.5, ge=0.0, le=1.0)


class Entity(BrainSchema):
    kind: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class Belief(BrainSchema):
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)
    state: Literal[
        "hypothesis", "provisional", "established", "contested", "rejected", "dormant"
    ] = "hypothesis"
    evidence_ids: list[str] = Field(default_factory=list)
    contradiction_ids: list[str] = Field(default_factory=list)


class Signal(BrainSchema):
    source_id: str
    evidence_ids: list[str]
    novelty: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    commercial_upside: float = Field(ge=0.0)
    attention_score: float


class Opportunity(BrainSchema):
    title: str
    belief_ids: list[str]
    status: Literal[
        "candidate", "research", "recommendation", "approved", "rejected", "closed"
    ] = "candidate"
    expected_value: float
    risk_score: float = Field(ge=0.0)


class CandidateAction(BrainSchema):
    description: str
    opportunity_id: str | None = None
    expected_value: float
    uncertainty: float = Field(ge=0.0, le=1.0)
    external: bool = False
    state: Literal["draft", "simulated", "approval_required", "approved", "blocked"] = "draft"


class ApprovalRequest(BrainSchema):
    action_id: str
    state: Literal["requested", "approved", "rejected", "expired"] = "requested"
    required_approver: str
    external_consequence: bool = True


class Outcome(BrainSchema):
    action_id: str
    value_created: float
    prediction_accuracy: float = Field(ge=0.0, le=1.0)
    operator_time_cost: float = Field(ge=0.0)
    trust_impact: float = 0.0
    legal_risk: float = Field(default=0.0, ge=0.0)


class Prediction(BrainSchema):
    belief_id: str
    forecast_probability: float = Field(ge=0.0, le=1.0)
    actual_outcome: bool | None = None
    brier_score: float | None = Field(default=None, ge=0.0, le=1.0)


class RewardEvent(BrainSchema):
    outcome_id: str
    score: float
    attributed_to: list[str]
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class PainEvent(BrainSchema):
    outcome_id: str
    score: float = Field(ge=0.0)
    attributed_to: list[str]
    mitigation_required: bool = True


class MemoryObject(BrainSchema):
    memory_type: MemoryKind
    content: str
    salience: float = Field(ge=0.0, le=1.0)
    linked_object_ids: list[str] = Field(default_factory=list)


class GraphNode(BrainSchema):
    kind: str
    key: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BrainSchema):
    source: str
    target: str
    relation: str
    weight: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(default_factory=list)


class FormulaRun(BrainSchema):
    formula_id: str
    owner_object_id: str
    owner_object_type: str
    inputs: dict[str, float]
    output: float
    service: str
    table_store: str
    dashboard: str
    decision_consequence: str


class DecisionExplanation(BrainSchema):
    decision_id: str
    decision_type: str
    evidence_ids: list[str]
    formula_run_ids: list[str]
    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)


class AcceptanceReport(BrainSchema):
    report_id: str
    ticket_id: str
    verdict: Literal["GO", "HOLD"]
    tests: list[str]
    fixtures: list[str]
    evidence: list[str]
    unresolved_items: list[str] = Field(default_factory=list)


# --- Cognitive-extension objects (affect, executive, circadian, theory of
# mind, hedonic, sensorimotor). Wire-format mirrors of the runtime
# dataclasses in brain/affect.py, brain/executive.py, brain/circadian.py,
# brain/theory_of_mind.py, brain/hedonic.py, brain/perception.py, and
# brain/motor.py -- the dataclasses remain the hot-path runtime
# representation; these are the validated schemas for anything crossing a
# process/storage/API boundary, matching how Belief/Signal/Outcome above
# mirror brain/domain.py's dataclasses.


class EmotionalStateSchema(BrainSchema):
    valence: float = Field(ge=-1.0, le=1.0)
    arousal: float = Field(ge=0.0, le=1.0)
    dominance: float = Field(ge=0.0, le=1.0)
    label: Literal[
        "joy", "interest", "relief", "pride", "fear", "anger", "frustration",
        "sadness", "disgust", "surprise", "boredom", "neutral",
    ]
    intensity: float = Field(ge=0.0, le=1.0)


class MoodSchema(BrainSchema):
    valence: float = Field(ge=-1.0, le=1.0)
    arousal_baseline: float = Field(ge=0.0, le=1.0)
    momentum: float = Field(ge=0.0, le=1.0)


class ResponseCandidateSchema(BrainSchema):
    action: str
    source: Literal["habitual", "deliberate"]
    prepotency: float = Field(ge=0.0, le=1.0)
    goal_alignment: float = Field(ge=-1.0, le=1.0)
    expected_value: float


class ExecutiveDecisionSchema(BrainSchema):
    chosen_action: str
    conflict_magnitude: float = Field(ge=0.0, le=1.0)
    override_attempted: bool
    override_succeeded: bool
    control_cost: float = Field(ge=0.0)
    effective_control: float = Field(ge=0.0, le=1.0)


class CircadianStateSchema(BrainSchema):
    phase: Literal["wake", "nrem", "rem"]
    pressure_ratio: float = Field(ge=0.0, le=1.0)
    oscillator_wake_drive: float = Field(ge=0.0, le=1.0)
    cycles_completed_this_sleep: int = Field(ge=0)


class AttributedBeliefSchema(BrainSchema):
    agent_id: str
    statement: str
    believed_confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str]


class AgentPredictionRecordSchema(BrainSchema):
    agent_id: str
    predicted_action: str
    actual_action: str | None = None
    correct: bool | None = None


class RewardPredictionErrorSchema(BrainSchema):
    expected_value: float
    actual_value: float


class PainSignalSchema(BrainSchema):
    intensity: float = Field(ge=0.0, le=1.0)
    source: str
    withdrawal_urgency: float = Field(ge=0.0, le=1.0)


class PerceptSchema(BrainSchema):
    modality: Literal["text", "numeric", "structured", "image", "audio"]
    raw_ref: str
    features: dict[str, float]
    novelty: float = Field(ge=0.0, le=1.0)


class MotorExecutionResultSchema(BrainSchema):
    action_description: str
    effector_name: str
    expected_outcome: float
    actual_outcome: float
    succeeded: bool
    error: float


CANONICAL_SCHEMAS: dict[str, type[BrainSchema]] = {
    "Source": Source,
    "Sensor": Sensor,
    "RawObservation": RawObservation,
    "PerceptualEvent": PerceptualEvent,
    "EvidenceItem": EvidenceItem,
    "Entity": Entity,
    "Belief": Belief,
    "Signal": Signal,
    "Opportunity": Opportunity,
    "CandidateAction": CandidateAction,
    "ApprovalRequest": ApprovalRequest,
    "Outcome": Outcome,
    "Prediction": Prediction,
    "RewardEvent": RewardEvent,
    "PainEvent": PainEvent,
    "MemoryObject": MemoryObject,
    "GraphNode": GraphNode,
    "GraphEdge": GraphEdge,
    "FormulaRun": FormulaRun,
    "DecisionExplanation": DecisionExplanation,
    "AcceptanceReport": AcceptanceReport,
    "EmotionalState": EmotionalStateSchema,
    "Mood": MoodSchema,
    "ResponseCandidate": ResponseCandidateSchema,
    "ExecutiveDecision": ExecutiveDecisionSchema,
    "CircadianState": CircadianStateSchema,
    "AttributedBelief": AttributedBeliefSchema,
    "AgentPredictionRecord": AgentPredictionRecordSchema,
    "RewardPredictionError": RewardPredictionErrorSchema,
    "PainSignal": PainSignalSchema,
    "Percept": PerceptSchema,
    "MotorExecutionResult": MotorExecutionResultSchema,
}


def validate_object(kind: str, payload: dict[str, Any]) -> BrainSchema:
    schema = CANONICAL_SCHEMAS[kind]
    return schema.model_validate(payload)


def schema_names() -> list[str]:
    return sorted(CANONICAL_SCHEMAS)
