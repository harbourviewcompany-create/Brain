# Brain Controlled Improvement Experiments

Status: APPROVED IMPLEMENTATION SPEC FOR AGENT-018.

AGENT-018 extends the AGENT-017 proposal-only optimization layer with bounded internal experiment evaluation. It does not grant autonomous code mutation, merge, deployment, spending, or external action.

## Core objects

`ExperimentCandidate`, `ImprovementExperiment`, `ExperimentRun`, `ExperimentResult`, `PromotionDecision`, and `RollbackRecord`.

## Services

- `ImprovementExperimentService`: validates candidate artifacts and creates experiments only from AGENT-017 plans already approved for experiment.
- `CandidateEvaluationService`: computes before/after benchmark deltas and protected regressions.
- `PromotionGateService`: emits `PROMOTE`, `REVISE`, `REJECT`, or `HOLD` as evidence-only decisions.
- `RollbackService`: preserves rollback instructions and failure evidence without executing mutations.

## Canonical loop

approved optimization plan -> registered candidate -> operator-approved experiment -> evidence-bearing run -> benchmark/control evaluation -> promotion decision -> preserve result and rollback evidence -> external implementation process, if separately authorized.

## Hard gates

- Candidate requires artifact refs, test targets, benchmark targets and rollback plan.
- Experiment requires AGENT-017 `APPROVED_FOR_EXPERIMENT` state and explicit operator approval.
- Protected benchmark regression beyond tolerance forces HOLD.
- Any failed required control suite forces REJECT.
- Mixed unprotected results require REVISE.
- Experiment runtime cannot mutate code, merge pull requests, deploy, spend, or perform external actions.
- Rejected/HOLD experiments and rollback records remain preserved.

## GO/HOLD

GO for repository experiment-evaluation runtime after exact-head protected CI. HOLD for autonomous mutation, merge/deploy execution, external action, or unsupported superiority claims.
