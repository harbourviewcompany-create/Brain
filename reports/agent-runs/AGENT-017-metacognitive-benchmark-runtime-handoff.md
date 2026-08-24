# AGENT-017 Metacognitive Benchmark Runtime Handoff

## Ticket

Issue #77 — Build metacognitive benchmark and self-optimization flywheel.

## Work completed

Implemented runtime V0 as an extension of `brain/developmental/self_model.py` so the existing developmental traceability path remains intact without introducing an untraced new code module.

Added:

- `CapabilityBenchmark`
- `BenchmarkRun`
- `RegressionSignal`
- `LearningDebtItem`
- `ImprovementHypothesis`
- `SelfOptimizationPlan`
- `BenchmarkService`
- `RegressionDetectionService`
- `LearningDebtPrioritizationService`
- `SelfOptimizationPlanner`

## Tests

Added `tests/test_metacognitive_benchmark_flywheel.py` covering:

- evidence-backed benchmark runs
- visible regression detection
- regression-hidden fail-closed behavior
- learning-debt priority from regression pressure
- proposal-only self-optimization plans
- rollback/test/acceptance requirements
- superiority-claim external evidence gating

## Fixtures

Added `tests/fixtures/brain/metacognitive_benchmark_runtime.json`.

## Acceptance evidence

Added:

- `reports/acceptance/AGENT-017-metacognitive-benchmark-runtime.json`
- `reports/go-hold/AGENT-017-RUNTIME-GO-HOLD.json`

## Unresolved items

- Live self-modification remains HOLD.
- External action remains HOLD.
- Unsupported full-Brain and superior-intelligence claims remain HOLD.
- Archive byte upload remains blocked by #52.

## GO/HOLD

GO for AGENT-017 runtime V0 after CI passes.

HOLD for live autonomous self-modification, external action, full Brain completion, biological equivalence, consciousness, and superior-intelligence claims without external benchmark evidence.
