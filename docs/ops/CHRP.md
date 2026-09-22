# Cognitive Host Resurrection Protocol (CHRP)

**Status**: production recovery authority · original to this repository  
**Version**: 1.0 · dual-path (Railway + Fly) · seed-aware · Observatory-aware

## Why CHRP exists

The Brain API host can disappear (Railway service deletion, region failure, credential drift).  
The Observatory correctly enters DEGRADED when the upstream is unreachable.  
CHRP is the single, idempotent way to bring cognition back online on either or both hosts without guesswork.

## Design principles (unique)

1. **Dual-host first** — Railway and Fly are peers. Prefer both for resilience.
2. **Seed is not optional** — `BRAIN_OBSERVATORY_SEED_PACK=observatory-production-seed-v1` is set automatically so the production baseline beliefs appear on first healthy boot.
3. **Migrations stay capped at 18** until the explicit tenant/RLS release.
4. **Zero secrets in git** — the script only consumes environment variables.
5. **Observatory hand-off is explicit** — the script always prints the exact Vercel steps.

## One-command restore

```bash
# Prerequisites: DATABASE_URL and BRAIN_API_KEY in the environment
export DATABASE_URL='postgresql://…'
export BRAIN_API_KEY='…'          # strong random, shared with Vercel

# Optional overrides
export BRAIN_CORS_ORIGINS='https://brain-seven-puce.vercel.app,…'
export FLY_APP=brain-api
export FLY_ORG=your-org

# Run
./scripts/restore_api_host.sh both     # or railway | fly
```

## What the script does

| Step | Railway | Fly |
|------|---------|-----|
| Ensure service/app exists | uses linked project | creates `brain-api` if missing |
| Set identity + seed vars | yes | yes |
| Apply migrations ≤18 | preDeployCommand | release_command |
| Run production seed | preDeployCommand | release_command |
| Scale worker | (separate service) | `app=1 worker=1` |
| Health path | `/ready` | `/ready` |

## After CHRP succeeds

1. Confirm API:
   ```bash
   curl -s https://<host>/ready
   curl -s https://<host>/health
   ```
2. Point Vercel project `brain`:
   - `BRAIN_API_URL` = live host (no trailing slash)
   - `BRAIN_API_KEY` = same value
3. Redeploy Observatory.
4. Verify:
   ```bash
   curl -s https://brain-seven-puce.vercel.app/api/brain-status | jq .
   ```
   Expect `upstream_health_ok: true` and non-empty `upstream_base`.

## Dual-host resilience pattern

Run CHRP with `both`. Keep Railway as standby or active secondary.  
The Observatory only needs one healthy upstream; the second host can take over by flipping `BRAIN_API_URL`.

## Contract tests

`tests/test_railway_deploy_contract.py` continues to enforce that Fly and Railway share the same Dockerfile, OIDC-bridged entrypoint, `/ready` probe, and pre-tenant migration ceiling.

## Phoenix additions (v1)

- Seed pack is forced on every restore so DEGRADED never returns to an empty belief field.
- Inline cognition remains enabled so cycles can start even if the worker is still scaling.
- CORS and OIDC scope are written identically on both hosts, eliminating the most common post-restore 401s.
