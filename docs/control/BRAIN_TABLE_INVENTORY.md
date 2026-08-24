# BRAIN_TABLE_INVENTORY

Status: PR 1 table inventory from inspected migrations. Documentation only.

## Actual tables found

| Table | Source | Current role | Tenant field observed | Classification | Risk | Next PR |
|---|---|---|---:|---|---:|---:|
| `brain_events` | `db/migrations/001_init.sql` | Canonical event ledger | No | Canonical, append-only intended | High | PR 3 |
| `sources` | `db/migrations/001_init.sql` | Source registry | No | Canonical | High | PR 3/7 |
| `observations` | `db/migrations/001_init.sql` | Raw/embedded observations | No | Canonical | High | PR 3/7 |
| `evidence` | `db/migrations/001_init.sql` | Claims/evidence ledger | No | Canonical | High | PR 3 |
| `entities` | `db/migrations/001_init.sql` | Entity records | No | Canonical | High | PR 3 |
| `beliefs` | `db/migrations/001_init.sql` | Belief ledger | No | Canonical | High | PR 3/4 |
| `belief_evidence` | `db/migrations/001_init.sql` | Belief/evidence relation | No | Canonical | High | PR 3 |
| `graph_nodes` | `db/migrations/001_init.sql` | Graph tissue nodes | No | Canonical | High | PR 3/4 |
| `graph_edges` | `db/migrations/001_init.sql` | Graph tissue edges | No | Canonical | High | PR 3/4 |
| `rewire_events` | `db/migrations/001_init.sql` | Rewiring audit/event log | No | Canonical | High | PR 3/10 |
| `actions` | `db/migrations/001_init.sql` | Action proposals/governance | No | Canonical but under-scoped | Critical | PR 5 |
| `outcomes` | `db/migrations/001_init.sql` | Outcome/reward input | No | Canonical but under-scoped | Critical | PR 10 |
| `memory_items` | `db/migrations/002_cognitive_runtime.sql` | Sensory/working/episodic/semantic/procedural/prospective memory | No | Canonical | Critical | PR 3/6/10 |
| `bitemporal_facts` | `db/migrations/002_cognitive_runtime.sql` | Time-aware facts | No | Canonical | High | PR 3 |
| `neuromodulator_snapshots` | `db/migrations/002_cognitive_runtime.sql` | Cognitive modulation snapshot | No | Canonical | Medium | PR 10 |
| `homeostatic_snapshots` | `db/migrations/002_cognitive_runtime.sql` | Homeostasis/resource state | No | Canonical | Medium | PR 7/10 |
| `cognitive_tasks` | `db/migrations/002_cognitive_runtime.sql` | Task queue/cognition scheduler | No | Canonical | Critical | PR 6 |
| `cognitive_experiments` | `db/migrations/002_cognitive_runtime.sql` | Experiment registry | No | Canonical | High | PR 10/V1 |
| `cognitive_experiment_results` | `db/migrations/002_cognitive_runtime.sql` | Experiment result ledger | No | Canonical | High | PR 10/V1 |
| `projection_checkpoints` | `db/migrations/002_cognitive_runtime.sql` | Projection/replay checkpoint | No | Canonical | Medium | PR 6 |

## Security hardening observed

`003_cognitive_security_hardening.sql` enables RLS and revokes direct `anon`/`authenticated` grants for the listed cognitive tables. It also creates an append-only mutation prevention trigger for `brain_events` update/delete.

This is a useful hardening layer, but it is not tenant isolation. No tenant ownership model was observed in inspected migrations.

## Migration naming concern

The migration list contains both:

- `006_money_spine.sql`
- `006_working_memory_predictions_learning.sql`

This duplicate numeric prefix must be reconciled before migration ordering can be trusted.

## Corpus/registry-only table concepts not found in inspected migrations

| Table concept | Status | Why retained |
|---|---:|---|
| `tenants` | Missing-from-repo | Required for multi-tenancy. |
| `memberships` | Missing-from-repo | Required for role-gated tenant access. |
| `tenant_invites` | Missing-from-repo | Required for invite lifecycle. |
| `audit_events` | Missing/under-confirmed | Required for append-only governance beyond `brain_events`. |
| `idempotency_keys` | Missing-from-repo | Required for webhooks/outcomes/jobs/reward propagation. |
| `webhook_events` | Missing-from-repo | Required before live payments. |
| `payments` | Missing/under-confirmed in inspected migrations | Required before payment workflow. |
| `refund_events` | Missing-from-repo | Required for payment reversal. |
| `invoice_records` | Missing-from-repo | Deferred unless B2B billing implemented. |
| `subscription_events` | Missing-from-repo | Deferred unless recurring billing implemented. |
| `fulfillment_jobs` | Missing-from-repo | Required before automated fulfillment. |
| `exports` | Missing-from-repo | Required for export controls. |
| `file_metadata` | Missing-from-repo | Required for object storage isolation. |
| `outbox_messages` | Missing-from-repo | Required for durable external effects. |
| `dead_letters` | Missing-from-repo | Required for safe job/webhook failure handling. |
| `service_circuit_breakers` | Missing-from-repo | Required for external adapter resilience. |
| `belief_history` | Missing-from-repo | Required for immutable belief versioning. |
| `capital_reallocation_audit` | Missing-from-repo | Required for capital decision audit. |
| `working_memory_sessions` | Missing-from-repo as dedicated table | Existing `memory_items` covers working memory kind, but not session protocol. |
| `decision_explanations` | Missing-from-repo | Required for WHY/explainability API. |
| `self_model_snapshots` | Missing-from-repo | Required for Meta Brain self-model. |

## GO/HOLD

GO:

- Use actual table inventory for PR 2/3 design.

HOLD:

- Runtime table changes.
- Migration work.
- Treating RLS hardening as tenant isolation.
