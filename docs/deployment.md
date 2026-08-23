# Brain deployment state

## Production topology

The Brain runtime is split into independently deployable processes:

1. **Brain API** — `apps.api.main:app`; serves operator/control-plane traffic and cognitive APIs.
2. **Cognition worker** — `apps.worker.main`; consumes the sensory inbox and can run either the existing continuous loop or the Temporal durable workflow mode.
3. **Supabase/PostgreSQL** — canonical event ledger and durable Brain projections.
4. **Temporal** — optional but preferred durable orchestration for long-lived cognition.
5. **Neo4j** — optional graph projection; PostgreSQL remains canonical unless a later approved architecture changes that contract.
6. **Existing Railway cockpit** — `Dockerfile.railway` remains a separate operator/cockpit deployment path and is not replaced by the Brain API image.

## Supabase

- Project: `Brain`
- Project ref: `fkvwjhevjjfoiyoaeuzf`
- Region: `ca-central-1`
- API URL: `https://fkvwjhevjjfoiyoaeuzf.supabase.co`
- Canonical memory: PostgreSQL
- Event ledger: `public.brain_events`
- Reconciled migration sequence includes the existing repository migrations plus `011_cognitive_object_store.sql` on this branch.

Secrets are never committed. Runtime services receive `DATABASE_URL`, `BRAIN_API_KEY`, and any Temporal/Neo4j credentials through the deployment environment or secret manager.

## Production security contract

`BRAIN_ENV=production` fails closed unless `BRAIN_API_KEY` is configured. All API paths except `/health` and `/ready` require either `Authorization: Bearer <key>` or `X-Brain-Api-Key: <key>`.

`BRAIN_CORS_ORIGINS` is an explicit comma-separated allow-list in production. An empty production list does not become wildcard CORS.

Consequential external actions remain disabled by default. If `BRAIN_EXTERNAL_ACTIONS_ENABLED=true`, startup also requires `BRAIN_EXTERNAL_ACTION_APPROVAL_MODE=explicit`; this configuration permits the runtime to use approval-gated action paths but does not itself constitute approval for any individual action.

## Database and readiness invariants

1. `brain_events` is append-only at the database layer.
2. Cognitive tables have RLS enabled where migrations declare it.
3. `anon` and `authenticated` have direct cognitive-table privileges revoked where migrations declare it.
4. Backend cognitive services use privileged server-side database credentials only.
5. `PostgresBrainStore` makes PostgreSQL authoritative for beliefs, evidence, graph nodes/edges, rewires and events when `DATABASE_URL` is configured; in-memory dictionaries are disposable projections.
6. `/health` reports degraded state and HTTP 503 when a configured database is unavailable.
7. `/ready` is the deployment readiness endpoint and returns HTTP 503 when a configured database is unavailable.
8. A configured database must never silently fall back to process-only memory.

## API container

Build locally:

```bash
docker build -t brain-api -f Dockerfile .
```

Minimum production environment:

```text
BRAIN_ENV=production
DATABASE_URL=<server-side PostgreSQL/Supabase pooler URL>
BRAIN_API_KEY=<strong secret>
BRAIN_CORS_ORIGINS=https://<approved-control-plane-domain>
BRAIN_EXTERNAL_ACTIONS_ENABLED=false
```

The image exposes port 8000 by default and its Docker health check probes `/ready`.

## Cognition worker

Build locally:

```bash
docker build -t brain-worker -f Dockerfile.worker .
```

For the existing continuous loop:

```text
BRAIN_WORKER_MODE=cognition
DATABASE_URL=<server-side PostgreSQL URL>
```

For durable Temporal orchestration:

```text
BRAIN_WORKER_MODE=temporal
DATABASE_URL=<server-side PostgreSQL URL>
TEMPORAL_ADDRESS=<host:port>
TEMPORAL_NAMESPACE=<namespace>
BRAIN_TEMPORAL_TASK_QUEUE=brain-cognition
BRAIN_TEMPORAL_WORKFLOW_ID=brain-continuous-cognition
BRAIN_TEMPORAL_AUTOSTART=true
```

Temporal coordinates timers, maintenance and history rollover. Cognitive work remains in activities backed by the same PostgreSQL state. If Temporal is not configured, the existing local continuous cognition mode remains available.

## Railway

`railway.toml` targets the API `Dockerfile` and probes `/ready`.

`railway.worker.toml` targets `Dockerfile.worker` and has no HTTP health endpoint because it is a background worker.

Create separate Railway services for the API and worker so one process cannot starve or restart the other. Both services require `DATABASE_URL`; the API additionally requires `BRAIN_API_KEY` in production. The Temporal worker requires the Temporal connection environment.

## Fly.io

`fly.toml` defines an `app` process for the HTTP API and a `worker` process for cognition. Only the `app` process is attached to the HTTP service. `/ready` is the Fly health check.

## Deployment acceptance before GO

A production deployment is not GO merely because a container starts. Acceptance evidence must show:

- schema migrations applied successfully;
- API starts with production authentication enabled;
- unauthenticated protected requests return 401;
- authenticated belief create/read survives an API process restart;
- `/ready` returns 503 during an induced database outage and recovers afterward;
- cognition worker reconnects after restart;
- Temporal mode, when enabled, survives worker restart without losing workflow intent;
- external actions remain disabled or explicitly approval-gated;
- rollback procedure is tested;
- repository control, test and lint checks are green on the exact deployed commit.

Until those checks are evidenced, production deployment status remains HOLD.
