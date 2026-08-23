# Brain deployment

## Topology (canonical)

| Layer | Host | Role |
|-------|------|------|
| Event ledger / memory | **Supabase Postgres** | Canonical state |
| Cognitive API | **Railway** (preferred) or **Fly.io** | FastAPI (`apps.api`) |
| Cognition worker | **Railway/Fly** (separate service) | Temporal / continuous loop (`apps.worker`) |
| Operator control plane | **Vercel** (Next.js) | Cockpit, approvals, inspection |
| Graph projection | Neo4j Aura (optional) | Rebuildable topology |
| Durable workflows | Temporal Cloud (optional) | Slice 3+ |

Vercel is **not** the host for the Python API or worker. Serverless Python is a poor fit for a long-lived cognitive runtime.

Deploy artifacts on this branch: `Dockerfile`, `Dockerfile.worker`, `Procfile`, `railway.toml`, `railway.worker.toml`, `fly.toml`.

## Supabase

- Project: `Brain`
- Project ref: `fkvwjhevjjfoiyoaeuzf`
- Region: `ca-central-1`
- API URL: `https://fkvwjhevjjfoiyoaeuzf.supabase.co`
- Canonical memory: PostgreSQL
- Event ledger: `public.brain_events`
- Belief projection: `public.beliefs` (hydrate on API startup)
- Schema migrations: `db/migrations/` (`001` onward; apply before durable production)

Secrets are never committed. Runtime services receive `DATABASE_URL` via the host secret manager.

### Database invariants

1. `brain_events` is append-only at the database layer.
2. Cognitive tables have RLS enabled.
3. `anon` and `authenticated` have direct table privileges revoked.
4. No client-facing RLS policies yet; backend services use privileged server credentials only.
5. Current-state projections are disposable and rebuildable from the event ledger.

## Production API host (Railway — preferred)

1. Create a Railway project from this GitHub repo (`harbourviewcompany-create/Brain`), branch with deploy configs.
2. **API service:** build `Dockerfile` / `railway.toml`.
3. **Worker service (separate):** build `Dockerfile.worker` / `railway.worker.toml`.
4. Set variables on both services as needed:

| Name | Value |
|------|--------|
| `DATABASE_URL` | Supabase **pooler** URI (port `6543`, `sslmode=require`) |
| `BRAIN_ENV` | `production` |
| `BRAIN_EXTERNAL_ACTIONS_ENABLED` | `false` until governance GO |
| `BRAIN_API_KEY` | Required in production for API auth |
| `BRAIN_CORS_ORIGINS` | Control-plane origin(s), comma-separated |
| `PORT` | Injected by Railway on the API service |

5. Health: `GET /health` (returns 503 if `DATABASE_URL` is set but DB is unhealthy).
6. Public API URL example: `https://brain-api-production.up.railway.app`

## Alternative: Fly.io

```bash
fly apps create brain-api
fly secrets set DATABASE_URL="postgresql://..." BRAIN_ENV=production
fly deploy
```

See `fly.toml` (region `yyz` near Supabase `ca-central-1`). Keep API process always-on; run worker as the second process definition.

## Local / Docker

```bash
docker build -t brain-api .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="$DATABASE_URL" \
  brain-api

curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/beliefs
```

Without `DATABASE_URL`, the API uses the in-memory store (demos only; not durable).

With `DATABASE_URL`, `PostgresBrainStore.hydrate()` loads `public.beliefs` (and related projections) into the working set at startup so `GET /beliefs` survives process restart.

## Control plane wiring (Vercel)

| Variable | Purpose |
|----------|--------|
| `NEXT_PUBLIC_BRAIN_API_URL` | Public FastAPI base URL (**no trailing slash**) |
| `NEXT_PUBLIC_OPERATOR_ID` | Operator id for approval surfaces (default `tyler`) |

Example:

```text
NEXT_PUBLIC_BRAIN_API_URL=https://brain-api-production.up.railway.app
NEXT_PUBLIC_OPERATOR_ID=tyler
```

Redeploy the control plane after setting env vars. Live mode requires a reachable `/health`. Temporary `*.trycloudflare.com` tunnels expire; use Railway/Fly for production.

### Control-plane relevant API surface

| Method | Path | Notes |
|--------|------|--------|
| GET | `/health` | Status; `persistence: postgres\|in_memory` |
| GET | `/ready` | Readiness (DB when configured) |
| GET | `/beliefs` | List beliefs; `source: postgres\|memory` |
| GET | `/beliefs/{id}` | Single belief |
| POST | `/beliefs` | Create belief (persists when durable store active) |
| POST | `/learn` | Evidence update |
| GET/POST | `/predictions` | Predictions |
| GET | `/money-lanes` | Money spine lanes |

## Next infrastructure

1. Deploy API and worker with `DATABASE_URL` (this pack).
2. Apply remaining migrations on Supabase if not already applied.
3. Temporal Cloud namespace and worker wiring.
4. Neo4j Aura projection adapter.
5. Continuous observation → event → projection workflow.
6. Restrict CORS to production control-plane origins only.
