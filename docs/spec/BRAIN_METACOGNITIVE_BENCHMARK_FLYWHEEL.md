# Brain Metacognitive Benchmark and Self-Optimization Flywheel

Status: APPROVED control architecture. Runtime implementation remains governed by issue #77.

## Objective

The Brain must improve by measuring itself, detecting regressions, prioritizing learning debt, and proposing evidence-bound upgrades. This layer prevents vague intelligence claims by requiring benchmark evidence, regression records, acceptance targets, rollback plans, and explicit claim boundaries.

## Canonical loop

```text
capability question
-> benchmark definition
-> benchmark run
-> score + evidence
-> regression / improvement signal
-> learning debt priority
-> self-optimization proposal
-> human/agent review
-> implementation issue
-> test + replay + acceptance evidence
-> capability ledger update
-> claim-boundary report
```

## Required objects

- `CapabilityBenchmark`: named measurable capability with task class, success metric, minimum evidence and claim boundary.
- `BenchmarkRun`: one deterministic run against a benchmark, including inputs, outputs, score, errors and artifacts.
- `RegressionSignal`: evidence that capability has degraded or become unstable.
- `ImprovementHypothesis`: proposed change that should improve measured capability.
- `LearningDebtItem`: preserved gap between desired capability and demonstrated capability.
- `SelfOptimizationPlan`: ordered proposal for improvement with test targets, rollback plan, owner, risk and HOLD gates.
- `CapabilityClaimBoundary`: explicit statement of what may and may not be claimed from the benchmark evidence.

## Required services

- `BenchmarkService`: creates and evaluates benchmark runs without mutating live behavior.
- `RegressionDetectionService`: compares current runs to baselines and emits non-deletable regression records.
- `LearningDebtPrioritizationService`: ranks gaps by consequence, repeated failure, user value, dependency centrality and safety risk.
- `SelfOptimizationPlanner`: converts learning debt into proposal-only improvement plans.
- `ClaimBoundaryService`: blocks superiority, biological-equivalence and full-completion claims unless evidence exists.

## Hard gates

1. No intelligence-superiority claim without external benchmark evidence.
2. No self-modification execution from benchmark output alone.
3. No hidden regression, deleted failure, or overwritten benchmark run.
4. No optimization proposal without traceability, rollback, tests, acceptance criteria and GO/HOLD status.
5. No benchmark accepted as authoritative unless the task, metric, evidence source and failure mode are recorded.

## Operator surface requirements

The operator must see:

- capability map by module and benchmark family;
- latest score, baseline score and regression delta;
- failed benchmark cases with evidence links;
- learning debt ranked by severity and leverage;
- proposed improvement plans;
- plans blocked by missing evidence;
- claim-boundary report.

## GO/HOLD

GO for architecture and issue definition.

HOLD for runtime completion until the repo contains code, tests, fixtures, deterministic replay evidence, operator surface, traceability and acceptance report for issue #77.

HOLD permanently for unsupported claims that this Brain is more intelligent than any existing system unless validated by benchmark evidence that is preserved in the repo.
