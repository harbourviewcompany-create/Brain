from __future__ import annotations

import json
from pathlib import Path

from brain.neuro import (
    UnknownMechanismRecord,
    UnknownMechanismRegistryService,
    UnknownMechanismValidationService,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs/neuroscience/json/unknown-mechanism-registry.json"
FIXTURE_PATH = ROOT / "tests/fixtures/neuro/unknown_mechanism_registry.json"


def load_unknowns() -> list[UnknownMechanismRecord]:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return [
        UnknownMechanismRecord.model_validate(item)
        for item in data["unknown_mechanisms"]
    ]


def test_unknown_mechanisms_are_materialized() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    records = load_unknowns()
    service = UnknownMechanismRegistryService(records)

    assert len(records) >= fixture["expected"]["minimum_unknown_count"]
    assert set(fixture["expected"]["required_unknown_ids"]).issubset(
        set(service.unresolved_ids())
    )


def test_unknown_mechanisms_remain_hold() -> None:
    records = load_unknowns()
    validator = UnknownMechanismValidationService()

    assert validator.validate_all_records_hold(records) == []


def test_unknown_mechanisms_have_claim_boundaries() -> None:
    records = load_unknowns()
    service = UnknownMechanismRegistryService(records)

    assert service.missing_claim_boundaries() == []
    assert service.missing_execution_mappings() == []


def test_unknown_mechanisms_block_overclaims() -> None:
    records = load_unknowns()
    service = UnknownMechanismRegistryService(records)

    assert service.overclaim_violations() == []
    assert all(record.forbidden_claims for record in records)
