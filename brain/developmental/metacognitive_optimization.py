from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class BenchmarkEvidenceClass(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    THIRD_PARTY = "third_party"


class OptimizationPlanState(StrEnum):
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    APPROVED_FOR_EXPERIMENT = "approved_for_experiment"
    VALIDATED = "validated"
    REJECTED = "rejected"


@dataclass(slots=True)
class CapabilityBenchmark:
    name: str
    capability: str
    metric: str
    higher_is_better: bool
    minimum_evidence_count: int = 1
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class BenchmarkRun:
    benchmark_id: UUID
    score: float
    evidence_refs: list[str]
    evidence_class: BenchmarkEvidenceClass
    implementation_ref: str
    test_target: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class RegressionSignal:
    benchmark_id: UUID
    baseline_run_id: UUID
    current_run_id: UUID
    delta: float
    severity: float
    evidence_refs: list[str]
    acknowledged: bool = False
    resolved: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ImprovementHypothesis:
    target_capability: str
    mechanism: str
    expected_gain: float
    confidence: float
    evidence_refs: list[str]
    rollback_plan: str
    test_target: str
    acceptance_criteria: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class LearningDebtItem:
    capability: str
    gap: str
    severity: float
    strategic_value: float
    evidence_refs: list[str]
    source_regression_ids: list[UUID] = field(default_factory=list)
    priority: float = 0.0
    resolved: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class SelfOptimizationPlan:
    objective: str
    hypothesis_ids: list[UUID]
    learning_debt_ids: list[UUID]
    traceability_refs: list[str]
    rollback_plan: str
    test_targets: list[str]
    acceptance_criteria: list[str]
    state: OptimizationPlanState = OptimizationPlanState.PROPOSED
    executable: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


class BenchmarkService:
    def __init__(self) -> None:
        self.benchmarks: dict[UUID, CapabilityBenchmark] = {}
        self.runs: dict[UUID, BenchmarkRun] = {}
        self.run_history: dict[UUID, list[UUID]] = {}

    def register(self, benchmark: CapabilityBenchmark) -> CapabilityBenchmark:
        if benchmark.minimum_evidence_count < 1:
            raise ValueError("benchmark_requires_positive_evidence_threshold")
        self.benchmarks[benchmark.id] = benchmark
        return benchmark

    def record(self, run: BenchmarkRun) -> BenchmarkRun:
        benchmark = self.benchmarks.get(run.benchmark_id)
        if benchmark is None:
            raise ValueError("benchmark_run_requires_registered_benchmark")
        if len(run.evidence_refs) < benchmark.minimum_evidence_count:
            raise ValueError("benchmark_run_requires_evidence")
        if not run.implementation_ref or not run.test_target:
            raise ValueError("benchmark_run_requires_traceable_implementation_and_test")
        self.runs[run.id] = run
        self.run_history.setdefault(run.benchmark_id, []).append(run.id)
        return run

    def history(self, benchmark_id: UUID) -> list[BenchmarkRun]:
        return [self.runs[run_id] for run_id in self.run_history.get(benchmark_id, [])]


class RegressionDetectionService:
    def detect(
        self,
        *,
        benchmark: CapabilityBenchmark,
        baseline: BenchmarkRun,
        current: BenchmarkRun,
    ) -> RegressionSignal | None:
        if baseline.benchmark_id != benchmark.id or current.benchmark_id != benchmark.id:
            raise ValueError("regression_runs_must_match_benchmark")
        raw_delta = current.score - baseline.score
        regressed = raw_delta < 0 if benchmark.higher_is_better else raw_delta > 0
        if not regressed:
            return None
        severity = clamp(abs(raw_delta) / max(abs(baseline.score), 1.0))
        return RegressionSignal(
            benchmark_id=benchmark.id,
            baseline_run_id=baseline.id,
            current_run_id=current.id,
            delta=raw_delta,
            severity=severity,
            evidence_refs=sorted(set(baseline.evidence_refs + current.evidence_refs)),
        )


class LearningDebtPrioritizationService:
    def prioritize(self, items: list[LearningDebtItem]) -> list[LearningDebtItem]:
        for item in items:
            if not item.evidence_refs:
                raise ValueError("learning_debt_requires_evidence")
            item.severity = clamp(item.severity)
            item.strategic_value = clamp(item.strategic_value)
            regression_boost = min(0.25, 0.05 * len(item.source_regression_ids))
            item.priority = clamp(0.55 * item.severity + 0.45 * item.strategic_value + regression_boost)
        return sorted(items, key=lambda item: item.priority, reverse=True)


class SelfOptimizationPlanner:
    def __init__(self) -> None:
        self.plans: dict[UUID, SelfOptimizationPlan] = {}

    def propose(
        self,
        *,
        objective: str,
        hypotheses: list[ImprovementHypothesis],
        learning_debt: list[LearningDebtItem],
        traceability_refs: list[str],
    ) -> SelfOptimizationPlan:
        if not hypotheses or not learning_debt:
            raise ValueError("optimization_plan_requires_hypothesis_and_learning_debt")
        if not traceability_refs:
            raise ValueError("optimization_plan_requires_traceability")
        for hypothesis in hypotheses:
            if not hypothesis.evidence_refs:
                raise ValueError("improvement_hypothesis_requires_evidence")
            if not hypothesis.rollback_plan:
                raise ValueError("improvement_hypothesis_requires_rollback")
            if not hypothesis.test_target:
                raise ValueError("improvement_hypothesis_requires_test_target")
            if not hypothesis.acceptance_criteria:
                raise ValueError("improvement_hypothesis_requires_acceptance_criteria")
        plan = SelfOptimizationPlan(
            objective=objective,
            hypothesis_ids=[item.id for item in hypotheses],
            learning_debt_ids=[item.id for item in learning_debt],
            traceability_refs=list(traceability_refs),
            rollback_plan="; ".join(sorted({item.rollback_plan for item in hypotheses})),
            test_targets=sorted({item.test_target for item in hypotheses}),
            acceptance_criteria=sorted({criterion for item in hypotheses for criterion in item.acceptance_criteria}),
            state=OptimizationPlanState.PROPOSED,
            executable=False,
        )
        self.plans[plan.id] = plan
        return plan

    def mark_reviewed(self, plan_id: UUID) -> SelfOptimizationPlan:
        plan = self.plans[plan_id]
        if plan.state is not OptimizationPlanState.PROPOSED:
            raise ValueError("optimization_plan_invalid_review_transition")
        plan.state = OptimizationPlanState.REVIEWED
        plan.executable = False
        return plan

    def approve_experiment(self, plan_id: UUID, *, operator_approval_ref: str) -> SelfOptimizationPlan:
        plan = self.plans[plan_id]
        if plan.state is not OptimizationPlanState.REVIEWED:
            raise ValueError("optimization_plan_requires_review_before_experiment")
        if not operator_approval_ref:
            raise ValueError("optimization_plan_requires_operator_approval")
        plan.traceability_refs.append(operator_approval_ref)
        plan.state = OptimizationPlanState.APPROVED_FOR_EXPERIMENT
        plan.executable = False
        return plan

    def direct_self_modify(self, plan_id: UUID) -> None:
        if plan_id not in self.plans:
            raise ValueError("unknown_optimization_plan")
        raise ValueError("benchmark_output_cannot_directly_self_modify")


class ClaimBoundaryService:
    @staticmethod
    def superiority_claim_allowed(runs: list[BenchmarkRun]) -> bool:
        if not runs:
            return False
        external = [
            run
            for run in runs
            if run.evidence_class in {BenchmarkEvidenceClass.EXTERNAL, BenchmarkEvidenceClass.THIRD_PARTY}
        ]
        return bool(external) and all(run.evidence_refs for run in external)

    @staticmethod
    def claim_report(runs: list[BenchmarkRun]) -> dict[str, object]:
        allowed = ClaimBoundaryService.superiority_claim_allowed(runs)
        return {
            "superiority_claim_allowed": allowed,
            "blocked_claims": [] if allowed else ["superior_intelligence_without_external_benchmark_evidence"],
            "self_modification": "proposal_only",
        }


class MetacognitiveOptimizationRuntime:
    def __init__(self) -> None:
        self.benchmarks = BenchmarkService()
        self.regressions: dict[UUID, RegressionSignal] = {}
        self.learning_debt: dict[UUID, LearningDebtItem] = {}
        self.hypotheses: dict[UUID, ImprovementHypothesis] = {}
        self.planner = SelfOptimizationPlanner()

    def register_regression(self, signal: RegressionSignal) -> RegressionSignal:
        if not signal.evidence_refs:
            raise ValueError("regression_signal_requires_evidence")
        self.regressions[signal.id] = signal
        return signal

    def add_learning_debt(self, item: LearningDebtItem) -> LearningDebtItem:
        if not item.evidence_refs:
            raise ValueError("learning_debt_requires_evidence")
        self.learning_debt[item.id] = item
        return item

    def add_hypothesis(self, hypothesis: ImprovementHypothesis) -> ImprovementHypothesis:
        if not hypothesis.evidence_refs:
            raise ValueError("improvement_hypothesis_requires_evidence")
        self.hypotheses[hypothesis.id] = hypothesis
        return hypothesis

    def capability_map(self) -> dict[str, object]:
        latest: dict[str, float] = {}
        for benchmark in self.benchmarks.benchmarks.values():
            history = self.benchmarks.history(benchmark.id)
            if history:
                latest[benchmark.capability] = history[-1].score
        return {
            "capabilities": latest,
            "regressions": len([item for item in self.regressions.values() if not item.resolved]),
            "learning_debt": len([item for item in self.learning_debt.values() if not item.resolved]),
            "optimization_plans": len(self.planner.plans),
            "hold_boundaries": ClaimBoundaryService.claim_report(list(self.benchmarks.runs.values())),
        }
