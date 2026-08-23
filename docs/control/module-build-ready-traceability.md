# Module BUILD-READY Traceability Matrix

Status: REVIEW-ONLY / HOLD for runtime modules.

This matrix expands the minimum traceability registry into a per-module readiness map. It does **not** mark runtime modules BUILD-READY. A module may only become BUILD-READY when every required field has concrete source and validation evidence.

Required fields for every module:

1. owner object
2. schema
3. runtime service
4. state machine
5. fixtures
6. tests
7. acceptance criteria
8. audit events
9. GO/HOLD status

## Readiness rule

A module is BUILD-READY only when all required fields are present and evidence-backed. Partial tests, partial schemas, or executable code alone are insufficient.

## Current module map

| Module path | Owner object | Schema | Runtime service | State machine | Fixtures / tests | Acceptance evidence | Audit events | GO/HOLD |
|---|---|---|---|---|---|---|---|---|
| apps/api/main.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| apps/operator/main.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| apps/worker/main.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| brain/adapters/cognition.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| brain/adapters/developmental_evidence_store.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/adapters/economic_store.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/adapters/learning_store.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/adapters/postgres.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/attention.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/attribution.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/beliefs.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/cognitive_state.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/contradiction.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/contradiction_queue.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/curiosity.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/cycle.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/debate.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/developmental/consolidation.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/evidence_store.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/global_workspace.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/higher_order_cognition.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/immune.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/improvement_experiments.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/metacognitive_optimization.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/module_genesis.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/plasticity.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/prediction_error.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/self_model.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/theory_registry.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/domain.py | partial | present | partial | missing | partial | missing | partial | HOLD |
| brain/dreaming.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/economic.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_atomic_lifecycles.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/economic_atomic_services.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/economic_attribution.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_capital.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_codec.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_compounding.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_conformance.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/economic_hard_gates.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_replay.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_runtime.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_sources.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_transaction.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/events.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/experiments.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/formulas.py | partial | present | partial | partial | partial | partial | partial | HOLD |
| brain/governance.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/homeostasis.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/hydrate.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/learning.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/memory.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/metabolism.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/money_spine.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/neuro/abstractions.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/neuro/multiscale.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/neuro/regions.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/ports.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/prediction.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/projections.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/protocol.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/replay.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/resources.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/reward.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/rewiring.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/runner.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/runtime.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/scheduler.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/schemas.py | partial | present | partial | partial | partial | partial | partial | HOLD |
| brain/theory_of_mind.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/working_memory.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| scripts/ingest_current_thread_archive.py | present | present | present | present | present | present | present | HOLD |
| scripts/validate_archive_manifest.py | present | present | present | present | present | present | present | HOLD |
| scripts/validate_build_ready_traceability.py | present | present | present | present | present | present | present | HOLD |
| scripts/validate_control_layer.py | present | present | present | present | present | present | present | HOLD |
| scripts/validate_pr_body.py | present | present | present | present | present | present | present | HOLD |

## Notes

- Traceability is mandatory. BUILD-READY is not automatic.
- Runtime modules remain HOLD until schema, state machine, fixtures, acceptance evidence, and audit events are complete.
- Control and archive validators may be GO for their own narrow function without implying Brain runtime readiness.
