from __future__ import annotations

import json
from pathlib import Path

from brain.neuro import NeuroscienceTheory, TheoryConflict, TheoryRegistryService, TheoryValidationService

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs/neuroscience/json/theory-conflict-registry.json"
FIXTURE_PATH = ROOT / "tests/fixtures/neuro/theory_conflict_registry.json"


def load_theories() -> tuple[list[NeuroscienceTheory], list[TheoryConflict]]:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    theories = [NeuroscienceTheory.model_validate(item) for item in data["theories"]]
    conflicts = [TheoryConflict.model_validate(item) for item in data["conflicts"]]
    return theories, conflicts


def test_theory_registry_is_materialized() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    theories, conflicts = load_theories()

    assert len(theories) >= fixture["expected"]["minimum_theory_count"]
    assert len(conflicts) >= fixture["expected"]["minimum_conflict_count"]
    assert set(fixture["expected"]["required_theory_ids"]).issubset(
        {theory.theory_id for theory in theories}
    )


def test_competing_theories_have_explicit_conflicts() -> None:
    theories, conflicts = load_theories()
    service = TheoryRegistryService(theories, conflicts)

    assert service.invalid_conflict_references() == []
    assert service.missing_competing_conflicts() == []


def test_disputed_or_competing_theories_do_not_go_without_gate() -> None:
    theories, conflicts = load_theories()
    service = TheoryRegistryService(theories, conflicts)

    assert service.unsafe_implementation_postures() == []


def test_theory_boundaries_and_evidence_exist() -> None:
    theories, conflicts = load_theories()
    validator = TheoryValidationService()

    assert validator.validate(theories, conflicts) == []
