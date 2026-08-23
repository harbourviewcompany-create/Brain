# Brain deployment

## Topology (canonical)

| Layer | Host | Role |
|-------|------|------|
| Event ledger / memory | **Supabase Postgres** | Canonical state |
| Cognitive API | **Railway** (preferred) or **Fly.io** | FastAPI runtime |
| Operator control plane | **Vercel** (Next.js) | Inspection, approvals, cockpit |
| Graph projection | Neo4j Aura (optional) | Rebuildable topology |
| Durable workflows | Temporal Cloud (optional) | Slice 3+ |

Vercel is **not** the host for the Python API. Serverless Python is a poor fit for a long-lived cognitive runtime.

## Supabase

- Project: `Brain`
- Project ref: `fkvwjhevjjfoiyoaeuzf`
- Region: `ca-central-1`
- API URL: `https://fkvwjhevjjfoiyoaeuzf.supabase.co`
- Canonical memory: PostgreSQL
- Event ledger: `public.brain_events`
- Schema migrations: `db/migrations/001` onward

Secrets are never committed. Runtime services receive `DATABASE_URL` via the host secret manager.

### Database invariants

1. `brain_events` is append-only at the database layer.
2. Cognitive tables have RLS enabled.
3. `anon` and `authenticated` have direct table privileges revoked.
4. No client-facing RLS policies yet; backend services use privileged server credentials only.
5. Current-state projections are disposable and rebuildable from the event ledger.

## Production API host (Railway — preferred)

1. Create a Railway project from this GitHub repo (`harbourviewcompany-create/Brain`).
2. Build uses `Dockerfile` (`railway.toml`).
3. Set variables:

| Name | Value |
|------|--------|
| `DATABASE_URL` | Supabase **pooler** URI (port `6543`, `sslmode=require`) |
| `BRAIN_ENV` | `production` |
| `BRAIN_EXTERNAL_ACTIONS_ENABLED` | `false` until governance GO |
| `PORT` | injected by Railway |

4. Health check: `GET /health`
5. Public URL example: `https://brain-api-production.up.railway.app`
6. Point the control plane at it:

```text
NEXT_PUBLIC_BRAIN_API_URL=https://<your-railway-host>
```

Redeploy the Vercel control plane after setting the env var.

## Alternative: Fly.io

```bash
fly apps create brain-api
fly secrets set DATABASE_URL="postgresql://..." BRAIN_ENV=production
fly deploy
```

See `fly.toml` (region `yyz` near Supabase `ca-central-1`). Keep `min_machines_running = 1` so cognition does not sleep.

## Local / Docker

```bash
docker build -t brain-api .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="$DATABASE_URL" \
  brain-api

curl -s http://127.0.0.1:8000/health
```

Without `DATABASE_URL`, the API uses the in-memory store (fine for demos; not durable).

## Control plane wiring

| Variable (Vercel) | Purpose |
|-------------------|---------|
| `NEXT_PUBLIC_BRAIN_API_URL` | Public FastAPI base URL (no trailing slash) |
| `NEXT_PUBLIC_OPERATOR_ID` | Operator id for approval surfaces (default `tyler`) |

Live mode requires a reachable `/health`. Temporary `*.trycloudflare.com` tunnels expire; use Railway/Fly for production.

## API surface (control-plane relevant)

| Method | Path | Notes |
|--------|------|--------|
| GET | `/health` | Status + counts |
| GET | `/beliefs` | List beliefs |
| GET | `/beliefs/{id}` | Single belief |
| POST | `/beliefs` | Create belief |
| POST | `/learn` | Evidence update |
| GET | `/predictions` | List predictions |
| POST | `/predictions` | Create prediction |
| GET | `/money-lanes` | Money spine lanes |

CORS is enabled for browser calls from the Vercel control plane.

## Next infrastructure

1. Deploy API with `DATABASE_URL` (this pack).
2. Apply remaining migrations on Supabase if not already applied.
3. Temporal Cloud namespace + worker.
4. Neo4j Aura projection adapter.
5. Continuous observation → event → projection workflow.
6. Restrict CORS `allow_origins` to the production control-plane origin(s).
