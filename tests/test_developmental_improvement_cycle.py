from uuid import uuid4

import pytest

from brain.developmental.evidence_store import (
    DevelopmentalReplayService,
    InMemoryDevelopmentalEvidenceStore,
)
from brain.developmental.improvement_cycle import DevelopmentalImprovementCycleService
from brain.developmental.improvement_experiments import (
    ExperimentCandidate,
    ExperimentRun,
    PromotionDecision,
)
from brain.developmental.metacognitive_optimization import (
    BenchmarkEvidenceClass,
    BenchmarkRun,
    CapabilityBenchmark,
)


def evidence() -> list[str]:
    return ["fixture:agent-020", "test:developmental-cycle"]


def benchmark_triplet(*, baseline_score: float, current_score: float):
    benchmark = CapabilityBenchmark("planning", "planning", "score", True)
    baseline = BenchmarkRun(
        benchmark.id,
        baseline_score,
        evidence(),
        BenchmarkEvidenceClass.INTERNAL,
        "impl:baseline",
        "test:planning",
    )
    current = BenchmarkRun(
        benchmark.id,
        current_score,
        evidence(),
        BenchmarkEvidenceClass.INTERNAL,
        "impl:current",
        "test:planning",
    )
    return benchmark, baseline, current


def regression_plan(service: DevelopmentalImprovementCycleService):
    benchmark, baseline, current = benchmark_triplet(baseline_score=0.8, current_score=0.55)
    assessment = service.assess_capability(
        benchmark=benchmark,
        baseline=baseline,
        current=current,
        evidence_refs=evidence(),
    )
    plan = service.propose_improvement(
        assessment=assessment,
        capability="planning",
        gap="long-horizon decomposition regression",
        mechanism="adversarial decomposition curriculum",
        expected_gain=0.2,
        confidence=0.7,
        severity=0.9,
        strategic_value=0.9,
        rollback_plan="restore curriculum baseline",
        test_target="tests/test_developmental_improvement_cycle.py",
        acceptance_criteria=["planning recovers", "control suite passes"],
        evidence_refs=evidence(),
    )
    return assessment, plan


def candidate() -> ExperimentCandidate:
    return ExperimentCandidate(
        artifact_refs=["candidate:planning-v2"],
        description="planning improvement candidate",
        test_targets=["tests/test_developmental_improvement_cycle.py"],
        benchmark_targets=["planning", "memory"],
        rollback_plan="restore candidate:planning-v1",
    )


def test_no_regression_is_persisted_as_explicit_cycle_state() -> None:
    store = InMemoryDevelopmentalEvidenceStore()
    service = DevelopmentalImprovementCycleService(store)
    benchmark, baseline, current = benchmark_triplet(baseline_score=0.7, current_score=0.8)
    assessment = service.assess_capability(
        benchmark=benchmark,
        baseline=baseline,
        current=current,
        evidence_refs=evidence(),
    )
    assert assessment.state == "NO_REGRESSION"
    result = service.cycle_result(assessment.cycle_id)
    assert result.state == "NO_REGRESSION"
    assert result.persistence_integrity["cycle_checkpoints"] == 1


def test_regression_flows_to_durable_debt_hypothesis_and_plan() -> None:
    store = InMemoryDevelopmentalEvidenceStore()
    service = DevelopmentalImprovementCycleService(store)
    assessment, plan = regression_plan(service)
    assert assessment.state == "REGRESSION_DETECTED"
    assert store.get("SelfOptimizationPlan", plan.id) is not None
    assert len(store.list("RegressionSignal")) == 1
    assert len(store.list("LearningDebtItem")) == 1
    assert len(store.list("ImprovementHypothesis")) == 1
    assert service.cycle_result(assessment.cycle_id).state == "PLAN_PROPOSED"


def test_plan_authorization_cannot_bypass_operator_approval() -> None:
    store = InMemoryDevelopmentalEvidenceStore()
    service = DevelopmentalImprovementCycleService(store)
    assessment, plan = regression_plan(service)
    with pytest.raises(ValueError, match="operator_approval"):
        service.authorize_plan_for_experiment(
            cycle_id=assessment.cycle_id,
            plan_id=plan.id,
            operator_approval_ref="",
            evidence_refs=evidence(),
        )


def test_successful_end_to_end_cycle_promotes_as_evidence_only() -> None:
    store = InMemoryDevelopmentalEvidenceStore()
    service = DevelopmentalImprovementCycleService(store)
    assessment, plan = regression_plan(service)
    service.authorize_plan_for_experiment(
        cycle_id=assessment.cycle_id,
        plan_id=plan.id,
        operator_approval_ref="approval:plan",
        evidence_refs=evidence(),
    )
    result = service.evaluate_candidate(
        cycle_id=assessment.cycle_id,
        plan_id=plan.id,
        candidate=candidate(),
        run=ExperimentRun(
            experiment_id=uuid4(),
            before_scores={"planning": 0.55, "memory": 0.7},
            after_scores={"planning": 0.82, "memory": 0.72},
            control_results={"pytest": True, "control": True},
            evidence_refs=evidence(),
        ),
        experiment_operator_approval_ref="approval:experiment",
        protected_benchmarks=["planning", "memory"],
        evidence_refs=evidence(),
    )
    assert result.decision is PromotionDecision.PROMOTE
    cycle = service.cycle_result(assessment.cycle_id)
    assert cycle.state == "EXPERIMENT_PROMOTE"
    assert cycle.decision is PromotionDecision.PROMOTE
    with pytest.raises(ValueError, match="cannot_self_approve_mutate_merge_or_deploy"):
        service.direct_self_modify(assessment.cycle_id)


def test_protected_regression_holds_and_persists_rollback_evidence() -> None:
    store = InMemoryDevelopmentalEvidenceStore()
    service = DevelopmentalImprovementCycleService(store)
    assessment, plan = regression_plan(service)
    service.authorize_plan_for_experiment(
        cycle_id=assessment.cycle_id,
        plan_id=plan.id,
        operator_approval_ref="approval:plan",
        evidence_refs=evidence(),
    )
    result = service.evaluate_candidate(
        cycle_id=assessment.cycle_id,
        plan_id=plan.id,
        candidate=candidate(),
        run=ExperimentRun(
            experiment_id=uuid4(),
            before_scores={"planning": 0.55, "memory": 0.8},
            after_scores={"planning": 0.8, "memory": 0.5},
            control_results={"pytest": True},
            evidence_refs=evidence(),
        ),
        experiment_operator_approval_ref="approval:experiment",
        protected_benchmarks=["planning", "memory"],
        evidence_refs=evidence(),
        regression_tolerance=0.01,
    )
    assert result.decision is PromotionDecision.HOLD
    assert len(store.list("RollbackRecord")) == 1
    assert service.cycle_result(assessment.cycle_id).state == "EXPERIMENT_HOLD"


def test_failed_control_rejects_and_restart_replay_preserves_cycle() -> None:
    store = InMemoryDevelopmentalEvidenceStore()
    service = DevelopmentalImprovementCycleService(store)
    assessment, plan = regression_plan(service)
    service.authorize_plan_for_experiment(
        cycle_id=assessment.cycle_id,
        plan_id=plan.id,
        operator_approval_ref="approval:plan",
        evidence_refs=evidence(),
    )
    result = service.evaluate_candidate(
        cycle_id=assessment.cycle_id,
        plan_id=plan.id,
        candidate=candidate(),
        run=ExperimentRun(
            experiment_id=uuid4(),
            before_scores={"planning": 0.55},
            after_scores={"planning": 0.9},
            control_results={"pytest": False},
            evidence_refs=evidence(),
        ),
        experiment_operator_approval_ref="approval:experiment",
        protected_benchmarks=["planning"],
        evidence_refs=evidence(),
    )
    assert result.decision is PromotionDecision.REJECT
    replayed = DevelopmentalReplayService().replay(store.events())
    restarted = DevelopmentalImprovementCycleService(replayed)
    cycle = restarted.cycle_result(assessment.cycle_id)
    assert cycle.state == "EXPERIMENT_REJECT"
    assert cycle.persistence_integrity["failed_or_hold_results"] == 1
    assert cycle.persistence_integrity["unresolved_regressions"] == 1


def test_candidate_experiment_requires_separate_operator_approval() -> None:
    store = InMemoryDevelopmentalEvidenceStore()
    service = DevelopmentalImprovementCycleService(store)
    assessment, plan = regression_plan(service)
    service.authorize_plan_for_experiment(
        cycle_id=assessment.cycle_id,
        plan_id=plan.id,
        operator_approval_ref="approval:plan",
        evidence_refs=evidence(),
    )
    with pytest.raises(ValueError, match="operator_approval"):
        service.evaluate_candidate(
            cycle_id=assessment.cycle_id,
            plan_id=plan.id,
            candidate=candidate(),
            run=ExperimentRun(
                experiment_id=uuid4(),
                before_scores={"planning": 0.55},
                after_scores={"planning": 0.9},
                control_results={"pytest": True},
                evidence_refs=evidence(),
            ),
            experiment_operator_approval_ref="",
            protected_benchmarks=["planning"],
            evidence_refs=evidence(),
        )
