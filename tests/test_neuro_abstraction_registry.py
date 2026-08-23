from __future__ import annotations

import json
from pathlib import Path

from brain.neuro.abstractions import (
    MechanismCertainty,
    NeuroAbstraction,
    NeuroAbstractionRegistryService,
    NeuroAbstractionValidationService,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs/neuroscience/json/neuro-abstraction-registry.json"
FIXTURE_PATH = ROOT / "tests/fixtures/neuro/neuro_abstraction_registry.json"


def load_registry() -> list[NeuroAbstraction]:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return [NeuroAbstraction.model_validate(item) for item in data["abstractions"]]


def test_every_abstraction_has_required_mapping_fields() -> None:
    abstractions = load_registry()
    service = NeuroAbstractionRegistryService(abstractions)

    assert len(abstractions) >= 12
    assert service.missing_required_mappings() == []


def test_unknown_or_disputed_mechanisms_are_not_marked_implemented() -> None:
    abstractions = load_registry()
    validator = NeuroAbstractionValidationService()

    for item in abstractions:
        if item.mechanism_certainty in {
            MechanismCertainty.DISPUTED,
            MechanismCertainty.UNKNOWN,
            MechanismCertainty.SPECULATIVE,
        }:
            assert item.mechanism_certainty != MechanismCertainty.IMPLEMENTED
            assert item.unknowns or item.competing_theories

    assert validator.validate_unknowns_not_overclaimed(abstractions) == []


def test_no_abstraction_missing_dashboard_or_acceptance_rule() -> None:
    abstractions = load_registry()
    validator = NeuroAbstractionValidationService()

    assert validator.validate_dashboard_and_acceptance(abstractions) == []


def test_scale_coverage_includes_molecular_cellular_circuit_system_meta() -> None:
    abstractions = load_registry()
    levels = {item.scale_level.value for item in abstractions}

    assert "L0_RESOURCE_SUBSTRATE" in levels
    assert "L1_GLOBAL_MODULATION" in levels
    assert "L2_CELLULAR_PRIMITIVE" in levels
    assert "L3_SYNAPTIC_TOPOLOGY" in levels
    assert "L4_MICROCIRCUIT" in levels
    assert "L5_REGION_ORGAN" in levels
    assert "L8_SELF_MODEL_POLICY" in levels
    assert "L11_DEVELOPMENT_SELF_IMPROVEMENT" in levels


def test_fixture_expected_registry_rules_match_materialized_registry() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    abstractions = load_registry()
    levels = {item.scale_level.value for item in abstractions}

    expected = fixture["expected"]
    assert fixture["fixture_id"] == "neuro_abstraction_registry"
    assert len(abstractions) >= expected["minimum_abstraction_count"]
    assert set(expected["required_scale_levels"]).issubset(levels)
