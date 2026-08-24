# ACTUAL_SOURCE_MAP

Status: PR 1 source-discovery document. Documentation only. No runtime code, migrations, dependencies, deployment settings, or behavior changes are authorized by this file.

## Repository

- Repository: `harbourviewcompany-create/Brain`
- Default branch inspected: `main`
- PR 1 branch: `brain-pr1-source-discovery`
- Visibility observed: public
- Primary repository identity from README: `Brain Runtime`, described as a cloud-native, event-sourced, self-rewiring cognitive runtime.

## Actual framework and runtime

- Language/runtime: Python, requires Python `>=3.12`.
- Web framework: FastAPI.
- ASGI server: Uvicorn.
- Validation/schema layer: Pydantic v2.
- Database/client dependencies declared: `psycopg[binary,pool]`, `neo4j`, `temporalio`, `httpx`.
- Test/dev tools declared: `pytest`, `ruff`.
- Package manager/build source: `pyproject.toml` with setuptools package discovery.
- Main Python package: `brain`.

## Actual application layout

- `apps/api/main.py`: primary FastAPI runtime API.
- `apps/operator/main.py`: economic/operator FastAPI surface with HTML and JSON operator endpoints.
- `apps/worker/main.py`: continuous cognition worker entrypoint.
- `brain/`: core cognitive runtime modules and adapters.
- `db/migrations/`: SQL migration files.
- `docs/`: conceptual, architecture, agent-control, neuroscience, revenue, operator, spec, and control documentation.
- `infra/`: deployment/local infrastructure assets.
- `reports/`: generated or acceptance/report artifacts.
- `.github/workflows/`: GitHub Actions workflows.

## Actual API surfaces identified

### `apps/api/main.py`

Observed routes:

- `GET /health`
- `GET /beliefs`
- `GET /beliefs/{belief_id}`
- `POST /beliefs`
- `POST /learn`
- `POST /edges`
- `GET /predictions`
- `POST /predictions`
- `GET /predictions/{prediction_id}`
- `POST /outcomes`
- `GET /money-lanes`
- `POST /revenue-signals/score`
- `POST /revenue-signals/package`
- `POST /revenue-experiments/evaluate`
- `POST /daily-revenue-report`

Auth observed:

- Minimal API-key middleware in `apps/api/main.py`.
- Header used: `x-api-key`.
- Environment variable used: `BRAIN_API_KEY`.
- Exempt path observed: `/health`.
- Fail-closed behavior observed when `BRAIN_API_KEY` is unset.

Risk note:

- This is API-key auth, not a full user/tenant/session model.
- CORS is configured with wildcard origins in `apps/api/main.py`; this must be reviewed before production exposure.

### `apps/operator/main.py`

Observed routes:

- `GET /health`
- `GET /operator`
- `GET /operator/pressure`
- `GET /operator/money-paths`
- `GET /operator/counterparties`
- `GET /operator/transactions`
- `GET /operator/sources`
- `GET /operator/ui`

Auth observed:

- No route-level auth was observed in this file during PR 1 inspection.
- The operator surface uses `DATABASE_URL` if present, otherwise in-memory economic runtime.

### `apps/worker/main.py`

Observed worker behavior:

- Reads `DATABASE_URL` from environment.
- Builds `ContinuousCognitionRunner`.
- Uses Postgres event/projection/sensory inbox stores.
- Supports `BRAIN_WORKER_MODE` with default `cognition` and alternate `maintenance` mode.
- Maintenance mode expires due predictions while idle.

## Actual database/migration map

Migration directory: `db/migrations`.

Observed migrations:

- `001_init.sql`
- `002_cognitive_runtime.sql`
- `003_cognitive_security_hardening.sql`
- `004_cognitive_database_tuning.sql`
- `005_continuous_cognition.sql`
- `006_money_spine.sql`
- `006_working_memory_predictions_learning.sql`
- `007_economic_cognition.sql`
- `008_neuroscience_abstraction_layer.sql`
- `009_neuro_region_multiscale_maps.sql`
- `010_neuro_unknown_theory_registry.sql`
- `011_developmental_evidence_ledger.sql`

Important finding:

- There are two migrations numbered `006`, which creates ordering ambiguity. This must be reconciled before any migration sequencing work.

Database technology observed:

- PostgreSQL SQL migrations.
- `vector` extension.
- `pgcrypto` extension.
- README positions PostgreSQL as canonical event ledger/structured memory and Neo4j as rebuildable graph projection.

## Actual tables observed from inspected migrations

From `001_init.sql`:

- `brain_events`
- `sources`
- `observations`
- `evidence`
- `entities`
- `beliefs`
- `belief_evidence`
- `graph_nodes`
- `graph_edges`
- `rewire_events`
- `actions`
- `outcomes`

From `002_cognitive_runtime.sql`:

- `memory_items`
- `bitemporal_facts`
- `neuromodulator_snapshots`
- `homeostatic_snapshots`
- `cognitive_tasks`
- `cognitive_experiments`
- `cognitive_experiment_results`
- `projection_checkpoints`

From `003_cognitive_security_hardening.sql`:

- RLS is enabled for the listed cognitive tables.
- Direct grants to `anon` and `authenticated` are revoked for the listed cognitive tables.
- Append-only mutation prevention triggers are added for `brain_events` update/delete.

## Actual auth and tenant state

Observed auth:

- API-key middleware in `apps/api/main.py`.
- No full user/session/membership auth model found in inspected files.
- No tenant model found from search for `tenant`.

Observed tenant state:

- No `tenant_id` field was found in inspected migrations.
- No `tenants`, `memberships`, `tenant_users`, `tenant_invites`, or equivalent schema was found in inspected material.
- This means Brain currently appears single-tenant/system-scoped from inspected source, despite RLS being enabled.

GO/HOLD:

- HOLD for multi-tenant implementation until tenant model is designed and migrated in a dedicated PR.

## Actual environment variables observed

From `.env.example` and source inspection:

- `BRAIN_ENV`
- `DATABASE_URL`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `TEMPORAL_ADDRESS`
- `TEMPORAL_NAMESPACE`
- `BRAIN_EXTERNAL_ACTIONS_ENABLED`
- `BRAIN_API_KEY` observed in source but missing from `.env.example`
- `BRAIN_WORKER_MODE` observed in worker source but missing from `.env.example`

Risk:

- `.env.example` should eventually include all required runtime variables, but PR 1 does not modify runtime config.

## Actual CI/workflows observed

Observed workflow files:

- `.github/workflows/test.yml`
- `.github/workflows/control-policy.yml`
- `.github/workflows/repository-hardening.yml`

Test runner declared:

- `pytest`, configured in `pyproject.toml` with `testpaths = ["tests"]`.

Linting declared:

- `ruff`.

## Deployment/local runtime evidence

Observed files:

- `Dockerfile.railway`
- `infra/docker-compose.yml` referenced by README local start command.
- README recommends Supabase/PostgreSQL, Neo4j AuraDB, Temporal Cloud, Python workers, Vercel + Next.js operator control plane, and object storage.

Actual source currently observed:

- Python FastAPI app surfaces exist.
- No Next.js operator control plane files were observed in the inspected root/app layout.

## Unknowns remaining after PR 1 quick inspection

- Full contents of every `brain/*.py` file were not exhaustively enumerated in this document.
- Full contents of every migration after `003` were not line-enumerated in this document.
- Actual test suite inventory still requires complete `tests/` traversal.
- Actual docs/spec inventory remains broad and should be cross-linked later.
- Actual deployment target and active hosting configuration are not proven from source alone.
- Actual production database state is unknown.

## GO/HOLD

GO:

- Use this map as PR 1 source-discovery baseline.
- Proceed to inventory docs and contaminated-artifact quarantine docs.

HOLD:

- Runtime code changes.
- Migrations.
- Auth/tenant implementation.
- Payment/webhook/fulfillment implementation.
- Agent/job scheduler changes.
- Storage/export implementation.
- Copying any uploaded pseudo-code.
