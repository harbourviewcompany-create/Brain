from __future__ import annotations

import json
from pathlib import Path

from brain.neuro.regions import BrainRegionFunction, BrainRegionMappingService

ROOT = Path(__file__).resolve().parents[1]
REGION_PATH = ROOT / "docs/neuroscience/json/brain-region-map.json"
FIXTURE_PATH = ROOT / "tests/fixtures/neuro/brain_region_software_map.json"


def load_regions() -> list[BrainRegionFunction]:
    data = json.loads(REGION_PATH.read_text(encoding="utf-8"))
    return [BrainRegionFunction.model_validate(item) for item in data["regions"]]


def test_required_brain_regions_are_mapped() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    regions = load_regions()
    service = BrainRegionMappingService(regions)

    assert len(regions) >= fixture["expected"]["minimum_region_count"]
    assert service.missing_required_regions() == []


def test_region_entries_have_software_equivalents() -> None:
    regions = load_regions()
    service = BrainRegionMappingService(regions)

    assert service.missing_executable_mappings() == []


def test_region_entries_do_not_claim_literal_equivalence() -> None:
    regions = load_regions()
    service = BrainRegionMappingService(regions)

    assert service.literal_equivalence_violations() == []


def test_region_failure_modes_exist() -> None:
    regions = load_regions()

    assert all(region.failure_modes for region in regions)
    assert all(region.acceptance_criteria for region in regions)
