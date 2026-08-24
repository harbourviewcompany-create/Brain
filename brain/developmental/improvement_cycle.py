from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from .evidence_store import (
    DevelopmentalCycleCheckpoint,
    DevelopmentalEvidenceStore,
    DevelopmentalReplayService,
)
from .improvement_experiments import (
    CandidateEvaluationService,
    ExperimentCandidate,
    ExperimentResult,
    ExperimentRun,
    ImprovementExperimentService,
    PromotionDecision,
    RollbackService,
)
from .metacognitive_optimization import (
    BenchmarkRun,
    CapabilityBenchmark,
    ImprovementHypothesis,
    LearningDebtItem,
    MetacognitiveOptimizationRuntime,
    RegressionDetectionService,
    RegressionSignal,
    SelfOptimizationPlan,
)


@dataclass(slots=True)
class CapabilityAssessment:
    cycle_id: UUID
    benchmark_id: UUID
    baseline_run_id: UUID
    current_run_id: UUID
    regression_id: UUID | None
    state: str


@dataclass(slots=True)
class DevelopmentalCycleResult:
    cycle_id: UUID
    state: str
    decision: PromotionDecision | None
    related_record_ids: list[UUID]
    persistence_integrity: dict[str, object]


class DevelopmentalImprovementCycleService:
    """Governed AGENT-017 -> AGENT-018 -> AGENT-019 orchestration layer."""

    def __init__(self, store: DevelopmentalEvidenceStore) -> None:
        self.store = store
        self.metacognitive = MetacognitiveOptimizationRuntime()
        self.experiments = ImprovementExperimentService()

    def _persist(self, record: object, event_type: str, evidence_refs: list[str]) -> None:
        self.store.put(record, event_type=event_type, evidence_refs=evidence_refs)

    def _checkpoint(
        self,
        *,
        cycle_id: UUID,
        state: str,
        related_record_ids: list[UUID],
        evidence_refs: list[str],
        metadata: dict[str, object] | None = None,
    ) -> DevelopmentalCycleCheckpoint:
        checkpoint = DevelopmentalCycleCheckpoint(
            cycle_id=cycle_id,
            state=state,
            related_record_ids=list(related_record_ids),
            metadata=dict(metadata or {}),
        )
        self._persist(checkpoint, f"DEVELOPMENTAL_CYCLE_{state}", evidence_refs)
        return checkpoint

    def assess_capability(
        self,
        *,
        benchmark: CapabilityBenchmark,
        baseline: BenchmarkRun,
        current: BenchmarkRun,
        evidence_refs: list[str],
        cycle_id: UUID | None = None,
    ) -> CapabilityAssessment:
        if not evidence_refs:
            raise ValueError("capability_assessment_requires_evidence")
        cycle_id = cycle_id or uuid4()
        self.metacognitive.benchmarks.register(benchmark)
        self.metacognitive.benchmarks.record(baseline)
        self.metacognitive.benchmarks.record(current)
        self._persist(benchmark, "CAPABILITY_BENCHMARK_REGISTERED", evidence_refs)
        self._persist(baseline, "BENCHMARK_BASELINE_RECORDED", evidence_refs)
        self._persist(current, "BENCHMARK_CURRENT_RECORDED", evidence_refs)
        regression = RegressionDetectionService().detect(
            benchmark=benchmark,
            baseline=baseline,
            current=current,
        )
        related = [benchmark.id, baseline.id, current.id]
        if regression is None:
            state = "NO_REGRESSION"
            regression_id = None
        else:
            self.metacognitive.register_regression(regression)
            self._persist(regression, "REGRESSION_DETECTED", evidence_refs)
            related.append(regression.id)
            state = "REGRESSION_DETECTED"
            regression_id = regression.id
        self._checkpoint(
            cycle_id=cycle_id,
            state=state,
            related_record_ids=related,
            evidence_refs=evidence_refs,
        )
        return CapabilityAssessment(
            cycle_id=cycle_id,
            benchmark_id=benchmark.id,
            baseline_run_id=baseline.id,
            current_run_id=current.id,
            regression_id=regression_id,
            state=state,
        )

    def propose_improvement(
        self,
        *,
        assessment: CapabilityAssessment,
        capability: str,
        gap: str,
        mechanism: str,
        expected_gain: float,
        confidence: float,
        severity: float,
        strategic_value: float,
        rollback_plan: str,
        test_target: str,
        acceptance_criteria: list[str],
        evidence_refs: list[str],
    ) -> SelfOptimizationPlan:
        if assessment.regression_id is None:
            raise ValueError("improvement_plan_requires_regression_or_explicit_debt_path")
        regression = self.store.get("RegressionSignal", assessment.regression_id)
        if not isinstance(regression, RegressionSignal):
            raise ValueError("improvement_plan_requires_persisted_regression")
        debt = LearningDebtItem(
            capability=capability,
            gap=gap,
            severity=severity,
            strategic_value=strategic_value,
            evidence_refs=list(evidence_refs),
            source_regression_ids=[regression.id],
        )
        hypothesis = ImprovementHypothesis(
            target_capability=capability,
            mechanism=mechanism,
            expected_gain=expected_gain,
            confidence=confidence,
            evidence_refs=list(evidence_refs),
            rollback_plan=rollback_plan,
            test_target=test_target,
            acceptance_criteria=list(acceptance_criteria),
        )
        self.metacognitive.add_learning_debt(debt)
        self.metacognitive.add_hypothesis(hypothesis)
        plan = self.metacognitive.planner.propose(
            objective=f"repair:{capability}:{gap}",
            hypotheses=[hypothesis],
            learning_debt=[debt],
            traceability_refs=[f"cycle:{assessment.cycle_id}", *evidence_refs],
        )
        self._persist(debt, "LEARNING_DEBT_CREATED", evidence_refs)
        self._persist(hypothesis, "IMPROVEMENT_HYPOTHESIS_CREATED", evidence_refs)
        self._persist(plan, "SELF_OPTIMIZATION_PLAN_PROPOSED", evidence_refs)
        self._checkpoint(
            cycle_id=assessment.cycle_id,
            state="PLAN_PROPOSED",
            related_record_ids=[regression.id, debt.id, hypothesis.id, plan.id],
            evidence_refs=evidence_refs,
        )
        return plan

    def authorize_plan_for_experiment(
        self,
        *,
        cycle_id: UUID,
        plan_id: UUID,
        operator_approval_ref: str,
        evidence_refs: list[str],
    ) -> SelfOptimizationPlan:
        if not operator_approval_ref:
            raise ValueError("plan_authorization_requires_operator_approval")
        plan = self.store.get("SelfOptimizationPlan", plan_id)
        if not isinstance(plan, SelfOptimizationPlan):
            raise ValueError("unknown_persisted_optimization_plan")
        self.metacognitive.planner.plans[plan.id] = plan
        reviewed = self.metacognitive.planner.mark_reviewed(plan.id)
        self._persist(reviewed, "SELF_OPTIMIZATION_PLAN_REVIEWED", evidence_refs)
        approved = self.metacognitive.planner.approve_experiment(
            plan.id,
            operator_approval_ref=operator_approval_ref,
        )
        self._persist(approved, "SELF_OPTIMIZATION_PLAN_EXPERIMENT_APPROVED", evidence_refs)
        self._checkpoint(
            cycle_id=cycle_id,
            state="PLAN_EXPERIMENT_APPROVED",
            related_record_ids=[approved.id],
            evidence_refs=evidence_refs,
            metadata={"operator_approval_ref": operator_approval_ref},
        )
        return approved

    def evaluate_candidate(
        self,
        *,
        cycle_id: UUID,
        plan_id: UUID,
        candidate: ExperimentCandidate,
        run: ExperimentRun,
        experiment_operator_approval_ref: str,
        protected_benchmarks: list[str],
        evidence_refs: list[str],
        regression_tolerance: float = 0.0,
    ) -> ExperimentResult:
        if not experiment_operator_approval_ref:
            raise ValueError("candidate_experiment_requires_operator_approval")
        plan = self.store.get("SelfOptimizationPlan", plan_id)
        if not isinstance(plan, SelfOptimizationPlan):
            raise ValueError("candidate_experiment_requires_persisted_plan")
        self.experiments.register_candidate(candidate)
        self._persist(candidate, "EXPERIMENT_CANDIDATE_REGISTERED", evidence_refs)
        experiment = self.experiments.create_experiment(
            plan=plan,
            candidate=candidate,
            operator_approval_ref=experiment_operator_approval_ref,
            protected_benchmarks=protected_benchmarks,
            regression_tolerance=regression_tolerance,
        )
        self._persist(experiment, "IMPROVEMENT_EXPERIMENT_CREATED", evidence_refs)
        run.experiment_id = experiment.id
        recorded = self.experiments.record_run(run)
        self._persist(recorded, "IMPROVEMENT_EXPERIMENT_RUN_RECORDED", evidence_refs)
        result = CandidateEvaluationService().evaluate(experiment=experiment, run=recorded)
        self.experiments.results[result.id] = result
        self._persist(result, f"IMPROVEMENT_EXPERIMENT_{result.decision.value.upper()}", evidence_refs)
        related = [plan.id, candidate.id, experiment.id, recorded.id, result.id]
        if result.decision in {PromotionDecision.REJECT, PromotionDecision.HOLD}:
            rollback = RollbackService().record(
                service=self.experiments,
                experiment=experiment,
                reason=f"promotion_decision:{result.decision.value}",
                evidence_refs=evidence_refs,
            )
            self._persist(rollback, "ROLLBACK_RECORD_CREATED", evidence_refs)
            related.append(rollback.id)
        self._checkpoint(
            cycle_id=cycle_id,
            state=f"EXPERIMENT_{result.decision.value.upper()}",
            related_record_ids=related,
            evidence_refs=evidence_refs,
            metadata={"decision_is_evidence_only": True},
        )
        return result

    def cycle_result(self, cycle_id: UUID) -> DevelopmentalCycleResult:
        checkpoints = [
            item
            for item in self.store.list("DevelopmentalCycleCheckpoint")
            if item.cycle_id == cycle_id
        ]
        if not checkpoints:
            raise ValueError("unknown_developmental_cycle")
        latest = checkpoints[-1]
        decision = None
        if latest.state.startswith("EXPERIMENT_"):
            value = latest.state.removeprefix("EXPERIMENT_").lower()
            decision = PromotionDecision(value)
        return DevelopmentalCycleResult(
            cycle_id=cycle_id,
            state=latest.state,
            decision=decision,
            related_record_ids=list(latest.related_record_ids),
            persistence_integrity=DevelopmentalReplayService.integrity_report(self.store),
        )

    def direct_self_modify(self, cycle_id: UUID) -> None:
        self.cycle_result(cycle_id)
        raise ValueError("developmental_cycle_cannot_self_approve_mutate_merge_or_deploy")
