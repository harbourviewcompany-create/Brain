import pytest

from brain.developmental.self_model import (
    BenchmarkDomain,
    BenchmarkRun,
    BenchmarkService,
    CapabilityBenchmark,
    ImprovementHypothesis,
    LearningDebtItem,
    LearningDebtPrioritizationService,
    RegressionDetectionService,
    SelfOptimizationPlanner,
)


def test_benchmark_runs_are_evidence_backed() -> None:
    service = BenchmarkService()
    service.register_benchmark(
        CapabilityBenchmark(
            benchmark_id="commercial-reasoning-v0",
            name="Commercial reasoning replay",
            domain=BenchmarkDomain.COMMERCIAL,
            capability="commercial-reasoning-v0",
            target_score=0.85,
            evidence_refs=["docs/spec/BRAIN_METACOGNITIVE_BENCHMARK_FLYWHEEL.md"],
        )
    )

    with pytest.raises(ValueError, match="benchmark_run_requires_evidence"):
        service.record_run(
            BenchmarkRun(
                benchmark_id="commercial-reasoning-v0",
                score=0.81,
                baseline_score=0.72,
                evidence_refs=[],
                test_refs=[],
            )
        )

    run = service.record_run(
        BenchmarkRun(
            benchmark_id="commercial-reasoning-v0",
            score=0.81,
            baseline_score=0.72,
            evidence_refs=["reports/acceptance/AGENT-017-metacognitive-benchmark-runtime.json"],
            test_refs=["tests/test_metacognitive_benchmark_flywheel.py"],
        )
    )

    assert run.delta == pytest.approx(0.09)


def test_regression_detection_cannot_hide_regressions() -> None:
    prior = BenchmarkRun(
        benchmark_id="governance-boundary-v0",
        score=0.91,
        baseline_score=0.82,
        evidence_refs=["prior-run"],
        test_refs=["tests/test_metacognitive_benchmark_flywheel.py"],
    )
    current = BenchmarkRun(
        benchmark_id="governance-boundary-v0",
        score=0.74,
        baseline_score=0.82,
        evidence_refs=["current-run"],
        test_refs=["tests/test_metacognitive_benchmark_flywheel.py"],
    )

    service = RegressionDetectionService()
    signal = service.detect(current, prior, threshold=0.05)

    assert signal is not None
    assert signal.hidden is False
    assert signal.severity == pytest.approx(0.17)
    service.assert_visible(signal)
    signal.hidden = True
    with pytest.raises(ValueError, match="regression_signal_cannot_be_hidden"):
        service.assert_visible(signal)


def test_learning_debt_priority_uses_regression_pressure() -> None:
    current = BenchmarkRun(
        benchmark_id="memory-consolidation-v0",
        score=0.60,
        baseline_score=0.75,
        evidence_refs=["current-run"],
        test_refs=["tests/test_metacognitive_benchmark_flywheel.py"],
    )
    prior = BenchmarkRun(
        benchmark_id="memory-consolidation-v0",
        score=0.82,
        baseline_score=0.75,
        evidence_refs=["prior-run"],
        test_refs=["tests/test_metacognitive_benchmark_flywheel.py"],
    )
    regression = RegressionDetectionService().detect(current, prior, threshold=0.05)
    assert regression is not None

    debts = [
        LearningDebtItem(
            debt_id="debt-memory",
            capability="memory-consolidation-v0",
            gap="replay coverage is too shallow",
            severity=0.70,
            evidence_refs=["reports/go-hold/AGENT-017-RUNTIME-GO-HOLD.json"],
        ),
        LearningDebtItem(
            debt_id="debt-ui",
            capability="operator-surface-v0",
            gap="dashboard lacks longitudinal view",
            severity=0.40,
            evidence_refs=["docs/operator-surfaces/metacognitive-benchmark-dashboard.json"],
        ),
    ]

    prioritized = LearningDebtPrioritizationService().prioritize(debts, [regression])

    assert prioritized[0].debt_id == "debt-memory"
    assert prioritized[0].priority > prioritized[1].priority


def test_self_optimization_plan_is_proposal_only_and_rollback_bound() -> None:
    hypothesis = ImprovementHypothesis(
        hypothesis_id="hyp-calibration-loop",
        target_capability="benchmark-bound-metacognition",
        mechanism="increase calibration replay fixtures before strategy promotion",
        expected_gain=0.11,
        risk=0.03,
        evidence_refs=["tests/fixtures/brain/metacognitive_benchmark_runtime.json"],
        rollback_plan="revert fixture and scoring change if benchmark score declines",
        test_target="tests/test_metacognitive_benchmark_flywheel.py",
        acceptance_criteria=["regression detection remains visible"],
    )
    debt = LearningDebtItem(
        debt_id="debt-calibration",
        capability="benchmark-bound-metacognition",
        gap="not enough calibration cases",
        severity=0.65,
        evidence_refs=["reports/acceptance/AGENT-017-metacognitive-benchmark-runtime.json"],
    )

    plan = SelfOptimizationPlanner().create_plan(
        plan_id="plan-agent-017-v0",
        hypotheses=[hypothesis],
        debts=[debt],
        evidence_refs=["reports/acceptance/AGENT-017-metacognitive-benchmark-runtime.json"],
    )

    assert plan.proposal_only is True
    assert plan.rollback_required is True
    assert plan.test_targets == ["tests/test_metacognitive_benchmark_flywheel.py"]
    with pytest.raises(ValueError, match="proposal_only"):
        SelfOptimizationPlanner().execute_plan(plan)


def test_superiority_claim_requires_external_benchmark_evidence() -> None:
    service = BenchmarkService()
    service.register_benchmark(
        CapabilityBenchmark(
            benchmark_id="external-intelligence-comparison-v0",
            name="External intelligence comparison",
            domain=BenchmarkDomain.REASONING,
            capability="general-intelligence-claim-boundary",
            target_score=0.95,
            evidence_refs=["docs/spec/BRAIN_METACOGNITIVE_BENCHMARK_FLYWHEEL.md"],
            external_comparison_required=True,
        )
    )
    service.record_run(
        BenchmarkRun(
            benchmark_id="external-intelligence-comparison-v0",
            score=0.97,
            baseline_score=0.70,
            evidence_refs=["internal-run"],
            test_refs=["tests/test_metacognitive_benchmark_flywheel.py"],
        )
    )

    assert service.superiority_claim_allowed("external-intelligence-comparison-v0") is False
    service.add_external_comparison_evidence(
        "external-intelligence-comparison-v0",
        ["external-benchmark-report-placeholder"],
    )
    assert service.superiority_claim_allowed("external-intelligence-comparison-v0") is True
