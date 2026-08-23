from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from math import exp
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class EpisodicMemory:
    content: str
    occurred_at: datetime
    learned_at: datetime
    source_refs: list[str]
    context: dict[str, str] = field(default_factory=dict)
    salience: float = 0.5
    confidence: float = 0.5
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class SemanticMemory:
    statement: str
    source_episode_ids: list[UUID]
    source_refs: list[str]
    confidence: float
    last_validated_at: datetime = field(default_factory=utcnow)
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ProceduralMemory:
    procedure: str
    steps: list[str]
    source_refs: list[str]
    success_count: int = 0
    failure_count: int = 0
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ProspectiveMemory:
    intention: str
    due_at: datetime | None
    trigger: str | None
    source_refs: list[str]
    completed: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ReconsolidationRecord:
    memory_id: UUID
    previous_content: str
    revised_content: str
    reason: str
    evidence_refs: list[str]
    reversible: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class MemoryRetrieval:
    memory_id: UUID
    score: float
    reason: list[str]
    source_refs: list[str]


class MultiSystemMemory:
    """Source-aware episodic, semantic, procedural and prospective memory."""

    def __init__(self) -> None:
        self.episodes: dict[UUID, EpisodicMemory] = {}
        self.semantics: dict[UUID, SemanticMemory] = {}
        self.procedures: dict[UUID, ProceduralMemory] = {}
        self.prospective: dict[UUID, ProspectiveMemory] = {}
        self.reconsolidations: list[ReconsolidationRecord] = []

    def remember_episode(self, memory: EpisodicMemory) -> EpisodicMemory:
        if not memory.source_refs:
            raise ValueError("episodic memory requires source provenance")
        self.episodes[memory.id] = memory
        return memory

    def consolidate_semantic(
        self,
        statement: str,
        episode_ids: list[UUID],
        *,
        confidence: float,
    ) -> SemanticMemory:
        if not episode_ids:
            raise ValueError("semantic consolidation requires episodes")
        episodes = [self.episodes[episode_id] for episode_id in episode_ids]
        refs = sorted({ref for episode in episodes for ref in episode.source_refs})
        if not refs:
            raise ValueError("semantic consolidation cannot create source amnesia")
        memory = SemanticMemory(
            statement=statement,
            source_episode_ids=list(episode_ids),
            source_refs=refs,
            confidence=_clamp01(confidence),
        )
        self.semantics[memory.id] = memory
        return memory

    def remember_procedure(self, memory: ProceduralMemory) -> ProceduralMemory:
        if not memory.source_refs or not memory.steps:
            raise ValueError("procedural memory requires source evidence and steps")
        self.procedures[memory.id] = memory
        return memory

    def record_procedure_outcome(self, memory_id: UUID, *, success: bool) -> ProceduralMemory:
        memory = self.procedures[memory_id]
        if success:
            memory.success_count += 1
        else:
            memory.failure_count += 1
        return memory

    def remember_intention(self, memory: ProspectiveMemory) -> ProspectiveMemory:
        if not memory.source_refs:
            raise ValueError("prospective memory requires provenance")
        if memory.due_at is None and not memory.trigger:
            raise ValueError("prospective memory requires time or trigger")
        self.prospective[memory.id] = memory
        return memory

    def due_intentions(self, *, at: datetime | None = None, trigger: str | None = None) -> list[ProspectiveMemory]:
        at = at or utcnow()
        due = []
        for memory in self.prospective.values():
            if memory.completed:
                continue
            time_due = memory.due_at is not None and memory.due_at <= at
            trigger_due = trigger is not None and memory.trigger == trigger
            if time_due or trigger_due:
                due.append(memory)
        return due

    @staticmethod
    def forgetting_strength(
        memory: EpisodicMemory,
        *,
        at: datetime | None = None,
        half_life_days: float = 90.0,
    ) -> float:
        at = at or utcnow()
        age_days = max((at - memory.learned_at).total_seconds() / 86400.0, 0.0)
        retention = exp(-0.69314718056 * age_days / max(half_life_days, 0.01))
        return _clamp01(retention * (0.5 + 0.5 * _clamp01(memory.salience)))

    def retrieve_episodes(
        self,
        query: str,
        *,
        at: datetime | None = None,
        limit: int = 10,
    ) -> list[MemoryRetrieval]:
        terms = {term for term in query.lower().split() if term}
        results: list[MemoryRetrieval] = []
        for memory in self.episodes.values():
            words = set(memory.content.lower().split())
            lexical = len(terms & words) / max(len(terms), 1)
            retention = self.forgetting_strength(memory, at=at)
            score = _clamp01(lexical * 0.65 + retention * 0.2 + memory.confidence * 0.15)
            if score <= 0:
                continue
            results.append(
                MemoryRetrieval(
                    memory.id,
                    score,
                    [f"lexical={lexical:.2f}", f"retention={retention:.2f}"],
                    list(memory.source_refs),
                )
            )
        return sorted(results, key=lambda item: (item.score, str(item.memory_id)), reverse=True)[:limit]

    def reconsolidate_episode(
        self,
        memory_id: UUID,
        *,
        revised_content: str,
        reason: str,
        evidence_refs: list[str],
    ) -> tuple[EpisodicMemory, ReconsolidationRecord]:
        if not evidence_refs:
            raise ValueError("memory reconsolidation requires new evidence")
        memory = self.episodes[memory_id]
        record = ReconsolidationRecord(
            memory_id=memory_id,
            previous_content=memory.content,
            revised_content=revised_content,
            reason=reason,
            evidence_refs=list(evidence_refs),
            reversible=True,
        )
        updated = replace(
            memory,
            content=revised_content,
            source_refs=sorted(set(memory.source_refs + evidence_refs)),
            learned_at=utcnow(),
        )
        self.episodes[memory_id] = updated
        self.reconsolidations.append(record)
        return updated, record

    def rollback_reconsolidation(self, record: ReconsolidationRecord) -> EpisodicMemory:
        if not record.reversible:
            raise ValueError("reconsolidation record is not reversible")
        memory = self.episodes[record.memory_id]
        restored = replace(memory, content=record.previous_content)
        self.episodes[record.memory_id] = restored
        return restored
