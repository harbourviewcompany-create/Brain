import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from brain.neuro.memory_systems import (
    MemoryLifecycleState,
    MemoryRecord,
    MemorySystemKind,
    RichMemorySystemService,
    RichMemoryValidationService,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "neuroscience" / "json" / "rich-memory-systems.json"
FIXTURE = ROOT / "tests" / "fixtures" / "neuro" / "rich_memory_systems.json"
MIGRATION = ROOT / "db" / "migrations" / "018_neuro_rich_memory_systems.sql"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def memory_record(kind: MemorySystemKind, suffix: str | None = None) -> MemoryRecord:
    suffix = suffix or kind.value.upper().replace("_", "-")
    return MemoryRecord(
        memory_id=f"MEM-{suffix}-001",
        kind=kind,
        content_ref=f"memory:{kind.value}",
        evidence_refs=[f"evidence:{kind.value}"],
        source_refs=[f"source:{kind.value}"],
        provenance="externally sourced or internally generated with explicit trace",
        confidence=0.77,
        retrieval_cues=[kind.value, "urgent contradiction" if kind == MemorySystemKind.CONTRADICTION else "general"],
        linked_workspace_frame_ids=["workspace:frame-001"],
        retention_policy="operator_review" if kind in {MemorySystemKind.DREAM_HYPOTHESIS, MemorySystemKind.QUARANTINED} else "retain",
        replay_required=kind in {MemorySystemKind.FAILURE, MemorySystemKind.CONTRADICTION},
        go_hold_status="HOLD" if kind in {MemorySystemKind.DREAM_HYPOTHESIS, MemorySystemKind.QUARANTINED} else "GO",
        quarantine_reason="source contamination risk" if kind == MemorySystemKind.QUARANTINED else None,
        lifecycle_state=MemoryLifecycleState.QUARANTINED if kind == MemorySystemKind.QUARANTINED else MemoryLifecycleState.ENCODED,
    )


def test_rich_memory_registry_covers_required_memory_systems() -> None:
    registry = load_json(REGISTRY)
    fixture = load_json(FIXTURE)
    kinds = {item["kind"] for item in registry["memory_systems"]}

    assert registry["slice_id"] == "NEURO-007"
    assert registry["runtime_anchor"] == "brain.neuro.memory_systems.RichMemorySystemService"
    assert len(kinds) == fixture["expected"]["required_count"]
    assert {kind.value for kind in MemorySystemKind}.issubset(kinds)
    assert "human-memory equivalence" in registry["non_claims"]


def test_memory_service_validates_coverage_and_retrieves_by_cue() -> None:
    fixture = load_json(FIXTURE)
    records = [memory_record(kind) for kind in MemorySystemKind]
    service = RichMemorySystemService(records)

    assert service.missing_required_kinds() == []
    retrieved = service.retrieve_by_cue(fixture["expected"]["retrieval_cue"])

    assert [record.memory_id for record in retrieved] == [fixture["expected"]["retrieved_memory_id"]]
    assert RichMemoryValidationService().validate(records) == []


def test_memory_encoding_requires_evidence_source_and_provenance() -> None:
    with pytest.raises(ValidationError):
        MemoryRecord(
            memory_id="MEM-BAD-001",
            kind=MemorySystemKind.SEMANTIC,
            content_ref="memory:bad",
            evidence_refs=[],
            source_refs=["source:bad"],
            provenance="externally sourced",
            confidence=0.5,
            retention_policy="retain",
        )

    with pytest.raises(ValidationError):
        MemoryRecord(
            memory_id="MEM-BAD-002",
            kind=MemorySystemKind.SEMANTIC,
            content_ref="memory:bad",
            evidence_refs=["evidence:bad"],
            source_refs=[],
            provenance="externally sourced",
            confidence=0.5,
            retention_policy="retain",
        )


def test_quarantine_forces_hold_and_excludes_retrieval() -> None:
    fixture = load_json(FIXTURE)
    service = RichMemorySystemService([memory_record(MemorySystemKind.SEMANTIC, "SEMANTIC")])
    quarantined = service.quarantine("MEM-SEMANTIC-001", fixture["expected"]["quarantine_reason"])

    assert quarantined.go_hold_status == "HOLD"
    assert quarantined.lifecycle_state == MemoryLifecycleState.QUARANTINED
    assert quarantined.quarantine_reason == fixture["expected"]["quarantine_reason"]
    assert service.retrieve_by_cue("semantic") == []


def test_no_fabricated_memory_can_remain_go() -> None:
    record = memory_record(MemorySystemKind.SEMANTIC, "FABRICATED")
    fabricated = record.model_copy(update={"provenance": "fabricated memory payload"})

    assert RichMemoryValidationService().validate_no_fabricated_memory([fabricated]) == ["MEM-FABRICATED-001"]


def test_memory_persistence_tables_exist() -> None:
    fixture = load_json(FIXTURE)
    migration = MIGRATION.read_text()

    for table in fixture["expected"]["required_tables"]:
        assert table in migration
    assert "quarantine_reason is not null" in migration
    assert "jsonb_array_length(evidence_refs) > 0" in migration
