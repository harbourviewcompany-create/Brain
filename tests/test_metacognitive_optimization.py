from brain.developmental.metacognitive_optimization import (
    BenchmarkEvidenceClass,
    BenchmarkRun,
    CapabilityBenchmark,
    ClaimBoundaryService,
    ImprovementHypothesis,
    LearningDebtItem,
    LearningDebtPrioritizationService,
    MetacognitiveOptimizationRuntime,
    OptimizationPlanState,
    RegressionDetectionService,
)


def evidence() -> list[str]:
    return ["fixture:agent-017", "test:metacognitive-optimization"]


def test_benchmark_runs_require_evidence_and_traceable_test_target() -> None:
    runtime = MetacognitiveOptimizationRuntime()
    benchmark = runtime.benchmarks.register(
        CapabilityBenchmark("reasoning-suite", "reasoning", "score", True, minimum_evidence_count=2)
    )
    run = BenchmarkRun(
        benchmark.id,
        0.72,
        evidence(),
        BenchmarkEvidenceClass.INTERNAL,
        "brain/developmental/higher_order_cognition.py",
        "tests/test_developmental_higher_order_cognition.py",
    )
    runtime.benchmarks.record(run)
    assert runtime.benchmarks.history(benchmark.id) == [run]


def test_regressions_are_detected_and_preserved() -> None:
    runtime = MetacognitiveOptimizationRuntime()
    benchmark = runtime.benchmarks.register(CapabilityBenchmark("planning", "planning", "score", True))
    baseline = runtime.benchmarks.record(
        BenchmarkRun(benchmark.id, 0.80, evidence(), BenchmarkEvidenceClass.INTERNAL, "impl:v1", "test:planning")
    )
    current = runtime.benchmarks.record(
        BenchmarkRun(benchmark.id, 0.55, evidence(), BenchmarkEvidenceClass.INTERNAL, "impl:v2", "test:planning")
    )
    signal = RegressionDetectionService().detect(benchmark=benchmark, baseline=baseline, current=current)
    assert signal is not None
    runtime.register_regression(signal)
    assert runtime.regressions[signal.id] is signal
    assert signal.delta < 0
    assert signal.resolved is False


def test_learning_debt_prioritization_uses_severity_value_and_regressions() -> None:
    regression_backed = LearningDebtItem(
        "planning", "long-horizon decomposition regression", 0.9, 0.9, evidence(), source_regression_ids=[]
    )
    lower = LearningDebtItem("style", "minor response inconsistency", 0.2, 0.2, evidence())
    ranked = LearningDebtPrioritizationService().prioritize([lower, regression_backed])
    assert ranked[0] is regression_backed
    assert ranked[0].priority > ranked[1].priority


def test_optimization_plans_are_proposal_only_and_require_rollback_test_and_acceptance() -> None:
    runtime = MetacognitiveOptimizationRuntime()
    debt = runtime.add_learning_debt(
        LearningDebtItem("planning", "planning regression", 0.8, 0.9, evidence())
    )
    hypothesis = runtime.add_hypothesis(
        ImprovementHypothesis(
            "planning",
            "add adversarial decomposition curriculum",
            0.15,
            0.7,
            evidence(),
            "revert curriculum manifest and runtime commit",
            "tests/test_metacognitive_optimization.py",
            ["planning benchmark returns to baseline", "no regression in control suite"],
        )
    )
    plan = runtime.planner.propose(
        objective="repair planning regression",
        hypotheses=[hypothesis],
        learning_debt=[debt],
        traceability_refs=["issue:77", "issue:82"],
    )
    assert plan.state is OptimizationPlanState.PROPOSED
    assert plan.executable is False
    reviewed = runtime.planner.mark_reviewed(plan.id)
    assert reviewed.state is OptimizationPlanState.REVIEWED
    approved = runtime.planner.approve_experiment(plan.id, operator_approval_ref="approval:test-only")
    assert approved.state is OptimizationPlanState.APPROVED_FOR_EXPERIMENT
    assert approved.executable is False


def test_benchmark_output_cannot_directly_self_modify() -> None:
    runtime = MetacognitiveOptimizationRuntime()
    debt = runtime.add_learning_debt(LearningDebtItem("memory", "retrieval debt", 0.5, 0.7, evidence()))
    hypothesis = runtime.add_hypothesis(
        ImprovementHypothesis(
            "memory",
            "retrieval curriculum",
            0.1,
            0.6,
            evidence(),
            "revert retrieval curriculum",
            "tests/test_metacognitive_optimization.py",
            ["retrieval score improves"],
        )
    )
    plan = runtime.planner.propose(
        objective="improve retrieval",
        hypotheses=[hypothesis],
        learning_debt=[debt],
        traceability_refs=["issue:77"],
    )
    try:
        runtime.planner.direct_self_modify(plan.id)
    except ValueError as exc:
        assert str(exc) == "benchmark_output_cannot_directly_self_modify"
    else:
        raise AssertionError("direct self-modification must fail closed")


def test_superiority_claim_requires_external_or_third_party_benchmark_evidence() -> None:
    internal = BenchmarkRun(
        CapabilityBenchmark("internal", "reasoning", "score", True).id,
        0.95,
        evidence(),
        BenchmarkEvidenceClass.INTERNAL,
        "impl",
        "test",
    )
    assert ClaimBoundaryService.superiority_claim_allowed([internal]) is False
    external = BenchmarkRun(
        internal.benchmark_id,
        0.91,
        ["external-benchmark:published-result"],
        BenchmarkEvidenceClass.THIRD_PARTY,
        "impl",
        "test",
    )
    assert ClaimBoundaryService.superiority_claim_allowed([internal, external]) is True


def test_operator_capability_map_exposes_regressions_learning_debt_plans_and_holds() -> None:
    runtime = MetacognitiveOptimizationRuntime()
    benchmark = runtime.benchmarks.register(CapabilityBenchmark("memory", "memory", "score", True))
    runtime.benchmarks.record(
        BenchmarkRun(benchmark.id, 0.7, evidence(), BenchmarkEvidenceClass.INTERNAL, "impl", "test")
    )
    runtime.add_learning_debt(LearningDebtItem("memory", "retrieval gap", 0.6, 0.8, evidence()))
    surface = runtime.capability_map()
    assert surface["capabilities"]["memory"] == 0.7
    assert surface["learning_debt"] == 1
    assert surface["hold_boundaries"]["self_modification"] == "proposal_only"
