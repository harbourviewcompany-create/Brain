# Brain PR Acceptance Evidence

## Control Preflight

- [x] I read and followed the Brain control rules already preserved in the repository.
- [x] I used the repository acceptance-evidence structure for this PR.

## Scope

```text
SLICE-GLOBAL-SOURCE-P1: make external connector acquisition restart-safe and provenance-first. Persist connector scheduling, expiring worker leases, ingestion runs and raw observations; change dedupe from global hash suppression to source-scoped identity so independent corroboration survives; preserve observed/retrieved time; exclude credentials from durable config; and automatically use PostgreSQL acquisition state when migration 024 is available while retaining an explicit pre-024 compatibility fallback. This slice does not apply production migrations or alter Railway configuration.
```

## Source Authority

- [x] SOURCE
- [x] APPROVED
- [ ] PROPOSAL
- [ ] SPECULATIVE
- [ ] REVIEW-ONLY
- [ ] BLOCKED
- [x] BUILD-READY

Source records:

| Source ID | Path / Citation | Label | Preserved Original | Notes |
|---|---|---|---|---|
| SRC-BRAIN-GLOBAL-SOURCE-P1-20260827 | `docs/spec/GLOBAL_SOURCE_RUNTIME_P1.md` | APPROVED | yes | Current operator instruction traced to preserved always-on objective. |
| SRC-BRAIN-ALWAYS-ON-20260827 | `docs/spec/ALWAYS_ON_PERSONAL_INTELLIGENCE_RUNTIME.md` | SOURCE | yes | Full Brain objective remains the parent scope and is not narrowed by P1. |

## GO/HOLD Status

- [ ] GO
- [x] HOLD
- [ ] REVIEW
- [ ] BLOCKED

Reason:

```text
Implementation is committed to the feature branch. Merge readiness remains HOLD until exact-head GitHub Actions prove migration 024 replay/RLS behavior, the full Python suite, lint, Observatory compatibility and production-container gates. Production migration/Railway actions are outside this PR's authorization.
```

## Changed Files

| Path | Artifact Type | Source ID | Notes |
|---|---|---|---|
| `brain/connectors/protocol.py` | runtime contract | SRC-BRAIN-GLOBAL-SOURCE-P1-20260827 | Adds source-scoped observation receipt contract. |
| `brain/connectors/store.py` | runtime adapter | SRC-BRAIN-GLOBAL-SOURCE-P1-20260827 | Adds Postgres connector registry, leases, raw ledger and secret-safe config. |
| `brain/connectors/service.py` | runtime service | SRC-BRAIN-GLOBAL-SOURCE-P1-20260827 | Provenance-first ingest, durable auto-selection, claims, run accounting and timestamps. |
| `db/migrations/024_durable_connector_runtime.sql` | schema/RLS | SRC-BRAIN-GLOBAL-SOURCE-P1-20260827 | Durable source schedule, ingestion runs, raw observations and tenant isolation. |
| `tests/test_connectors_ingest.py` | tests | SRC-BRAIN-GLOBAL-SOURCE-P1-20260827 | Source-scoped corroboration and provenance regressions. |
| `tests/test_durable_connector_runtime.py` | tests | SRC-BRAIN-GLOBAL-SOURCE-P1-20260827 | Migration, secret boundary and capability-fallback gates. |
| `docs/spec/GLOBAL_SOURCE_RUNTIME_P1.md` | spec/trace | SRC-BRAIN-GLOBAL-SOURCE-P1-20260827 | Full P1 requirements and preserved follow-on scope. |
| `docs/control/GLOBAL_SOURCE_RUNTIME_P1_ACCEPTANCE.md` | evidence | SRC-BRAIN-GLOBAL-SOURCE-P1-20260827 | Acceptance ledger. |

## Module Completion Requirements

- [x] owner object
- [x] schema
- [x] runtime service
- [x] state machine
- [x] fixtures/tests
- [x] acceptance criteria
- [x] audit/provenance events
- [x] GO/HOLD status

## Traceability

- [x] Every P1 implementation artifact traces to the preserved source/spec.
- [x] No broader always-on/world-intelligence requirement was removed or treated as complete.

Missing trace links:

```text
none for SLICE-GLOBAL-SOURCE-P1; later world-model/source-universe work remains explicitly unresolved.
```

## Tests / Validation

Command(s):

```bash
pytest -q tests/test_connectors_ingest.py tests/test_durable_connector_runtime.py
pytest -q
ruff check .
# plus repository-required migration/container/RLS/control workflows
```

Result(s):

```text
Pending exact-head GitHub Actions. No passing result is claimed before CI evidence exists.
```

## External Actions

- [ ] No external actions were taken.
- [x] External actions were taken and are documented below.

```text
Approved target: GitHub repository branch and PR only.
Effect: reversible source/schema/test/documentation commits.
Production database, Railway, credentials, paid sources and billing were not changed.
Rollback: close/revert the PR. Migration 024 is additive and code capability-detects its presence.
```

## Memory Writes

- [x] No memory writes were made.
- [ ] Memory writes were made and are documented below.

## Acceptance Criteria

Satisfied by implementation, pending CI proof:

- [x] connector schedule can persist across restarts
- [x] expiring leases suppress concurrent source fetches
- [x] raw observation is captured before sensory enqueue
- [x] dedupe identity is source-scoped
- [x] observed_at and retrieved_at survive acquisition
- [x] durable config excludes headers/credential metadata
- [x] pre-024 deployment fallback remains functional
- [x] migration 024 contains tenant/RLS policies

Not satisfied yet:

- [ ] exact-head required checks are green
- [ ] production migration 024 applied and runtime verified; separate execution gate
- [ ] broad global source population and historical backfill; later preserved slices

## Unresolved Gaps

```text
Broad authoritative source population, historical/backfill acquisition, normalized MOD-017 promotion, credential-provider abstraction, additional connector classes, temporal world-state/entity/corroboration modeling, prediction calibration, self-curriculum/benchmark promotion, truthful Observatory coverage metrics, current-main Railway deployment and dedicated continuous worker topology remain explicit follow-up work.
```

## Source Preservation Statement

```text
No source objective was deleted or narrowed. P1 is a durable acquisition foundation beneath the preserved always-on personal-intelligence objective, not a replacement definition of the Brain.
```

## Next Required Action

```text
Run exact-head CI. Repair real failures on this branch. Synchronize with protected main if required, mark GO only after all required checks succeed, then merge with expected-head protection. Production migration/Railway execution remains a separate authorized step.
```
