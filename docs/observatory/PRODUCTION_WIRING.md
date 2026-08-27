> Canonical Brain copy. Paths beginning with `src/` in historical notes refer to `apps/observatory/src/` in the consolidated repository.

# Brain ↔ Control Plane Production Wiring

This document is the authoritative production-wiring record for the Brain runtime and the Vercel control plane (Observatory).

Verified runtime baseline snapshot: **2026-08-27** (Fly host alternative documented; Railway may still be the live API until cutover).

## Repository boundary

The Brain repository is consolidated. Both the runtime and the operator UI / BFF live in `harbourviewcompany-create/Brain`.

| Responsibility | Location in repo | Production host |
|---|---|---|
| Brain runtime, API, persistence adapters, migrations, host build/deploy configuration, Vercel identity verification bridge | `apps/api/*`, `brain/*`, `db/migrations/*`, `tools/*`, `Dockerfile*`, `railway*.toml`, `fly.toml` | **Railway or Fly.io** (same image) |
| Brain operator UI (Observatory), same-origin BFF, Vercel deployment identity acquisition/forwarding, browser-safe API client | `apps/observatory/*` (and related Vercel config) | Vercel |
| Event ledger / projections | `db/migrations/*` | Supabase / PostgreSQL |

### Brain API host ownership (Railway **or** Fly)

The Brain repository owns runtime and database behavior, including:

- `apps/api/*`
- `brain/*`
- `db/migrations/*`
- `tools/apply_migrations.py`
- `tools/live_cockpit_routes.py`
- `tools/vercel_oidc.py`
- `Dockerfile` / `Dockerfile.railway` / `Dockerfile.worker`
- `railway*.toml`
- `fly.toml` and `docs/deployment-fly.md`

Either Railway or Fly may run the canonical API image. Only one should be the Vercel BFF upstream at a time (`BRAIN_API_URL`).

### Control plane / Vercel ownership

The same repository owns the Vercel-facing operator surface and BFF under the Observatory app tree, including:

- Observatory app routes and components under `apps/observatory/`
- Same-origin BFF routes that proxy `/api/brain/*`
- Vercel-facing configuration and this production wiring document

No Brain database migration or API runtime implementation belongs solely on the Vercel host; no browser-safe UI belongs on the API image.

## Production endpoints

- Operator UI / canonical Vercel production URL: `https://brain-seven-puce.vercel.app`
- Additional Vercel production aliases: `https://brain-harbourview.vercel.app`, `https://brain-git-main-harbourview.vercel.app`
- Brain Runtime API (Railway, current documented live): `https://brain-api-live-production.up.railway.app`
- Brain Runtime API (Fly alternative): `https://<fly-app>.fly.dev` after `fly deploy` (see `docs/deployment-fly.md`)

The browser calls only same-origin `/api/brain/*`. The BFF is responsible for authenticating upstream requests to the active API host.

> Historical note: earlier wiring used Vercel project `thebrain` and URL `https://thebrain-sandy.vercel.app`. That project is no longer the canonical production authority. Do not point CI smoke tests or OIDC scope at `thebrain-sandy.vercel.app`.

## Production authentication model

Vercel deployment OIDC is the primary server-to-server authentication path.

1. The browser calls the control plane at `/api/brain/*` and receives no upstream credential.
2. The Vercel BFF obtains its signed deployment identity at runtime.
3. The BFF forwards that identity to the API host as `Authorization: Bearer <deployment-token>`.
4. The API host verifies the Vercel token against the configured production identity scope.
5. After successful verification, the host substitutes its own locally stored `BRAIN_API_KEY` internally so the existing Brain API authentication boundary remains unchanged.

The expected identity scope is:

- team slug: `harbourview`
- project: `brain`
- environment: `production`

API hosts therefore carry these non-secret identity-scope variables:

- `BRAIN_VERCEL_OIDC_TEAM_SLUG=harbourview`
- `BRAIN_VERCEL_OIDC_PROJECT=brain`
- `BRAIN_VERCEL_OIDC_ENVIRONMENT=production`

While tenant mode is disabled, production may also set `BRAIN_OBSERVATORY_LEGACY_OIDC_BRIDGE=true` (#169) so a verified Vercel deployment identity can reach protected reads without durable membership rows.

### Server-only fallback

`BRAIN_API_KEY` remains an optional server-only fallback on the Vercel BFF and the authoritative local API credential on the API host. If Vercel OIDC is unavailable, the BFF may send the server-only fallback credential as `X-Brain-Api-Key`.

The browser must never receive, embed, log, or persist the upstream credential.

Credential matching on the Brain API accepts any presented recognized header that matches `BRAIN_API_KEY` (merged via #160). An unrelated Vercel OIDC bearer must not mask a valid `X-Brain-Api-Key`.

## Environment ownership

### API host: Railway `brain-api-live` **or** Fly `brain-api`

Production runtime variables include:

- `BRAIN_ENV=production`
- `DATABASE_URL`
- `BRAIN_API_KEY`
- `BRAIN_CORS_ORIGINS` (must allow the Vercel production origin(s), e.g. `https://brain-seven-puce.vercel.app,https://brain-harbourview.vercel.app`)
- `BRAIN_EXTERNAL_ACTIONS_ENABLED`
- `BRAIN_VERCEL_OIDC_TEAM_SLUG`
- `BRAIN_VERCEL_OIDC_PROJECT`
- `BRAIN_VERCEL_OIDC_ENVIRONMENT`
- `BRAIN_OBSERVATORY_LEGACY_OIDC_BRIDGE` (optional; tenant-disabled legacy path only)

Both hosts run the canonical API image (`Dockerfile` → `tools.live_cockpit_routes:app`). Ordinary production migrations remain capped at **018** until the explicit tenant/RLS release (`railway.brain-api-live.toml` preDeployCommand and Fly `release_command`).

Fly cutover (create app, secrets, scale worker, point Vercel `BRAIN_API_URL`): **`docs/deployment-fly.md`**.

### Vercel: `brain`

- Team: `harbourview`
- Project ID: `prj_Fr14GlGBNeae7coqrnhgXteHC0jA`
- Project name: `brain`
- Linked repository: `harbourviewcompany-create/Brain`

Server-side production configuration includes:

- `BRAIN_API_URL=<active API host HTTPS origin>` — Railway live URL **or** Fly app URL after cutover
- `BRAIN_API_KEY` only when the server-only fallback path is intentionally configured

Vercel deployment identity remains the primary production authentication path. Vercel Authentication (SSO) may be enabled for deployment URLs; custom domains can be exempted per project protection settings.

## Verified production deployment mapping

This section records the last runtime-affecting production baseline verified at the snapshot date. Merging documentation can produce newer hosting deployment IDs even when application behavior is unchanged, so these identifiers are evidence of the verified runtime baseline rather than a promise that they remain the newest docs-only deployment.

### Railway (may remain live until Fly cutover)

- project: `Brain`
- service: `brain-api-live`
- service ID: `81c88785-4d36-4621-8125-8c22b2ef3520`
- production URL: `https://brain-api-live-production.up.railway.app`
- **Pending for full #168/#169/#171 effect:** redeploy `main` at or after `4c24aec` with OIDC env set.

### Fly (alternative API+worker host)

- config: `fly.toml` (`app = brain-api`, region `yyz`)
- image: `Dockerfile`
- processes: `app` (HTTP `/ready`), `worker` (`apps.worker.main`)
- migrations: `release_command` → `apply_migrations.py --max-version 18`
- runbook: `docs/deployment-fly.md`
- status: repository-ready; live GO requires `fly deploy`, secrets, and Vercel `BRAIN_API_URL` switch

### Vercel — canonical production project

- team: `harbourview` (`team_0rK4jTvMLlSufR0ZzX4LCKYi`)
- project: `brain`
- project ID: `prj_Fr14GlGBNeae7coqrnhgXteHC0jA`
- source repository: `harbourviewcompany-create/Brain`
- production branch: `main`
- production domains:
  - `https://brain-seven-puce.vercel.app`
  - `https://brain-harbourview.vercel.app`
  - `https://brain-git-main-harbourview.vercel.app`

Legacy / non-canonical Vercel projects (`thebrain`, etc.) are not production authority.

## Deployment boundary

A Brain production release follows these boundaries:

1. Backend/runtime/schema work merges to `harbourviewcompany-create/Brain` `main`.
2. The active API host (Railway **or** Fly) deploys from Brain `main`.
3. Migrations apply only through the approved ceiling (018 pre-tenant) before runtime promotion.
4. Observatory / BFF / UI work merges to the same `main`.
5. Vercel project `brain` deploys from Brain `main`.
6. Keep host responsibilities split: API/worker on Railway or Fly; operator UI and same-origin BFF on Vercel; data on Supabase.

## Post-deploy verification

For a production wiring change, verify at minimum:

- `GET https://<api-host>/health` and `/ready` succeed.
- `GET https://brain-seven-puce.vercel.app/api/brain/health` succeeds through the BFF.
- Protected Observatory read paths succeed with real or empty-state envelopes, not auth collision or missing-route failures.
- A protected BFF route succeeds through Vercel deployment identity.
- Protected API routes remain unauthorized without an accepted credential.
- The browser/client bundle contains no upstream API credential.
- API host logs show no authentication regression, migration drift, `UndefinedTable`, or startup failure.
- OIDC project scope matches Vercel project name `brain`.
- `BRAIN_CORS_ORIGINS` includes the live Vercel production origin(s).
- After cognition is running: cockpit **CYCLE** is a durable signal (#168), not a permanent structural zero.
- The deployed API commit belongs to `harbourviewcompany-create/Brain`.
- The deployed Vercel commit belongs to `harbourviewcompany-create/Brain`.

## Source of truth

Repository ownership is structural, not inferred from file names. Vercel-related verifier code that executes inside the API host remains Brain backend code; Vercel token acquisition and forwarding remain Observatory BFF code on Vercel.

When this deployment snapshot becomes stale because runtime behavior changes, update this document in `harbourviewcompany-create/Brain`.
