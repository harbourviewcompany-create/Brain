from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MemorySystemKind(StrEnum):
    ICONIC = "iconic"
    ECHOIC = "echoic"
    SENSORY_TRACE = "sensory_trace"
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    EMOTIONAL = "emotional"
    SPATIAL = "spatial"
    AUTOBIOGRAPHICAL = "autobiographical"
    PROSPECTIVE = "prospective"
    SOURCE = "source"
    RELATIONAL = "relational"
    SOCIAL = "social"
    SKILL = "skill"
    HABIT = "habit"
    THREAT = "threat"
    PREFERENCE = "preference"
    CONTRADICTION = "contradiction"
    UNCERTAINTY = "uncertainty"
    FAILURE = "failure"
    DREAM_HYPOTHESIS = "dream_hypothesis"
    QUARANTINED = "quarantined"


class MemoryLifecycleState(StrEnum):
    ENCODED = "encoded"
    RETRIEVABLE = "retrievable"
    CONSOLIDATED = "consolidated"
    RECONSOLIDATED = "reconsolidated"
    DECAY_CANDIDATE = "decay_candidate"
    FORGOTTEN = "forgotten"
    QUARANTINED = "quarantined"


class MemoryRecord(BaseModel):
    """Executable memory-control object with provenance and GO/HOLD state.

    This is not a claim that software memory is biologically equivalent to human memory.
    It is a typed control record for encoding, retrieval, consolidation, decay and quarantine.
    """

    model_config = ConfigDict(extra="forbid")

    memory_id: str = Field(pattern=r"^MEM-[A-Z0-9-]+$")
    kind: MemorySystemKind
    content_ref: str
    evidence_refs: list[str] = Field(min_length=1)
    source_refs: list[str] = Field(min_length=1)
    provenance: str
    confidence: float = Field(ge=0.0, le=1.0)
    retrieval_cues: list[str] = Field(default_factory=list)
    linked_workspace_frame_ids: list[str] = Field(default_factory=list)
    linked_memory_ids: list[str] = Field(default_factory=list)
    contradiction_refs: list[str] = Field(default_factory=list)
    lifecycle_state: MemoryLifecycleState = MemoryLifecycleState.ENCODED
    retention_policy: Literal["retain", "decay", "forget", "quarantine", "operator_review"]
    replay_required: bool = False
    quarantine_reason: str | None = None
    go_hold_status: Literal["GO", "HOLD"] = "GO"


class MemoryConsolidationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(pattern=r"^MEM-CONS-[A-Z0-9-]+$")
    input_memory_ids: list[str] = Field(min_length=1)
    output_memory_ids: list[str] = Field(default_factory=list)
    operation: Literal[
        "consolidate",
        "reconsolidate",
        "decay",
        "forget",
        "quarantine",
        "replay",
    ]
    evidence_refs: list[str] = Field(min_length=1)
    operator_review_required: bool = False
    audit_event: str


class RichMemorySystemService:
    """Validate and operate on rich memory records without fabricating memory."""

    REQUIRED_KINDS = {kind for kind in MemorySystemKind}

    def __init__(self, records: list[MemoryRecord] | None = None):
        self.records = list(records or [])

    def encode(self, record: MemoryRecord) -> MemoryRecord:
        self._validate_record(record)
        self.records.append(record)
        return record

    def by_id(self, memory_id: str) -> MemoryRecord:
        for record in self.records:
            if record.memory_id == memory_id:
                return record
        raise KeyError(memory_id)

    def retrieve_by_cue(self, cue: str) -> list[MemoryRecord]:
        return [
            record
            for record in self.records
            if cue in record.retrieval_cues
            and record.lifecycle_state not in {
                MemoryLifecycleState.FORGOTTEN,
                MemoryLifecycleState.QUARANTINED,
            }
        ]

    def consolidate(self, memory_id: str, evidence_refs: list[str]) -> MemoryRecord:
        if not evidence_refs:
            raise ValueError("memory_consolidation_requires_evidence")
        record = self.by_id(memory_id)
        updated = record.model_copy(
            update={"lifecycle_state": MemoryLifecycleState.CONSOLIDATED},
        )
        self._replace(updated)
        return updated

    def quarantine(self, memory_id: str, reason: str) -> MemoryRecord:
        if not reason:
            raise ValueError("memory_quarantine_requires_reason")
        record = self.by_id(memory_id)
        updated = record.model_copy(
            update={
                "lifecycle_state": MemoryLifecycleState.QUARANTINED,
                "quarantine_reason": reason,
                "go_hold_status": "HOLD",
                "retention_policy": "quarantine",
            },
        )
        self._replace(updated)
        return updated

    def missing_required_kinds(self) -> list[str]:
        present = {record.kind for record in self.records}
        return sorted(kind.value for kind in self.REQUIRED_KINDS - present)

    def provenance_gaps(self) -> list[str]:
        gaps: list[str] = []
        for record in self.records:
            if not record.evidence_refs or not record.source_refs or not record.provenance:
                gaps.append(record.memory_id)
        return sorted(set(gaps))

    def unsafe_memory_states(self) -> list[str]:
        unsafe: list[str] = []
        for record in self.records:
            if record.kind == MemorySystemKind.QUARANTINED and record.go_hold_status != "HOLD":
                unsafe.append(record.memory_id)
            if record.lifecycle_state == MemoryLifecycleState.QUARANTINED and not record.quarantine_reason:
                unsafe.append(record.memory_id)
            if record.retention_policy == "forget" and record.replay_required:
                unsafe.append(record.memory_id)
        return sorted(set(unsafe))

    def _replace(self, updated: MemoryRecord) -> None:
        self.records = [
            updated if record.memory_id == updated.memory_id else record
            for record in self.records
        ]

    def _validate_record(self, record: MemoryRecord) -> None:
        if not record.evidence_refs:
            raise ValueError("memory_requires_evidence")
        if not record.source_refs:
            raise ValueError("memory_requires_source_refs")
        if not record.provenance:
            raise ValueError("memory_requires_provenance")
        if record.lifecycle_state == MemoryLifecycleState.QUARANTINED:
            if record.go_hold_status != "HOLD" or not record.quarantine_reason:
                raise ValueError("quarantined_memory_requires_hold_and_reason")


class RichMemoryValidationService:
    """Aggregate GO/HOLD checks for NEURO-007 memory systems."""

    def validate(self, records: list[MemoryRecord]) -> list[str]:
        service = RichMemorySystemService(records)
        return sorted(
            set(
                service.missing_required_kinds()
                + service.provenance_gaps()
                + service.unsafe_memory_states()
            )
        )

    def validate_no_fabricated_memory(self, records: list[MemoryRecord]) -> list[str]:
        fabricated: list[str] = []
        blocked_terms = {"fabricated", "unsupported", "invented", "unverified as fact"}
        for record in records:
            provenance = record.provenance.lower()
            if any(term in provenance for term in blocked_terms) and record.go_hold_status == "GO":
                fabricated.append(record.memory_id)
        return sorted(fabricated)
