> Canonical location: `harbourviewcompany-create/Brain/apps/observatory`. Consolidated from `harbourviewcompany-create/brain-control-plane` at `03e3c462ff8f8233033457fc703c418d21200b32`.

# Brain/apps/observatory

Brain Control Plane — operator UI and server-side BFF for the Brain cognitive runtime (Next.js).

Vercel project: `brain` (`prj_Fr14GlGBNeae7coqrnhgXteHC0jA`) — the canonical Vercel project for this repository.

Canonical production URL: `https://brain-seven-puce.vercel.app`.
Additional production aliases are `https://brain-harbourview.vercel.app` and `https://brain-git-main-harbourview.vercel.app`.

Vercel production deploys `harbourviewcompany-create/Brain` from `main` with Root Directory `apps/observatory`. The obsolete repository-root static placeholder is not part of production.

> The former `thebrain-sandy.vercel.app` belonged to a separate, pre-consolidation project and is not production authority.

## Production wiring authority

The canonical Brain ↔ control-plane production ownership, authentication, environment, deployment and verification record is [`docs/observatory/PRODUCTION_WIRING.md`](../../docs/observatory/PRODUCTION_WIRING.md).

## Security model

**Operators sign in before anything reaches the Brain.** `src/middleware.ts` requires a
valid signed operator session on every route except `/login` and the auth endpoints,
including `/api/brain/*` and `/api/brain-status`. The BFF attaches the server-side Brain
credential to everything it forwards, so an unauthenticated caller here would be an
unauthenticated caller against the Brain itself. Set `OBSERVATORY_ACCESS_KEY` and
`OBSERVATORY_SESSION_SECRET`; without both, the Observatory refuses every request rather
than falling open. Sessions are HttpOnly, SameSite=Lax and last 12 hours.

The browser talks only to same-origin `/api/brain/*` and receives no upstream credential.

Two upstream authentication paths exist, and which one applies depends on the Brain image
being addressed:

- **`Dockerfile.railway`** (`railway.brain-api-live.toml`, the BFF's default upstream)
  wraps the app in `VercelOidcAuthBridge`. It verifies the deployment token's issuer,
  audience and subject via `tools/vercel_oidc.py`, then exchanges it for the locally
  stored Brain API key. This is the OIDC path.
- **`Dockerfile`** (`railway.toml`, the repository default) runs `apps.api.tenant_app` and
  authenticates on `BRAIN_API_KEY` alone. It has no OIDC bridge and ignores the bearer
  token.

The BFF sends both credentials, and `apps/api/main.py` accepts any presented credential
that matches — so a deployment token no longer masks a valid `X-Brain-Api-Key`. Set
`BRAIN_UPSTREAM_ACCEPTS_OIDC=false` to stop forwarding the deployment token.

`BRAIN_API_KEY` is server-only and must equal the Brain runtime's `BRAIN_API_KEY`.
`BRAIN_API_URL` is also server-side and points to the Railway runtime.

Default upstream if `BRAIN_API_URL` is unset: `https://brain-api-live-production.up.railway.app`.

## Local

```bash
cp .env.example .env.local
npm install
npm run dev
```

## Vercel

1. Keep the Vercel project linked to `harbourviewcompany-create/Brain` on `main` with Root Directory `apps/observatory`.
2. Set `BRAIN_API_URL` to the production Railway runtime.
3. Configure `BRAIN_API_KEY` only when the server-only fallback path is intentionally required.
4. Redeploy.
5. Confirm the TopBar reports the API live and the browser continues to use `/api/brain`.
