# PR 2 GO/HOLD Report — Tenant/Auth/Membership/Invite/Lifecycle Foundation

## Scope

PR 2 implements the first runtime foundation for multi-tenant Brain control:

- tenant lifecycle root
- tenant memberships
- tenant roles
- tenant invites
- tenant lifecycle audit events
- in-memory domain service for tenant/auth lifecycle rules
- tests for lifecycle invariants
- migration guard tests

## Explicit non-scope

PR 2 does not retrofit existing cognitive tables with `tenant_id`.

PR 2 does not add tenant-aware RLS policies for existing Brain state.

PR 2 does not change payments, agents, capital, fulfillment, graph tissue, belief ledger, revenue, storage, exports, external actions, or worker execution.

PR 2 does not copy any uploaded SQL/TypeScript/Python snippets from contaminated artifacts.

## Files changed

- `brain/tenant_auth.py`
- `db/migrations/012_tenant_auth_foundation.sql`
- `tests/test_tenant_auth.py`
- `tests/test_tenant_auth_migration.py`
- `docs/control/PR2_GO_HOLD_REPORT.md`

## Implemented invariants

- tenant names and owner IDs are required
- tenant creation creates an active owner membership
- membership authorization requires an active tenant and active membership
- only owners/admins can create invites
- only owners can invite owners
- invite tokens are single-use lifecycle objects
- expired invites are marked expired and rejected
- revoked invites cannot be accepted
- last active owner cannot be removed
- last active owner cannot be demoted
- tenant status changes emit audit events
- suspended tenants block normal membership authorization
- lifecycle audit events are appended to the store

## Database foundation

Added `012_tenant_auth_foundation.sql` with:

- `tenants`
- `tenant_memberships`
- `tenant_invites`
- `tenant_audit_events`
- RLS enabled on all four tables
- direct grants revoked from `anon` and `authenticated`
- active-owner index for last-owner checks
- invite token hash storage requirement

## GO/HOLD

GO for PR 2 review.

HOLD for PR 3 until PR 2 is reviewed and accepted.

## Recommended PR 3 scope

PR 3 should add tenant ownership to existing cognitive state:

- add `tenant_id` to existing tenant-owned tables
- backfill or fixture-seed tenant ownership
- add tenant-aware RLS policies
- add same-tenant constraints where applicable
- add cross-tenant isolation tests
- update API/service paths to require tenant context before accessing Brain state
