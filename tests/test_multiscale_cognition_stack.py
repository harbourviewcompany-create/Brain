from __future__ import annotations

import json
from pathlib import Path

from brain.neuro.multiscale import MultiscaleCognitionService, MultiscaleCognitionStack

ROOT = Path(__file__).resolve().parents[1]
STACK_PATH = ROOT / "docs/neuroscience/json/multiscale-cognition-stack.json"
FIXTURE_PATH = ROOT / "tests/fixtures/neuro/multiscale_cognition_stack.json"


def load_stack() -> MultiscaleCognitionStack:
    data = json.loads(STACK_PATH.read_text(encoding="utf-8"))
    return MultiscaleCognitionStack.model_validate(data)


def test_all_required_scale_levels_exist() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    stack = load_stack()
    service = MultiscaleCognitionService(stack)

    assert {level.level_id for level in stack.levels} == set(fixture["expected"]["required_levels"])
    assert service.missing_levels() == []


def test_scale_levels_have_executable_mappings() -> None:
    stack = load_stack()
    service = MultiscaleCognitionService(stack)

    assert service.missing_executable_mappings() == []


def test_cross_scale_dependencies_have_valid_endpoints() -> None:
    stack = load_stack()
    service = MultiscaleCognitionService(stack)

    assert service.invalid_dependencies() == []


def test_no_scale_claims_complete_biological_equivalence() -> None:
    stack = load_stack()
    service = MultiscaleCognitionService(stack)

    assert service.equivalence_violations() == []
