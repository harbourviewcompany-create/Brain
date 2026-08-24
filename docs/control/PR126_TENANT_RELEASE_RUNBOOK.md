# PR #126 Tenant Production Release Runbook

Status: release verification only. Do not promote until every gate below is green.

## Release boundary

This release introduces migrations 019-023 plus tenant-aware runtime enforcement. It is separate from the currently verified Railway production deployment at Brain commit `22b1fe76cdb3cff67ba54fe03c8dcb8cad89c556`.

## Database role contract

The production API/worker `DATABASE_URL` must authenticate as a dedicated PostgreSQL login that is:

- not a database/table owner;
- `NOSUPERUSER`;
- `NOBYPASSRLS`;
- granted only the schema/table/sequence privileges required by Brain runtime operations.

`BRAIN_MIGRATION_DATABASE_URL` is the separate privileged connection used only by `tools/apply_migrations.py` during pre-deploy migration execution. It must not be used by the running API process as `DATABASE_URL`.

Cross-tenant internal maintenance is a separate concern. If needed, it must use an explicitly audited database role that is a member of `brain_trusted_service_role`; no HTTP header, API key, tenant signature, or custom GUC may grant that bypass.

## Legacy production ownership

Migrations 020-022 add FORCE RLS to tenant-owned cognitive state while intentionally leaving pre-tenant rows nullable. A compliant ordinary runtime role therefore cannot see the existing production rows until ownership is assigned.

Migration `023_legacy_observatory_tenant_backfill.sql` creates the deterministic compatibility tenant:

- tenant id: `7d4427c4-8b8d-4f4a-9f75-b46cedc2f126`
- slug: `brain-observatory-legacy-production`
- service actor: `brain-observatory-bff`
- durable role: `operator`

It assigns rows that are still `tenant_id IS NULL` in tables already tenant-owned by migrations 020/021/022 to that compatibility tenant. Tenant auth/control rows are excluded. System registries that migrations 020/021 intentionally left global do not have `tenant_id` and are not touched.

`brain_events` remains append-only in normal operation. Migration 023 suspends only the UPDATE append-only trigger inside the migration transaction, changes only `tenant_id` for pre-tenant rows, and immediately re-enables the trigger. PostgreSQL transactional DDL prevents a failed migration from committing the trigger in a disabled state.

## Observatory/BFF runtime contract

`Dockerfile.railway` continues to expose the Observatory compatibility routes through `tools.live_cockpit_routes`, but that module must initialize `apps.api.tenant_app` first and use its tenant-scoped runtime.

For the Vercel BFF path:

1. Railway verifies the Vercel deployment OIDC token.
2. Railway exchanges it internally for the existing server-only Brain API key.
3. Incoming tenant, role, service-context, and API-key headers are stripped.
4. Railway binds the request to the server-configured compatibility tenant and service actor.
5. The actor's role is resolved from durable `tenant_memberships`.
6. `TenantScopedConnectionPool` stamps only `brain.tenant_id` and `brain.actor_id` into the transaction.
7. FORCE RLS remains authoritative.

Direct API-key clients do not inherit the Observatory service identity. When tenant mode is required they must satisfy the signed tenant-context and membership contract.

## Promotion gates

Before production promotion, require all of the following on one immutable release SHA:

- protected control validators pass;
- focused tenant/auth/OIDC/Observatory regressions pass;
- full pytest and Ruff pass;
- zero-state migrations 001-023 pass;
- second migration-runner execution skips all migrations cleanly;
- raw replay of 019-023 is idempotent;
- migrations run through `BRAIN_MIGRATION_DATABASE_URL` while runtime `DATABASE_URL` points to a separate `NOSUPERUSER NOBYPASSRLS` login;
- production-shaped 001-018 legacy data upgrades through 019-023 without loss;
- legacy `/edges` and `/signals` remain visible to the compatibility tenant under the ordinary runtime role;
- protected edge and signal writes succeed for an authorized operator and are stamped with the compatibility tenant;
- unauthenticated, missing-tenant, spoofed-role, and spoofed-service-context requests fail closed;
- the `brain_events_append_only_update` trigger is enabled after migration;
- current live BFF/Observatory baseline remains healthy before deployment;
- production role creation/grants and environment-variable split are verified without exposing credentials.

Only after these gates are green should the release be deployed. After deployment, repeat BFF/API read/write persistence smoke and inspect Railway logs before declaring production GO.
