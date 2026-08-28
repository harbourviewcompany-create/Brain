# PR #183 — Revenue Persistence Repair Evidence

## Source authority

- SOURCE: protected repository migrations 006/017/020/022/023, merged PR #180 migration 024, the existing migration-025 contract, revenue-domain/runtime behavior, and the canonical tenant-aware API entrypoint.
- APPROVED: PR #183 revenue persistence repair, the source-requirement traceability record, and the three review findings repaired in this pass: stale resolved persistence wording, non-atomic signal/score persistence, and warm-replica execution-state staleness.
- Migration ownership remains fixed: PR #180 owns migration 024; PR #183 owns migration 025. This repair adds no migration.
- Current integration base during the verified implementation run is protected `main` at `80cbda7d88ffed1be73edf490e4f3f4fcff3fc9e`, which descends from merged PR #180 squash commit `ae77e18123a7b2275cad79c5e6874ed499762333`.

## Scope

Repair PR #183 so that:

1. resolved revenue-persistence work is removed from active `unresolved_gaps` while real remaining boundaries stay explicit;
2. `RevenueSignal` and `ScoredOpportunity` audit rows persist atomically so failure of the score insert cannot leave an orphan signal; and
3. action detail/approval/follow-up/outcome operations are durable-read-through or refresh-safe across already-warm API replicas under the existing tenant/RLS architecture.

The repair does not merge PR #183, deploy, apply production migrations, alter production configuration or data, restart production services, or enable revenue extraction.

## Enforced runtime properties

1. `revenue_signals.source_id`, `revenue_signals.money_lane_id`, and `scored_revenue_opportunities.money_lane_id` use stable text keys after migration 025.
2. Migration 025 performs legacy UUID-ID → stable-key translation only while the corresponding column is actually `uuid`; replay after conversion does not reinterpret legitimate UUID-shaped text keys.
3. Existing valid nullable legacy keys remain nullable; migration 025 preserves pre-existing valid rows and restores FORCE RLS after any required schema-owner conversion step.
4. `PostgresRevenueStore` safely degrades scoring-audit persistence on the pre-025 UUID layout and rechecks negative capability results so persistence can activate after migration 025 without process restart.
5. Migration-017 execution-ledger tables gain tenant ownership/RLS/runtime DML in migration 025 because they predate the migration-020/022 tenant stamping/grant pass.
6. The canonical tenant adapter capability-gates execution-ledger persistence below migration 025, keeping constrained non-owner runtimes healthy without broadening pre-025 privileges.
7. Canonical `apps.api.tenant_app` constructs both `MoneySpineService` and `RevenueExecutionSpine` with a tenant-scoped `PostgresRevenueStore` over the existing `TenantScopedConnectionPool`.
8. Tenant lane/source learning remains reconstructable from tenant-owned `revenue_outcome_ledger` rows after bundle eviction; global `money_lanes` and pre-tenant `revenue_source_scores` are not exposed as tenant-mutable shared storage.
9. `PostgresRevenueStore.save_signal_and_score()` inserts the signal and its scored opportunity on one PostgreSQL connection/transaction and rolls the transaction back if either write fails.
10. `MoneySpineService.score_signal()` prefers the atomic pairwise store operation when the store exposes it, retaining compatibility with simpler stores through the existing separate-write fallback.
11. `PostgresRevenueStore.get_action()` provides tenant/RLS-scoped durable point reads for revenue actions.
12. `RevenueExecutionSpine.get_action()` reads through to durable storage when execution persistence is available and updates its local cache rather than treating constructor hydration as authoritative.
13. Approval, manual-action logging, follow-up scheduling, and outcome recording all resolve the action through the durable read-through path before state transition.
14. Snapshot/due-follow-up reads refresh durable execution state, allowing already-warm replicas to observe actions/follow-ups/outcomes created by another replica.
15. Tenant pre-025 capability gating still applies to durable point reads, so the replica fix does not regress below-025 runtime compatibility.
16. Revenue actions remain approval-required; no send/spend/external revenue execution is enabled.

## Source-requirement registry correction

`docs/control/source-requirement-registry.json` no longer lists resolved migration-025 persistence work inside `unresolved_gaps` and no longer carries the obsolete blanket statement that the migration-017 execution tables remain unreachable under the tenant topology.

The remaining lane/source boundary is intentionally narrower and current: `money_lanes` and `revenue_source_scores` remain global/non-tenant storage, tenant runtimes do not mutate them, and tenant lane/source learning is reconstructed from tenant-owned `revenue_outcome_ledger` rows after migration 025. Existing real gaps concerning enrichment before queueing and approval-gated live external action remain preserved.

## Production-shaped PostgreSQL verification

The existing `Revenue Persistence Migration` workflow runs against isolated disposable PostgreSQL 16 and now proves the complete PR #183 persistence contract, including the three current repair findings:

1. production-compatible baseline replay through migration 018;
2. pre-025 scoring safely degrades on the legacy UUID audit schema;
3. migrations 019-023 and prerequisite migration 024 apply through the existing tenant/RLS release boundary;
4. migration 025 applies through the ordinary `NOSUPERUSER NOBYPASSRLS` migration-owner path;
5. `TENANT_REVENUE_PRE025_GO`: constrained signed-tenant runtime remains healthy before 025;
6. `SIGNAL_AUDIT_LIVE_UPGRADE_GO`: a long-lived store that observed pre-025 capability begins persistence after 025 without restart;
7. `TENANT_REVENUE_EVICTION_LEARNING_GO`: tenant learning reconstructs after forced bundle eviction;
8. `MIGRATION025_LEGACY_GO`: legacy UUID/null/FORCE-RLS and tenant-execution controls remain correct;
9. `POST025_GO`: stable-key signal → score → offer persistence succeeds;
10. `MIGRATION025_UUID_TEXT_REPLAY_GO`: legitimate UUID-shaped stable text keys survive migration replay unchanged;
11. `TENANT_REVENUE_HTTP_GO`: canonical signed-tenant HTTP persistence and cross-tenant isolation remain green;
12. `REVENUE_SIGNAL_SCORE_ATOMIC_ROLLBACK_GO`: a PostgreSQL trigger deliberately fails the scored-opportunity insert and the verifier proves that both the signal and score rows remain absent, demonstrating transactional rollback rather than an orphan audit row; and
13. `TENANT_REVENUE_TWO_REPLICA_GO`: two already-warm tenant execution spines share the canonical tenant/RLS database; replica A queues an action, replica B immediately reads it durably, approves it, schedules a follow-up, records a paid outcome, replica A subsequently observes the updated durable action state, and a different tenant remains unable to read the action.

Executable verification helpers include:

- `tools/verify_revenue_persistence_migration.py`
- `tools/verify_tenant_revenue_http.py`
- `tools/verify_tenant_revenue_live_upgrade.py`
- `tools/verify_revenue_atomic_replica.py`

A focused unit contract in `tests/test_revenue_atomic_contract.py` also proves that `MoneySpineService` selects the atomic signal+score store API when available.

## Exact implementation-head evidence

Implementation head: `19e2b7b19db64306e64cfac25ad86d9d32d546b6`.

Current protected main used by the synthesized integration checkout: `80cbda7d88ffed1be73edf490e4f3f4fcff3fc9e`.

Verified pull-request merge ref: `834bc9446e3c19908b26cbb5ca7e3f2e3c7a576e` (`Merge 19e2b7b19db64306e64cfac25ad86d9d32d546b6 into 80cbda7d88ffed1be73edf490e4f3f4fcff3fc9e`).

Exact implementation-head workflows:

- Brain Control Policy run `33173690105` (#809): **SUCCESS**.
- Revenue Persistence Migration run `33173690066` (#83): **SUCCESS**.
  - `TENANT_REVENUE_PRE025_GO`: PASS.
  - `SIGNAL_AUDIT_LIVE_UPGRADE_GO`: PASS.
  - `TENANT_REVENUE_EVICTION_LEARNING_GO`: PASS.
  - `MIGRATION025_LEGACY_GO`: PASS.
  - `POST025_GO`: PASS.
  - `MIGRATION025_UUID_TEXT_REPLAY_GO`: PASS.
  - `TENANT_REVENUE_HTTP_GO`: PASS.
  - `REVENUE_SIGNAL_SCORE_ATOMIC_ROLLBACK_GO`: PASS; injected scored-opportunity failure rolled back both audit rows.
  - `TENANT_REVENUE_TWO_REPLICA_GO`: PASS; warm replica B read/approved/followed-up/recorded an outcome for replica A's durable action while the second tenant remained isolated.
- Verify PR126 Observatory Compatibility run `33173690085` (#244): **SUCCESS**, including exact-head proof, focused compatibility tests, tenant migrations/RLS, and explicit legacy strategy verification.
- Standard `test` run `33173690125` (#2328): **SUCCESS**.
  - synthesized checkout: `834bc9446e3c19908b26cbb5ca7e3f2e3c7a576e`;
  - Brain agent-control validation: **GO**;
  - MOD-008 through MOD-015: **117/117 PASS**, 0 partial, 0 fail;
  - Python: **817 passed**, 1 deprecation warning;
  - Ruff selected checks: **PASS**;
  - Brain Observatory structural verification: **PASS**;
  - operator-session verification: **PASS**;
  - Next.js 15.5.24 production build: **PASS**, 27/27 static pages;
  - Tenant RLS release gate: **SUCCESS**;
  - Production container persistence: **SUCCESS**, including authenticated durable-belief round trip and readiness failure when the database disappears.

## Review-warning assessment

A later static-analysis pass raised raw-SQL warnings in the disposable verification helpers. The flagged SQL does not accept untrusted identifiers:

- `tools/verify_revenue_atomic_replica.py` interpolates only the module-level hard-coded `FAULT_SCORE` UUID into the CI-only trigger definition used for fault injection;
- `tools/verify_tenant_revenue_http.py` interpolates a table identifier only after membership in a closed four-table allow-list, while the row ID remains a bound `%s` UUID parameter; and
- `tools/verify_tenant_revenue_live_upgrade.py` uses the same closed allow-list pattern for its three permitted audit tables with a bound row-ID parameter.

These are evidence-backed static-analysis false positives, not unbounded query construction or externally supplied SQL identifiers. They may be resolved only after the final evidence-only head remains green.

## Tenant / RLS boundary

Migration 020 already tenant-owns `revenue_signals`, `scored_revenue_opportunities`, and `packaged_offers`; migration 022 grants `brain_runtime_role` DML to tenant-owned tables existing at that point. Migration-017 execution-ledger tables predate those controls, so migration 025 explicitly adds their tenant boundary and runtime DML.

Replica read-through continues to use the existing tenant-scoped connection pool and RLS context. It does not create a cross-tenant cache, bypass RLS, add a shared execution service, or broaden runtime privileges. The two-replica regression verifies both same-tenant visibility and different-tenant invisibility against the disposable PostgreSQL/RLS topology.

## Ordering and production boundary

PR #180 remains the owner of `024_durable_connector_runtime.sql`; PR #183 remains the owner of `025_revenue_signal_source_lane_text_keys.sql`. This repair introduces no migration and does not modify migration ownership.

Production migration/deployment remains **HOLD**. No live migration ceiling was raised, migration 025 was not applied to production, no production data or configuration was changed, no service was restarted or deployed, PR #183 was not merged, and revenue extraction was not enabled.

## Final synchronization gate

This evidence update is documentation-only and therefore changes the PR head after the fully green implementation proof above. Before PR #183 can return overall CODE/MERGE GO or any remaining review thread can be resolved, the same four workflow families must succeed again on the exact resulting final head and synthesized merge ref against then-current protected `main`:

- Brain Control Policy;
- Revenue Persistence Migration;
- standard `test`, including Tenant RLS release and Production container persistence; and
- Verify PR126 Observatory Compatibility.

If protected `main` moves again before those runs execute, the final merge-ref evidence must reflect the newer integration base rather than reusing the implementation-head merge ref.
