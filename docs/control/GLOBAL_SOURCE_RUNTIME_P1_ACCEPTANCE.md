# Global Source Runtime P1 — Acceptance Ledger

Status: HOLD pending final exact-head CI synchronization; production migration/deployment remains HOLD.

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
- [x] implementation head immediately before documentation reconciliation passed the full repository suite, lint, production-container persistence, tenant-RLS gate, Brain control policy and Observatory compatibility
- [x] pull-request acceptance metadata now uses the repository's mandatory control headings
- [ ] final exact-head synchronization run green after this documentation-only commit

## Migration ordering

PR #180 owns `024_durable_connector_runtime.sql`. PR #183 owns `025_revenue_signal_source_lane_text_keys.sql` and currently targets this branch while both PRs remain open. After #180 eventually lands under separate operator authorization, #183 must be retargeted to updated `main` and rerun before any merge decision.

## Verification note

The prior exact-head Brain Control Policy failure was metadata-only: module BUILD-READY traceability and migration integrity both passed, while the PR-body validator rejected missing mandatory section headings. The PR body has now been aligned to those exact headings. This commit intentionally synchronizes that corrected metadata with a fresh pull-request head event so the validator does not reuse a stale event payload.

## External actions

Repository branch and PR metadata writes only. No production database mutation, Railway configuration change, paid provider activation, credential change, service provisioning, merge, deployment, restart, or public release action is part of this build slice.

## Memory writes

None.

## Source preservation

The P1 specification points to the preserved full always-on objective in `docs/spec/ALWAYS_ON_PERSONAL_INTELLIGENCE_RUNTIME.md`. This slice does not replace or narrow that objective.

## Unresolved gaps

See `docs/spec/GLOBAL_SOURCE_RUNTIME_P1.md`. Broad source population, historical backfill, normalization into MOD-017, provider credential abstraction, temporal world modeling, prediction calibration, self-improvement and Observatory coverage remain explicit follow-up surfaces.

## GO/HOLD

**MERGE/CODE: HOLD pending the fresh exact-head synchronization run.** No implementation defect is known; the preceding implementation head was fully green and this change is documentation/control synchronization only.

**PRODUCTION MIGRATION / DEPLOYMENT: HOLD.** Production execution remains separately gated and was not authorized here.
