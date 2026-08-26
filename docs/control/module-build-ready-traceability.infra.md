# Infrastructure Canonical BUILD-READY Traceability Extension

Status: REVIEW-ONLY / HOLD for runtime modules.

This required canonical extension covers the infrastructure modules added by the
cloud-backend integration work. It does not replace the historical matrix or
the PR #126 tenant/RLS extension.

| Module path | Owner object | Schema | Runtime service | State machine | Fixtures / tests | Acceptance evidence | Audit events | GO/HOLD |
|---|---|---|---|---|---|---|---|---|
| brain/adapters/infra_health.py | configured infrastructure health | native client health results | infrastructure_status | configured -> native check -> healthy/degraded | tests/test_infra_adapters.py; protected test workflow | repository evidence present; managed-service production proof absent | INFRA_HEALTH_CHECKED | HOLD |
| brain/adapters/neo4j_projection.py | tenant-scoped derived graph projection | projection_id + tenant_scope | Neo4jProjection | explicit tenant scope -> replace scoped nodes/edges -> rebuildable materialization | tests/test_infra_adapters.py | repository isolation/consistency evidence present; managed Neo4j rollout absent | NEO4J_TENANT_PROJECTION_REBUILT | HOLD |
| brain/adapters/object_storage.py | immutable object bytes | ObjectRef + SHA-256 metadata | S3ObjectStorage | content hash -> conditional create -> same-digest idempotence or conflicting-key failure | tests/test_infra_adapters.py | repository immutability/streaming evidence present; evidence-pipeline routing absent | OBJECT_STORED_IMMUTABLY | HOLD |
| scripts/infra_healthcheck.py | operator infra verification command | infrastructure_status JSON | CLI | check configured services -> print -> zero/nonzero exit | protected test workflow | repository evidence present; production service execution absent | INFRA_HEALTH_CHECKED | HOLD |
| scripts/rebuild_neo4j_projection.py | tenant-scoped projection rebuild command | explicit tenant UUID + canonical graph rows | CLI | validate tenant -> select tenant rows -> scoped Neo4j replace -> report | tests/test_infra_adapters.py; protected test workflow | repository scope evidence present; production rebuild not executed | NEO4J_TENANT_PROJECTION_REBUILT | HOLD |

## Source preservation statement

PostgreSQL remains authoritative. Tenant/RLS enforcement from PR #144 is
preserved. Real-time dual writes, production managed-service rollout and
evidence-byte routing are explicitly retained as HOLD rather than being
silently claimed complete.
