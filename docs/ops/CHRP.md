# Cognitive Host Resurrection Protocol (CHRP) v1

Original dual-path recovery so the Brain API never stays dead.

## Principles

1. **Dual-host first** — Railway and Fly are peers.
2. **Seed is not optional** — every restore forces `observatory-production-seed-v1`.
3. **Migrations capped at 18** until explicit tenant/RLS release.
4. **Zero secrets in git** — env vars only.
5. **Explicit Observatory hand-off** — always print Vercel `BRAIN_API_URL` steps.

## Usage

### GitHub Action

Actions → **Cognitive Host Resurrection (CHRP)** → Run workflow → provider `fly` or `both`.

Requires repository secrets: `DATABASE_URL`, `BRAIN_API_KEY`, `FLY_API_TOKEN` (and optionally `RAILWAY_TOKEN`).

### CLI

```bash
export DATABASE_URL='postgresql://…'
export BRAIN_API_KEY='…'
./scripts/restore_api_host.sh both
```

## Post-restore

1. Set Vercel project `brain` env `BRAIN_API_URL` to the live host (no trailing slash).
2. Ensure `BRAIN_API_KEY` matches the host secret.
3. Redeploy Vercel production.
4. Verify: `curl -s https://brain-seven-puce.vercel.app/api/brain-status`

## Control preflight

- GO when DATABASE_URL + BRAIN_API_KEY + host token are present.
- Prefer Fly if Railway returns Application not found.
