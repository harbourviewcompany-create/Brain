from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from difflib import SequenceMatcher
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class WorldObservation:
    source_id: str
    modality: str
    content: str
    world_valid_from: datetime
    observed_at: datetime = field(default_factory=utcnow)
    world_valid_to: datetime | None = None
    geography: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class WorldEntity:
    canonical_name: str
    kind: str
    aliases: set[str] = field(default_factory=set)
    attributes: dict[str, str | float | bool | None] = field(default_factory=dict)
    source_observation_ids: set[UUID] = field(default_factory=set)
    confidence: float = 0.5
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class WorldRelation:
    source_entity_id: UUID
    target_entity_id: UUID
    relation: str
    confidence: float
    evidence_refs: list[str]
    world_valid_from: datetime
    learned_at: datetime = field(default_factory=utcnow)
    world_valid_to: datetime | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class WorldChange:
    entity_id: UUID
    attribute: str
    previous_value: str | float | bool | None
    current_value: str | float | bool | None
    world_valid_at: datetime
    learned_at: datetime
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class BitemporalWorldModel:
    """World state keeps world-valid time separate from when the Brain learned it."""

    def __init__(self) -> None:
        self.observations: dict[UUID, WorldObservation] = {}
        self.entities: dict[UUID, WorldEntity] = {}
        self.relations: dict[UUID, WorldRelation] = {}
        self.changes: list[WorldChange] = []

    def ingest(self, observation: WorldObservation) -> WorldObservation:
        if not observation.source_id or not observation.evidence_refs:
            raise ValueError("world observation requires source and evidence provenance")
        if observation.world_valid_to and observation.world_valid_to < observation.world_valid_from:
            raise ValueError("world-valid interval is inverted")
        self.observations[observation.id] = observation
        return observation

    def resolve_entity(
        self,
        *,
        name: str,
        kind: str,
        observation_id: UUID,
        attributes: dict[str, str | float | bool | None] | None = None,
        similarity_threshold: float = 0.92,
    ) -> WorldEntity:
        observation = self.observations.get(observation_id)
        if observation is None:
            raise KeyError("observation_not_found")
        normalized = name.strip().lower()
        candidates = [entity for entity in self.entities.values() if entity.kind == kind]
        best = max(
            candidates,
            key=lambda entity: SequenceMatcher(None, normalized, entity.canonical_name.lower()).ratio(),
            default=None,
        )
        similarity = (
            SequenceMatcher(None, normalized, best.canonical_name.lower()).ratio() if best else 0.0
        )
        if best is None or similarity < similarity_threshold:
            best = WorldEntity(canonical_name=name.strip(), kind=kind)
            self.entities[best.id] = best
        elif best.canonical_name.lower() != normalized:
            best.aliases.add(name.strip())
        best.source_observation_ids.add(observation_id)
        best.confidence = min(1.0, best.confidence + 0.05)
        for key, value in (attributes or {}).items():
            previous = best.attributes.get(key)
            if key in best.attributes and previous != value:
                self.changes.append(
                    WorldChange(
                        entity_id=best.id,
                        attribute=key,
                        previous_value=previous,
                        current_value=value,
                        world_valid_at=observation.world_valid_from,
                        learned_at=observation.observed_at,
                        evidence_refs=list(observation.evidence_refs),
                    )
                )
            best.attributes[key] = value
        return best

    def relate(
        self,
        source_entity_id: UUID,
        target_entity_id: UUID,
        relation: str,
        *,
        confidence: float,
        evidence_refs: list[str],
        world_valid_from: datetime,
        world_valid_to: datetime | None = None,
    ) -> WorldRelation:
        if source_entity_id not in self.entities or target_entity_id not in self.entities:
            raise KeyError("relation_entity_not_found")
        if not evidence_refs:
            raise ValueError("world relation requires provenance")
        edge = WorldRelation(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation=relation,
            confidence=max(0.0, min(1.0, confidence)),
            evidence_refs=list(evidence_refs),
            world_valid_from=world_valid_from,
            world_valid_to=world_valid_to,
        )
        self.relations[edge.id] = edge
        return edge

    def state_as_of(self, entity_id: UUID, at: datetime) -> dict[str, str | float | bool | None]:
        entity = self.entities[entity_id]
        state = dict(entity.attributes)
        relevant = sorted(
            [change for change in self.changes if change.entity_id == entity_id],
            key=lambda item: (item.world_valid_at, str(item.id)),
            reverse=True,
        )
        for change in relevant:
            if change.world_valid_at > at:
                if change.previous_value is None:
                    state.pop(change.attribute, None)
                else:
                    state[change.attribute] = change.previous_value
        return state
