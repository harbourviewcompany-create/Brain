# Control plane ↔ Runtime wiring

Operator UI: **brain-control-plane** → https://thebrain-sandy.vercel.app  
Runtime API (current live): https://brain-api-live-production.up.railway.app (v0.5.0 in-memory)

## Already working

- CORS on live Railway allows `https://thebrain-sandy.vercel.app`
- Control plane client falls back to the live Railway base when `NEXT_PUBLIC_BRAIN_API_URL` is unset
- Cockpit lists beliefs / signals / contradictions / curiosity / approvals / sources against live API

## A — Harden (Vercel)

In the Vercel project for `brain-control-plane` (team harbourview-plat):

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_BRAIN_API_URL` | `https://brain-api-live-production.up.railway.app` (no trailing slash) |
| `NEXT_PUBLIC_BRAIN_API_KEY` | *(set after Railway promote — same secret as `BRAIN_API_KEY`)* |
| `NEXT_PUBLIC_OPERATOR_ID` | `tyler` (optional) |

Redeploy production after setting env.

The client already sends `X-Brain-Api-Key` when the key env is present.

## B — Organism layer (control plane)

Control plane exposes:

- Nav → **Organism**
- `/organism` page (self-state, curiosity, agency, quarantine, persistence)
- Cockpit strip that reports whether `/organism/cockpit` is live

These routes exist on Brain **main** (`register_cognitive_organism_routes`). They return **404** on the current Railway v0.5 deploy. After promote, the UI lights up without further control-plane code changes.

## C — Promote Runtime on Railway

Redeploy the Railway service from Brain `main` (not the older v0.5 image).

### Required Railway environment

| Variable | Notes |
|----------|--------|
| `BRAIN_ENV` | `production` |
| `BRAIN_API_KEY` | Strong secret; fail-closed auth on all non-`/health` `/ready` paths |
| `BRAIN_CORS_ORIGINS` | Comma-separated. **Must include** `https://thebrain-sandy.vercel.app` |
| `BRAIN_EXTERNAL_ACTIONS_ENABLED` | `false` unless policy explicitly enables |
| `DATABASE_URL` | Optional; omit keeps in-memory store |

Example:

```text
BRAIN_ENV=production
BRAIN_API_KEY=<generate-strong-secret>
BRAIN_CORS_ORIGINS=https://thebrain-sandy.vercel.app,http://localhost:3000
BRAIN_EXTERNAL_ACTIONS_ENABLED=false
```

### After Railway is healthy

1. Confirm `GET /health` → version ≥ 0.8.x and status ok
2. Confirm `GET /organism/cockpit` without key → 401; with `X-Brain-Api-Key` → 200
3. Set `NEXT_PUBLIC_BRAIN_API_KEY` on Vercel to the same secret
4. Redeploy control plane
5. Open https://thebrain-sandy.vercel.app — TopBar **API live**, Organism strip green, `/organism` populated

### Rollback

Keep the previous Railway deployment available. Control plane fallback still targets the known live host if env is cleared.

## Guardrails

- External actions stay permissioned (`BRAIN_EXTERNAL_ACTIONS_ENABLED=false` by default)
- Production without `BRAIN_API_KEY` refuses startup / requests (SecurityConfig)
- Control plane never logs the API key
