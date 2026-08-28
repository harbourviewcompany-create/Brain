# PR #183 — Revenue Persistence Repair Evidence

## Source authority

- SOURCE: protected repository migrations 006/017/020/022/023, merged PR #180 migration 024, the existing migration-025 contract, revenue-domain/runtime behavior, and the canonical tenant-aware API entrypoint.
- APPROVED: PR #183 revenue persistence repair, the source-requirement traceability record, and the three post-#180 review findings repaired in this pass.
- Dependency state: PR #180 has merged to `main` as `ae77e18123a7b2275cad79c5e6874ed499762333` and owns migration 024. PR #183 is based on that post-#180 main and owns migration 025.

## Scope

Repair migration-025 replay safety, canonical tenant-aware revenue persistence, pre-025 compatibility under the constrained non-owner runtime role, live 024→025 capability activation without restart, and tenant learning reconstruction after service-bundle eviction on `fix/revenue-signal-schema`, without merging, deploying, applying production migrations, changing production configuration, or enabling revenue extraction.

## Enforced runtime properties

1. `revenue_signals.source_id`, `revenue_signals.money_lane_id`, and `scored_revenue_opportunities.money_lane_id` use stable text keys after migration 025.
2. Migration 025 checks the pre-conversion PostgreSQL column type and performs legacy UUID-ID → stable-key translation only while the corresponding column is actually `uuid`.
3. Replaying migration 025 after those columns are text performs no legacy-key translation, so legitimate UUID-shaped stable text keys cannot be reinterpreted as legacy foreign-key IDs and silently rewritten.
4. Existing non-null migration-006 rows are translated to `sources.key` / `money_lanes.lane_key`; valid legacy nulls remain null and all three key columns remain nullable.
5. Migration 025 remains compatible with migrations 020-022 FORCE-RLS state. It temporarily removes FORCE only when UUID conversion is required, leaves RLS enabled, and restores FORCE before completion.
6. `PostgresRevenueStore` capability-checks the three scoring-audit column types and safely no-ops signal/score/offer audit writes on a pre-025 UUID schema.
7. A negative scoring-audit capability result is never cached. Only a positive migration-025-compatible result is cached, so a long-lived process that observed the pre-025 UUID layout begins persistence immediately after 025 is applied without requiring restart.
8. Migration-017 execution-ledger tables (`revenue_execution_actions`, `revenue_followups`, `revenue_outcome_ledger`) gain tenant ownership in 025 because they predate the migration-020/022 tenant stamping/grant pass. Migration 025 adds `tenant_id`, tenant-context defaults, RLS/FORCE policies, and `brain_runtime_role` DML while preserving valid legacy/system null-tenant rows.
9. The canonical tenant revenue adapter capability-gates execution-ledger loading/writes until the migration-025 tenant columns and non-owner runtime privileges are actually present. Before 025, `RevenueExecutionSpine` constructs with empty in-memory execution state rather than raising `InsufficientPrivilege`; after 025, the same long-lived adapter rechecks capability and uses the durable ledger.
10. Migration 025 remains executable by an ordinary `NOSUPERUSER NOBYPASSRLS` table-owner migrator. The CI fixture grants only the required `REFERENCES` privilege on `public.tenants`; no public-schema `CREATE` privilege is added.
11. Canonical `apps.api.tenant_app` builds a tenant-scoped revenue store from the existing `TenantScopedConnectionPool`, then constructs both `MoneySpineService(store=...)` and `RevenueExecutionSpine(money=..., store=...)` and exposes both through the tenant service registry/proxy boundary.
12. Tenant money/source learning is reconstructable after LRU bundle eviction. `record_outcome()` persists the causal tenant-owned `revenue_outcome_ledger` row first; a rebuilt bundle deterministically replays those outcomes using the same reward/reply/cost/risk delta formula as `MoneySpineService.apply_outcome_learning`, restoring lane priority and source reliability state.
13. System-global money-lane templates and the pre-tenant `revenue_source_scores` table remain outside tenant mutation paths. Tenant reconstruction uses in-code lane templates plus tenant-owned outcome rows rather than granting cross-tenant mutable access to global state.
14. Revenue actions remain approval-required; this repair does not enable autonomous send/spend/external execution.

## Production-shaped PostgreSQL verification

`.github/workflows/revenue-persistence-migration.yml` creates isolated PostgreSQL 16 and proves:

1. production-compatible baseline replay through migration 018;
2. pre-025 scoring safely degrades on the legacy UUID audit schema;
3. legacy UUID-backed rows plus valid nullable rows are seeded before tenant migrations;
4. migrations 019-023 apply through the repository tenant/RLS release boundary;
5. prerequisite migration 024 is applied from the post-#180 main tree;
6. the API runtime uses `brain_api_ci` while migration 025 is applied by an ordinary `NOSUPERUSER NOBYPASSRLS` `brain_migrator_ci` table owner;
7. `TENANT_REVENUE_PRE025_GO`: the canonical signed-tenant API remains healthy before 025 under the non-owner runtime role and safely skips unavailable execution/audit persistence;
8. migration 025 is applied inside the same Python verifier process without restarting the tenant API or its store instance;
9. `SIGNAL_AUDIT_LIVE_UPGRADE_GO`: the store that already observed a pre-025 negative capability result rechecks after 025 and begins persisting signal → score → offer audit rows without restart;
10. a tenant action is queued/approved, a paid outcome is persisted, a second tenant forces LRU eviction, and `TENANT_REVENUE_EVICTION_LEARNING_GO` proves the rebuilt tenant restores the same lane priority, source score, action count, and outcome count from tenant-owned durable state;
11. `MIGRATION025_LEGACY_GO`: initial UUID keys translate once, valid nulls remain null, all three converted columns remain nullable, scoring FORCE is restored, and execution-ledger tenant RLS/runtime grants are present;
12. `POST025_GO`: real signal → score → offer persistence succeeds with stable text keys;
13. post-025 rows are seeded with legitimate UUID-shaped stable text source/lane keys that deliberately equal existing legacy UUID IDs;
14. migration 025 is replayed and `MIGRATION025_UUID_TEXT_REPLAY_GO` proves those legitimate text keys remain unchanged and legacy FKs remain absent;
15. `TENANT_REVENUE_HTTP_GO`: canonical signed-tenant HTTP requests persist tenant-owned signal/score/offer/approval-required action rows and tenant B cannot read tenant A's action.

Executable verification helpers:

- `tools/verify_revenue_persistence_migration.py`
- `tools/verify_tenant_revenue_http.py`
- `tools/verify_tenant_revenue_live_upgrade.py`

## Exact-head implementation evidence

Implementation head `4578cbfd2b611be5d5944d62f43feee28e532b16` over post-#180 `main` `ae77e18123a7b2275cad79c5e6874ed499762333`; verified pull-request merge ref `36581ea9aa197767f55b44b529d8ab532d347221`:

- Brain Control Policy run `33168735890`: **SUCCESS**.
- Revenue Persistence Migration run `33168735904`: **SUCCESS**.
  - `TENANT_REVENUE_PRE025_GO`
  - `SIGNAL_AUDIT_LIVE_UPGRADE_GO`
  - `TENANT_REVENUE_EVICTION_LEARNING_GO`
  - `MIGRATION025_LEGACY_GO`
  - `POST025_GO`
  - `MIGRATION025_UUID_TEXT_REPLAY_GO`
  - `TENANT_REVENUE_HTTP_GO`
- Verify PR126 Observatory Compatibility run `33168735922`: **SUCCESS**.
- Standard `test` run `33168736023`: **SUCCESS**.
  - exact checkout: merge ref `36581ea9aa197767f55b44b529d8ab532d347221`;
  - Brain agent-control validation: **GO**;
  - MOD-008 through MOD-015: **117/117 PASS**;
  - Python: **808 passed**, 1 deprecation warning;
  - Ruff: **PASS**;
  - Observatory structural verification: **PASS**;
  - operator session verification: **PASS**;
  - Next.js 15.5.24 production build: **PASS**, 27/27 static pages;
  - Tenant RLS release gate: **SUCCESS**;
  - production-container persistence: **SUCCESS**, including authentication/durable-belief round trip and readiness failure when the database disappears.

This evidence document is the final control-synchronization commit after the fully green implementation proof above. Because it changes the pull-request head, the same four workflow families must rerun successfully against that exact final head before the three remaining review threads are resolved or CODE is returned to GO.

## Tenant / RLS boundary

Migration 020 already adds tenant ownership to `revenue_signals`, `scored_revenue_opportunities`, and `packaged_offers`; migration 022 grants `brain_runtime_role` DML to tenant-owned tables existing at that point. Migration 017's execution-ledger tables predate those controls, so migration 025 explicitly adds their tenant boundary and runtime DML.

The canonical tenant adapter checks that execution-ledger tenant columns and runtime privileges are available before loading or writing them. This makes the tenant API compatible below migration 025 without granting broader pre-025 access and lets the same adapter transition to durable persistence once 025 lands.

Tenant learning reconstruction deliberately uses tenant-owned outcome rows created under migration 025. Global `money_lanes` and the pre-tenant `revenue_source_scores` table are not converted into tenant-mutable shared state by this repair.

## Ordering and production boundary

PR #180 has already merged and owns `024_durable_connector_runtime.sql`. PR #183 is based on that updated `main` and owns `025_revenue_signal_source_lane_text_keys.sql`; no competing migration 024 is contributed by this PR.

Production migration/deployment remains **HOLD**. This repair does not authorize raising the live migration ceiling, applying migration 025 to production, changing Railway/Fly/Vercel production configuration, restarting services, merging the PR, or enabling revenue extraction.
