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

## CI evidence

Latest observed PR head before this handoff update passed:

- Brain Control Policy: success
- test: success

This handoff update changes only this report file, so CI must re-run on the new head before merge.

## Merge gate

The GitHub merge API returned a branch-protection response that the two required checks are still expected. No branch-protection bypass was performed.

## Unresolved items

- PR #78 remains open until GitHub accepts the required checks for the latest head.
- Live self-modification remains HOLD.
- External action remains HOLD.
- Unsupported full-Brain and superior-intelligence claims remain HOLD.
- Archive byte upload remains blocked by #52.

## GO/HOLD

GO for AGENT-017 runtime V0 after CI passes on the final PR head.

HOLD for merge until branch protection accepts the required checks. HOLD for live autonomous self-modification, external action, full Brain completion, biological equivalence, consciousness, and superior-intelligence claims without external benchmark evidence.
