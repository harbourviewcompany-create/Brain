# Sovereign Brain (no third-party host)

## Principle

The Brain must run **without** Railway, Fly, or any external API host.
Observatory on Vercel is the only required surface.

## Mode selection

| `BRAIN_API_URL` | Behavior |
|-----------------|----------|
| empty / unset / Railway rejected | **Sovereign** — in-process endogenous kernel |
| HTTPS host on allowlist | Proxy to that runtime (optional Turso API project) |

## What sovereign provides

- Seeded foundational beliefs on first request
- `/api/brain/beliefs`, `/health`, `/ready`, `/organism`, `/working-memory`, `/curiosity`
- `/api/brain/tick` and `/api/cron/think` for bounded cognition cycles
- Status endpoint reports `mode: "sovereign"` and advances one tick per poll

## Operator steps

1. Vercel project **brain** → Environment Variables
2. **Remove or empty** `BRAIN_API_URL` (so proxy does not try a dead host)
3. Redeploy production
4. Open Observatory — DEGRADED clears; beliefs appear
5. Optional: Vercel Cron → `GET /api/cron/think` every 5 minutes

## Limits

- State is process-local (warm instances keep it; cold starts re-seed)
- Not a substitute for Turso durable ledger when you later want multi-instance persistence
- Full Python BrainRuntime remains available via optional second Vercel project + Turso (zero-cost Path B)
