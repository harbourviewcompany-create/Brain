> Canonical Brain copy. Source preserved from `harbourviewcompany-create/brain-control-plane@03e3c462ff8f8233033457fc703c418d21200b32`. Paths beginning with `src/` refer to `apps/observatory/src/` in the consolidated repository.

# Brain ↔ Control Plane Production Wiring

This document is the authoritative production-wiring record for the Brain runtime and the Vercel control plane.

Verified runtime baseline snapshot: 2026-08-24.

## Repository boundary

| Responsibility | Repository | Production host |
|---|---|---|
| Brain runtime, API, persistence adapters, migrations, Railway build/deploy configuration, Railway-side Vercel identity verification | `harbourviewcompany-create/Brain` | Railway |
| Brain operator UI, same-origin BFF, Vercel deployment identity acquisition/forwarding, browser-safe API client | `harbourviewcompany-create/Brain` | Vercel |

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

No Vercel UI or BFF implementation belongs in this repository.

### Control plane / Vercel ownership

The control-plane repository owns the Vercel-facing operator surface and BFF, including:

- `src/app/api/brain/[...path]/route.ts`
- `src/lib/brain-upstream.ts`
- `src/lib/api.ts`
- UI routes and components under `src/app/*` and `src/components/*`
- Vercel-facing configuration examples and production wiring documentation

No Brain database migration, Railway runtime implementation, or backend persistence code belongs in this repository.

## Production endpoints

- Operator UI / canonical Vercel production URL: `https://thebrain-sandy.vercel.app`
- Brain Runtime API / Railway production URL: `https://brain-api-live-production.up.railway.app`

The browser calls only same-origin `/api/brain/*`. The BFF is responsible for authenticating upstream requests to Railway.

## Production authentication model

Vercel deployment OIDC is the primary server-to-server authentication path.

1. The browser calls the control plane at `/api/brain/*` and receives no upstream credential.
2. The Vercel BFF obtains its signed deployment identity at runtime.
3. The BFF forwards that identity to Railway as `Authorization: Bearer <deployment-token>`.
4. Railway verifies the Vercel token against the configured production identity scope.
5. After successful verification, Railway substitutes its own locally stored `BRAIN_API_KEY` internally so the existing Brain API authentication boundary remains unchanged.

The expected Railway identity scope is:

- team slug: `harbourview`
- project: `thebrain`
- environment: `production`

Railway therefore carries these non-secret identity-scope variables:

- `BRAIN_VERCEL_OIDC_TEAM_SLUG`
- `BRAIN_VERCEL_OIDC_PROJECT`
- `BRAIN_VERCEL_OIDC_ENVIRONMENT`

### Server-only fallback

`BRAIN_API_KEY` remains an optional server-only fallback on the Vercel BFF and the authoritative local API credential on Railway. If Vercel OIDC is unavailable, the BFF may send the server-only fallback credential as `X-Brain-Api-Key`.

The browser must never receive, embed, log, or persist the upstream credential.

## Environment ownership

### Railway: `brain-api-live`

Production runtime variables include:

- `BRAIN_ENV=production`
- `DATABASE_URL`
- `BRAIN_API_KEY`
- `BRAIN_CORS_ORIGINS`
- `BRAIN_EXTERNAL_ACTIONS_ENABLED`
- `BRAIN_VERCEL_OIDC_TEAM_SLUG`
- `BRAIN_VERCEL_OIDC_PROJECT`
- `BRAIN_VERCEL_OIDC_ENVIRONMENT`

Railway is configured to build `Dockerfile.railway` and run `python tools/apply_migrations.py` as the pre-deploy migration/verification step.

### Vercel: `thebrain`

Server-side production configuration includes:

- `BRAIN_API_URL=https://brain-api-live-production.up.railway.app`
- `BRAIN_API_KEY` only when the server-only fallback path is intentionally configured

Vercel deployment identity remains the primary production authentication path.

## Verified production deployment mapping

This section records the last runtime-affecting production baseline verified immediately before this documentation-only boundary cleanup. Merging documentation can produce newer hosting deployment IDs even when application behavior is unchanged, so these identifiers are evidence of the verified runtime baseline rather than a promise that they remain the newest docs-only deployment.

### Railway

- project: `Brain`
- project ID: `54914617-2d60-488d-a144-9492082c5b9d`
- environment: `production`
- environment ID: `a05b761c-d332-4cda-abd7-5b55cdf08867`
- service: `brain-api-live`
- service ID: `81c88785-4d36-4621-8125-8c22b2ef3520`
- source repository: `harbourviewcompany-create/Brain`
- runtime baseline Brain commit: `2acb3d4bd02e85607edf27ab1f736202c8688d1c`
- Railway deployment ID: `99fefce8-c4a0-4096-b498-ab88c23206d5`
- deployment status: `SUCCESS`
- production URL: `https://brain-api-live-production.up.railway.app`

### Vercel — canonical production project

- team: `harbourview`
- project: `thebrain`
- source repository: `harbourviewcompany-create/Brain`
- runtime baseline control-plane commit: `800090dc56c1aa33c392d58c352d36b05ccca98c`
- GitHub Vercel status: `success`
- Vercel deployment target reference: `D8J6MREB12uopsRFQ4AJm9P1wJv1`
- Vercel deployment target: `https://vercel.com/harbourview/thebrain/D8J6MREB12uopsRFQ4AJm9P1wJv1`
- production URL: `https://thebrain-sandy.vercel.app`

A second Vercel project, `harbourviewcompany-create-brain-control-plane`, also reported a successful deployment for the same control-plane runtime baseline commit with target reference `8PeVc4qHKTuwDMACM7E6bpStBzks`. It is not the canonical production authority described by this document.

## Deployment boundary

A Brain production release follows these boundaries:

1. Backend/runtime/schema work merges to `harbourviewcompany-create/Brain`.
2. Railway `brain-api-live` deploys from Brain `main`.
3. `python tools/apply_migrations.py` applies/verifies only the Brain repository migration tree before runtime promotion.
4. BFF/UI work merges to `harbourviewcompany-create/Brain`.
5. Vercel `thebrain` deploys from control-plane `main`.
6. No migration or backend implementation is copied into the control-plane repository, and no Vercel BFF/UI implementation is copied into the Brain repository.

## Post-deploy verification

For a production wiring change, verify at minimum:

- `GET https://brain-api-live-production.up.railway.app/health` succeeds.
- `GET https://thebrain-sandy.vercel.app/api/brain/health` succeeds through the BFF.
- A protected BFF route succeeds through Vercel deployment identity.
- Protected Railway routes remain unauthorized without an accepted credential.
- The browser/client bundle contains no upstream API credential.
- Railway logs show no authentication regression, migration drift, `UndefinedTable`, or startup failure.
- The deployed Railway commit belongs to `harbourviewcompany-create/Brain`.
- The deployed Vercel commit belongs to `harbourviewcompany-create/Brain`.

## Source of truth

Repository ownership is structural, not inferred from file names. Vercel-related verifier code that executes inside Railway remains Brain backend code; Vercel token acquisition and forwarding remain control-plane BFF code.

When this deployment snapshot becomes stale because runtime behavior changes, update this document in `harbourviewcompany-create/Brain`. Do not recreate a control-plane wiring guide in the Brain repository.
