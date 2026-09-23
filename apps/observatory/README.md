> Canonical location: `harbourviewcompany-create/Brain/apps/observatory`. Consolidated from `harbourviewcompany-create/brain-control-plane` at `03e3c462ff8f8233033457fc703c418d21200b32`.

# Brain/apps/observatory

Brain Control Plane — operator UI and server-side BFF for the Brain cognitive runtime (Next.js).

Vercel project: `brain` (`prj_Fr14GlGBNeae7coqrnhgXteHC0jA`) — the canonical Vercel project for this repository.

Canonical production URL: `https://brain-seven-puce.vercel.app`.
Additional production aliases are `https://brain-harbourview.vercel.app` and `https://brain-git-main-harbourview.vercel.app`.

Vercel production deploys `harbourviewcompany-create/Brain` from `main` with the repository root as the deployment boundary. The Next.js Observatory is built from `apps/observatory`, while repository-root `api/index.py` supplies the serverless Brain API.

> The former `thebrain-sandy.vercel.app` belonged to a separate, pre-consolidation project and is not production authority.

## Production wiring authority

The canonical production topology is Vercel + Turso/libSQL. The repository root is the Vercel boundary; `/api/*` is served by `api/index.py`, and the browser uses the same-origin `/api/brain/*` BFF.

The canonical Brain ↔ control-plane production ownership, authentication, environment, deployment and verification record is [`docs/observatory/PRODUCTION_WIRING.md`](../../docs/observatory/PRODUCTION_WIRING.md).

## Security model

**Operators sign in before anything reaches the Brain.** `src/middleware.ts` requires a
valid signed operator session on every route except `/login` and the auth endpoints,
including `/api/brain/*` and `/api/brain-status`. The BFF attaches the server-side Brain
credential only on the server. Set `OBSERVATORY_ACCESS_KEY` and
`OBSERVATORY_SESSION_SECRET`; without both, the Observatory refuses requests rather
than falling open. Sessions are HttpOnly, SameSite=Lax and last 12 hours.

The browser talks only to same-origin `/api/brain/*` and receives no upstream credential.
The BFF upstream is restricted to an explicit HTTPS hostname allowlist and fails closed for
credentials, explicit ports, wildcards, or unapproved hosts.

`BRAIN_API_KEY` is server-only. `BRAIN_API_URL` is server-side and must resolve only to
the approved canonical HTTPS Brain API host.

## Local

```bash
cp .env.example .env.local
npm install
npm run dev
```

## Vercel

1. Keep the Vercel project linked to `harbourviewcompany-create/Brain` on `main` with Root Directory set to the repository root.
2. Set `BRAIN_API_URL` to the approved canonical Brain API origin.
3. Configure `BRAIN_API_KEY` only when the server-only fallback path is intentionally required.
4. Redeploy.
5. Confirm the TopBar reports the API live and the browser continues to use `/api/brain`.
