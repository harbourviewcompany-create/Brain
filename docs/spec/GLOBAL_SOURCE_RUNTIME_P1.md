# Global Source Runtime P1 — Durable Acquisition Spine

## Source authority

```yaml
source_record:
  id: SRC-BRAIN-GLOBAL-SOURCE-P1-20260827
  label: APPROVED
  source_type: instruction
  supplied_by: Tyler
  approval_statement: "Optimize this further"
  parent_source: docs/spec/ALWAYS_ON_PERSONAL_INTELLIGENCE_RUNTIME.md
  approved_action: Further engineer the always-on Brain toward persistent global perception and learning.
  boundaries_of_approval: Repository implementation and verification for this reversible build slice. Production migration application, Railway topology/config mutation, paid data providers, credentials, billing, and destructive database actions remain separate execution gates.
  go_hold_status: GO
```

## Why this slice exists

P0 made the cognitive sensory/cycle/learning path durable when PostgreSQL is configured. The next root continuity defect is external perception: connector source schedules and content-hash dedupe still live in process memory. A restart can therefore forget what was due, forget what was already observed, and re-fetch/re-enqueue old material. Multiple workers can also fetch the same source concurrently.

P1 turns external acquisition into a durable, provenance-first subsystem without narrowing the broader world-intelligence objective.

## Build slice

Build ID: `SLICE-GLOBAL-SOURCE-P1`

Owner objects:

- `IngestService`
- `PostgresConnectorRegistry`
- `source_connector_runtime_state`
- `source_connector_ingestion_runs`
- `source_connector_observations`

### Runtime contract

```text
configured source
    ↓
durable schedule + expiring lease
    ↓
fetch
    ↓
durable raw observation + provenance
    ↓
source-scoped dedupe
    ↓
durable sensory inbox
    ↓
cognitive cycle / learning
```

A fetched observation is persisted before sensory enqueue. If durable observation capture fails, that item is not silently promoted into cognition.

### Acquisition state machine

```text
source due
  → leased
  → ingestion run started
  → fetched
     → raw observation captured
        → enqueued
        → duplicate/corroboration accounted
     → run success | empty | partial
  → fetch/run failure
  → lease released by mark_fetch or expires automatically
  → next_due_at scheduled with backoff
```

### Dedupe semantics

Dedupe identity is `(source_id, content_hash)`, not global `content_hash`.

This is mandatory because the same claim independently observed from two sources is corroborating provenance. It must remain two source observations even when their content hashes match.

### Provenance contract

Every durable raw observation preserves at minimum:

- source identity
- connector item identity
- source URL
- content hash
- raw content
- claim
- observed time
- retrieved time
- confidence
- signal hints
- extracted entities
- ingestion run
- first/last seen time
- duplicate count
- sensory inbox id once enqueued

### Credential boundary

`source_connector_runtime_state.public_config` contains only non-secret parser/runtime configuration. Connector HTTP headers, bearer tokens, API keys, cookies, passwords and secrets are never serialized into the durable registry. Credential injection remains a runtime concern.

### Tenant boundary

Migration 024 follows the existing tenant/RLS foundation. System/global sources use `tenant_id is null` and require trusted-service context. Tenant-owned rows remain isolated by `current_brain_tenant_id()` or the separately audited trusted worker role. P1 does not introduce a tenant-by-tenant connector scheduler; it preserves the existing trusted-service transition boundary for later replacement.

## Requirements

| Requirement | Behavior | P1 state |
|---|---|---|
| REQ-SOURCE-P1-001 | Connector schedules survive process restart. | implemented |
| REQ-SOURCE-P1-002 | Concurrent workers cannot normally double-fetch a due source. | implemented with expiring DB lease |
| REQ-SOURCE-P1-003 | Raw observations are durable before sensory enqueue. | implemented |
| REQ-SOURCE-P1-004 | Dedupe survives restart. | implemented |
| REQ-SOURCE-P1-005 | Dedupe is source-scoped so independent corroboration survives. | implemented |
| REQ-SOURCE-P1-006 | `observed_at` and `retrieved_at` are both preserved. | implemented |
| REQ-SOURCE-P1-007 | Secrets are excluded from durable connector config and observation metadata. | implemented |
| REQ-SOURCE-P1-008 | Existing pre-024 deployments keep running and explicitly fall back to in-memory connector state until the migration is available. | implemented |
| REQ-SOURCE-P1-009 | RLS/tenant isolation applies to all new persistent acquisition tables. | implemented in migration; CI proof required |
| REQ-SOURCE-P1-010 | Existing RSS/HTTP ingestion and cognition behavior remains compatible. | tests/CI required |

## Migration and rollout behavior

Migration: `db/migrations/024_durable_connector_runtime.sql`.

Because migration 024 is above the tenant/RLS release boundary, applying it to production requires the repository's existing migration gates and audited runtime/worker role topology. Repository merge does not itself authorize or require a production database mutation.

`IngestService` capability-detects the migration tables. If they exist, it automatically binds to `PostgresConnectorRegistry`; if they do not, it keeps the existing in-memory connector runtime and emits a warning rather than crash-looping an older production deployment.

## Explicit non-completion / preserved next surfaces

P1 is not the complete global-intelligence system. The following remain required and are preserved rather than narrowed out:

- broad authoritative source-universe population across news, government, business, markets, sport, science, history, geography, geopolitics, health, law, employment, supply chains and culture;
- durable normalization bridge from raw connector observations into MOD-017 `source_registry_observations` with explicit source-authority mapping;
- bounded historical/backfill acquisition distinct from realtime polling;
- credential-provider abstraction for approved authenticated/paid sources;
- HTTP text, document/PDF, bulk dataset and other connector classes where approved;
- entity resolution, contradiction/corroboration graphing and temporal world-state maintenance;
- prediction/calibration convergence and outcome scoring;
- self-curriculum and benchmark-gated capability improvement;
- truthful Observatory coverage, freshness, lag, acquisition health and cognition-liveness metrics;
- canonical Railway production tracking current protected `main` and a dedicated continuously running worker topology.

## Acceptance evidence required before merge

- exact changed-file list;
- migration uniqueness and tenant/RLS checks;
- connector unit tests;
- source-scoped dedupe/corroboration test;
- provenance time test;
- durable-registry capability/fallback tests;
- full repository `test` and lint checks;
- production-container persistence gate;
- tenant-RLS release gate;
- Brain control-policy check;
- unresolved gaps and GO/HOLD status.

## Rollback

Revert the P1 merge. The runtime capability check allows code to operate without migration 024. If migration 024 has been applied, its additive tables may remain unused during rollback; destructive down-migration is not required for application rollback.

## Current status

`GO` for branch implementation and CI verification. `HOLD` for production migration/configuration changes until exact-head repository checks are green and production execution is explicitly authorized.
