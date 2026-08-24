# PR 3 GO/HOLD Report — Tenant RLS Cognitive Table Baseline

## Scope

PR 3 starts the tenant retrofit of existing Brain runtime data surfaces. It is stacked on PR 2 because it depends on the `tenants`, `tenant_memberships`, `tenant_invites`, and `tenant_audit_events` foundation introduced there.

This PR does not narrow the Brain scope. It adds tenant ownership scaffolding to the existing cognitive/economic tables that PR 1 identified as globally scoped, while preserving explicit deferred surfaces for later specification.

## Files changed

- `db/migrations/013_tenant_scope_cognitive_tables.sql`
- `brain/tenant_context.py`
- `tests/test_tenant_context.py`
- `tests/test_tenant_scope_migration.py`
- `docs/control/PR3_GO_HOLD_REPORT.md`

## Runtime changes

Adds `brain.tenant_context` as an application-layer tenant context helper:

- `TenantContext`
- `TenantScopeViolation`
- `parse_tenant_context_headers`
- same-tenant guard
- role guard
- SQL setting export for `brain.tenant_id`, `brain.actor_id`, and `brain.service_context`

Existing API routes are not fully converted in PR 3. That remains a later route-by-route enforcement task because forcing tenant headers globally would break existing API behavior before cognitive rows are backfilled.

## Database changes

Adds migration `013_tenant_scope_cognitive_tables.sql` with:

- `current_brain_tenant_id()`
- `current_brain_actor_id()`
- `current_brain_service_context()`
- nullable `tenant_id` columns on existing cognitive/economic tenant-owned tables
- tenant indexes
- RLS re-enabled on affected tables
- baseline `tenant_isolation_select`
- baseline `tenant_isolation_insert`
- baseline `tenant_isolation_update`
- baseline `tenant_isolation_delete`

The migration is additive. It does not force `tenant_id not null` because existing rows may be legacy/global rows created before tenant ownership existed.

## Tables receiving tenant ownership scaffold

- `brain_events`
- `sources`
- `observations`
- `evidence`
- `entities`
- `beliefs`
- `belief_evidence`
- `graph_nodes`
- `graph_edges`
- `rewire_events`
- `actions`
- `outcomes`
- `memory_items`
- `bitemporal_facts`
- `neuromodulator_snapshots`
- `homeostatic_snapshots`
- `cognitive_tasks`
- `cognitive_experiments`
- `cognitive_experiment_results`
- `projection_checkpoints`
- `money_lane_sources`
- `money_lane_search_queries`
- `revenue_signals`
- `scored_revenue_opportunities`
- `packaged_offers`
- `revenue_experiments`
- `revenue_experiment_results`
- `daily_revenue_reports`
- `economic_objects`
- `economic_transitions`
- `economic_formula_runs`

## Explicit deferred surfaces

The following remain system/global/control registry surfaces in PR 3 and must be specified later before tenant-specific behavior is introduced:

- `money_lanes`
- `neuro_abstractions`
- `neuro_scale_levels`
- `implementation_hypotheses`
- `mechanistic_gaps`
- `neuro_acceptance_reports`

These are not excluded from the Brain. They are preserved as explicit deferred surfaces.

## Tests added

- tenant context same-tenant guard
- role guard
- service context behavior
- tenant context header parsing
- migration helper-function checks
- migration table-coverage checks
- migration policy checks
- additive/no `tenant_id not null` guard
- deferred registry comments checks

## GO/HOLD

GO for PR 3 review.

HOLD for PR 4 until PR 3 is reviewed and accepted.

## Remaining HOLD items

- Actual database migration dry-run was not executed in ChatGPT.
- Existing API routes still allow global behavior unless later route work requires and applies tenant context.
- Existing repository/adapters still need tenant-aware query filters.
- Legacy/global row backfill plan is not implemented.
- `tenant_id not null` enforcement is deferred until backfill evidence exists.
- Same-tenant foreign-key invariants across related tables require table-specific constraints/triggers in a later PR.
- Operator UI remains a separate risk surface from PR 1 and is not fixed here.

## Recommended PR 4 scope

Tenant-safe route and repository enforcement:

1. require tenant context on selected read/write cognitive API routes;
2. thread `TenantContext` through store/service methods;
3. add tenant filters to belief, evidence, graph, action, outcome, prediction, revenue, and economic queries;
4. add cross-tenant API tests;
5. add legacy-row handling policy for existing global records;
6. keep payments, fulfillment, agents, exports, and capital out of scope until their gates.
