from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class ModuleHypothesis:
    name: str
    repeated_pattern: str
    source_refs: list[str]
    status: str = "hypothesis"
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ModuleMaturityEvidence:
    hypothesis_id: UUID
    schema_path: str
    service_path: str
    fixture_path: str
    test_path: str
    acceptance_report_path: str
    id: UUID = field(default_factory=uuid4)

    def complete(self) -> bool:
        return all(
            [
                self.schema_path,
                self.service_path,
                self.fixture_path,
                self.test_path,
                self.acceptance_report_path,
            ]
        )


@dataclass(slots=True)
class ModuleActivationRecord:
    hypothesis_id: UUID
    maturity_evidence_id: UUID
    active_module_id: str
    status: str = "active"
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ModuleRetirementRecord:
    active_module_id: str
    reason: str
    preserved_history_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass
class ModuleGenesisService:
    hypotheses: dict[UUID, ModuleHypothesis] = field(default_factory=dict)
    maturity: dict[UUID, ModuleMaturityEvidence] = field(default_factory=dict)
    activations: list[ModuleActivationRecord] = field(default_factory=list)
    retirements: list[ModuleRetirementRecord] = field(default_factory=list)

    def create_hypothesis(
        self,
        *,
        name: str,
        repeated_pattern: str,
        source_refs: list[str],
    ) -> ModuleHypothesis:
        if not source_refs:
            raise ValueError("module_hypothesis_requires_source_traceability")
        hypothesis = ModuleHypothesis(name=name, repeated_pattern=repeated_pattern, source_refs=list(source_refs))
        self.hypotheses[hypothesis.id] = hypothesis
        return hypothesis

    def attach_maturity_evidence(
        self,
        hypothesis: ModuleHypothesis,
        *,
        schema_path: str,
        service_path: str,
        fixture_path: str,
        test_path: str,
        acceptance_report_path: str,
    ) -> ModuleMaturityEvidence:
        evidence = ModuleMaturityEvidence(
            hypothesis_id=hypothesis.id,
            schema_path=schema_path,
            service_path=service_path,
            fixture_path=fixture_path,
            test_path=test_path,
            acceptance_report_path=acceptance_report_path,
        )
        self.maturity[evidence.id] = evidence
        hypothesis.status = "maturity_evidence_attached"
        return evidence

    def activate_module(
        self,
        hypothesis: ModuleHypothesis,
        evidence: ModuleMaturityEvidence,
        *,
        active_module_id: str,
    ) -> ModuleActivationRecord:
        if evidence.hypothesis_id != hypothesis.id:
            raise ValueError("maturity_evidence_hypothesis_mismatch")
        if not evidence.complete():
            raise ValueError("module_activation_requires_schema_service_fixture_test_acceptance")
        hypothesis.status = "active"
        record = ModuleActivationRecord(hypothesis.id, evidence.id, active_module_id)
        self.activations.append(record)
        return record

    def retire_module(
        self,
        *,
        active_module_id: str,
        reason: str,
        preserved_history_refs: list[str],
    ) -> ModuleRetirementRecord:
        if not preserved_history_refs:
            raise ValueError("module_retirement_requires_history_preservation")
        record = ModuleRetirementRecord(active_module_id, reason, list(preserved_history_refs))
        self.retirements.append(record)
        return record
