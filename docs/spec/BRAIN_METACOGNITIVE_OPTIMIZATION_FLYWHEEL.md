# Brain Metacognitive Optimization Flywheel

Status: APPROVED IMPLEMENTATION SPEC FOR AGENT-017.

## Objective

Measure Brain capability with evidence-bearing benchmarks, detect regressions, preserve learning debt, generate improvement hypotheses, prioritize a curriculum/repair plan, and record improvement evidence without allowing benchmark output to directly self-modify runtime code or authorize unsupported superiority claims.

## Core objects

`CapabilityBenchmark`, `BenchmarkRun`, `RegressionSignal`, `ImprovementHypothesis`, `LearningDebtItem`, and `SelfOptimizationPlan` are first-class records.

## Runtime services

- `BenchmarkService`: registers benchmark definitions and preserves run history.
- `RegressionDetectionService`: compares baseline/current runs using benchmark directionality and emits explicit regression signals.
- `LearningDebtPrioritizationService`: scores unresolved capability debt from severity, strategic value and regression evidence.
- `SelfOptimizationPlanner`: creates proposal-only plans with traceability, rollback, test targets and acceptance criteria.
- `ClaimBoundaryService`: blocks superiority claims unless external or third-party benchmark evidence exists.
- `MetacognitiveOptimizationRuntime`: aggregates benchmarks, regressions, debt, hypotheses, plans and operator capability state.

## Canonical loop

1. Register capability benchmark.
2. Record evidence-backed benchmark run.
3. Compare against a preserved baseline/run history.
4. Emit and preserve regression signal when performance degrades.
5. Convert capability gaps/regressions into learning-debt records.
6. Rank learning debt.
7. Register evidence-backed improvement hypotheses.
8. Propose a non-executable self-optimization plan.
9. Review and, when explicitly approved, mark the plan approved for a bounded experiment only.
10. Run tests/benchmarks outside this planning object and record results as new evidence.
11. Accept, revise or reject based on evidence; never erase failed/regressed history.

## Hard gates

- No benchmark run without evidence, implementation reference and test target.
- No optimization plan without learning debt, hypothesis, traceability, rollback, test target and acceptance criteria.
- Benchmark output cannot directly execute self-modification.
- Operator approval may authorize an experiment but does not make a plan directly executable.
- Regression records are preserved; regressions may be resolved but not hidden by deletion.
- Internal/self-referential benchmarks cannot authorize superior-intelligence claims.
- External/third-party benchmark evidence only makes a claim eligible for evaluation; it does not prove universal superiority.

## Operator surface

The operator surface must show capability scores/history, regression alerts, prioritized learning debt, improvement proposals and claim/HOLD boundaries.

## GO/HOLD

GO for repository runtime V0 when runtime code, deterministic fixture, tests, operator surface, traceability and acceptance evidence pass protected CI. HOLD for live autonomous self-modification and unsupported claims that Brain is more intelligent than all other systems.
