# Developmental Intelligence Build Queue

Status: issue-backed build-control queue to make the Brain grow and develop under evidence, replay, and governance.

This queue extends the existing Brain runtime beyond static modules. It does not replace open revenue, operator, or transaction work. It adds the developmental intelligence spine required for the Brain to become more capable over time.

## AGENT-008 Prediction Error and Development Pressure Runtime

Objective: implement prediction records, prediction error, calibration trace, and development pressure objects/services.

Files to create or modify:

- `brain/developmental/prediction_error.py`
- `tests/test_developmental_prediction_error.py`
- `tests/fixtures/brain/developmental_growth_loop.json`
- `reports/acceptance/AGENT-008-prediction-error-runtime.json`

Required tests:

- prediction_error_updates_attention
- calibration_trace_is_preserved
- development_pressure_prioritizes_learning

GO/HOLD: GO only when prediction error can change attention/curriculum through audited state transitions.

## AGENT-009 Plasticity, Rewiring and Pruning Runtime

Objective: implement evidence-bound cognitive edge strengthening, weakening, quarantine, pruning, and rollback.

Files to create or modify:

- `brain/developmental/plasticity.py`
- `tests/test_developmental_plasticity.py`
- `tests/fixtures/brain/plasticity_pruning_cycle.json`
- `reports/acceptance/AGENT-009-plasticity-pruning.json`

Required tests:

- reward_strengthens_edge
- pain_weakens_edge
- pruning_requires_evidence
- rewire_is_replayable_and_reversible

GO/HOLD: HOLD if any rewire lacks evidence, replay, or rollback.

## AGENT-010 Module Genesis and Maturity Runtime

Objective: create a module-birth workflow for new Brain structures that emerge from repeated unresolved patterns.

Files to create or modify:

- `brain/developmental/module_genesis.py`
- `tests/test_developmental_module_genesis.py`
- `tests/fixtures/brain/module_birth_acceptance_gate.json`
- `reports/acceptance/AGENT-010-module-genesis.json`

Required tests:

- module_hypothesis_requires_source_traceability
- module_birth_requires_schema_service_fixture_test
- module_activation_requires_acceptance_report
- module_retirement_preserves_history

GO/HOLD: HOLD if agents can activate a module by preference without acceptance evidence.

## AGENT-011 Global Workspace Proxy

Objective: implement attention-coalition competition and controlled broadcast to other modules.

Files to create or modify:

- `brain/developmental/global_workspace.py`
- `tests/test_developmental_global_workspace.py`
- `tests/fixtures/brain/workspace_competition_broadcast.json`
- `reports/acceptance/AGENT-011-global-workspace.json`

Required tests:

- workspace_winner_has_evidence
- suppressed_items_are_logged
- broadcast_records_consumers
- broadcast_does_not_claim_consciousness

GO/HOLD: HOLD if broadcast lacks supporting evidence or suppressed alternatives.

## AGENT-012 Sleep, Dream and Consolidation Runtime

Objective: implement offline simulation, rehearsal, memory compression, and rewire proposal generation.

Files to create or modify:

- `brain/developmental/consolidation.py`
- `tests/test_developmental_consolidation.py`
- `tests/fixtures/brain/sleep_consolidation_cycle.json`
- `reports/acceptance/AGENT-012-sleep-consolidation.json`

Required tests:

- dream_outputs_are_simulated
- dream_cannot_execute_external_action
- consolidation_preserves_provenance
- compression_does_not_delete_source_evidence

GO/HOLD: HOLD if dream outputs can bypass approval gates.

## AGENT-013 Cognitive Immune System

Objective: implement alerts, quarantine, contamination tracing, and recovery plans for unsafe cognition and unsafe growth.

Files to create or modify:

- `brain/developmental/immune.py`
- `tests/test_developmental_immune.py`
- `tests/fixtures/brain/immune_quarantine_recovery.json`
- `reports/acceptance/AGENT-013-cognitive-immune-system.json`

Required tests:

- approval_bypass_is_quarantined
- contaminated_source_is_blocked
- overconfidence_triggers_alert
- recovery_requires_evidence

GO/HOLD: HOLD if unsafe growth is not blocked and recoverable.

## AGENT-014 Self Model and Capability Ledger

Objective: implement a self-model that tracks capabilities, limits, uncertainty, learning debt, evidence gaps, fatigue/load, and confidence in internal claims.

Files to create or modify:

- `brain/developmental/self_model.py`
- `tests/test_developmental_self_model.py`
- `tests/fixtures/brain/self_model_capability_update.json`
- `reports/acceptance/AGENT-014-self-model.json`

Required tests:

- capability_claim_requires_evidence
- limitation_is_preserved
- learning_debt_affects_priority
- self_model_blocks_overclaiming

GO/HOLD: HOLD if the Brain can claim capability without evidence.

## AGENT-015 Unknown Mechanism and Theory Registry

Objective: implement registries for unknown mechanisms, speculative theories, open questions, and competing explanations.

Files to create or modify:

- `brain/developmental/theory_registry.py`
- `tests/test_developmental_theory_registry.py`
- `tests/fixtures/brain/unknown_mechanism_theory_competition.json`
- `reports/acceptance/AGENT-015-theory-unknown-registry.json`

Required tests:

- unknown_is_not_deleted
- theory_competition_preserves_alternatives
- speculative_status_is_explicit
- theory_promotion_requires_evidence

GO/HOLD: HOLD if uncertainty is hidden, flattened, or deleted.

## Queue-level acceptance

The developmental intelligence spine is GO only when AGENT-008 through AGENT-015 have:

- executable code;
- fixtures;
- deterministic replay evidence;
- tests;
- dashboard/operator surfaces;
- GO/HOLD acceptance reports;
- source-to-build traceability;
- immune and approval gate compliance.

Until then: HOLD for developmental intelligence implementation, GO for build-control specification.
