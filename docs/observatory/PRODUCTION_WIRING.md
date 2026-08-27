> Canonical Brain copy. Paths beginning with `src/` in historical notes refer to `apps/observatory/src/` in the consolidated repository.

# Brain ↔ Control Plane Production Wiring

This document is the authoritative production-wiring record for the Brain runtime and the Vercel control plane (Observatory).

Verified runtime baseline snapshot: **2026-08-26**.

## Repository boundary

The Brain repository is consolidated. Both the runtime and the operator UI / BFF live in `harbourviewcompany-create/Brain`.

| Responsibility | Location in repo | Production host |
|---|---|---|
| Brain runtime, API, persistence adapters, migrations, Railway build/deploy configuration, Railway-side Vercel identity verification | `apps/api/*`, `brain/*`, `db/migrations/*`, `tools/*`, `Dockerfile*`, `railway*.toml` | Railway |
| Brain operator UI (Observatory), same-origin BFF, Vercel deployment identity acquisition/forwarding, browser-safe API client | `apps/observatory/*` (and related Vercel config) | Vercel |

### Brain / Railway ownership

The Brain repository owns runtime and database behavior, including:

- `apps/api/*`
- `brain/*`
- `db/migrations/*`
- `tools/apply_migrations.py`
- `tools/live_cockpit_routes.py`
- `tools/vercel_oidc.py`
- `Dockerfile.railway`
- `railway*.toml`

### Control plane / Vercel ownership

The same repository owns the Vercel-facing operator surface and BFF under the Observatory app tree, including:

- Observatory app routes and components under `apps/observatory/`
- Same-origin BFF routes that proxy `/api/brain/*`
- Vercel-facing configuration and this production wiring document

No Brain database migration or Railway runtime implementation belongs solely on the Vercel host; no browser-safe UI belongs on the Railway API image.

## Production endpoints

- Operator UI / canonical Vercel production URL: `https://brain-seven-puce.vercel.app`
- Additional Vercel production aliases: `https://brain-harbourview.vercel.app`, `https://brain-git-main-harbourview.vercel.app`
- Brain Runtime API / Railway production URL: `https://brain-api-live-production.up.railway.app`

The browser calls only same-origin `/api/brain/*`. The BFF is responsible for authenticating upstream requests to Railway.

> Historical note: earlier wiring used Vercel project `thebrain` and URL `https://thebrain-sandy.vercel.app`. That project is no longer the canonical production authority. Do not point CI smoke tests or OIDC scope at `thebrain-sandy.vercel.app`.

## Production authentication model

Vercel deployment OIDC is the primary server-to-server authentication path.

1. The browser calls the control plane at `/api/brain/*` and receives no upstream credential.
2. The Vercel BFF obtains its signed deployment identity at runtime.
3. The BFF forwards that identity to Railway as `Authorization: Bearer <deployment-token>`.
4. Railway verifies the Vercel token against the configured production identity scope.
5. After successful verification, Railway substitutes its own locally stored `BRAIN_API_KEY` internally so the existing Brain API authentication boundary remains unchanged.

The expected Railway identity scope is:

- team slug: `harbourview`
- project: `brain`
- environment: `production`

Railway therefore carries these non-secret identity-scope variables:

- `BRAIN_VERCEL_OIDC_TEAM_SLUG=harbourview`
- `BRAIN_VERCEL_OIDC_PROJECT=brain`
- `BRAIN_VERCEL_OIDC_ENVIRONMENT=production`

### Server-only fallback

`BRAIN_API_KEY` remains an optional server-only fallback on the Vercel BFF and the authoritative local API credential on Railway. If Vercel OIDC is unavailable, the BFF may send the server-only fallback credential as `X-Brain-Api-Key`.

The browser must never receive, embed, log, or persist the upstream credential.

Credential matching on the Brain API accepts any presented recognized header that matches `BRAIN_API_KEY` (merged via #160). An unrelated Vercel OIDC bearer must not mask a valid `X-Brain-Api-Key`.

## Environment ownership

### Railway: `brain-api-live`

Production runtime variables include:

- `BRAIN_ENV=production`
- `DATABASE_URL`
- `BRAIN_API_KEY`
- `BRAIN_CORS_ORIGINS` (must allow the Vercel production origin(s), e.g. `https://brain-seven-puce.vercel.app,https://brain-harbourview.vercel.app`)
- `BRAIN_EXTERNAL_ACTIONS_ENABLED`
- `BRAIN_VERCEL_OIDC_TEAM_SLUG`
- `BRAIN_VERCEL_OIDC_PROJECT`
- `BRAIN_VERCEL_OIDC_ENVIRONMENT`

Railway runs the canonical API image (`Dockerfile` → `tools.live_cockpit_routes:app`, which is `apps.api.tenant_app` wrapped in the Vercel OIDC bridge). Observatory cockpit read routes (`/signals`, `/edges`, `/contradictions`, `/curiosity`, `/sources`, and empty-state collection routes) are registered on that surface as of #160. A Railway redeploy of `main` is required before live OBS 18/18 can be claimed.

Until this change, that redeploy could not have delivered OBS 18/18 by either
route. The canonical image did not copy `tools/`, so it carried neither the OIDC
bridge nor `apply_migrations.py`: a service switched to `railway.toml` would have
rejected the BFF's `Authorization: Bearer <OIDC token>` and applied no
migrations. A service left on `railway.brain-api-live.toml` kept the bridge but
was pinned to `Dockerfile.railway`. `railway.toml`,
`railway.brain-api-live.toml`, `Dockerfile`, `Dockerfile.railway` and `fly.toml`
now all resolve to one image and one entrypoint, so the live surface no longer
depends on which of them the host selects.

`Dockerfile.railway` remains a compatibility path; it builds the same runtime as `Dockerfile`.

**Still required outside the repository:** confirm in the Railway dashboard which
config path or Dockerfile path the `brain-api-live` service is pinned to, and
that `BRAIN_VERCEL_OIDC_TEAM_SLUG`, `BRAIN_VERCEL_OIDC_PROJECT` and
`BRAIN_VERCEL_OIDC_ENVIRONMENT` are set there. The repository cannot read those
settings, and no repository change can substitute for them.

### Vercel: `brain`

- Team: `harbourview`
- Project ID: `prj_Fr14GlGBNeae7coqrnhgXteHC0jA`
- Project name: `brain`
- Linked repository: `harbourviewcompany-create/Brain`

Server-side production configuration includes:

- `BRAIN_API_URL=https://brain-api-live-production.up.railway.app`
- `BRAIN_API_KEY` only when the server-only fallback path is intentionally configured

Vercel deployment identity remains the primary production authentication path. Vercel Authentication (SSO) may be enabled for deployment URLs; custom domains can be exempted per project protection settings.

## Verified production deployment mapping

This section records the last runtime-affecting production baseline verified at the snapshot date. Merging documentation can produce newer hosting deployment IDs even when application behavior is unchanged, so these identifiers are evidence of the verified runtime baseline rather than a promise that they remain the newest docs-only deployment.

### Railway

- project: `Brain`
- project ID: `54914617-2d60-488d-a144-9492082c5b9d`
- environment: `production`
- environment ID: `a05b761c-d332-4cda-abd7-5b55cdf08867`
- service: `brain-api-live`
- service ID: `81c88785-4d36-4621-8125-8c22b2ef3520`
- source repository: `harbourviewcompany-create/Brain`
- runtime baseline Brain commit: `2acb3d4bd02e85607edf27ab1f736202c8688d1c` (last documented; re-verify on next Railway promote)
- Railway deployment ID: `99fefce8-c4a0-4096-b498-ab88c23206d5` (last documented)
- deployment status: `SUCCESS` (last documented)
- production URL: `https://brain-api-live-production.up.railway.app`
- **Pending:** redeploy `main` including #160 (`7a4bc83`) so the canonical image serves Observatory read routes in production.

### Vercel — canonical production project

- team: `harbourview` (`team_0rK4jTvMLlSufR0ZzX4LCKYi`)
- project: `brain`
- project ID: `prj_Fr14GlGBNeae7coqrnhgXteHC0jA`
- source repository: `harbourviewcompany-create/Brain`
- production branch: `main`
- verified production commit: `f4fa774985b84f92a4468dfeebddd59827439f6f` ("feat: optimize operator cockpit and static frontend")
- verified production deployment ID: `dpl_ACjhEdvt32T16dFRofhs6dsiutgq`
- deployment state: `READY`
- deployment target: production
- inspector: `https://vercel.com/harbourview/brain/ACjhEdvt32T16dFRofhs6dsiutgq`
- production domains:
  - `https://brain-seven-puce.vercel.app`
  - `https://brain-harbourview.vercel.app`
  - `https://brain-git-main-harbourview.vercel.app`

Legacy / non-canonical Vercel projects (`thebrain`, `harbourviewcompany-create-brain-control-plane`, or other control-plane-only projects) are not production authority. Do not use their hostnames for smoke tests, CORS allow-lists, or OIDC scope.

## Deployment boundary

A Brain production release follows these boundaries:

1. Backend/runtime/schema work merges to `harbourviewcompany-create/Brain` `main`.
2. Railway `brain-api-live` deploys from Brain `main`.
3. `python tools/apply_migrations.py` applies/verifies only the Brain repository migration tree before runtime promotion.
4. Observatory / BFF / UI work merges to the same `harbourviewcompany-create/Brain` `main`.
5. Vercel project `brain` deploys from Brain `main`.
6. Keep host responsibilities split: Railway runs the API/worker; Vercel runs the operator UI and same-origin BFF.

## Post-deploy verification

For a production wiring change, verify at minimum:

- `GET https://brain-api-live-production.up.railway.app/health` succeeds.
- `GET https://brain-seven-puce.vercel.app/api/brain/health` (or the active production domain) succeeds through the BFF.
- Protected Observatory read paths (e.g. signals/edges/beliefs proxies) succeed with real or empty-state envelopes, not auth collision or missing-route failures.
- A protected BFF route succeeds through Vercel deployment identity.
- Protected Railway routes remain unauthorized without an accepted credential.
- The browser/client bundle contains no upstream API credential.
- Railway logs show no authentication regression, migration drift, `UndefinedTable`, or startup failure.
- Railway `BRAIN_VERCEL_OIDC_PROJECT` matches Vercel project name `brain`.
- `BRAIN_CORS_ORIGINS` includes the live Vercel production origin(s).
- The deployed Railway commit belongs to `harbourviewcompany-create/Brain` and includes the #160 canonical read surface when claiming OBS 18/18.
- The deployed Vercel commit belongs to `harbourviewcompany-create/Brain`.

## Source of truth

Repository ownership is structural, not inferred from file names. Vercel-related verifier code that executes inside Railway remains Brain backend code; Vercel token acquisition and forwarding remain Observatory BFF code on Vercel.

When this deployment snapshot becomes stale because runtime behavior changes, update this document in `harbourviewcompany-create/Brain`.
