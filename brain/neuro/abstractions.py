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


class UnknownMechanismKind(StrEnum):
    UNKNOWN = "unknown"
    DISPUTED = "disputed"
    SPECULATIVE = "speculative"
    MEASUREMENT_GAP = "measurement_gap"
    IMPLEMENTATION_GAP = "implementation_gap"


class UnknownMechanismRecord(BaseModel):
    """Preserves neuroscience uncertainty as an executable control object."""

    model_config = ConfigDict(extra="forbid")

    unknown_id: str = Field(pattern=r"^NEURO-UNK-[0-9]{3}$")
    name: str
    kind: UnknownMechanismKind
    related_abstraction_ids: list[str] = Field(default_factory=list)
    current_claim_boundary: str
    forbidden_claims: list[str] = Field(default_factory=list)
    allowed_uses: list[str] = Field(default_factory=list)
    evidence_needed: list[str] = Field(default_factory=list)
    research_questions: list[str] = Field(default_factory=list)
    owner_object: str
    runtime_service: str
    database_table: str
    fixture_id: str
    test_id: str
    dashboard: str
    go_hold_status: Literal["HOLD"] = "HOLD"


class UnknownMechanismRegistryService:
    """Query and validate preserved unknown mechanisms."""

    def __init__(self, records: list[UnknownMechanismRecord]):
        self.records = records

    def by_id(self, unknown_id: str) -> UnknownMechanismRecord:
        for record in self.records:
            if record.unknown_id == unknown_id:
                return record
        raise KeyError(unknown_id)

    def unresolved_ids(self) -> list[str]:
        return sorted(record.unknown_id for record in self.records)

    def missing_claim_boundaries(self) -> list[str]:
        missing: list[str] = []
        for record in self.records:
            if not record.current_claim_boundary:
                missing.append(record.unknown_id)
            if not record.forbidden_claims or not record.allowed_uses:
                missing.append(record.unknown_id)
            if not record.evidence_needed or not record.research_questions:
                missing.append(record.unknown_id)
        return sorted(set(missing))

    def missing_execution_mappings(self) -> list[str]:
        missing: list[str] = []
        for record in self.records:
            required_values = [
                record.owner_object,
                record.runtime_service,
                record.database_table,
                record.fixture_id,
                record.test_id,
                record.dashboard,
            ]
            if not all(required_values):
                missing.append(record.unknown_id)
        return sorted(set(missing))

    def overclaim_violations(self) -> list[str]:
        blocked_terms = {
            "solved",
            "complete equivalence",
            "literal equivalence",
            "consciousness achieved",
            "sentience achieved",
        }
        violations: list[str] = []
        for record in self.records:
            boundary = record.current_claim_boundary.lower()
            forbidden = " ".join(record.forbidden_claims).lower()
            if any(term in boundary for term in blocked_terms):
                violations.append(record.unknown_id)
            if "may claim solved" in forbidden:
                violations.append(record.unknown_id)
        return sorted(set(violations))


class UnknownMechanismValidationService:
    """GO/HOLD checks for unresolved neuroscience claims."""

    def validate_records(self, records: list[UnknownMechanismRecord]) -> list[str]:
        service = UnknownMechanismRegistryService(records)
        return sorted(
            set(
                service.missing_claim_boundaries()
                + service.missing_execution_mappings()
                + service.overclaim_violations()
            )
        )

    def validate_all_records_hold(
        self,
        records: list[UnknownMechanismRecord],
    ) -> list[str]:
        return sorted(
            record.unknown_id
            for record in records
            if record.go_hold_status != "HOLD"
        )


class TheoryStatus(StrEnum):
    SUPPORTED = "supported"
    COMPETING = "competing"
    DISPUTED = "disputed"
    RETIRED = "retired"
    RESEARCH_DEBT = "research_debt"


class ImplementationPosture(StrEnum):
    DO_NOT_IMPLEMENT_DIRECTLY = "do_not_implement_directly"
    USE_AS_HEURISTIC = "use_as_heuristic"
    REQUIRES_OPERATOR_GATE = "requires_operator_gate"
    RESEARCH_ONLY = "research_only"


class NeuroscienceTheory(BaseModel):
    """Theory registry entry with explicit implementation boundaries."""

    model_config = ConfigDict(extra="forbid")

    theory_id: str = Field(pattern=r"^NEURO-THEORY-[0-9]{3}$")
    name: str
    mechanism_area: str
    claim: str
    status: TheoryStatus
    implementation_posture: ImplementationPosture
    competing_theory_ids: list[str] = Field(default_factory=list)
    linked_unknown_ids: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    claim_boundary: str
    owner_object: str
    runtime_service: str
    fixture_id: str
    test_id: str
    dashboard: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    go_hold_status: Literal["GO", "HOLD"]


class TheoryConflict(BaseModel):
    """Explicit conflict between theories that must not be silently resolved."""

    model_config = ConfigDict(extra="forbid")

    conflict_id: str = Field(pattern=r"^NEURO-CONFLICT-[0-9]{3}$")
    theory_ids: list[str] = Field(min_length=2)
    conflict_summary: str
    resolution_rule: str
    operator_surface: str
    acceptance_criteria: list[str] = Field(default_factory=list)


class TheoryRegistryService:
    """Validate theory conflicts, evidence and implementation posture."""

    def __init__(
        self,
        theories: list[NeuroscienceTheory],
        conflicts: list[TheoryConflict],
    ):
        self.theories = theories
        self.conflicts = conflicts

    def theory_ids(self) -> set[str]:
        return {theory.theory_id for theory in self.theories}

    def invalid_conflict_references(self) -> list[str]:
        ids = self.theory_ids()
        invalid: list[str] = []
        for conflict in self.conflicts:
            if any(theory_id not in ids for theory_id in conflict.theory_ids):
                invalid.append(conflict.conflict_id)
        return sorted(invalid)

    def missing_competing_conflicts(self) -> list[str]:
        conflict_pairs = {
            frozenset(conflict.theory_ids)
            for conflict in self.conflicts
        }
        missing: list[str] = []
        for theory in self.theories:
            for competing_id in theory.competing_theory_ids:
                pair = frozenset({theory.theory_id, competing_id})
                if pair not in conflict_pairs:
                    missing.append(theory.theory_id)
        return sorted(set(missing))

    def unsafe_implementation_postures(self) -> list[str]:
        unsafe_statuses = {
            TheoryStatus.COMPETING,
            TheoryStatus.DISPUTED,
            TheoryStatus.RESEARCH_DEBT,
        }
        violations: list[str] = []
        for theory in self.theories:
            if theory.status in unsafe_statuses and theory.go_hold_status == "GO":
                violations.append(theory.theory_id)
            if (
                theory.status in unsafe_statuses
                and theory.implementation_posture
                == ImplementationPosture.DO_NOT_IMPLEMENT_DIRECTLY
                and not theory.claim_boundary
            ):
                violations.append(theory.theory_id)
        return sorted(set(violations))

    def missing_evidence_or_boundaries(self) -> list[str]:
        missing: list[str] = []
        for theory in self.theories:
            if not theory.claim_boundary:
                missing.append(theory.theory_id)
            if not theory.supporting_evidence and not theory.contradicting_evidence:
                missing.append(theory.theory_id)
            if not theory.acceptance_criteria:
                missing.append(theory.theory_id)
        return sorted(set(missing))


class TheoryValidationService:
    """Aggregate GO/HOLD checks for neuroscience theory records."""

    def validate(
        self,
        theories: list[NeuroscienceTheory],
        conflicts: list[TheoryConflict],
    ) -> list[str]:
        service = TheoryRegistryService(theories, conflicts)
        return sorted(
            set(
                service.invalid_conflict_references()
                + service.missing_competing_conflicts()
                + service.unsafe_implementation_postures()
                + service.missing_evidence_or_boundaries()
            )
        )
