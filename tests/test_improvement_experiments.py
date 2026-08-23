import pytest

from brain.developmental.improvement_experiments import (
    CandidateEvaluationService,
    ExperimentCandidate,
    ExperimentRun,
    ImprovementExperimentService,
    PromotionDecision,
    RollbackService,
)
from brain.developmental.metacognitive_optimization import (
    ImprovementHypothesis,
    LearningDebtItem,
    SelfOptimizationPlanner,
)


def approved_plan():
    planner = SelfOptimizationPlanner()
    debt = LearningDebtItem("planning", "regression", 0.8, 0.9, ["evidence:debt"])
    hypothesis = ImprovementHypothesis(
        "planning",
        "candidate curriculum change",
        0.1,
        0.7,
        ["evidence:hypothesis"],
        "revert candidate artifact",
        "tests/test_improvement_experiments.py",
        ["planning improves", "control suite passes"],
    )
    plan = planner.propose(
        objective="repair planning",
        hypotheses=[hypothesis],
        learning_debt=[debt],
        traceability_refs=["issue:87"],
    )
    planner.mark_reviewed(plan.id)
    planner.approve_experiment(plan.id, operator_approval_ref="approval:planner")
    return plan


def registered_candidate(service: ImprovementExperimentService) -> ExperimentCandidate:
    return service.register_candidate(
        ExperimentCandidate(
            artifact_refs=["candidate:curriculum-v2"],
            description="planning curriculum candidate",
            test_targets=["tests/test_improvement_experiments.py"],
            benchmark_targets=["planning", "memory"],
            rollback_plan="restore candidate:curriculum-v1",
        )
    )


def test_experiment_requires_approved_plan_operator_approval_and_rollback_candidate() -> None:
    service = ImprovementExperimentService()
    candidate = registered_candidate(service)
    plan = approved_plan()
    experiment = service.create_experiment(
        plan=plan,
        candidate=candidate,
        operator_approval_ref="approval:experiment",
        protected_benchmarks=["planning", "memory"],
    )
    assert experiment.candidate_id == candidate.id


def test_successful_improvement_emits_promote_without_mutating_code() -> None:
    service = ImprovementExperimentService()
    candidate = registered_candidate(service)
    experiment = service.create_experiment(
        plan=approved_plan(),
        candidate=candidate,
        operator_approval_ref="approval:experiment",
        protected_benchmarks=["planning", "memory"],
    )
    run = service.record_run(
        ExperimentRun(
            experiment.id,
            before_scores={"planning": 0.6, "memory": 0.7},
            after_scores={"planning": 0.8, "memory": 0.75},
            control_results={"pytest": True, "control": True},
            evidence_refs=["run:successful"],
        )
    )
    result = CandidateEvaluationService().evaluate(experiment=experiment, run=run)
    assert result.decision is PromotionDecision.PROMOTE
    with pytest.raises(ValueError, match="cannot_mutate_merge_or_deploy"):
        service.direct_mutation(experiment.id)


def test_protected_regression_forces_hold() -> None:
    service = ImprovementExperimentService()
    candidate = registered_candidate(service)
    experiment = service.create_experiment(
        plan=approved_plan(),
        candidate=candidate,
        operator_approval_ref="approval:experiment",
        protected_benchmarks=["planning", "memory"],
        regression_tolerance=0.01,
    )
    run = service.record_run(
        ExperimentRun(
            experiment.id,
            before_scores={"planning": 0.8, "memory": 0.8},
            after_scores={"planning": 0.9, "memory": 0.6},
            control_results={"pytest": True},
            evidence_refs=["run:regression"],
        )
    )
    result = CandidateEvaluationService().evaluate(experiment=experiment, run=run)
    assert result.decision is PromotionDecision.HOLD
    assert result.protected_regressions == ["memory"]


def test_failed_control_suite_forces_reject() -> None:
    service = ImprovementExperimentService()
    candidate = registered_candidate(service)
    experiment = service.create_experiment(
        plan=approved_plan(),
        candidate=candidate,
        operator_approval_ref="approval:experiment",
        protected_benchmarks=["planning"],
    )
    run = service.record_run(
        ExperimentRun(
            experiment.id,
            before_scores={"planning": 0.6},
            after_scores={"planning": 0.9},
            control_results={"pytest": False},
            evidence_refs=["run:failed-control"],
        )
    )
    result = CandidateEvaluationService().evaluate(experiment=experiment, run=run)
    assert result.decision is PromotionDecision.REJECT


def test_mixed_nonprotected_results_require_revision() -> None:
    service = ImprovementExperimentService()
    candidate = registered_candidate(service)
    experiment = service.create_experiment(
        plan=approved_plan(),
        candidate=candidate,
        operator_approval_ref="approval:experiment",
        protected_benchmarks=["planning"],
        regression_tolerance=0.2,
    )
    run = service.record_run(
        ExperimentRun(
            experiment.id,
            before_scores={"planning": 0.6, "style": 0.8},
            after_scores={"planning": 0.7, "style": 0.75},
            control_results={"pytest": True},
            evidence_refs=["run:mixed"],
        )
    )
    result = CandidateEvaluationService().evaluate(experiment=experiment, run=run)
    assert result.decision is PromotionDecision.REVISE


def test_rollback_record_preserves_failed_experiment_evidence() -> None:
    service = ImprovementExperimentService()
    candidate = registered_candidate(service)
    experiment = service.create_experiment(
        plan=approved_plan(),
        candidate=candidate,
        operator_approval_ref="approval:experiment",
        protected_benchmarks=["planning"],
    )
    rollback = RollbackService().record(
        service=service,
        experiment=experiment,
        reason="control regression",
        evidence_refs=["result:reject"],
    )
    assert rollback.rollback_plan == candidate.rollback_plan
    assert rollback.executed is False
    assert service.rollbacks[rollback.id] is rollback
