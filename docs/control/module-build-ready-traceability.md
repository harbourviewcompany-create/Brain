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
| apps/api/cognitive_organism_routes.py | cognitive organism API routes | organism route request models | register_cognitive_organism_routes | approval-gated route dispatch | tests/test_cognitive_organism_api.py | reports/acceptance/COGNITIVE-ORGANISM-V1.json | ORGANISM_COCKPIT_READ | HOLD |
| apps/api/main.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| apps/operator/main.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| apps/worker/main.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| brain/adapters/cognition.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| brain/adapters/developmental_evidence_store.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/adapters/economic_store.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/adapters/learning_store.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/adapters/postgres.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/agency.py | cognitive organism agency | AgencyAction, AgencyPolicy, AgencyTier | GovernedAgency | agency tier machine | tests/test_governed_agency.py | docs/cognitive-organism/AGENCY_BOUNDARIES.md | AGENCY_PROPOSED | HOLD |
| brain/attention.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/attribution.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/beliefs.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/cognitive_immune.py | cognitive organism immune system | QuarantineItem, QuarantineState | CognitiveImmuneSystem | quarantine state machine | tests/test_cognitive_immune.py | docs/cognitive-organism/COGNITIVE_IMMUNE_SYSTEM.md | IMMUNE_QUARANTINE | HOLD |
| brain/cognitive_organism.py | cognitive organism orchestrator | SelfStateSnapshot, OriginalIdea, AgencyAction | CognitiveOrganism | functional organism cycle | tests/test_cognitive_organism_replay.py | reports/acceptance/COGNITIVE-ORGANISM-V1.json | ORGANISM_CYCLE_REPLAYED | HOLD |
| brain/cognitive_state.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/contradiction.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/contradiction_queue.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/curiosity.py | cognitive organism curiosity | CuriosityTask, CuriosityState | CuriosityEngine | curiosity task machine | tests/test_curiosity_engine_v2.py | docs/cognitive-organism/COGNITIVE_ORGANISM_V1.md | CURIOSITY_TASK_GENERATED | HOLD |
| brain/cycle.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/debate.py | cognitive organism debate | InternalDebate, DebateArgument | CognitiveDebateSociety | debate state machine | tests/test_internal_debate_society.py | docs/cognitive-organism/COGNITIVE_ORGANISM_V1.md | INTERNAL_DEBATE_RECORDED | HOLD |
| brain/development.py | cognitive organism development timeline | DevelopmentEvent | DevelopmentTimeline | development event machine | tests/test_development_timeline.py | docs/cognitive-organism/COGNITIVE_ORGANISM_V1.md | DEVELOPMENT_EVENT_RECORDED | HOLD |
| brain/developmental/consolidation.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/evidence_store.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/global_workspace.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/higher_order_cognition.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/immune.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/improvement_cycle.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/improvement_experiments.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/metacognitive_optimization.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/module_genesis.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/plasticity.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/prediction_error.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/self_model.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/developmental/theory_registry.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/domain.py | partial | present | partial | missing | partial | missing | partial | HOLD |
| brain/dreaming.py | cognitive organism dream consolidation | DreamCycle, DreamInsight | DreamConsolidationEngine | dream cycle machine | tests/test_dream_consolidation.py | docs/cognitive-organism/DREAM_CONSOLIDATION.md | DREAM_INSIGHT_GENERATED | HOLD |
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
| brain/global_workspace.py | cognitive organism global workspace | GlobalWorkspaceItem, WorkspaceState | GlobalWorkspace | workspace admission machine | tests/test_global_workspace.py | docs/cognitive-organism/FUNCTIONAL_CONSCIOUSNESS_PROXY.md | WORKSPACE_ITEM_ADMITTED | HOLD |
| brain/goals.py | cognitive organism goal pressure | GoalState, GoalPressureEvent | GoalPressureSystem | goal pressure machine | tests/test_goal_pressure.py | docs/cognitive-organism/COGNITIVE_ORGANISM_V1.md | GOAL_PRESSURE_UPDATED | HOLD |
| brain/governance.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/homeostasis.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/hydrate.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/imagination.py | cognitive organism imagination | ImaginationRun | ImaginationEngine | imagination recombination machine | tests/test_imagination_originality.py | docs/cognitive-organism/ORIGINALITY_ENGINE.md | IMAGINATION_RECOMBINED | HOLD |
| brain/learning.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/memory.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/metabolism.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/money_spine.py | partial | partial | partial | partial | partial | missing | partial | HOLD |
| brain/neuro/abstractions.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/neuro/multiscale.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/neuro/regions.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/originality_engine.py | cognitive organism originality | OriginalIdea, IdeaState | OriginalityEngine | originality review machine | tests/test_imagination_originality.py | docs/cognitive-organism/ORIGINALITY_ENGINE.md | ORIGINAL_IDEA_GENERATED | HOLD |
| brain/ports.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/prediction.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/projections.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/protocol.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/replay.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/resources.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/reward.py | partial | partial | partial | missing | partial | missing | partial | HOLD |
| brain/rewiring.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/runner.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/runtime.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/scheduler.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| brain/schemas.py | partial | present | partial | partial | partial | partial | partial | HOLD |
| brain/self_model.py | cognitive organism self model | SelfStateSnapshot, SelfModelTransition | SelfModel | self model phase machine | tests/test_self_model.py | docs/cognitive-organism/FUNCTIONAL_CONSCIOUSNESS_PROXY.md | SELF_STATE_SNAPSHOT_CREATED | HOLD |
| brain/working_memory.py | partial | partial | partial | partial | partial | partial | partial | HOLD |
| scripts/ingest_current_thread_archive.py | partial | partial | partial | missing | partial | missing | missing | HOLD |
| scripts/validate_archive_manifest.py | partial | partial | partial | missing | partial | partial | missing | HOLD |
| scripts/validate_build_ready_traceability.py | partial | partial | partial | missing | partial | partial | missing | HOLD |
| scripts/validate_control_layer.py | partial | partial | partial | missing | partial | partial | missing | HOLD |
| scripts/validate_pr_body.py | partial | partial | partial | missing | partial | partial | missing | HOLD |

## Cognitive organism traceability note

The V1 cognitive organism modules are represented as controlled runtime paths with tests, fixtures, state machines and acceptance evidence. Their BUILD-READY status remains HOLD because production autonomy, live external actions, irreversible outreach and Tier 5 behavior remain explicitly out of scope.

## Developmental traceability note

The thirteen `brain/developmental/*` rows are included because those code paths exist and must be represented by the readiness validator. AGENT-020 integrates AGENT-017/018/019 into an end-to-end governed developmental cycle, but PROMOTE remains evidence-only and repository-wide BUILD-READY remains HOLD.

## Adapter traceability note

`brain/adapters/developmental_evidence_store.py` remains the PostgreSQL persistence boundary for developmental improvement evidence. Production migration execution is environment-specific and remains HOLD until deployed and verified.

## MOD-008 through MOD-015 repair traceability note

`brain/economic_conformance.py`, `brain/economic_atomic_services.py`, `brain/economic_atomic_lifecycles.py`, and `tools/validate_mod_008_015_conformance.py` remain controlled evidence paths. Their rows remain HOLD at the BUILD-READY matrix level because BUILD-READY is stricter than MOD-008 through MOD-015 atomic conformance.

## Neuroscience traceability note

`brain/neuro/abstractions.py`, `brain/neuro/multiscale.py` and `brain/neuro/regions.py` remain controlled neuroscience abstraction paths and do not imply biological equivalence or whole-system BUILD-READY.

## Source preservation statement

No source material is deleted, narrowed, or reinterpreted by this matrix. Unknowns are preserved as `missing`, `partial`, or `HOLD` instead of being hidden.

## Next expansion required

For each module, replace `partial` and `missing` with source-backed evidence paths only after the repo contains the corresponding owner object, schema, runtime service, state machine, fixtures, tests, acceptance criteria, audit events, and GO/HOLD report.
