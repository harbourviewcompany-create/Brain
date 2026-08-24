# Brain Governed Developmental Improvement Cycle

Status: APPROVED IMPLEMENTATION SPEC FOR AGENT-020.

## Objective

Connect the existing metacognitive benchmark layer (AGENT-017), bounded experiment layer (AGENT-018), and durable evidence ledger (AGENT-019) into a single governed developmental cycle.

## Canonical cycle

1. Register a capability benchmark and persist it.
2. Persist baseline and current benchmark runs.
3. Detect regression or explicitly record `NO_REGRESSION`.
4. When a regression exists, create and persist learning debt and an improvement hypothesis.
5. Propose and persist a non-executable self-optimization plan.
6. Require explicit operator approval before the plan can enter `APPROVED_FOR_EXPERIMENT`.
7. Register a candidate artifact with tests, benchmarks and rollback instructions.
8. Require a separate operator approval to instantiate the candidate experiment.
9. Persist experiment, run and evidence.
10. Evaluate protected regressions and control-suite status through AGENT-018 gates.
11. Persist `PROMOTE`, `REVISE`, `REJECT` or `HOLD` result and a cycle checkpoint.
12. For REJECT/HOLD, persist rollback evidence.
13. Reconstruct the complete cycle after restart through AGENT-019 replay.

## Controller

`DevelopmentalImprovementCycleService` is an orchestration boundary, not an execution authority. It coordinates already governed services and writes every material object/state to `DevelopmentalEvidenceStore`.

## Approval separation

Plan experiment authorization and candidate experiment execution are separate approval transitions. The controller may not manufacture either approval reference. Missing approval fails closed.

## Durable checkpoints

Every material cycle state is represented by `DevelopmentalCycleCheckpoint`, including `NO_REGRESSION`, `REGRESSION_DETECTED`, `PLAN_PROPOSED`, `PLAN_EXPERIMENT_APPROVED`, and final experiment decision states.

## Hard boundaries

- `PROMOTE` is an evidence recommendation, not code mutation or merge authority.
- No self-approval.
- No source mutation, PR merge, deployment, spending or external action.
- No deletion/suppression of regressions, failed controls, rejected experiments, HOLD results or rollback records.
- Production execution of persistence migration remains environment-specific.

## GO/HOLD

GO for repository end-to-end developmental improvement orchestration after exact-head protected CI. HOLD for autonomous code mutation, self-approval, merge, deploy, spending, external action and unsupported superiority claims.
