# PR #126 Tenant Production Release Runbook

Status: repository release verification only. Production promotion remains HOLD until a later explicitly authorized release action.

## Canonical release boundary

PR #144 is the canonical current-main repair for the merged PR #126 tenant/RLS rollout. Canonical schema migrations remain 019 through 022. They enforce the tenant model and FORCE RLS while deliberately preserving pre-tenant `tenant_id IS NULL` rows as quarantined legacy state.

PR #145's useful production-shaped verification and Observatory compatibility design are preserved here without making its legacy ownership choice automatic.

## Database role contract

Tenant/RLS migration release requires all of the following before migration 019 can run through `tools/apply_migrations.py`:

- `BRAIN_TENANT_RLS_RELEASE=1`;
- `BRAIN_TENANT_MODE=required`;
- `BRAIN_TENANT_CONTEXT_SECRET` supplied by the deployment environment;
- `BRAIN_MIGRATION_DATABASE_URL` using the privileged migration identity;
- `DATABASE_URL` using a distinct non-owner, `NOSUPERUSER`, `NOBYPASSRLS` API runtime login;
- `BRAIN_WORKER_DATABASE_URL` using a distinct constrained trusted-service worker login.

The API runtime must never inherit `brain_trusted_service_role`. The worker may use that role only through its dedicated database identity. Request headers or session GUC assertions do not grant trusted-service authority.

## Explicit legacy-data strategies

The repository supports two separately verified strategies. Applying canonical migrations does not silently decide historical ownership.

### Strategy A — quarantine legacy NULL ownership (canonical default)

Canonical migrations 019-022 leave pre-tenant rows with `tenant_id IS NULL`. Under FORCE RLS:

- ordinary tenant runtime users cannot see those rows;
- tenant A cannot read or write tenant B data;
- an audited dedicated trusted-service worker can inspect the legacy rows for later disposition;
- no historical row is reassigned merely because the tenant release migrations were applied.

This is the default repository behaviour and the behaviour verified by `tools/verify_tenant_rls_release.py`.

### Strategy B — Observatory compatibility assignment (explicit release action)

If the operator explicitly decides that the existing pre-tenant installation belongs to the Brain Observatory compatibility tenant, apply the separate release SQL asset:

`db/release/023_legacy_observatory_tenant_backfill.sql`

This file is intentionally outside `db/migrations/`; `tools/apply_migrations.py` cannot apply it automatically.

The compatibility identity is:

- tenant id: `7d4427c4-8b8d-4f4a-9f75-b46cedc2f126`;
- slug: `brain-observatory-legacy-production`;
- service actor: `brain-observatory-bff`;
- durable membership role: `operator`.

The release SQL assigns only rows that are still `tenant_id IS NULL` in already tenant-owned tables. Tenant auth/control rows are excluded. For `brain_events`, the append-only UPDATE trigger is suspended only inside the transaction needed to assign ownership and is re-enabled before completion.

Do not apply this release SQL merely because migrations 019-022 are being released. Historical ownership assignment requires an explicit operator decision at production-promotion time.

## Observatory/BFF runtime contract

`tools.live_cockpit_routes` remains registered on the same tenant-aware FastAPI object as the canonical API.

For a verified Vercel deployment OIDC request:

1. Railway verifies the Vercel deployment token.
2. Railway uses only its existing server-side Brain API key.
3. Incoming API-key, tenant, actor, role and service-context headers are stripped.
4. Railway binds the request to the server-owned Observatory tenant/actor identity.
5. The actor's durable role is resolved from `tenant_memberships`.
6. Writes require owner, admin or operator membership.
7. The resolved context is carried through `TenantScopedConnectionPool`; FORCE RLS remains authoritative.

Without the compatibility tenant + membership created by the explicit release action, the Observatory bridge fails closed rather than creating or assigning ownership itself.

## Repository verification gates

Before this repair is merge-ready, one immutable PR head must show:

- protected `Validate Brain control policy` success;
- protected `test` success, including full pytest and Ruff;
- tenant migration release gate refusal when release variables are absent;
- zero-state canonical migration application through 022;
- second-run migration idempotency and exact migration-ledger/hash verification;
- separate migration/API/worker database identities;
- API and worker role safety checks;
- FORCE RLS on critical tenant-owned tables;
- two-tenant cross-read/write denial;
- forged service-context denial;
- legacy NULL rows invisible to ordinary tenant runtime and visible only to the trusted worker under Strategy A;
- separate isolated verification that the explicit Observatory release SQL is idempotent, assigns the intended legacy row, creates the intended membership, restores the append-only trigger, and preserves cross-tenant denial under Strategy B;
- OIDC bridge tests proving spoofed tenant/role/service headers are stripped and write-role enforcement is durable-membership based.

## Production boundary

This PR does not create production database roles, change Railway/Vercel variables, run migrations against production, apply the Observatory compatibility release action, deploy, restart services or mutate production data.

At production-promotion time, the operator must first choose and record Strategy A or Strategy B, verify the real split-role credentials without exposing them, and then execute only the authorized release path.
