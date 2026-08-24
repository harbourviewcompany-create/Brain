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
- `docs/control/module-build-ready-traceability.md`

## Runtime changes

Adds `brain.tenant_context` as an application-layer tenant context helper:

- `TenantContext`
- `TenantScopeViolation`
- `parse_tenant_context_headers`
- `trusted_tenant_context`
- same-tenant guard
- role guard
- SQL setting export for `brain.tenant_id` and `brain.actor_id`

Trust-boundary repair: request headers may provide transitional tenant and actor identity only. They may not assert tenant roles or service-context status. Roles must come from verified membership records, and service context must use a trusted internal construction path plus database role controls.

Existing API routes are not fully converted in PR 3. That remains a later route-by-route enforcement task because forcing tenant headers globally would break existing API behavior before cognitive rows are backfilled.

## Database changes

Adds migration `013_tenant_scope_cognitive_tables.sql` with:

- `current_brain_tenant_id()`
- `current_brain_actor_id()`
- `current_brain_service_context()` based on PostgreSQL role membership in `brain_trusted_service_role`, not a user-settable custom setting
- nullable `tenant_id` columns on existing cognitive/economic tenant-owned tables
- tenant indexes
- RLS re-enabled and forced on affected tables
- baseline `tenant_isolation_select`
- baseline `tenant_isolation_insert`
- baseline `tenant_isolation_update`
- baseline `tenant_isolation_delete`
- partial tenant-scoped natural uniqueness for safe global-key tables

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
- `sensory_inbox`
- `cognitive_cycle_runs`
- `predictions`
- `attribution_records`
- `working_memory_snapshots`
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

## Natural uniqueness repair

PR 3 converts these existing global natural uniqueness rules into tenant-safe partial uniqueness patterns:

- `sources.key`
- `entities(kind, canonical_key)`
- `graph_nodes(kind, node_key)`
- `daily_revenue_reports.report_date`

Legacy/system rows with `tenant_id is null` preserve global uniqueness. Tenant-owned rows use composite tenant uniqueness.

Known remaining uniqueness HOLD:

- `projection_checkpoints.projection_name` remains a tenant-breaking primary key in PR 3. It is documented as a hard blocker for the later projection-specific migration because changing primary-key identity requires table-specific safety review.

## Runtime role / RLS enforcement requirement

PR 3 policies are only effective when API and worker `DATABASE_URL` values connect as a non-owner, non-`BYPASSRLS` database role. Table owners, superusers, and roles with `BYPASSRLS` remain forbidden for tenant runtime connections.

Internal service jobs that need audited cross-tenant access must use a separately provisioned trusted database role that is a member of `brain_trusted_service_role`. No request header and no custom GUC may grant service bypass.

## Explicit deferred surfaces

The following remain system/global/control registry surfaces in PR 3 and must be specified later before tenant-specific behavior is introduced:

- `money_lanes`
- `neuro_abstractions`
- `neuro_scale_levels`
- `implementation_hypotheses`
- `mechanistic_gaps`
- `neuro_acceptance_reports`

These are not excluded from the Brain. They are preserved as explicit deferred surfaces.

## Tests added / repaired

- tenant context same-tenant guard
- role guard
- trusted service-context behavior
- tenant context header parsing
- untrusted role-header rejection
- untrusted service-context-header rejection
- malformed tenant-id conversion into `TenantScopeViolation`
- migration helper-function checks
- migration active-learning table coverage checks
- migration policy checks
- additive/no `tenant_id not null` guard
- tenant-scoped natural uniqueness guardrails
- projection-checkpoint uniqueness blocker documentation
- runtime-role/RLS requirement documentation checks
- deferred registry comments checks

## GO/HOLD

GO for PR 3 review after CI and review-thread revalidation.

HOLD for PR 4 until PR 3 is reviewed, accepted, and merged into its PR 2 stack base.

## Remaining HOLD items

- Actual database migration dry-run was not executed in ChatGPT.
- Existing API routes still allow global behavior unless later route work requires and applies tenant context.
- Existing repository/adapters still need tenant-aware query filters.
- Legacy/global row backfill plan is not implemented.
- `tenant_id not null` enforcement is deferred until backfill evidence exists.
- Same-tenant foreign-key invariants across related tables require table-specific constraints/triggers in a later PR.
- `projection_checkpoints.projection_name` remains globally unique until a projection-specific migration changes checkpoint identity.
- Operator UI remains a separate risk surface from PR 1 and is not fixed here.
- Production database roles must be verified outside this PR to ensure runtime connections are constrained by RLS.

## Recommended PR 4 scope

Tenant-safe route and repository enforcement:

1. require verified tenant context on selected read/write cognitive API routes;
2. resolve roles from tenant membership records, not request headers;
3. thread `TenantContext` through store/service methods;
4. add tenant filters to belief, evidence, graph, action, outcome, prediction, revenue, and economic queries;
5. stamp `tenant_id` on new tenant-owned rows;
6. add cross-tenant API tests;
7. add legacy-row handling policy for existing global records;
8. keep payments, fulfillment, agents, exports, and capital out of scope until their gates.
