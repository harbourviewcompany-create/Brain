# Metacognitive Benchmark Build Queue

Status: APPROVED queue. Runtime remains HOLD until issue #77 is implemented.

## AGENT-017 — Metacognitive Benchmark and Self-Optimization Flywheel

Governing issue: #77

### Objective

Implement an evidence-bound measurement layer that lets the Brain improve like a developing system without silently rewriting itself, hiding regressions, or claiming unsupported superiority.

### Required implementation files

```text
brain/developmental/metacognitive_benchmark.py
tests/test_developmental_metacognitive_benchmark.py
tests/fixtures/brain/metacognitive_benchmark_flywheel.json
docs/operator-surfaces/metacognitive-benchmark-dashboard.json
reports/acceptance/AGENT-017-metacognitive-benchmark.json
reports/go-hold/AGENT-017-METACOGNITIVE-BENCHMARK-GO-HOLD.json
reports/agent-runs/AGENT-017-metacognitive-benchmark-handoff.md
```

### Required tests

- `benchmark_run_requires_evidence`
- `regression_cannot_be_hidden_or_deleted`
- `learning_debt_priority_is_deterministic`
- `self_optimization_plan_is_proposal_only`
- `optimization_requires_rollback_and_acceptance_target`
- `superiority_claim_requires_external_benchmark_evidence`

### Required replay scenarios

- baseline capability measurement;
- regression after score drop;
- repeated failure producing higher learning-debt priority;
- improvement proposal blocked by missing rollback;
- superiority claim blocked without external benchmark evidence.

### GO/HOLD

GO only when implementation, tests, fixture, replay evidence, operator surface, traceability and acceptance report exist.

HOLD for any live autonomous self-modification, live external action, unsupported biological equivalence claim, or unsupported claim that the Brain is more intelligent than any existing system.
