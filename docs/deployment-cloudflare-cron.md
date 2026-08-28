# Free Cloudflare cron → Brain cognition tick

Use this when you cannot run a paid always-on worker, but still want an external
metronome that advances cognition when the API is the only process available.

| Piece | Role |
|-------|------|
| Cloudflare Worker (free) | Cron every minute; only `fetch` |
| `POST /internal/cognition/tick` | Lease-aware, bounded Python tick on the API |
| Cognition lease | Prevents double-write with inline cognition or a real worker |

This does **not** replace `apps/worker` or inline cognition. Prefer:

1. Dedicated worker (best)
2. Inline cognition on the API (#168)
3. This cron as a free external backup / wake-up when the host only thinks on HTTP

## API contract

```http
POST /internal/cognition/tick
X-Brain-Api-Key: <BRAIN_API_KEY>
Content-Type: application/json

{"max_items": 1, "max_ticks": 1}
```

Responses (always authenticated; 401 without a valid key):

| `status` | Meaning |
|----------|---------|
| `ticked` | Lease acquired (or no DB), ran ticks, released |
| `lease_held_elsewhere` | Another process holds the lease; **no work** (correct) |

`max_items` and `max_ticks` are capped at 5 so a free cron cannot run unbounded work.

Existing `POST /tick` still exists for authenticated operators; it does **not**
take the cognition lease. Prefer `/internal/cognition/tick` for schedulers.

## Deploy the Worker ($0)

Prerequisites: Cloudflare account on the **Workers Free** plan; API already
reachable at an HTTPS origin with `BRAIN_API_KEY` set.

```bash
cd deploy/cloudflare-cognition-cron
npm install
npx wrangler login
npx wrangler secret put BRAIN_API_URL    # e.g. https://brain-api-live-production.up.railway.app
npx wrangler secret put BRAIN_API_KEY    # same value as the API host
npx wrangler deploy
```

Optional path override (default `/internal/cognition/tick`):

```bash
npx wrangler secret put BRAIN_TICK_PATH
```

Schedule is `* * * * *` (every minute) in `wrangler.toml`. Free plan allows a
small number of cron triggers per account; one is enough.

## Verify

1. `npx wrangler tail` — each minute should log `status: 200` and either
   `ticked` or `lease_held_elsewhere`.
2. Manual: open the Worker URL in a browser (runs one tick via the `fetch` handler).
3. Cockpit: if nothing else holds the lease and the API is up, durable **CYCLE**
   should advance over successive minutes (`source: durable` on `/health`).

## Interaction with inline cognition

| Who holds the lease | Cron result |
|---------------------|-------------|
| Inline API thread | `lease_held_elsewhere` (good) |
| Dedicated worker | `lease_held_elsewhere` (good) |
| Nobody | `ticked` |

If both inline cognition and cron are enabled, cron is a no-op while the API
thread holds the lease. That is intentional.

## Limits (free tier)

- Cloudflare: ~100k Worker requests/day; **~10 ms CPU** on free — fine because
  the Worker only issues HTTP.
- Cognition quality: at most one short tick per minute from cron alone — far
  coarser than the ~1s in-process loop. Use inline cognition when the API stays up.

## Secrets

Never commit `BRAIN_API_KEY`. Rotate the API key on the host and in
`wrangler secret put` together.
