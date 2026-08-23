from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BeliefState(StrEnum):
    HYPOTHESIS = "hypothesis"
    PROVISIONAL = "provisional"
    ESTABLISHED = "established"
    CONTESTED = "contested"
    REJECTED = "rejected"
    DORMANT = "dormant"


class RewireOperation(StrEnum):
    CREATE_NODE = "create_node"
    CREATE_EDGE = "create_edge"
    STRENGTHEN_EDGE = "strengthen_edge"
    WEAKEN_EDGE = "weaken_edge"
    PRUNE_EDGE = "prune_edge"
    MERGE_NODES = "merge_nodes"
    SPLIT_NODE = "split_node"
    PROMOTE_BELIEF = "promote_belief"
    DEMOTE_BELIEF = "demote_belief"


@dataclass(slots=True)
class Observation:
    content: str
    source_id: str
    observed_at: datetime = field(default_factory=utcnow)
    id: UUID = field(default_factory=uuid4)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Evidence:
    claim: str
    source_id: str
    reliability: float
    observation_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Belief:
    statement: str
    confidence: float = 0.5
    state: BeliefState = BeliefState.HYPOTHESIS
    id: UUID = field(default_factory=uuid4)
    supporting_evidence: set[UUID] = field(default_factory=set)
    contradicting_evidence: set[UUID] = field(default_factory=set)
    unknowns: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=utcnow)
    version: int = 1


@dataclass(slots=True)
class Node:
    kind: str
    key: str
    properties: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class Edge:
    source: UUID
    target: UUID
    relation: str
    weight: float = 0.5
    confidence: float = 0.5
    id: UUID = field(default_factory=uuid4)
    evidence_ids: set[UUID] = field(default_factory=set)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class RewireEvent:
    operation: RewireOperation
    reason: str
    target_id: UUID
    previous: dict[str, Any]
    current: dict[str, Any]
    evidence_ids: list[UUID] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class CandidateAction:
    description: str
    expected_value: float
    uncertainty: float
    external: bool = False
    id: UUID = field(default_factory=uuid4)
    rationale: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Outcome:
    action_id: UUID
    value_created: float
    operator_time_cost: float
    prediction_accuracy: float
    trust_impact: float = 0.0
    legal_risk: float = 0.0
    prediction_id: UUID | None = None
    edge_ids: list[UUID] = field(default_factory=list)
    source_keys: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
