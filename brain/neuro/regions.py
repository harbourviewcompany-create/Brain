from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BrainRegionFunction(BaseModel):
    """Functional software translation for a brain region or neural system."""

    model_config = ConfigDict(extra="forbid")

    region_id: str
    name: str
    biological_scope: str
    software_equivalent: str
    owner_object: str
    runtime_service: str
    database_table: str
    signals_handled: list[str] = Field(default_factory=list)
    implemented_state: Literal["mapped", "partial", "research_debt"]
    does_not_claim_literal_equivalence: bool = True
    failure_modes: list[str] = Field(default_factory=list)
    dashboard: str
    acceptance_criteria: list[str] = Field(default_factory=list)


class BrainRegionMappingService:
    """GO/HOLD checks for brain-region-to-software mappings."""

    REQUIRED_REGIONS = {
        "prefrontal_cortex",
        "orbitofrontal_cortex",
        "anterior_cingulate_cortex",
        "insula",
        "hippocampus",
        "entorhinal_cortex",
        "amygdala",
        "basal_ganglia",
        "thalamus",
        "cerebellum",
        "default_mode_network",
        "salience_network",
        "executive_control_network",
    }

    def __init__(self, regions: list[BrainRegionFunction]):
        self.regions = regions

    def missing_required_regions(self) -> list[str]:
        present = {region.region_id for region in self.regions}
        return sorted(self.REQUIRED_REGIONS - present)

    def missing_executable_mappings(self) -> list[str]:
        missing: list[str] = []
        for region in self.regions:
            required_values = [
                region.software_equivalent,
                region.owner_object,
                region.runtime_service,
                region.database_table,
                region.dashboard,
            ]
            if not all(required_values):
                missing.append(region.region_id)
            if not region.signals_handled or not region.failure_modes:
                missing.append(region.region_id)
            if not region.acceptance_criteria:
                missing.append(region.region_id)
        return sorted(set(missing))

    def literal_equivalence_violations(self) -> list[str]:
        return [
            region.region_id
            for region in self.regions
            if not region.does_not_claim_literal_equivalence
        ]
