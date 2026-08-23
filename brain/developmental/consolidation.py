from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class MemoryTrace:
    content: str
    salience: float
    source_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class DreamProposal:
    source_memory_ids: list[UUID]
    proposal: str
    simulated: bool = True
    can_execute_external_action: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ConsolidationRecord:
    memory_ids: list[UUID]
    compressed_summary: str
    preserved_source_refs: list[str]
    rewire_proposal_ids: list[UUID]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class SleepConsolidationService:
    memories: dict[UUID, MemoryTrace] = field(default_factory=dict)
    dream_proposals: list[DreamProposal] = field(default_factory=list)
    consolidations: list[ConsolidationRecord] = field(default_factory=list)

    def add_memory(self, *, content: str, salience: float, source_refs: list[str]) -> MemoryTrace:
        if not source_refs:
            raise ValueError("memory_requires_source_refs")
        trace = MemoryTrace(content=content, salience=salience, source_refs=list(source_refs))
        self.memories[trace.id] = trace
        return trace

    def dream(self, memory_ids: list[UUID], *, proposal: str) -> DreamProposal:
        if not memory_ids:
            raise ValueError("dream_requires_memories")
        for memory_id in memory_ids:
            if memory_id not in self.memories:
                raise ValueError("dream_memory_missing")
        dream = DreamProposal(
            source_memory_ids=list(memory_ids),
            proposal=proposal,
            simulated=True,
            can_execute_external_action=False,
        )
        self.dream_proposals.append(dream)
        return dream

    def consolidate(self, memory_ids: list[UUID], *, compressed_summary: str) -> ConsolidationRecord:
        if not memory_ids:
            raise ValueError("consolidation_requires_memories")
        preserved: list[str] = []
        for memory_id in memory_ids:
            memory = self.memories[memory_id]
            preserved.extend(memory.source_refs)
        record = ConsolidationRecord(
            memory_ids=list(memory_ids),
            compressed_summary=compressed_summary,
            preserved_source_refs=sorted(set(preserved)),
            rewire_proposal_ids=[proposal.id for proposal in self.dream_proposals],
        )
        self.consolidations.append(record)
        return record
