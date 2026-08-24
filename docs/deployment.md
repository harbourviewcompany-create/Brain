# Brain deployment state

## Production topology

The Brain runtime is split into independently deployable processes:

1. **Brain API** — `apps.api.main:app`; operator/control-plane and cognitive APIs.
2. **Cognition worker** — `apps.worker.main`; continuous local mode or Temporal durable workflow mode.
3. **Supabase/PostgreSQL** — canonical event ledger, Brain projections, developmental evidence and generic cognitive objects.
4. **Temporal** — preferred durable orchestration for long-lived cognition; workflow intent is separate from process lifetime.
5. **Neo4j** — optional graph projection; PostgreSQL remains canonical unless a later approved architecture changes that contract.
6. **Existing Railway cockpit** — `Dockerfile.railway` remains a separate cockpit path and is not replaced by the Brain API image.

## Supabase / PostgreSQL

- Project: `Brain`
- Region: `ca-central-1`
- Canonical memory: PostgreSQL
- Event ledger: `public.brain_events`
- Migration `011_developmental_evidence_ledger.sql`: AGENT-019 developmental evidence authority.
- Migration `012_cognitive_organism.sql`: Cognitive Organism V1 persistence authority.
- Migration `013_neuro_global_workspace_proxy.sql`: NEURO-006 Global Workspace Proxy persistence authority.
- Migration `014_cognitive_object_store.sql`: generic provenance-aware cognitive objects.
- Migration `015_source_registry_runtime.sql`: MOD-017 persistent source-registry and signal-intake SQL target.
- Migration `016_cognitive_organism_persistence.sql`: Cognitive Organism checkpoint persistence and audit hardening.

Secrets are never committed. Runtime services receive `DATABASE_URL`, `BRAIN_API_KEY`, Temporal credentials and Neo4j credentials through deployment environment configuration or a secret manager.

## Production security contract

`BRAIN_ENV=production` fails closed unless `BRAIN_API_KEY` is configured. Protected API paths accept `Authorization: Bearer <key>`, `X-Brain-Api-Key: <key>`, or the compatibility header `X-Api-Key: <key>`.

`BRAIN_CORS_ORIGINS` is an explicit comma-separated allow-list in production. An empty production list does not become wildcard CORS.

Consequential external actions remain disabled by default. If `BRAIN_EXTERNAL_ACTIONS_ENABLED=true`, startup also requires `BRAIN_EXTERNAL_ACTION_APPROVAL_MODE=explicit`. This configuration enables only approval-gated paths; it is not approval for any individual action.

## Database and readiness invariants

1. `brain_events` remains append-only at the database layer.
2. Cognitive tables use the repository RLS/revoke controls declared by their migrations.
3. Backend cognitive services use privileged server-side credentials only.
4. `PostgresBrainStore` makes PostgreSQL authoritative for beliefs, evidence, graph nodes/edges, rewires and events when `DATABASE_URL` is configured; process dictionaries are disposable projections.
5. AGENT-019 developmental evidence, Cognitive Organism V1 tables/checkpoints, NEURO-006 workspace persistence and MOD-017 source-registry tables remain separately governed from the generic cognitive-object repository.
6. `/health` reports degraded state and HTTP 503 when a configured database is unavailable.
7. `/ready` is the deployment readiness endpoint and returns HTTP 503 when a configured database is unavailable.
8. A configured database must never silently fall back to process-only memory.

## API container

```bash
docker build -t brain-api -f Dockerfile .
```

Minimum production environment:

```text
BRAIN_ENV=production
DATABASE_URL=<server-side PostgreSQL/Supabase URL>
BRAIN_API_KEY=<strong secret>
BRAIN_CORS_ORIGINS=https://<approved-control-plane-domain>
BRAIN_EXTERNAL_ACTIONS_ENABLED=false
```

The image exposes port 8000 by default and probes `/ready`.

## Cognition worker

```bash
docker build -t brain-worker -f Dockerfile.worker .
```

Local continuous mode:

```text
BRAIN_WORKER_MODE=cognition
DATABASE_URL=<server-side PostgreSQL URL>
```

Temporal mode:

```text
BRAIN_WORKER_MODE=temporal
DATABASE_URL=<server-side PostgreSQL URL>
TEMPORAL_ADDRESS=<host:port>
TEMPORAL_NAMESPACE=<namespace>
BRAIN_TEMPORAL_TASK_QUEUE=brain-cognition
BRAIN_TEMPORAL_WORKFLOW_ID=brain-continuous-cognition
BRAIN_TEMPORAL_AUTOSTART=true
```

Temporal coordinates replay-safe timers, prediction maintenance and history rollover. Cognitive work executes as activities backed by the same PostgreSQL state. Worker process restart must not be treated as workflow completion.

## Railway

`railway.toml` targets the API `Dockerfile` and probes `/ready`. `railway.worker.toml` targets `Dockerfile.worker` as a background worker. API and worker should be separate services.

## Fly.io

`fly.toml` defines an `app` process for HTTP and a `worker` process for cognition. Only `app` is attached to the HTTP service; `/ready` is the health check.

## Deployment acceptance before GO

A production deployment is not GO merely because a container starts. Exact deployed-commit evidence must show:

- migration integrity validation passes and migrations through 016 apply successfully;
- production authentication is active and unauthenticated protected requests return 401;
- authenticated belief create/read survives API restart;
- `/ready` returns 503 during an induced database outage and recovers after restoration;
- API and worker images build from the exact commit;
- Temporal workflow test-server acceptance passes;
- live Temporal mode, if deployed, survives worker restart without losing workflow intent;
- Cognitive Organism checkpoint persistence/cockpit routes remain governed and non-external-actioning;
- external actions remain disabled or explicitly approval-gated;
- rollback/restore procedure is tested;
- protected control, 117-row conformance, pytest and Ruff checks are green on the exact deployed commit.

Until those checks are evidenced, production deployment status remains HOLD.
