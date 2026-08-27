# Brain deployment state

## Production topology

The Brain runtime is split into independently deployable processes:

1. **Brain API** — `tools.live_cockpit_routes:app`; the `apps.api.tenant_app` object (which wraps `apps.api.main` with tenant membership and RLS enforcement) plus the Vercel OIDC deployment-identity bridge. Operator/control-plane and cognitive APIs.
2. **Cognition worker** — `apps.worker.main`; continuous local mode or Temporal durable workflow mode.
3. **Supabase/PostgreSQL** — canonical event ledger, Brain projections, developmental evidence and generic cognitive objects.
4. **Temporal** — preferred durable orchestration for long-lived cognition; workflow intent is separate from process lifetime.
5. **Neo4j** — optional graph projection; PostgreSQL remains canonical unless a later approved architecture changes that contract.
6. **Legacy Railway cockpit compatibility** — `Dockerfile.railway` builds the same runtime as `Dockerfile`. It is retained only because a Railway service may still name it directly; nothing in the repository selects it.

## Deployment authority

Deployment entrypoints are explicit; there is no Procfile fallback.

There is exactly one API runtime entrypoint. Every host reaches it.

| Target | Build authority | Runtime entrypoint | Status |
|---|---|---|---|
| Brain API | `Dockerfile` | `tools.live_cockpit_routes:app` | canonical API image |
| Cognition worker | `Dockerfile.worker` | `python -m apps.worker.main` | canonical worker image |
| Railway API | `railway.toml` -> `Dockerfile` | inherited from image | canonical Railway API path |
| Railway API (alias) | `railway.brain-api-live.toml` -> `Dockerfile` | inherited from image | same image and deploy settings as `railway.toml` |
| Railway worker | `railway.worker.toml` -> `Dockerfile.worker` | inherited from image | canonical Railway worker path |
| Fly.io | `fly.toml` -> `Dockerfile` | explicit `app` / `worker` processes, same entrypoints | supported host definition |
| Legacy cockpit | `Dockerfile.railway` | `tools.live_cockpit_routes:app` | compatibility-only; same runtime as `Dockerfile` |

`tests/test_railway_deploy_contract.py` enforces this table. It fails if a host
config names a different image, a different entrypoint, a health path the others
do not use, or a `preDeployCommand` script the named Dockerfile never copies in.

The repository intentionally has no `Procfile`. Railway and Fly already declare their Docker/process authority explicitly; retaining an unused Procfile would create a second, ambiguous deployment contract.

## Reproducible image contract

`constraints.txt` pins the exact Python 3.12 dependency graph used by protected CI and production Docker builds. `pyproject.toml` remains the semantic dependency authority; the constraints file is a reproducibility lock and must be regenerated deliberately whenever dependency ranges change.

All production images use two build layers:

1. copy `pyproject.toml`, `README.md` and `constraints.txt`, then install the locked dependency graph;
2. copy Brain source and reinstall only the local package with `--no-deps`.

This keeps normal source edits from invalidating the expensive dependency layer. Each image runs `python -m pip check` before completion and runs as the unprivileged `brain` user.

`.dockerignore` excludes local environments, packaging outputs, tests, reports, documentation, local data and other non-runtime build context. `.gitignore` and the repository-hardening tests reject tracked root `venv/`, `.venv/`, `env/`, `build/`, `dist/` and `*.egg-info/` outputs. This is a regression guard for the repository-contamination class observed in PR #53.

When dependencies change, regenerate `constraints.txt` in a clean Python 3.12 environment from the updated `pyproject.toml`, review the resolved diff, and run all protected test/container gates before accepting the lock update. Do not generate it from a long-lived developer environment containing unrelated packages.

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

The image exposes port 8000 by default, probes `/ready`, validates installed dependencies, and executes as the non-root `brain` user.

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

`railway.toml` targets the canonical API `Dockerfile`, probes `/ready`, and
applies migrations with `preDeployCommand`. `railway.worker.toml` targets
`Dockerfile.worker` as a background worker. API and worker should be separate
services.

`railway.brain-api-live.toml` exists only because the live Railway service is
named `brain-api-live` and its config-as-code path may still point at that file.
It now declares the same image, entrypoint, health path and pre-deploy command
as `railway.toml`, so the deployed system no longer depends on which of the two
the service happens to select.

`Dockerfile.railway` is retained only because a Railway service may name a
Dockerfile path directly. It builds the same runtime as `Dockerfile`.

Two of these three files can be deleted, but only after reading the live Railway
service's build settings: the repository cannot observe which config path or
Dockerfile path the service is pinned to, and deleting the pinned one breaks the
next deploy. Converging them first makes that deletion safe to do later without
a behavior change.

### Why the pre-deploy command and the `tools` copy landed together

`tools/apply_migrations.py` lives under `tools/`, which the canonical
`Dockerfile` did not copy. So `railway.toml` could not have carried a
`preDeployCommand` naming it, and did not: a deploy driven by the file the
repository called canonical applied no migrations. The same missing copy left
that image without `tools/vercel_oidc.py`, so it could not verify the
`Authorization: Bearer <Vercel OIDC token>` the Observatory BFF sends -- the
production auth path described in `docs/observatory/PRODUCTION_WIRING.md`.

## Fly.io

`fly.toml` defines an `app` process for HTTP and a `worker` process for cognition. Only `app` is attached to the HTTP service; `/ready` is the health check.

## Protected CI deployment acceptance

The protected `test` workflow installs Python dependencies under `constraints.txt`, builds the API, worker and legacy cockpit images, verifies all three execute as non-root, applies every migration to clean PostgreSQL/pgvector, starts the production API with authentication enabled, verifies durable belief persistence across API restart, and verifies `/ready` fails closed when PostgreSQL disappears.

A production deployment is not GO merely because CI or a container build succeeds. Exact deployed-commit evidence must additionally show:

- migration integrity validation passes and migrations through 016 apply successfully;
- production authentication is active and unauthenticated protected requests return 401;
- authenticated belief create/read survives API restart;
- `/ready` returns 503 during an induced database outage and recovers after restoration;
- API and worker images build from the exact commit and execute as non-root;
- Temporal workflow test-server acceptance passes;
- live Temporal mode, if deployed, survives worker restart without losing workflow intent;
- Cognitive Organism checkpoint persistence/cockpit routes remain governed and non-external-actioning;
- external actions remain disabled or explicitly approval-gated;
- rollback/restore procedure is tested;
- protected control, 117-row conformance, pytest and Ruff checks are green on the exact deployed commit.

Until those checks are evidenced, production deployment status remains HOLD.
