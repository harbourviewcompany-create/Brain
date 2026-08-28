# PR #183 — Revenue Persistence Repair Evidence

## Source authority

- SOURCE: protected repository migrations 006/017/020/022/023, existing revenue-domain/runtime behavior, and the canonical tenant-aware API entrypoint.
- APPROVED: PR #183 revenue persistence repair and its source-requirement traceability record.
- Dependency: PR #180 owns prerequisite migration 024; PR #183 owns migration 025 and remains stacked on #180 until #180 lands.

## Scope

Repair migration-025 replay safety and canonical tenant-aware revenue persistence on `fix/revenue-signal-schema` without merging, deploying, applying production migrations, changing production configuration, or enabling revenue extraction.

## Enforced runtime properties

1. `revenue_signals.source_id`, `revenue_signals.money_lane_id`, and `scored_revenue_opportunities.money_lane_id` use stable text keys after migration 025.
2. Migration 025 checks the pre-conversion PostgreSQL column type and performs legacy UUID-ID → stable-key translation only while the corresponding column is actually `uuid`.
3. Replaying migration 025 after those columns are text performs no legacy-key translation, so legitimate UUID-shaped stable text keys cannot be reinterpreted as legacy foreign-key IDs and silently rewritten.
4. Existing non-null migration-006 rows are translated to `sources.key` / `money_lanes.lane_key`; valid legacy nulls remain null and all three key columns remain nullable.
5. Migration 025 remains compatible with migrations 020-022 FORCE-RLS state. It temporarily removes FORCE only when UUID conversion is required, leaves RLS enabled, and restores FORCE before completion.
6. `PostgresRevenueStore` capability-checks the three scoring-audit column types and safely no-ops signal/score/offer audit writes on a pre-025 UUID schema.
7. Migration-017 execution-ledger tables (`revenue_execution_actions`, `revenue_followups`, `revenue_outcome_ledger`) gain tenant ownership in 025 because they predate the migration-020/022 tenant stamping/grant pass. Migration 025 adds `tenant_id`, tenant-context defaults, RLS/FORCE policies, and `brain_runtime_role` DML while preserving valid legacy/system null-tenant rows.
8. Migration 025 remains executable by an ordinary `NOSUPERUSER NOBYPASSRLS` table-owner migrator. The CI fixture grants only the required `REFERENCES` privilege on `public.tenants`; no public-schema `CREATE` privilege is added.
9. Canonical `apps.api.tenant_app` builds a tenant-scoped revenue store from the existing `TenantScopedConnectionPool`, then constructs both `MoneySpineService(store=...)` and `RevenueExecutionSpine(money=..., store=...)` and exposes both through the tenant service registry/proxy boundary.
10. The tenant adapter intentionally keeps system-global money-lane templates and pre-tenant source-score learning out of tenant database credentials. Tenant API requests use the canonical in-code lane templates while operational signal/score/offer/approval persistence is durable and tenant-owned.
11. Revenue actions remain approval-required; this repair does not enable autonomous send/spend/external execution.

## Production-shaped PostgreSQL verification

`.github/workflows/revenue-persistence-migration.yml` creates isolated PostgreSQL 16 and proves:

1. production-compatible baseline replay through migration 018;
2. `PRE025_GO`: real scoring succeeds and incompatible scoring-audit writes safely no-op on the legacy UUID schema;
3. legacy UUID-backed rows plus valid nullable rows are seeded before tenant migrations;
4. migrations 019-023 apply through the repository tenant/RLS release boundary;
5. migration 025 applies as an ordinary `NOSUPERUSER NOBYPASSRLS` table owner under FORCE-RLS conditions;
6. `MIGRATION025_LEGACY_GO`: UUID keys translate once, nulls remain null, all three converted columns remain nullable, scoring FORCE RLS is restored, and execution-ledger tenant RLS/grants are present;
7. `POST025_GO`: real signal → score → offer persistence succeeds with stable text keys;
8. post-025 rows are seeded with legitimate UUID-shaped stable text source/lane keys that deliberately equal existing legacy UUID IDs;
9. migration 025 is replayed and `MIGRATION025_UUID_TEXT_REPLAY_GO` proves those legitimate text keys remain unchanged and legacy FKs remain absent;
10. `TENANT_REVENUE_HTTP_GO`: the canonical `apps.api.tenant_app` is exercised through signed tenant HTTP requests using the constrained API runtime login; tenant A persists signal/score/offer/approval-required action rows with tenant ownership, and tenant B cannot read the action through either detail or snapshot routes.

Executable verification helpers:

- `tools/verify_revenue_persistence_migration.py`
- `tools/verify_tenant_revenue_http.py`

## Exact-head implementation evidence

Implementation head `3a47b8b545b6ed8ec0789df3ff6fbd93f3d402c6` over finalized PR #180 base `b5bcfd600ce4ea29fa05cee5ccbd147a248ccc59`:

- Brain Control Policy run `33138999815`: SUCCESS.
- Revenue Persistence Migration run `33138999737`: SUCCESS.
  - `PRE025_GO`
  - `MIGRATION025_LEGACY_GO`
  - `POST025_GO`
  - `MIGRATION025_UUID_TEXT_REPLAY_GO`
  - `TENANT_REVENUE_HTTP_GO`
- Verify PR126 Observatory Compatibility run `33138999731`: SUCCESS.
- Standard `test` run `33138999741`: SUCCESS.
  - verified merge ref `5c5f5d32ae8e79616f6d1a1b2f9b21cf74ff2081`;
  - Brain agent-control validation: GO;
  - MOD-008 through MOD-015: 117/117 PASS;
  - Python: 802 passed, 1 deprecation warning;
  - Ruff: PASS;
  - Observatory structural verification: PASS;
  - operator session verification: PASS;
  - Next.js 15.5.24 production build: PASS, 27 static pages;
  - Tenant RLS release gate: SUCCESS;
  - production-container persistence: SUCCESS.

This evidence document is the final control synchronization commit after the implementation-head proof above. The final documentation head must rerun the same exact-head workflows before the two remaining review threads are resolved or STACKED CODE is returned to GO.

## Tenant / RLS boundary

Migration 020 already adds tenant ownership to `revenue_signals`, `scored_revenue_opportunities`, and `packaged_offers`; migration 022 grants `brain_runtime_role` DML to tenant-owned tables existing at that point. Migration 017's execution-ledger tables predate those controls, so migration 025 now explicitly adds their tenant boundary and runtime DML before canonical tenant HTTP persistence is enabled.

System-global lane templates and pre-tenant source-score learning are not converted into tenant-mutable shared state by this repair. `TenantRevenueStore` excludes those global mutation surfaces while preserving durable tenant operational persistence.

## Ordering and production boundary

PR #180 is the prerequisite migration-024 change. PR #183 remains verified against `feat/global-source-runtime-p1` while both PRs are open. After #180 lands under separate operator authorization, #183 must be retargeted to then-current `main`, confirm migration 024 is present, reconcile any upstream changes, and rerun exact-head CI before any #183 merge decision.

Production migration/deployment remains HOLD. This repair does not authorize raising the live migration ceiling, applying migration 025 to production, changing Railway/Fly/Vercel configuration, restarting services, merging the PR, or enabling revenue extraction.
