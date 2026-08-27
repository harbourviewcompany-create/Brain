# Fly.io API + worker host

Fly is a first-class alternative to Railway for the Brain **API** and **cognition worker**. It does not replace Supabase (Postgres) or Vercel (Observatory).

| Responsibility | Host |
|---|---|
| Operator UI + same-origin BFF | Vercel project `brain` |
| Event ledger + projections | Supabase / PostgreSQL |
| API (`tools.live_cockpit_routes:app`) | **Fly or Railway** |
| Cognition worker (`apps.worker.main`) | **Fly worker process or Railway worker service** |

Authority: `fly.toml` + `Dockerfile`. Contract tests live in `tests/test_railway_deploy_contract.py` (shared host invariant, including Fly).

## Why Fly

- Same canonical image Railway uses after #166 (OIDC bridge + migrations in `tools/`).
- Separate **app** and **worker** processes without depending on Railway free-plan service limits.
- `#168` inline cognition still works if worker count is temporarily 0; scaling `worker=1` is the intended steady state.

## Prerequisites

1. [Fly CLI](https://fly.io/docs/hands-on/install-flyctl/) authenticated (`fly auth login`).
2. Supabase (or other) `DATABASE_URL` for production.
3. Strong `BRAIN_API_KEY` shared with the Vercel BFF only as a server-side secret when using key fallback.
4. Vercel production origins for CORS and OIDC scope project name `brain`.

## One-time app bootstrap

```bash
# From repository root. App name must match fly.toml (brain-api) or edit fly.toml first.
fly apps create brain-api --org <your-org>   # skip if app already exists
fly regions set yyz                         # optional; fly.toml primary_region is yyz
```

## Secrets (required for production)

Never commit these. Set on the Fly app:

```bash
fly secrets set \
  DATABASE_URL='postgresql://…' \
  BRAIN_API_KEY='…' \
  BRAIN_CORS_ORIGINS='https://brain-seven-puce.vercel.app,https://brain-harbourview.vercel.app,https://brain-git-main-harbourview.vercel.app' \
  BRAIN_VERCEL_OIDC_TEAM_SLUG='harbourview' \
  BRAIN_VERCEL_OIDC_PROJECT='brain' \
  BRAIN_VERCEL_OIDC_ENVIRONMENT='production' \
  BRAIN_OBSERVATORY_LEGACY_OIDC_BRIDGE='true'
```

Notes:

- `BRAIN_OBSERVATORY_LEGACY_OIDC_BRIDGE=true` is only valid while `BRAIN_TENANT_MODE=disabled` (default in `fly.toml`). Under tenant required mode the bridge is ignored by design (#169).
- After tenant/RLS production release, remove the legacy bridge and raise the migration ceiling in `fly.toml` `release_command` (drop `--max-version 18`).
- Optional: `BRAIN_INLINE_COGNITION=false` only after `worker` is scaled ≥1 and verified holding the cognition lease.

## Deploy

```bash
fly deploy
```

`[deploy].release_command` runs `python tools/apply_migrations.py --max-version 18` against `DATABASE_URL` before machines are replaced—aligned with `railway.brain-api-live.toml`.

Scale the worker (recommended):

```bash
fly scale count app=1 worker=1
```

Confirm processes:

```bash
fly status
fly logs
```

## Point Observatory at Fly

On Vercel project `brain`:

1. Set `BRAIN_API_URL` to the Fly HTTPS hostname (e.g. `https://brain-api.fly.dev` or your custom domain).
2. Keep OIDC forwarding enabled (`BRAIN_UPSTREAM_ACCEPTS_OIDC=true` unless intentionally disabled).
3. Redeploy Vercel (or wait for the next `main` deploy) so the BFF uses the new upstream.
4. Ensure Fly `BRAIN_CORS_ORIGINS` includes every live Vercel production origin.

Railway can remain running as a standby until OBS and CYCLE checks pass on Fly; then retire or idle the Railway service.

## Post-deploy verification

- `GET https://<fly-host>/ready` → 200 with database up.
- `GET https://<fly-host>/health` → cognition counters from the shared event stream (#168), not a stuck process-local zero when cycles exist.
- `GET https://<vercel-host>/api/brain/health` through the BFF → 200.
- Observatory OBS matrix: protected reads succeed (200 / empty envelopes), not blanket 401.
- After ~30s with worker or inline cognition: **CYCLE** non-zero on the cockpit when the lease is held and ticks complete.
- Fly logs: no `UndefinedTable` on boot (#171); optional `vercel_oidc_auth_accepted` once #173-style audit is present.
- `fly status` shows `app` in the HTTP service and `worker` not attached to HTTP.

## Rollback

1. Point Vercel `BRAIN_API_URL` back to Railway (or prior Fly release).
2. `fly releases` / `fly deploy --image <previous>` as needed.
3. Database migrations through 018 are forward-compatible with the pre-tenant contract; do not apply 019+ from Fly until the explicit tenant release.

## Contract guarantees (CI)

`tests/test_railway_deploy_contract.py` fails if Fly:

- builds a different Dockerfile than Railway API configs,
- runs an entrypoint without the OIDC-bridged app,
- probes a health path other than `/ready`,
- attaches the worker process to the HTTP service,
- omits a release command that applies migrations with the pre-tenant ceiling.
