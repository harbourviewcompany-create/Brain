# DATA_CLASSIFICATION_MATRIX

Status: PR 1 discovery matrix. Documentation only. No RLS or schema changes are authorized by this file.

## Classification labels

- Public-safe
- Tenant-private
- Tenant-sensitive
- Payment-sensitive
- Webhook-sensitive
- Source/evidence-sensitive
- Agent-prompt-sensitive
- Agent-output-sensitive
- Credential/secret
- System-admin-only
- Audit-only
- Export-restricted
- Unknown

## Actual table/data classification from inspected migrations

| Table/surface | Source | Current tenant field observed | Classification | Risk | PR closure |
|---|---|---:|---:|---:|---:|
| `brain_events` | `db/migrations/001_init.sql` | No | Audit-only / system cognitive ledger | Critical if tenant use begins | PR 3 |
| `sources` | `db/migrations/001_init.sql` | No | Source/evidence-sensitive | High | PR 3/7 |
| `observations` | `db/migrations/001_init.sql` | No | Source/evidence-sensitive / export-restricted | High | PR 3/7 |
| `evidence` | `db/migrations/001_init.sql` | No | Source/evidence-sensitive | High | PR 3/7 |
| `entities` | `db/migrations/001_init.sql` | No | Tenant-sensitive | High | PR 3 |
| `beliefs` | `db/migrations/001_init.sql` | No | Tenant-private / tenant-sensitive | High | PR 3/4 |
| `belief_evidence` | `db/migrations/001_init.sql` | No | Tenant-sensitive | High | PR 3 |
| `graph_nodes` | `db/migrations/001_init.sql` | No | Tenant-sensitive | High | PR 3/4 |
| `graph_edges` | `db/migrations/001_init.sql` | No | Tenant-sensitive | High | PR 3/4 |
| `rewire_events` | `db/migrations/001_init.sql` | No | Audit-only / tenant-sensitive | High | PR 3/10 |
| `actions` | `db/migrations/001_init.sql` | No | Tenant-sensitive / external-action-sensitive | Critical | PR 3/5 |
| `outcomes` | `db/migrations/001_init.sql` | No | Tenant-sensitive / reward-sensitive | Critical | PR 3/10 |
| `memory_items` | `db/migrations/002_cognitive_runtime.sql` | No | Agent-output-sensitive / tenant-sensitive | Critical | PR 3/6/7 |
| `bitemporal_facts` | `db/migrations/002_cognitive_runtime.sql` | No | Tenant-sensitive | High | PR 3 |
| `neuromodulator_snapshots` | `db/migrations/002_cognitive_runtime.sql` | No | System cognitive state | Medium | PR 3/10 |
| `homeostatic_snapshots` | `db/migrations/002_cognitive_runtime.sql` | No | System cognitive/resource state | Medium | PR 3/7 |
| `cognitive_tasks` | `db/migrations/002_cognitive_runtime.sql` | No | Agent-output-sensitive / job-sensitive | Critical | PR 3/6 |
| `cognitive_experiments` | `db/migrations/002_cognitive_runtime.sql` | No | Agent-output-sensitive / experiment-sensitive | High | PR 3/10 |
| `cognitive_experiment_results` | `db/migrations/002_cognitive_runtime.sql` | No | Agent-output-sensitive / evaluation-sensitive | High | PR 3/10 |
| `projection_checkpoints` | `db/migrations/002_cognitive_runtime.sql` | No | System-admin-only | Medium | PR 3/6 |

## Environment/config classification

| Name | Observed source | Classification | Notes |
|---|---|---:|---|
| `DATABASE_URL` | `.env.example`, API/worker/operator source | Credential/secret | Must not be exposed to clients. |
| `NEO4J_URI` | `.env.example` | Credential/connection metadata | Treat as secret-adjacent. |
| `NEO4J_USER` | `.env.example` | Credential/secret | Must not be exposed. |
| `NEO4J_PASSWORD` | `.env.example` | Credential/secret | Must not be exposed. |
| `TEMPORAL_ADDRESS` | `.env.example` | Credential/connection metadata | Treat as secret-adjacent. |
| `TEMPORAL_NAMESPACE` | `.env.example` | System config | Not client-exposed. |
| `BRAIN_EXTERNAL_ACTIONS_ENABLED` | `.env.example` | Safety/governance config | Must be fail-safe. |
| `BRAIN_API_KEY` | `apps/api/main.py` | Credential/secret | Missing from `.env.example`; PR 1 notes only. |
| `BRAIN_WORKER_MODE` | `apps/worker/main.py` | Runtime config | Missing from `.env.example`; PR 1 notes only. |

## Planned sensitive surfaces from Brain corpus

These are registry-only until real tables/routes exist.

| Surface | Classification | Status |
|---|---:|---:|
| `webhook_events` | Webhook-sensitive | Registry-only |
| `payments` | Payment-sensitive | Registry-only or not yet confirmed in inspected migrations |
| `refund_events` | Payment-sensitive | Registry-only |
| `invoice_records` | Payment-sensitive | Registry-only |
| `subscription_events` | Payment-sensitive | Registry-only |
| `fulfillment_jobs` | Tenant-sensitive / artifact-sensitive | Registry-only |
| `exports` | Export-restricted | Registry-only |
| `file_metadata` | Export-restricted / tenant-sensitive | Registry-only |
| `working_memory_sessions` | Agent-output-sensitive | Registry-only |
| `decision_explanations` | Audit-only / tenant-sensitive | Registry-only |
| `self_model_snapshots` | System-admin/tenant-admin-sensitive | Registry-only |
| `idempotency_keys` | System/internal | Registry-only |
| `outbox_messages` | System/internal | Registry-only |
| `dead_letters` | System/internal / sensitive payload risk | Registry-only |

## Required enforcement later

- Every tenant-owned table needs explicit tenant ownership or a formally documented global/system scope.
- Every exportable field needs an allowlist and role mapping.
- Raw observations/evidence/memory/prompt/output data must be redacted from logs and exports by default.
- API-key auth is insufficient for multi-tenant field-level access.

## GO/HOLD

GO:

- Use this matrix to scope PR 2 and PR 3.

HOLD:

- Any RLS/policy implementation until PR 2 tenant/auth model is designed.
