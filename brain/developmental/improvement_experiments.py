from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from .metacognitive_optimization import OptimizationPlanState, SelfOptimizationPlan


def utcnow() -> datetime:
    return datetime.now(UTC)


class PromotionDecision(StrEnum):
    PROMOTE = "promote"
    REVISE = "revise"
    REJECT = "reject"
    HOLD = "hold"


@dataclass(slots=True)
class ExperimentCandidate:
    artifact_refs: list[str]
    description: str
    test_targets: list[str]
    benchmark_targets: list[str]
    rollback_plan: str
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ImprovementExperiment:
    plan_id: UUID
    candidate_id: UUID
    operator_approval_ref: str
    protected_benchmarks: list[str]
    regression_tolerance: float = 0.0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ExperimentRun:
    experiment_id: UUID
    before_scores: dict[str, float]
    after_scores: dict[str, float]
    control_results: dict[str, bool]
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ExperimentResult:
    run_id: UUID
    benchmark_deltas: dict[str, float]
    controls_passed: bool
    protected_regressions: list[str]
    evidence_refs: list[str]
    decision: PromotionDecision
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class RollbackRecord:
    experiment_id: UUID
    reason: str
    rollback_plan: str
    evidence_refs: list[str]
    executed: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


class ImprovementExperimentService:
    def __init__(self) -> None:
        self.candidates: dict[UUID, ExperimentCandidate] = {}
        self.experiments: dict[UUID, ImprovementExperiment] = {}
        self.runs: dict[UUID, ExperimentRun] = {}
        self.results: dict[UUID, ExperimentResult] = {}
        self.rollbacks: dict[UUID, RollbackRecord] = {}

    def register_candidate(self, candidate: ExperimentCandidate) -> ExperimentCandidate:
        if not candidate.artifact_refs:
            raise ValueError("experiment_candidate_requires_artifact_refs")
        if not candidate.test_targets or not candidate.benchmark_targets:
            raise ValueError("experiment_candidate_requires_tests_and_benchmarks")
        if not candidate.rollback_plan:
            raise ValueError("experiment_candidate_requires_rollback_plan")
        self.candidates[candidate.id] = candidate
        return candidate

    def create_experiment(
        self,
        *,
        plan: SelfOptimizationPlan,
        candidate: ExperimentCandidate,
        operator_approval_ref: str,
        protected_benchmarks: list[str],
        regression_tolerance: float = 0.0,
    ) -> ImprovementExperiment:
        if plan.state is not OptimizationPlanState.APPROVED_FOR_EXPERIMENT:
            raise ValueError("experiment_requires_approved_optimization_plan")
        if candidate.id not in self.candidates:
            raise ValueError("experiment_requires_registered_candidate")
        if not operator_approval_ref:
            raise ValueError("experiment_requires_operator_approval")
        if not protected_benchmarks:
            raise ValueError("experiment_requires_protected_benchmarks")
        experiment = ImprovementExperiment(
            plan_id=plan.id,
            candidate_id=candidate.id,
            operator_approval_ref=operator_approval_ref,
            protected_benchmarks=list(protected_benchmarks),
            regression_tolerance=max(regression_tolerance, 0.0),
        )
        self.experiments[experiment.id] = experiment
        return experiment

    def record_run(self, run: ExperimentRun) -> ExperimentRun:
        if run.experiment_id not in self.experiments:
            raise ValueError("experiment_run_requires_registered_experiment")
        if not run.evidence_refs:
            raise ValueError("experiment_run_requires_evidence")
        if not run.control_results:
            raise ValueError("experiment_run_requires_control_results")
        self.runs[run.id] = run
        return run

    def direct_mutation(self, experiment_id: UUID) -> None:
        if experiment_id not in self.experiments:
            raise ValueError("unknown_experiment")
        raise ValueError("experiment_runtime_cannot_mutate_merge_or_deploy")


class CandidateEvaluationService:
    def evaluate(
        self,
        *,
        experiment: ImprovementExperiment,
        run: ExperimentRun,
    ) -> ExperimentResult:
        names = sorted(set(run.before_scores) | set(run.after_scores))
        deltas = {
            name: run.after_scores.get(name, 0.0) - run.before_scores.get(name, 0.0)
            for name in names
        }
        controls_passed = all(run.control_results.values())
        regressions = [
            name
            for name in experiment.protected_benchmarks
            if deltas.get(name, 0.0) < -experiment.regression_tolerance
        ]
        decision = PromotionGateService().decide(
            controls_passed=controls_passed,
            protected_regressions=regressions,
            benchmark_deltas=deltas,
        )
        return ExperimentResult(
            run_id=run.id,
            benchmark_deltas=deltas,
            controls_passed=controls_passed,
            protected_regressions=regressions,
            evidence_refs=list(run.evidence_refs),
            decision=decision,
        )


class PromotionGateService:
    def decide(
        self,
        *,
        controls_passed: bool,
        protected_regressions: list[str],
        benchmark_deltas: dict[str, float],
    ) -> PromotionDecision:
        if not controls_passed:
            return PromotionDecision.REJECT
        if protected_regressions:
            return PromotionDecision.HOLD
        positives = [delta for delta in benchmark_deltas.values() if delta > 0]
        negatives = [delta for delta in benchmark_deltas.values() if delta < 0]
        if positives and not negatives:
            return PromotionDecision.PROMOTE
        if positives and negatives:
            return PromotionDecision.REVISE
        return PromotionDecision.REJECT


class RollbackService:
    def record(
        self,
        *,
        service: ImprovementExperimentService,
        experiment: ImprovementExperiment,
        reason: str,
        evidence_refs: list[str],
    ) -> RollbackRecord:
        candidate = service.candidates[experiment.candidate_id]
        if not evidence_refs:
            raise ValueError("rollback_requires_evidence")
        record = RollbackRecord(
            experiment_id=experiment.id,
            reason=reason,
            rollback_plan=candidate.rollback_plan,
            evidence_refs=list(evidence_refs),
            executed=False,
        )
        service.rollbacks[record.id] = record
        return record
