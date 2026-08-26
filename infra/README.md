# Brain local & cloud infrastructure

This stack wires the five production backends the Brain architecture requires:

| Concern | Local (docker compose) | Production |
|--------|-------------------------|------------|
| Canonical ledger | Postgres + pgvector | **Supabase / PostgreSQL** |
| Graph projection | Neo4j | **Neo4j AuraDB** |
| Durable workflows | Temporal auto-setup | **Temporal Cloud** |
| Object storage | MinIO (S3 API) | **AWS S3 / R2 / GCS** |
| Cognition workers | `python -m apps.worker.main` | Railway / Fly / ECS worker image |

PostgreSQL is always canonical. Neo4j is rebuildable. Temporal owns long-lived cognition intent. Object storage holds immutable evidence bytes; Postgres holds keys and metadata.

## Quick start (local)

```bash
docker compose -f infra/docker-compose.yml up -d
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
set -a && source .env && set +a
python -m tools.apply_migrations
python scripts/infra_healthcheck.py
uvicorn apps.api.main:app --reload
# separate terminal
python -m apps.worker.main
```

Local ports:

- Postgres `5432`
- Neo4j browser `7474`, bolt `7687`
- Temporal gRPC `7233`, UI `8088`
- MinIO API `9000`, console `9001`

## Cloud wiring

### Supabase / Postgres

1. Create a project; copy the connection string (prefer direct for migrations, pooler for app).
2. Set `DATABASE_URL`.
3. Run `python -m tools.apply_migrations`.
4. Confirm `/ready` returns 200.

### Neo4j Aura

1. Create an AuraDB instance; copy the `neo4j+s://…` URI and credentials.
2. Set `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`.
3. Keep `NEO4J_PROJECTION_ENABLED=true`.
4. Rebuild after cutover: `python scripts/rebuild_neo4j_projection.py` or `POST /admin/rebuild-neo4j`.

### Temporal Cloud

1. Create a namespace; note gRPC endpoint and auth.
2. Set `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, and `TEMPORAL_API_KEY` (TLS is enabled when the key is set).
3. Deploy the worker image (`Dockerfile.worker`).
4. Leave local `temporal` / `temporal-ui` compose services stopped.

### Object storage

**MinIO (local)** is pre-configured in `.env.example`.

**AWS S3:** set `OBJECT_STORAGE_BUCKET` and region; leave `OBJECT_STORAGE_ENDPOINT` empty; use `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.

**Cloudflare R2:** set `OBJECT_STORAGE_ENDPOINT` to the R2 S3 API URL and use R2 access keys.

## Worker modes

| `BRAIN_WORKER_MODE` | Behavior |
|--------------------|----------|
| `temporal` (or any mode with `TEMPORAL_ADDRESS` set) | Temporal worker + continuous cognition workflow |
| `cognition` | Local continuous cycle without Temporal |
| `maintenance` | Prediction maintenance loop only |

## Invariants

- History is append-only in Postgres (`brain_events`).
- Neo4j may be wiped and rebuilt from Postgres.
- External actions remain approval-gated (`BRAIN_EXTERNAL_ACTIONS_ENABLED=false` by default).
