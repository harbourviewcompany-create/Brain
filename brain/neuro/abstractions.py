from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NeuroScaleLevel(StrEnum):
    RESOURCE_SUBSTRATE = "L0_RESOURCE_SUBSTRATE"
    GLOBAL_MODULATION = "L1_GLOBAL_MODULATION"
    CELLULAR_PRIMITIVE = "L2_CELLULAR_PRIMITIVE"
    SYNAPTIC_TOPOLOGY = "L3_SYNAPTIC_TOPOLOGY"
    MICROCIRCUIT = "L4_MICROCIRCUIT"
    REGION_ORGAN = "L5_REGION_ORGAN"
    GLOBAL_COGNITIVE_STATE = "L6_GLOBAL_COGNITIVE_STATE"
    WORKSPACE_ATTENTION = "L7_WORKSPACE_ATTENTION"
    SELF_MODEL_POLICY = "L8_SELF_MODEL_POLICY"
    BODY_TOOLS_ENVIRONMENT = "L9_BODY_TOOLS_ENVIRONMENT"
    WORLD_AND_DEFENSE = "L10_WORLD_AND_DEFENSE"
    DEVELOPMENT_SELF_IMPROVEMENT = "L11_DEVELOPMENT_SELF_IMPROVEMENT"


class MechanismCertainty(StrEnum):
    IMPLEMENTED = "implemented"
    PROVISIONAL = "provisional"
    DISPUTED = "disputed"
    UNKNOWN = "unknown"
    SPECULATIVE = "speculative"


class ImplementationStatus(StrEnum):
    IMPLEMENTED = "implemented"
    MAPPED = "mapped"
    RESEARCH_DEBT = "research_debt"
    BLOCKED = "blocked"


class NeuroFailureMode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    mitigation: str | None = None


class NeuroAcceptanceCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion: str
    evidence_required: str | None = None


class NeuroAbstraction(BaseModel):
    """Executable registry row for one neuroscience abstraction.

    This is a software-control object. It does not claim biological equivalence.
    """

    model_config = ConfigDict(extra="forbid")

    abstraction_id: str = Field(pattern=r"^NEURO-[0-9]{4}$")
    name: str
    scale_level: NeuroScaleLevel
    biological_analogy: str
    brain_region_or_system: str
    computational_interpretation: str
    mechanism_certainty: MechanismCertainty
    unknowns: list[str] = Field(default_factory=list)
    competing_theories: list[str] = Field(default_factory=list)
    software_equivalent: str
    owner_object: str
    runtime_service: str
    database_table: str
    state_machine: str
    formulas_or_algorithms: list[str] = Field(default_factory=list)
    fixture_id: str
    test_id: str
    dashboard: str
    failure_modes: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    go_hold_status: Literal["GO", "HOLD"]


class NeuroAbstractionRegistryService:
    """Validate and query neuroscience abstractions without narrowing scope."""

    REQUIRED_SCALE_PREFIXES = {
        "L0_",
        "L1_",
        "L2_",
        "L3_",
        "L4_",
        "L5_",
        "L7_",
        "L8_",
        "L10_",
        "L11_",
    }

    def __init__(self, abstractions: list[NeuroAbstraction]):
        self.abstractions = abstractions

    def by_id(self, abstraction_id: str) -> NeuroAbstraction:
        for abstraction in self.abstractions:
            if abstraction.abstraction_id == abstraction_id:
                return abstraction
        raise KeyError(abstraction_id)

    def unknown_or_disputed(self) -> list[NeuroAbstraction]:
        blocked = {
            MechanismCertainty.DISPUTED,
            MechanismCertainty.UNKNOWN,
            MechanismCertainty.SPECULATIVE,
        }
        return [item for item in self.abstractions if item.mechanism_certainty in blocked]

    def missing_required_mappings(self) -> list[str]:
        missing: list[str] = []
        for item in self.abstractions:
            required_values = [
                item.biological_analogy,
                item.brain_region_or_system,
                item.computational_interpretation,
                item.software_equivalent,
                item.owner_object,
                item.runtime_service,
                item.database_table,
                item.state_machine,
                item.fixture_id,
                item.test_id,
                item.dashboard,
            ]
            if not all(required_values):
                missing.append(item.abstraction_id)
            if not item.failure_modes or not item.acceptance_criteria:
                missing.append(item.abstraction_id)
        return sorted(set(missing))

    def scale_prefixes(self) -> set[str]:
        return {item.scale_level.value[:3] for item in self.abstractions}


class NeuroAbstractionValidationService:
    """GO/HOLD checks for the neuroscience abstraction registry."""

    def validate_unknowns_not_overclaimed(
        self,
        abstractions: list[NeuroAbstraction],
    ) -> list[str]:
        errors: list[str] = []
        blocked = {
            MechanismCertainty.DISPUTED,
            MechanismCertainty.UNKNOWN,
            MechanismCertainty.SPECULATIVE,
        }
        for item in abstractions:
            if item.mechanism_certainty in blocked and item.go_hold_status == "GO":
                if not item.unknowns and not item.competing_theories:
                    errors.append(item.abstraction_id)
            if item.mechanism_certainty == MechanismCertainty.UNKNOWN:
                if item.go_hold_status != "HOLD":
                    errors.append(item.abstraction_id)
        return errors

    def validate_mapping_completeness(
        self,
        abstractions: list[NeuroAbstraction],
    ) -> list[str]:
        return NeuroAbstractionRegistryService(abstractions).missing_required_mappings()

    def validate_dashboard_and_acceptance(
        self,
        abstractions: list[NeuroAbstraction],
    ) -> list[str]:
        errors: list[str] = []
        for item in abstractions:
            if not item.dashboard or not item.acceptance_criteria:
                errors.append(item.abstraction_id)
        return errors
