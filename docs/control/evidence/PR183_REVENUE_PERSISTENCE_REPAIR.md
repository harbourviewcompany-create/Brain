# PR #183 — Revenue Persistence Repair Evidence

## Scope

Repair the migration-025 and pre-migration-ceiling persistence defects on `fix/revenue-signal-schema` without merging, deploying, applying production migrations, or changing production configuration. PR #183 is ordered after PR #180, whose durable connector runtime owns migration 024.

## Enforced runtime properties

1. `revenue_signals.source_id` uses the domain connector/source key as text.
2. `revenue_signals.money_lane_id` uses `MoneyLane.lane_id` / `money_lanes.lane_key` as text.
3. `scored_revenue_opportunities.money_lane_id` uses the same text lane key; its legacy UUID FK is removed by migration 025.
4. Existing non-null rows created under migration 006 are semantically preserved during 025: UUID strings are translated to `sources.key` and `money_lanes.lane_key` before normal operation resumes.
5. Legacy null `source_id` / `money_lane_id` values remain null. Migration 006 made those columns nullable, so migration 025 preserves that contract rather than inventing a backfill or failing on valid legacy rows.
6. Migration 025 remains compatible with migrations 020-022 FORCE-RLS state. It transactionally removes FORCE only for the schema-owner translation step, leaves RLS enabled, and restores FORCE before commit.
7. `PostgresRevenueStore` does not assume an above-ceiling schema means a missing table. It inspects the three required column types in `information_schema` and no-ops signal/score/offer audit writes until all three are migration-025-compatible text columns.
8. Existing lane/action/outcome persistence remains available below migration 025; only the scoring-audit writes are gated.

## Production-shaped PostgreSQL verification

`.github/workflows/revenue-persistence-migration.yml` creates an isolated pgvector/PostgreSQL 16 database and:

1. replays the repository baseline through migration 018;
2. executes the real `PostgresRevenueStore` + `MoneySpineService` signal/score/offer path and proves it succeeds while writing zero scoring-audit rows on the legacy UUID schema;
3. seeds both UUID-backed legacy audit rows and valid legacy rows with null source/lane keys;
4. applies tenant/RLS migrations 019-023 through the repository's gated migration runner;
5. transfers the affected table ownership to an ordinary `NOSUPERUSER NOBYPASSRLS` migration fixture and applies migration 025 under FORCE-RLS conditions;
6. proves the UUID-backed rows translate to stable text keys, null values remain null, all three key columns remain nullable, and FORCE RLS is restored on the affected tenant-owned tables and `sources`;
7. executes the real signal → score → offer path after 025 and proves the audit rows persist with stable text keys;
8. replays migration 025 and verifies the text-key schema and dropped legacy FKs remain stable.

The executable verifier is `tools/verify_revenue_persistence_migration.py`.

## Prior replay finding and correction

The strengthened replay already passed the pre-025 capability gate, tenant/RLS migrations, ordinary-owner FORCE-RLS application of migration 025, UUID-to-stable-key translation, legacy-null preservation and FORCE restoration. It then failed while constructing `MoneySpineService` because the verification fixture had seeded `money_lanes.opportunity_class='lead'`, which is not a valid domain `OpportunityClass`. The fixture is corrected to `high_intent_lead`; no migration or runtime logic change was required for that failure.

This documentation commit intentionally follows the PR-body control-schema correction so the next pull-request synchronization event validates the current metadata rather than the stale pre-correction body.

## Tenant / RLS boundary

The prior evidence incorrectly claimed that the scoring-audit tables lacked tenant ownership and runtime grants. Migration 020 adds `tenant_id` to `revenue_signals`, `scored_revenue_opportunities`, and `packaged_offers`; migration 022 grants `brain_runtime_role` DML dynamically to tenant-owned tables carrying `tenant_id`. That schema/grant boundary is therefore already present.

Migration 025 remains above the tenant-release boundary and must still be applied only through the repository's explicit tenant/RLS release controls. This PR does not authorize a production migration, raise a live migration ceiling, alter production credentials/topology, deploy, or restart services.

## Ordering

PR #180 is the prerequisite migration-024 change. PR #183 must be verified against `feat/global-source-runtime-p1` while both are open. After PR #180 eventually lands under separate operator authorization, PR #183 should be retargeted to updated `main` and exact-head CI rerun before any merge decision.
