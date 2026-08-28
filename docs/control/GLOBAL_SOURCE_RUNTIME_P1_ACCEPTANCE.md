# Global Source Runtime P1 — Acceptance Ledger

Status: GO for merge/code on the verified branch; HOLD for production migration/deployment.

Build slice: `SLICE-GLOBAL-SOURCE-P1`

Source authority: `SRC-BRAIN-GLOBAL-SOURCE-P1-20260827` in `docs/spec/GLOBAL_SOURCE_RUNTIME_P1.md`.

## Implemented artifacts

- `db/migrations/024_durable_connector_runtime.sql`
- `brain/connectors/protocol.py`
- `brain/connectors/store.py`
- `brain/connectors/service.py`
- `tests/test_connectors_ingest.py`
- `tests/test_durable_connector_runtime.py`
- `docs/spec/GLOBAL_SOURCE_RUNTIME_P1.md`

## Acceptance criteria

- [x] restart-safe connector schedule schema
- [x] expiring source leases for concurrent-worker suppression
- [x] durable raw observation ledger before sensory enqueue
- [x] source-scoped dedupe preserves independent corroboration
- [x] observed and retrieved timestamps preserved
- [x] credential/header exclusion from durable public config
- [x] capability fallback for pre-024 deployments
- [x] tenant/RLS policies included in migration 024
- [x] migration 024 is the unique, contiguous next slot on this branch
- [x] PR #183 is ordered after this slice as migration 025 and is verified separately as a stacked PR
- [x] exact-head full repository tests green on the implementation head before this documentation-only correction
- [x] exact-head lint green on the implementation head before this documentation-only correction
- [x] exact-head production-container persistence green on the implementation head before this documentation-only correction
- [x] exact-head tenant-RLS release gate green on the implementation head before this documentation-only correction
- [x] exact-head Brain control-policy check green on the implementation head before this documentation-only correction

The documentation-only correction that removes the prior contradictory #183/024 statement must receive its own exact-head CI before the PR body is relabeled to the new head.

## Migration ordering

PR #180 owns `024_durable_connector_runtime.sql`. PR #183 owns `025_revenue_signal_source_lane_text_keys.sql` and currently targets this branch while both PRs remain open. After #180 eventually lands under separate operator authorization, #183 must be retargeted to updated `main` and rerun before any merge decision.

## External actions

Repository branch writes only. No production database mutation, Railway configuration change, paid provider activation, credential change, service provisioning, merge, or public release action is part of this build slice.

## Memory writes

None.

## Source preservation

The P1 specification points to the preserved full always-on objective in `docs/spec/ALWAYS_ON_PERSONAL_INTELLIGENCE_RUNTIME.md`. This slice does not replace or narrow that objective.

## Unresolved gaps

See `docs/spec/GLOBAL_SOURCE_RUNTIME_P1.md`. Broad source population, historical backfill, normalization into MOD-017, provider credential abstraction, temporal world modeling, prediction calibration, self-improvement and Observatory coverage remain explicit follow-up surfaces.

## GO/HOLD

**MERGE/CODE: GO pending exact-head rerun for this documentation-only correction.** The implementation head immediately before this edit was fully green; the new head must revalidate before final GO is recorded.

**PRODUCTION MIGRATION / DEPLOYMENT: HOLD.** Production execution remains separately gated and was not authorized here.
