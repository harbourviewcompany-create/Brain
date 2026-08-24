# MOD-017 Persistent Source Registry and Signal Intake Runtime

## Status

APPROVED control-layer/runtime primitive. BUILD-READY remains HOLD for production deployment until database adapters, operator UI, live connector approvals and jurisdiction-specific legal/access controls are implemented.

## Objective

MOD-017 turns the MOD-016 source intelligence registry from static validated source records into a deterministic runtime boundary for persistence, ingestion runs, source observations, signal inbox routing, source health checks and replay snapshots.

The goal is not to activate scraping or live data collection. The goal is to make source movement durable, evidence-backed, reviewable and replayable before any external connector is allowed.

## Chain

Source record -> ingestion run -> source observation -> evidence-backed signal inbox item -> analyst review -> opportunity-board candidate -> outcome learning.

## Implemented runtime objects

- `IngestionRun`
- `SourceObservation`
- `SignalInboxItem`
- `SourceHealthCheck`
- `SourceRegistryEvent`
- `SourceRegistrySnapshot`
- `PersistentSourceRegistryRuntime`

## Implemented runtime services

- source registration
- lifecycle update with HOLD enforcement
- ingestion-run creation
- observation recording
- duplicate observation suppression by `(source_id, extract_hash_or_snapshot_id)`
- signal inbox routing
- signal review status update
- source health check recording
- dashboard counts
- source event timeline
- replay snapshot export and load

## Database target

The durable SQL target is defined in:

`db/migrations/008_source_registry_runtime.sql`

Tables:

- `source_registry_sources`
- `source_registry_ingestion_runs`
- `source_registry_observations`
- `source_registry_signal_inbox`
- `source_registry_health_checks`
- `source_registry_events`

## GO rules

A source may enter controlled ingestion only when:

1. the source is registered
2. legal/access status is not prohibited, PII-sensitive, terms-review, paid-licensed without controls or low-value reject
3. the requested access method is registered on the source
4. manual-only sources use manual review only
5. every observation preserves source URL/path, retrieval timestamp, observation timestamp, snapshot/hash, legal status and evidence refs
6. duplicate observations are suppressed idempotently
7. signal inbox routing preserves evidence refs and confidence
8. snapshot replay preserves state and dedupe indexes

## HOLD rules

The runtime holds or rejects:

- prohibited sources
- PII-sensitive sources
- terms-review-required sources
- paid-licensed sources without license metadata and cost controls
- automated ingestion for manual-only sources
- unknown source IDs
- unknown ingestion run IDs
- observations without evidence refs
- observations without snapshot/hash provenance
- source activation when legal/access disposition is HOLD

## Explicit non-goals

This PR does not implement:

- live web scraping
- API connector execution
- browser automation
- paid-license connector use
- external outreach
- marketplace action
- CRM writeback
- production UI dashboards
- Supabase migration execution
- real source population
- jurisdiction-specific legal/access registry

## Tests

Implemented in:

`tests/test_source_registry_runtime.py`

Covered behavior:

- ingestion run -> observation -> signal routing
- duplicate observation suppression
- paid-license and manual-only automation blocking
- health check lifecycle effects
- replay snapshot preservation

## Fixture

Fixture evidence:

`tests/fixtures/brain/source_registry_runtime.json`

## Acceptance criteria

- Runtime records observations with mandatory provenance.
- Signal inbox items cannot exist without evidence refs.
- Duplicate source snapshots are idempotent.
- Manual-only and paid-licensed sources cannot route to automation.
- Health checks update lifecycle state for broken/degraded sources.
- Runtime snapshots can replay state and preserve dedupe behavior.
- No live connector or external action is activated.

## Deferred but preserved

- Postgres adapter implementation
- Supabase RLS policies
- operator source health dashboard
- evidence viewer UI
- opportunity board integration
- source ROI attribution
- automated source discovery proposal service
- jurisdiction-specific access/legal registry
- live connector approval workflow
