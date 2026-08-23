from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from ..domain import utcnow


@dataclass(slots=True)
class DreamScenario:
    prompt: str
    source_refs: list[str]
    proposed_actions: list[str] = field(default_factory=list)
    simulated: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class MemoryRecord:
    content: str
    source_refs: list[str]
    salience: float = 0.5
    linked_ids: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class MemoryCompression:
    source_memory_ids: list[UUID]
    compressed_content: str
    source_refs: list[str]
    reversible: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class RehearsalTrace:
    scenario_id: UUID
    rehearsed_memory_ids: list[UUID]
    source_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class DreamRewireProposal:
    scenario_id: UUID
    description: str
    source_refs: list[str]
    proposal_only: bool = True
    external_action_authorized: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ConsolidationRun:
    compression_ids: list[UUID]
    rehearsal_ids: list[UUID]
    proposal_ids: list[UUID]
    source_refs: list[str]
    external_actions_executed: int = 0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


class DreamSimulationService:
    """Offline scenario generation. Dream output is proposal-only by construction."""

    def simulate(self, scenario: DreamScenario) -> list[DreamRewireProposal]:
        if not scenario.source_refs:
            raise ValueError("dream simulation requires provenance")
        if not scenario.simulated:
            raise ValueError("dream scenarios must remain explicitly simulated")
        return [
            DreamRewireProposal(
                scenario_id=scenario.id,
                description=action,
                source_refs=list(scenario.source_refs),
                proposal_only=True,
                external_action_authorized=False,
            )
            for action in scenario.proposed_actions
        ]


class MemoryCompressionService:
    """Compress repeated memory while preserving every source reference and source id."""

    def compress(self, memories: list[MemoryRecord]) -> MemoryCompression:
        if not memories:
            raise ValueError("memory compression requires source memories")
        if any(not memory.source_refs for memory in memories):
            raise ValueError("memory compression cannot erase provenance")
        ordered = sorted(memories, key=lambda memory: (memory.content, str(memory.id)))
        unique_contents = list(dict.fromkeys(memory.content.strip() for memory in ordered if memory.content.strip()))
        compressed = " | ".join(unique_contents)
        return MemoryCompression(
            source_memory_ids=[memory.id for memory in ordered],
            compressed_content=compressed,
            source_refs=sorted({ref for memory in ordered for ref in memory.source_refs}),
            reversible=True,
        )


class ConsolidationService:
    """Run compression and rehearsal and emit only governed rewire proposals."""

    def __init__(self) -> None:
        self.compression = MemoryCompressionService()
        self.dreams = DreamSimulationService()

    def run(
        self,
        *,
        memories: list[MemoryRecord],
        scenarios: list[DreamScenario],
    ) -> tuple[ConsolidationRun, list[MemoryCompression], list[RehearsalTrace], list[DreamRewireProposal]]:
        compressions: list[MemoryCompression] = []
        rehearsals: list[RehearsalTrace] = []
        proposals: list[DreamRewireProposal] = []
        if memories:
            compressions.append(self.compression.compress(memories))
        for scenario in scenarios:
            scenario_proposals = self.dreams.simulate(scenario)
            proposals.extend(scenario_proposals)
            rehearsals.append(
                RehearsalTrace(
                    scenario_id=scenario.id,
                    rehearsed_memory_ids=[memory.id for memory in memories],
                    source_refs=sorted(
                        set(scenario.source_refs + [ref for memory in memories for ref in memory.source_refs])
                    ),
                )
            )
        source_refs = sorted(
            {ref for memory in memories for ref in memory.source_refs}
            | {ref for scenario in scenarios for ref in scenario.source_refs}
        )
        run = ConsolidationRun(
            compression_ids=[item.id for item in compressions],
            rehearsal_ids=[item.id for item in rehearsals],
            proposal_ids=[item.id for item in proposals],
            source_refs=source_refs,
            external_actions_executed=0,
        )
        return run, compressions, rehearsals, proposals
