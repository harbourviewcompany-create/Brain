> Canonical location: `harbourviewcompany-create/Brain/apps/observatory`. Consolidated from `harbourviewcompany-create/brain-control-plane` at `03e3c462ff8f8233033457fc703c418d21200b32`.

# Brain/apps/observatory

Brain Control Plane — operator UI and server-side BFF for the Brain cognitive runtime (Next.js).

Production: https://thebrain-sandy.vercel.app

## Production wiring authority

The canonical Brain ↔ control-plane production ownership, authentication, environment, deployment and verification record is [`docs/PRODUCTION_WIRING.md`](docs/PRODUCTION_WIRING.md).

## Security model

The browser talks only to same-origin `/api/brain/*` and receives no upstream credential.

Vercel deployment OIDC is the primary server-to-server authentication path. The BFF obtains its signed deployment identity at runtime and forwards it to the Railway Brain API. Railway verifies the exact production identity before translating it internally to its locally stored Brain API credential.

`BRAIN_API_KEY` remains an optional server-only fallback for the BFF. `BRAIN_API_URL` is also server-side and points to the Railway runtime.

Default upstream if `BRAIN_API_URL` is unset: `https://brain-api-live-production.up.railway.app`.

## Local

```bash
cp .env.example .env.local
npm install
npm run dev
```

## Vercel

1. Set `BRAIN_API_URL` to the production Railway runtime.
2. Configure `BRAIN_API_KEY` only when the server-only fallback path is intentionally required.
3. Redeploy.
4. Confirm the TopBar reports the API live and the browser continues to use `/api/brain`.
