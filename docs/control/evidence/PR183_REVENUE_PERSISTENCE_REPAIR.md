# PR #183 — Revenue Persistence Repair Evidence

## Scope

Repair the migration-024 and pre-migration-ceiling persistence defects on `fix/revenue-signal-schema` without merging, deploying, applying production migrations, or changing production configuration.

## Enforced runtime properties

1. `revenue_signals.source_id` uses the domain connector/source key as text.
2. `revenue_signals.money_lane_id` uses `MoneyLane.lane_id` / `money_lanes.lane_key` as text.
3. `scored_revenue_opportunities.money_lane_id` now uses the same text lane key; its legacy UUID FK is removed by migration 024.
4. Existing rows created under migration 006 are semantically preserved during 024: UUID strings are translated to `sources.key` and `money_lanes.lane_key` before normal operation resumes.
5. `PostgresRevenueStore` no longer assumes an above-ceiling schema means a missing table. It inspects the three required column types in `information_schema` and no-ops signal/score/offer audit writes until all three are migration-024-compatible text columns.
6. The existing lane/action/outcome persistence remains available below migration 024; only the new scoring audit writes are gated.

## Production-shaped PostgreSQL verification

`.github/workflows/revenue-persistence-migration.yml` creates an isolated pgvector/PostgreSQL 16 database and:

1. replays the repository baseline through migration 018;
2. executes the real `PostgresRevenueStore` + `MoneySpineService` signal/score/offer path and proves it succeeds while writing zero scoring-audit rows on the legacy UUID schema;
3. applies migration 024;
4. executes the same real path and proves one `revenue_signals`, one `scored_revenue_opportunities`, and one `packaged_offers` row persist with the expected stable text keys;
5. replays migration 024 a second time and verifies all three key columns remain `text` and all three legacy FKs remain absent.

The executable verifier is `tools/verify_revenue_persistence_migration.py`.

## Deployment boundary

The pre-existing tenant/RLS/grant limitation remains unresolved: the three scoring-audit tables do not carry `tenant_id` and are not included in migration 022's constrained-runtime grant loop. This repair does not relax that hold, raise any production migration ceiling, or apply migration 024 to a live database.
