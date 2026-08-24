from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from ..benchmarks import BenchmarkBaseline, BenchmarkResult, CognitiveBenchmarkLab, RegressionDecision


@dataclass(slots=True)
class CandidateModuleBuild:
    module_name: str
    source_refs: list[str]
    schema_refs: list[str]
    service_refs: list[str]
    fixture_refs: list[str]
    test_refs: list[str]
    acceptance_refs: list[str]
    rollback_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class SandboxReplay:
    candidate_id: UUID
    replay_id: str
    deterministic: bool
    external_actions_executed: int
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class PromotionProposal:
    candidate_id: UUID
    benchmark_decision_id: UUID
    replay_id: UUID
    immune_scan_passed: bool
    promotion_allowed: bool
    reasons: list[str]
    external_action_authorized: bool = False
    id: UUID = field(default_factory=uuid4)


class SelfModificationSandbox:
    """Evaluate internal architecture changes without silently activating them."""

    def __init__(self) -> None:
        self.benchmarks = CognitiveBenchmarkLab()

    @staticmethod
    def validate_candidate(candidate: CandidateModuleBuild) -> None:
        requirements = {
            "source_refs": candidate.source_refs,
            "schema_refs": candidate.schema_refs,
            "service_refs": candidate.service_refs,
            "fixture_refs": candidate.fixture_refs,
            "test_refs": candidate.test_refs,
            "acceptance_refs": candidate.acceptance_refs,
            "rollback_refs": candidate.rollback_refs,
        }
        missing = [name for name, values in requirements.items() if not values]
        if missing:
            raise ValueError("candidate module missing: " + ",".join(missing))

    def evaluate(
        self,
        candidate: CandidateModuleBuild,
        *,
        replay: SandboxReplay,
        candidate_benchmark: BenchmarkResult,
        baseline: BenchmarkBaseline,
        immune_scan_passed: bool,
    ) -> tuple[PromotionProposal, RegressionDecision]:
        self.validate_candidate(candidate)
        if replay.candidate_id != candidate.id:
            raise ValueError("sandbox replay belongs to another candidate")
        if not replay.evidence_refs:
            raise ValueError("sandbox replay requires evidence")
        decision = self.benchmarks.compare(candidate_benchmark, baseline)
        reasons: list[str] = []
        if not replay.deterministic:
            reasons.append("replay_not_deterministic")
        if replay.external_actions_executed:
            reasons.append("sandbox_executed_external_action")
        if not immune_scan_passed:
            reasons.append("immune_scan_failed")
        if not decision.passed:
            reasons.extend(f"benchmark_regression:{item}" for item in decision.regressions)
        allowed = not reasons
        proposal = PromotionProposal(
            candidate_id=candidate.id,
            benchmark_decision_id=decision.id,
            replay_id=replay.id,
            immune_scan_passed=immune_scan_passed,
            promotion_allowed=allowed,
            reasons=reasons or ["candidate_passed_sandbox_gates"],
            external_action_authorized=False,
        )
        return proposal, decision
