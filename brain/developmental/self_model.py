from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(slots=True)
class CapabilityClaim:
    name: str
    confidence: float
    evidence_refs: list[str]
    test_refs: list[str]
    acceptance_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class LimitationRecord:
    limitation: str
    effect: str
    preserved: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class LearningDebt:
    area: str
    severity: float
    evidence_gap: str
    priority: float
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class SelfAssessment:
    capability_count: int
    limitation_count: int
    learning_debt_priority: float
    overclaim_blocked: bool
    id: UUID = field(default_factory=uuid4)


@dataclass
class SelfModelService:
    capabilities: list[CapabilityClaim] = field(default_factory=list)
    limitations: list[LimitationRecord] = field(default_factory=list)
    debts: list[LearningDebt] = field(default_factory=list)
    assessments: list[SelfAssessment] = field(default_factory=list)

    def claim_capability(
        self,
        *,
        name: str,
        confidence: float,
        evidence_refs: list[str],
        test_refs: list[str],
        acceptance_refs: list[str],
    ) -> CapabilityClaim:
        if not evidence_refs or not test_refs or not acceptance_refs:
            raise ValueError("capability_claim_requires_evidence_tests_acceptance")
        claim = CapabilityClaim(
            name=name,
            confidence=min(1.0, max(0.0, confidence)),
            evidence_refs=list(evidence_refs),
            test_refs=list(test_refs),
            acceptance_refs=list(acceptance_refs),
        )
        self.capabilities.append(claim)
        return claim

    def record_limitation(self, *, limitation: str, effect: str) -> LimitationRecord:
        record = LimitationRecord(limitation=limitation, effect=effect, preserved=True)
        self.limitations.append(record)
        return record

    def add_learning_debt(self, *, area: str, severity: float, evidence_gap: str) -> LearningDebt:
        priority = min(1.0, max(0.0, severity))
        debt = LearningDebt(area=area, severity=severity, evidence_gap=evidence_gap, priority=priority)
        self.debts.append(debt)
        return debt

    def assess(self) -> SelfAssessment:
        debt_priority = max((debt.priority for debt in self.debts), default=0.0)
        overclaim_blocked = any(limit.preserved for limit in self.limitations)
        assessment = SelfAssessment(
            capability_count=len(self.capabilities),
            limitation_count=len(self.limitations),
            learning_debt_priority=debt_priority,
            overclaim_blocked=overclaim_blocked,
        )
        self.assessments.append(assessment)
        return assessment

    def can_claim(self, capability_name: str) -> bool:
        return any(claim.name == capability_name for claim in self.capabilities)


class BenchmarkDomain(StrEnum):
    REASONING = "reasoning"
    MEMORY = "memory"
    PERCEPTION = "perception"
    COMMERCIAL = "commercial"
    GOVERNANCE = "governance"
    DEVELOPMENTAL = "developmental"
    OPERATOR = "operator"


class OptimizationStatus(StrEnum):
    PROPOSED = "proposed"
    BLOCKED = "blocked"
    READY_FOR_REVIEW = "ready_for_review"


@dataclass(slots=True)
class CapabilityBenchmark:
    benchmark_id: str
    name: str
    domain: BenchmarkDomain
    capability: str
    target_score: float
    evidence_refs: list[str]
    external_comparison_required: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class BenchmarkRun:
    benchmark_id: str
    score: float
    baseline_score: float
    evidence_refs: list[str]
    test_refs: list[str]
    run_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)

    @property
    def delta(self) -> float:
        return self.score - self.baseline_score


@dataclass(slots=True)
class RegressionSignal:
    benchmark_id: str
    severity: float
    current_score: float
    prior_score: float
    evidence_refs: list[str]
    hidden: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class LearningDebtItem:
    debt_id: str
    capability: str
    gap: str
    severity: float
    evidence_refs: list[str]
    priority: float = 0.0
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ImprovementHypothesis:
    hypothesis_id: str
    target_capability: str
    mechanism: str
    expected_gain: float
    risk: float
    evidence_refs: list[str]
    rollback_plan: str
    test_target: str
    acceptance_criteria: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class SelfOptimizationPlan:
    plan_id: str
    hypotheses: list[ImprovementHypothesis]
    learning_debt_ids: list[str]
    status: OptimizationStatus
    proposal_only: bool
    rollback_required: bool
    test_targets: list[str]
    acceptance_criteria: list[str]
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


class BenchmarkService:
    def __init__(self) -> None:
        self.benchmarks: dict[str, CapabilityBenchmark] = {}
        self.runs: list[BenchmarkRun] = []
        self.external_evidence: dict[str, list[str]] = {}

    def register_benchmark(self, benchmark: CapabilityBenchmark) -> CapabilityBenchmark:
        if not benchmark.evidence_refs:
            raise ValueError("benchmark_requires_source_evidence")
        benchmark.target_score = clamp(benchmark.target_score)
        self.benchmarks[benchmark.benchmark_id] = benchmark
        return benchmark

    def record_run(self, run: BenchmarkRun) -> BenchmarkRun:
        if run.benchmark_id not in self.benchmarks:
            raise ValueError("benchmark_run_requires_registered_benchmark")
        if not run.evidence_refs or not run.test_refs:
            raise ValueError("benchmark_run_requires_evidence_and_tests")
        run.score = clamp(run.score)
        run.baseline_score = clamp(run.baseline_score)
        self.runs.append(run)
        return run

    def add_external_comparison_evidence(self, benchmark_id: str, evidence_refs: list[str]) -> None:
        if benchmark_id not in self.benchmarks:
            raise ValueError("external_comparison_requires_registered_benchmark")
        if not evidence_refs:
            raise ValueError("external_comparison_requires_evidence")
        self.external_evidence[benchmark_id] = list(evidence_refs)

    def superiority_claim_allowed(self, benchmark_id: str) -> bool:
        benchmark = self.benchmarks.get(benchmark_id)
        if benchmark is None or not benchmark.external_comparison_required:
            return False
        if benchmark_id not in self.external_evidence:
            return False
        latest = next((run for run in reversed(self.runs) if run.benchmark_id == benchmark_id), None)
        return latest is not None and latest.score >= benchmark.target_score


class RegressionDetectionService:
    def detect(self, current_run: BenchmarkRun, prior_run: BenchmarkRun, *, threshold: float) -> RegressionSignal | None:
        if current_run.benchmark_id != prior_run.benchmark_id:
            raise ValueError("regression_comparison_requires_same_benchmark")
        decline = prior_run.score - current_run.score
        if decline < threshold:
            return None
        return RegressionSignal(
            benchmark_id=current_run.benchmark_id,
            severity=clamp(decline),
            current_score=current_run.score,
            prior_score=prior_run.score,
            evidence_refs=current_run.evidence_refs + prior_run.evidence_refs,
            hidden=False,
        )

    def assert_visible(self, signal: RegressionSignal) -> None:
        if signal.hidden:
            raise ValueError("regression_signal_cannot_be_hidden")
        if not signal.evidence_refs:
            raise ValueError("regression_signal_requires_evidence")


class LearningDebtPrioritizationService:
    def prioritize(self, debts: list[LearningDebtItem], regressions: list[RegressionSignal]) -> list[LearningDebtItem]:
        regression_pressure = {signal.benchmark_id: signal.severity for signal in regressions}
        prioritized: list[LearningDebtItem] = []
        for debt in debts:
            if not debt.evidence_refs:
                raise ValueError("learning_debt_requires_evidence")
            pressure = regression_pressure.get(debt.capability, 0.0)
            debt.priority = clamp((debt.severity * 0.7) + (pressure * 0.3))
            prioritized.append(debt)
        return sorted(prioritized, key=lambda item: item.priority, reverse=True)


class SelfOptimizationPlanner:
    def create_plan(
        self,
        *,
        plan_id: str,
        hypotheses: list[ImprovementHypothesis],
        debts: list[LearningDebtItem],
        evidence_refs: list[str],
    ) -> SelfOptimizationPlan:
        if not evidence_refs:
            raise ValueError("optimization_plan_requires_traceability")
        if not hypotheses:
            raise ValueError("optimization_plan_requires_hypotheses")
        test_targets: list[str] = []
        acceptance: list[str] = []
        for hypothesis in hypotheses:
            if not hypothesis.evidence_refs:
                raise ValueError("improvement_hypothesis_requires_evidence")
            if not hypothesis.rollback_plan:
                raise ValueError("improvement_hypothesis_requires_rollback")
            if not hypothesis.test_target:
                raise ValueError("improvement_hypothesis_requires_test_target")
            if not hypothesis.acceptance_criteria:
                raise ValueError("improvement_hypothesis_requires_acceptance_criteria")
            test_targets.append(hypothesis.test_target)
            acceptance.extend(hypothesis.acceptance_criteria)
        return SelfOptimizationPlan(
            plan_id=plan_id,
            hypotheses=hypotheses,
            learning_debt_ids=[debt.debt_id for debt in debts],
            status=OptimizationStatus.PROPOSED,
            proposal_only=True,
            rollback_required=True,
            test_targets=test_targets,
            acceptance_criteria=acceptance,
            evidence_refs=list(evidence_refs),
        )

    def execute_plan(self, plan: SelfOptimizationPlan) -> None:
        if plan.proposal_only:
            raise ValueError("self_optimization_plan_is_proposal_only")
        raise ValueError("self_optimization_execution_requires_explicit_external_approval")
