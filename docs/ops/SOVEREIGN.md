# Sovereign Cognitive Kernel

Vercel-only. No Railway. No Fly.

## Persistence

If `DATABASE_URL` (or `BRAIN_WORKER_DATABASE_URL`) is set on the Vercel project, the kernel:

1. Creates `sovereign_snapshot` and `sovereign_event` if missing
2. Hydrates the in-process store from row `id='live'` on first request
3. Upserts the snapshot after first lap, ticks, commands, and cron
4. Appends a compact event on those writes

If the URL is missing or the query fails, cognition stays in-process and status reports `persistence: "in-process"`.

Writes use monotonic ticks so a stale instance cannot rewind the mind.
