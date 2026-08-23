import pytest

from brain.developmental.module_genesis import ModuleGenesisService


def test_module_hypothesis_requires_source_traceability() -> None:
    service = ModuleGenesisService()
    with pytest.raises(ValueError, match="source_traceability"):
        service.create_hypothesis(
            name="UntracedModule",
            repeated_pattern="pattern without source",
            source_refs=[],
        )


def test_module_birth_requires_schema_service_fixture_test() -> None:
    service = ModuleGenesisService()
    hypothesis = service.create_hypothesis(
        name="BuyerIntentModule",
        repeated_pattern="buyer intent signals recur across source planes",
        source_refs=["docs/brain-readable-concept-manual.md#buyer-intent"],
    )
    evidence = service.attach_maturity_evidence(
        hypothesis,
        schema_path="brain/schemas.py",
        service_path="brain/developmental/module_genesis.py",
        fixture_path="tests/fixtures/brain/module_birth_acceptance_gate.json",
        test_path="tests/test_developmental_module_genesis.py",
        acceptance_report_path="",
    )

    with pytest.raises(ValueError, match="module_activation_requires"):
        service.activate_module(hypothesis, evidence, active_module_id="MOD-BUYER-INTENT")


def test_module_activation_requires_acceptance_report() -> None:
    service = ModuleGenesisService()
    hypothesis = service.create_hypothesis(
        name="PatternMemoryModule",
        repeated_pattern="same unresolved mechanism appears in three traces",
        source_refs=["docs/spec/BRAIN_DEVELOPMENTAL_INTELLIGENCE_ARCHITECTURE.md"],
    )
    evidence = service.attach_maturity_evidence(
        hypothesis,
        schema_path="brain/schemas.py",
        service_path="brain/developmental/module_genesis.py",
        fixture_path="tests/fixtures/brain/module_birth_acceptance_gate.json",
        test_path="tests/test_developmental_module_genesis.py",
        acceptance_report_path="reports/acceptance/AGENT-010-module-genesis.json",
    )
    record = service.activate_module(hypothesis, evidence, active_module_id="MOD-PATTERN-MEMORY")

    assert record.status == "active"
    assert hypothesis.status == "active"


def test_module_retirement_preserves_history() -> None:
    service = ModuleGenesisService()
    with pytest.raises(ValueError, match="history_preservation"):
        service.retire_module(active_module_id="MOD-OLD", reason="superseded", preserved_history_refs=[])

    record = service.retire_module(
        active_module_id="MOD-OLD",
        reason="superseded by accepted module",
        preserved_history_refs=["reports/acceptance/old-module.json"],
    )
    assert record.preserved_history_refs == ["reports/acceptance/old-module.json"]
