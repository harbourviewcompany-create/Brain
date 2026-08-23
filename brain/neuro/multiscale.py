from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CognitionScaleLayer(BaseModel):
    """One level in the Brain multi-scale cognition stack."""

    model_config = ConfigDict(extra="forbid")

    level_id: str = Field(pattern=r"^L(0|1|2|3|4|5|6|7|8|9|10|11)$")
    name: str
    scope: str
    software_equivalent: str
    owner_object: str
    runtime_service: str
    database_table: str
    state_machine: str
    interfaces_up: list[str] = Field(default_factory=list)
    interfaces_down: list[str] = Field(default_factory=list)
    dashboard: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    does_not_claim_complete_equivalence: bool = True


class CrossScaleDependency(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_level: str
    target_level: str
    relation: str
    evidence_required: str


class MultiscaleCognitionStack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    slice_id: str
    status: str
    non_claim: str
    levels: list[CognitionScaleLayer]
    dependencies: list[CrossScaleDependency] = Field(default_factory=list)


class MultiscaleCognitionService:
    """Validate that cognition is preserved as a stack, not a flat module list."""

    REQUIRED_LEVELS = {f"L{index}" for index in range(12)}

    def __init__(self, stack: MultiscaleCognitionStack):
        self.stack = stack

    def missing_levels(self) -> list[str]:
        present = {level.level_id for level in self.stack.levels}
        return sorted(self.REQUIRED_LEVELS - present)

    def missing_executable_mappings(self) -> list[str]:
        missing: list[str] = []
        for level in self.stack.levels:
            required_values = [
                level.software_equivalent,
                level.owner_object,
                level.runtime_service,
                level.database_table,
                level.state_machine,
                level.dashboard,
            ]
            if not all(required_values) or not level.acceptance_criteria:
                missing.append(level.level_id)
        return sorted(set(missing))

    def invalid_dependencies(self) -> list[str]:
        levels = {level.level_id for level in self.stack.levels}
        invalid: list[str] = []
        for dependency in self.stack.dependencies:
            if dependency.source_level not in levels or dependency.target_level not in levels:
                invalid.append(f"{dependency.source_level}->{dependency.target_level}")
        return invalid

    def equivalence_violations(self) -> list[str]:
        return [
            level.level_id
            for level in self.stack.levels
            if not level.does_not_claim_complete_equivalence
        ]
