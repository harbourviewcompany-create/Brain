# Sovereign Cognitive Kernel

Vercel-only. No Railway. No Fly.

## Persistence

If `DATABASE_URL` (or `BRAIN_WORKER_DATABASE_URL`) is set on the Vercel project, the kernel hydrates from `sovereign_snapshot` row `id=live` on first request and upserts after first lap, ticks, commands, and cron.

If the URL is missing or a query fails, cognition stays in-process.
