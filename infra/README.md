# Brain infrastructure adapters

PostgreSQL remains the canonical state and event ledger. This package adds
operational adapters for Neo4j, Temporal and S3-compatible object storage
without weakening the tenant/RLS boundary merged in PR #144.

## Local stack

```bash
docker compose -f infra/docker-compose.yml up -d
python -m tools.apply_migrations
python scripts/infra_healthcheck.py
```

The local stack provides PostgreSQL/pgvector, Neo4j, Temporal, Temporal UI and
MinIO. `minio-init` retries until MinIO is healthy and fails the compose job if
bucket creation cannot be completed.

## Neo4j

Neo4j is a **derived, rebuildable projection**, not an authoritative write
store. Projection identity is namespaced by tenant and rebuilds require
`BRAIN_NEO4J_REBUILD_TENANT_ID`; the implementation never performs a global
`MATCH (n) DETACH DELETE n`.

```bash
BRAIN_NEO4J_REBUILD_TENANT_ID=<tenant-uuid> \
BRAIN_WORKER_DATABASE_URL=<trusted-worker-dsn> \
python scripts/rebuild_neo4j_projection.py
```

Node upserts replace the complete derived property set so removed PostgreSQL
properties cannot remain stale. Edge upserts first remove the prior logical
projection edge before recreating it with the current endpoints.

Real-time dual writes are intentionally not used: a PostgreSQL commit must
never be reported as failed merely because a derived Neo4j write failed.
Automated projection scheduling/outbox delivery remains HOLD.

## Temporal

The existing cognition worker remains unchanged except for connection
configuration. `TEMPORAL_API_KEY` is passed to the Temporal SDK and enables TLS
automatically; `TEMPORAL_TLS=true` supports TLS endpoints using another
credential mechanism. Infrastructure health uses the authenticated Temporal
SDK health RPC rather than a raw TCP-port probe.

## Object storage

`S3ObjectStorage` supports MinIO, S3 and compatible services. Default keys are
content-addressed. Explicit keys are write-once: a repeated upload with the same
SHA-256 is idempotent, while a different digest at the same key fails. File
uploads are streamed from a file handle rather than loaded entirely into
memory. Standard AWS credential-provider behavior is retained when custom
`OBJECT_STORAGE_*` credentials are not configured; temporary custom
credentials may include `OBJECT_STORAGE_SESSION_TOKEN`.

The adapter is available for evidence/artifact integration. Existing canonical
evidence persistence is not silently redirected in this PR; wiring specific
evidence byte classes to object storage remains an explicit follow-up HOLD.

## Health

```bash
python scripts/infra_healthcheck.py
```

Only configured services participate in `all_configured_healthy`. PostgreSQL,
Neo4j, Temporal and object storage are checked through their native clients.

## Production boundary

This repository work changes no production credentials, services, database
state, tenant assignment or deployment. Managed-service rollout remains a
separate deployment decision.

## Merge gate

Repository integration requires the protected control-policy and test checks to
pass on the exact final pull-request head. Passing repository CI does not imply
that managed production infrastructure has been configured or verified.
