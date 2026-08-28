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
| apps/api/cognitive_organism_routes.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| apps/api/cognition_cron_routes.py | partial | partial | present | present | present | partial | missing | HOLD |
| apps/api/inline_cognition.py | partial | partial | present | present | present | missing | partial | HOLD |
| apps/api/main.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| apps/operator/main.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| apps/worker/main.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| brain/adapters/brain_store.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/adapters/cognition.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| brain/adapters/cognitive_object_store.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/adapters/developmental_evidence_store.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/adapters/economic_store.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/adapters/learning_store.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/adapters/postgres.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/adapters/revenue_store.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/affect.py | partial | present | partial | missing | present | missing | present | HOLD |
| brain/agency.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/attention.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/attribution.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/beliefs.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/benchmarks.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/circadian.py | partial | present | partial | present | present | missing | present | HOLD |
| brain/cognition_lease.py | present | present | present | present | present | missing | partial | HOLD |
| brain/cognitive_immune.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/cognitive_organism.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/cognitive_state.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/connectors/http_client.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/connectors/http_json.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/connectors/protocol.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/connectors/revenue_adapter.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/connectors/rss.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/connectors/service.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/connectors/store.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/contradiction.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/contradiction_queue.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/curiosity.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/cycle.py | partial | partial | partial | partial | present | missing | partial | HOLD |
| brain/debate.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/development.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/developmental/cognitive_extension_curriculum.py | partial | present | present | present | present | present | missing | HOLD |
| brain/developmental/consolidation.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/evidence_store.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/developmental/global_workspace.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/higher_order_cognition.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/immune.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/improvement_cycle.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/developmental/improvement_experiments.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/developmental/metacognitive_optimization.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/developmental/module_genesis.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/plasticity.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/prediction_error.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/sandbox.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/self_model.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/theory_registry.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/domain.py | partial | present | partial | missing | partial | missing | partial | HOLD |
| brain/dreaming.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/economic.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_atomic_lifecycles.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/economic_atomic_services.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/economic_attribution.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_capital.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_codec.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_compounding.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_conformance.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/economic_hard_gates.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_replay.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_runtime.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_sources.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/economic_transaction.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/endogenous.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/events.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/executive.py | partial | present | partial | partial | present | missing | present | HOLD |
| brain/experiments.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/formulas.py | partial | present | partial | partial | partial | partial | partial | HOLD |
| brain/generalization.py | partial | present | present | missing | present | partial | partial | HOLD |
| brain/global_workspace.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/goals.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/governance.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/growth_runtime.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/heartbeat.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/hedonic.py | partial | present | partial | missing | present | missing | present | HOLD |
| brain/homeostasis.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/hydrate.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/imagination.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/learning.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/memory.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/memory_systems.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/metabolism.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/mind_runtime.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/model_cortex.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/money_spine.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/motor.py | partial | present | partial | partial | present | missing | present | HOLD |
| brain/neuro/abstractions.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/neuro/memory_systems.py | partial | partial | partial | missing | partial | partial | partial | HOLD |
| brain/neuro/multiscale.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/neuro/regions.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/observability.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/originality_engine.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/perception.py | partial | present | partial | missing | present | missing | present | HOLD |
| brain/planning.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/ports.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/prediction.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/projections.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/protocol.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/reasoning.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/replay.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/resources.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/reward.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/rewiring.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/runner.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/runtime.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/scheduler.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/schemas.py | partial | present | partial | partial | partial | partial | partial | HOLD |
| brain/security.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/self_model.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/sensory_inbox.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/source_intelligence.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/theory_of_mind.py | partial | present | partial | partial | present | missing | present | HOLD |
| brain/working_memory.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/world_model.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| scripts/ingest_current_thread_archive.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| scripts/run_ingest.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| scripts/start_thinking.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| scripts/validate_archive_manifest.py | partial | partial | partial | missing | partial | partial | missing | HOLD |
| scripts/validate_build_ready_traceability.py | partial | partial | partial | missing | partial | partial | missing | HOLD |
| scripts/validate_control_layer.py | partial | partial | partial | missing | partial | partial | missing | HOLD |
| scripts/validate_pr_body.py | partial | partial | partial | missing | partial | partial | missing | HOLD |
| tools/validate_agent_control.py | partial | partial | partial | missing | partial | partial | missing | HOLD |
| tools/validate_mod_008_015_conformance.py | partial | partial | partial | missing | partial | partial | partial | HOLD |

## Developmental traceability note

The `brain/developmental/*` rows are included because those code paths exist and must be represented by the readiness validator. Their `partial` values and `HOLD` status are deliberate. They are traced to `docs/spec/BRAIN_DEVELOPMENTAL_INTELLIGENCE_ARCHITECTURE.md` through `docs/control/source-requirement-registry.json`; this traceability repair does **not** assert that the developmental modules are fully conformant or BUILD-READY.

## Source preservation statement

This matrix merges rows independently added on `main` (Cognitive Organism modules, MOD-016 source intelligence, control-plane wiring, and related additions) with rows added by the affect/executive/circadian/theory-of-mind/hedonic/sensorimotor cognitive-extension work, taking the union of both sets across repeated merges rather than one side overwriting the other. NEURO-007 adds `brain/neuro/memory_systems.py` as HOLD without deleting or narrowing existing rows. No source material is deleted, narrowed, or reinterpreted by these merges. No runtime module is marked BUILD-READY by this matrix. Unknowns remain visible as `missing`, `partial`, or `HOLD`.

## Next expansion required

For each module, replace `partial` and `missing` with source-backed evidence paths only after the repo contains the corresponding owner object, schema, runtime service, state machine, fixtures, tests, acceptance criteria, audit events, and GO/HOLD report.
