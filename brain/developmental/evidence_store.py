from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol
from uuid import UUID, uuid4

from .improvement_experiments import (
    ExperimentCandidate,
    ExperimentResult,
    ExperimentRun,
    ImprovementExperiment,
    PromotionDecision,
    RollbackRecord,
)
from .metacognitive_optimization import (
    BenchmarkEvidenceClass,
    BenchmarkRun,
    CapabilityBenchmark,
    ImprovementHypothesis,
    LearningDebtItem,
    OptimizationPlanState,
    RegressionSignal,
    SelfOptimizationPlan,
)


@dataclass(slots=True)
class DevelopmentalCycleCheckpoint:
    cycle_id: UUID
    state: str
    related_record_ids: list[UUID]
    metadata: dict[str, Any]
    id: UUID = field(default_factory=uuid4)


RECORD_TYPES: dict[str, type[Any]] = {
    cls.__name__: cls
    for cls in (
        CapabilityBenchmark,
        BenchmarkRun,
        RegressionSignal,
        ImprovementHypothesis,
        LearningDebtItem,
        SelfOptimizationPlan,
        ExperimentCandidate,
        ImprovementExperiment,
        ExperimentRun,
        ExperimentResult,
        RollbackRecord,
        DevelopmentalCycleCheckpoint,
    )
}

ENUM_TYPES: dict[str, type[Enum]] = {
    cls.__name__: cls
    for cls in (
        BenchmarkEvidenceClass,
        OptimizationPlanState,
        PromotionDecision,
    )
}


def _encode_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return {"__uuid__": str(value)}
    if isinstance(value, datetime):
        return {"__datetime__": value.isoformat()}
    if isinstance(value, Enum):
        return {"__enum__": type(value).__name__, "value": value.value}
    if is_dataclass(value):
        return {
            "__type__": type(value).__name__,
            "fields": {key: _encode_value(item) for key, item in asdict(value).items()},
        }
    if isinstance(value, dict):
        return {str(key): _encode_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_encode_value(item) for item in value]
    return value


def _decode_value(value: Any) -> Any:
    if isinstance(value, list):
        return [_decode_value(item) for item in value]
    if not isinstance(value, dict):
        return value
    if "__uuid__" in value:
        return UUID(value["__uuid__"])
    if "__datetime__" in value:
        return datetime.fromisoformat(value["__datetime__"])
    if "__enum__" in value:
        enum_type = ENUM_TYPES.get(value["__enum__"])
        if enum_type is None:
            raise ValueError(f"unknown_developmental_enum:{value['__enum__']}")
        return enum_type(value["value"])
    if "__type__" in value:
        record_type = RECORD_TYPES.get(value["__type__"])
        if record_type is None:
            raise ValueError(f"unknown_developmental_record_type:{value['__type__']}")
        decoded = {key: _decode_value(item) for key, item in value.get("fields", {}).items()}
        valid_names = {item.name for item in fields(record_type)}
        unknown = set(decoded) - valid_names
        if unknown:
            raise ValueError(f"unknown_developmental_fields:{sorted(unknown)}")
        return record_type(**decoded)
    return {key: _decode_value(item) for key, item in value.items()}


class DevelopmentalEvidenceCodec:
    @staticmethod
    def encode(record: Any) -> dict[str, Any]:
        if type(record).__name__ not in RECORD_TYPES:
            raise ValueError(f"unsupported_developmental_record:{type(record).__name__}")
        encoded = _encode_value(record)
        if not isinstance(encoded, dict):
            raise ValueError("developmental_record_encoding_failed")
        return encoded

    @staticmethod
    def decode(payload: dict[str, Any]) -> Any:
        return _decode_value(payload)


@dataclass(slots=True)
class DevelopmentalEvidenceEvent:
    sequence: int
    event_type: str
    record_kind: str
    record_id: UUID
    payload: dict[str, Any]
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class DevelopmentalEvidenceStore(Protocol):
    def put(self, record: Any, *, event_type: str, evidence_refs: list[str]) -> None: ...
    def get(self, record_kind: str, record_id: UUID) -> Any | None: ...
    def list(self, record_kind: str) -> list[Any]: ...
    def events(self) -> list[DevelopmentalEvidenceEvent]: ...


class InMemoryDevelopmentalEvidenceStore:
    def __init__(self) -> None:
        self._objects: dict[str, dict[UUID, Any]] = {}
        self._events: list[DevelopmentalEvidenceEvent] = []

    def put(self, record: Any, *, event_type: str, evidence_refs: list[str]) -> None:
        if not evidence_refs:
            raise ValueError("developmental_evidence_write_requires_evidence")
        record_id = getattr(record, "id", None)
        if not isinstance(record_id, UUID):
            raise ValueError("developmental_record_requires_uuid_id")
        kind = type(record).__name__
        payload = DevelopmentalEvidenceCodec.encode(record)
        self._objects.setdefault(kind, {})[record_id] = DevelopmentalEvidenceCodec.decode(payload)
        self._events.append(
            DevelopmentalEvidenceEvent(
                sequence=len(self._events) + 1,
                event_type=event_type,
                record_kind=kind,
                record_id=record_id,
                payload=payload,
                evidence_refs=list(evidence_refs),
            )
        )

    def get(self, record_kind: str, record_id: UUID) -> Any | None:
        return self._objects.get(record_kind, {}).get(record_id)

    def list(self, record_kind: str) -> list[Any]:
        return list(self._objects.get(record_kind, {}).values())

    def events(self) -> list[DevelopmentalEvidenceEvent]:
        return list(self._events)


class DevelopmentalReplayService:
    def replay(self, events: list[DevelopmentalEvidenceEvent]) -> InMemoryDevelopmentalEvidenceStore:
        expected = 1
        store = InMemoryDevelopmentalEvidenceStore()
        for event in sorted(events, key=lambda item: item.sequence):
            if event.sequence != expected:
                raise ValueError("developmental_evidence_sequence_gap")
            if not event.evidence_refs:
                raise ValueError("developmental_evidence_event_requires_evidence")
            record = DevelopmentalEvidenceCodec.decode(event.payload)
            if getattr(record, "id", None) != event.record_id:
                raise ValueError("developmental_evidence_record_id_mismatch")
            store._objects.setdefault(event.record_kind, {})[event.record_id] = record
            store._events.append(event)
            expected += 1
        return store

    @staticmethod
    def integrity_report(store: DevelopmentalEvidenceStore) -> dict[str, Any]:
        events = store.events()
        sequences = [event.sequence for event in events]
        contiguous = sequences == list(range(1, len(sequences) + 1))
        return {
            "event_count": len(events),
            "last_sequence": sequences[-1] if sequences else 0,
            "sequence_contiguous": contiguous,
            "failed_or_hold_results": len(
                [
                    record
                    for record in store.list("ExperimentResult")
                    if record.decision in {PromotionDecision.REJECT, PromotionDecision.HOLD}
                ]
            ),
            "unresolved_regressions": len(
                [record for record in store.list("RegressionSignal") if not record.resolved]
            ),
            "cycle_checkpoints": len(store.list("DevelopmentalCycleCheckpoint")),
            "persistence_authority": "evidence_only_no_mutation_merge_deploy",
        }
