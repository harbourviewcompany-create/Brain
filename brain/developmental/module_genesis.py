from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from ..domain import utcnow


class ModuleStage(StrEnum):
    HYPOTHESIZED = "hypothesized"
    SPECIFIED = "specified"
    TESTING = "testing"
    ACCEPTED = "accepted"
    ACTIVE = "active"
    RETIRED = "retired"


@dataclass(slots=True)
class ModuleHypothesis:
    name: str
    pattern: str
    source_refs: list[str]
    owner_objects: list[str] = field(default_factory=list)
    schemas: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    formulas: list[str] = field(default_factory=list)
    fixtures: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    dashboards: list[str] = field(default_factory=list)
    state: ModuleStage = ModuleStage.HYPOTHESIZED
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ModuleBirthRecord:
    module_id: UUID
    state: ModuleStage
    missing_requirements: list[str]
    source_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ModuleMaturityRecord:
    module_id: UUID
    previous_state: ModuleStage
    new_state: ModuleStage
    acceptance_report: str | None
    immune_scan_passed: bool
    replay_passed: bool
    source_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ModuleRetirementRecord:
    module_id: UUID
    reason: str
    source_refs: list[str]
    previous_state: ModuleStage
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


_REQUIRED_ARTIFACTS = {
    "owner_objects": "owner object",
    "schemas": "schema",
    "services": "runtime service",
    "fixtures": "fixture",
    "tests": "test",
    "dashboards": "dashboard",
}


class ModuleGenesisService:
    def propose(self, name: str, pattern: str, source_refs: list[str]) -> ModuleHypothesis:
        if not source_refs:
            raise ValueError("module hypothesis requires source traceability")
        if not name.strip() or not pattern.strip():
            raise ValueError("module hypothesis requires name and repeated pattern")
        return ModuleHypothesis(name=name.strip(), pattern=pattern.strip(), source_refs=list(source_refs))

    def specify(self, hypothesis: ModuleHypothesis, **artifacts: list[str]) -> tuple[ModuleHypothesis, ModuleBirthRecord]:
        values = {
            "owner_objects": list(artifacts.get("owner_objects", hypothesis.owner_objects)),
            "schemas": list(artifacts.get("schemas", hypothesis.schemas)),
            "services": list(artifacts.get("services", hypothesis.services)),
            "formulas": list(artifacts.get("formulas", hypothesis.formulas)),
            "fixtures": list(artifacts.get("fixtures", hypothesis.fixtures)),
            "tests": list(artifacts.get("tests", hypothesis.tests)),
            "dashboards": list(artifacts.get("dashboards", hypothesis.dashboards)),
        }
        updated = replace(hypothesis, **values)
        missing = [label for attr, label in _REQUIRED_ARTIFACTS.items() if not getattr(updated, attr)]
        next_state = ModuleStage.SPECIFIED if not missing else ModuleStage.HYPOTHESIZED
        updated = replace(updated, state=next_state)
        return updated, ModuleBirthRecord(
            module_id=updated.id,
            state=updated.state,
            missing_requirements=missing,
            source_refs=list(updated.source_refs),
        )


class ModuleMaturityService:
    def activate(
        self,
        module: ModuleHypothesis,
        *,
        acceptance_report: str | None,
        replay_passed: bool,
        immune_scan_passed: bool,
    ) -> tuple[ModuleHypothesis, ModuleMaturityRecord]:
        missing = [attr for attr in _REQUIRED_ARTIFACTS if not getattr(module, attr)]
        if missing:
            raise ValueError("module activation requires complete implementation artifacts")
        if not acceptance_report:
            raise ValueError("module activation requires acceptance report")
        if not replay_passed:
            raise ValueError("module activation requires deterministic replay")
        if not immune_scan_passed:
            raise ValueError("module activation requires passing immune scan")
        previous = module.state
        updated = replace(module, state=ModuleStage.ACTIVE)
        return updated, ModuleMaturityRecord(
            module_id=module.id,
            previous_state=previous,
            new_state=ModuleStage.ACTIVE,
            acceptance_report=acceptance_report,
            immune_scan_passed=True,
            replay_passed=True,
            source_refs=list(module.source_refs),
        )

    def retire(
        self, module: ModuleHypothesis, *, reason: str, source_refs: list[str]
    ) -> tuple[ModuleHypothesis, ModuleRetirementRecord]:
        if not source_refs:
            raise ValueError("module retirement requires evidence")
        previous = module.state
        updated = replace(module, state=ModuleStage.RETIRED)
        return updated, ModuleRetirementRecord(
            module_id=module.id,
            reason=reason,
            source_refs=list(source_refs),
            previous_state=previous,
        )
