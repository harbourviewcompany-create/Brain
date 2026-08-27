# Global Source Runtime P1 — Acceptance Ledger

Status: HOLD pending exact-head CI.

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
- [ ] exact-head full repository tests green
- [ ] exact-head lint green
- [ ] exact-head production-container persistence green
- [ ] exact-head tenant-RLS release gate green
- [ ] exact-head Brain control-policy check green

## External actions

Repository branch writes only. No production database mutation, Railway configuration change, paid provider activation, credential change, service provisioning, or public release action is part of this build slice.

## Memory writes

None.

## Source preservation

The P1 specification points to the preserved full always-on objective in `docs/spec/ALWAYS_ON_PERSONAL_INTELLIGENCE_RUNTIME.md`. This slice does not replace or narrow that objective.

## Unresolved gaps

See `docs/spec/GLOBAL_SOURCE_RUNTIME_P1.md`. Broad source population, historical backfill, normalization into MOD-017, provider credential abstraction, temporal world modeling, prediction calibration, self-improvement and Observatory coverage remain explicit follow-up surfaces.

## Next required action

Run exact-head CI, repair any real regression, synchronize with current protected `main`, then mark GO only if all required checks pass.
