# Global Source Runtime P1 — Acceptance Ledger

Status: CODE/INTEGRATION GO from completed exact-head CI; PR #180 is merged; production migration/deployment remains HOLD.

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
- [x] PR #183 is ordered after this slice as migration 025 and is verified separately
- [x] implementation head immediately before documentation reconciliation passed the full repository suite, lint, production-container persistence, tenant-RLS gate, Brain control policy and Observatory compatibility
- [x] pull-request acceptance metadata uses the repository's mandatory control headings
- [x] final exact-head synchronization run green after the documentation-only synchronization commit

## Migration ordering

PR #180 owns `024_durable_connector_runtime.sql` and was merged to `main` as squash commit `ae77e18123a7b2275cad79c5e6874ed499762333`. PR #183 owns `025_revenue_signal_source_lane_text_keys.sql` and has been retargeted to `main`. PR #183 must independently satisfy its post-#180 exact-head workflows, migration ordering, mergeability, and review-thread requirements before any merge decision.

## Verification note

PR #180 exact head `b5bcfd600ce4ea29fa05cee5ccbd147a248ccc59` completed the required pull-request verification before merge:

- Brain Control Policy run `33132315400`: SUCCESS.
- Verify PR126 Observatory Compatibility run `33132315401`: SUCCESS.
- Standard `test` run `33132315391`: SUCCESS, including the tenant-RLS release gate and production-container persistence jobs.

The standard test run also proved 797 Python tests passing, Ruff PASS, Brain agent-control GO, MOD-008–015 117/117 PASS, Observatory structural/session verification PASS, and the Next.js production build PASS. The earlier HOLD language in this ledger was stale control metadata after those exact-head checks completed; it did not represent a remaining implementation defect.

PR #180 was subsequently merged before this follow-up documentation correction was created. This correction changes only the acceptance ledger so repository control evidence matches the already-completed verification and merge state.

## External actions

This follow-up performs GitHub documentation/PR/CI actions only. PR #180 had already been merged before this correction began. No runtime code, migration, production database, Railway configuration, paid provider, credential, service, deployment, restart, revenue-extraction activation, or production-write action is part of this correction.

## Memory writes

None.

## Source preservation

The P1 specification points to the preserved full always-on objective in `docs/spec/ALWAYS_ON_PERSONAL_INTELLIGENCE_RUNTIME.md`. This slice does not replace or narrow that objective.

## Unresolved gaps

See `docs/spec/GLOBAL_SOURCE_RUNTIME_P1.md`. Broad source population, historical backfill, normalization into MOD-017, provider credential abstraction, temporal world modeling, prediction calibration, self-improvement and Observatory coverage remain explicit follow-up surfaces.

## GO/HOLD

**CODE / INTEGRATION: GO; PR #180: ALREADY MERGED.** The required #180 exact-head Control Policy, Observatory compatibility, repository tests/lint/build, tenant-RLS release gate, and production-container persistence were green before merge. This follow-up only reconciles stale control evidence.

**PRODUCTION MIGRATION / DEPLOYMENT: HOLD.** Production execution remains separately gated and was not authorized here.
