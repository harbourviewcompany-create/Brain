# Developmental Intelligence Build Queue

Status: implemented for AGENT-008 through AGENT-015. This queue remains active as the control surface for future developmental expansion.

This queue extends the Brain runtime beyond static modules. It adds the developmental intelligence spine required for the Brain to become more capable over time under evidence, replay, immune review, self-model limits, and approval governance.

## Implemented tickets

| Ticket | Runtime | Code | Tests | Fixture | Acceptance |
|---|---|---|---|---|---|
| AGENT-008 | Prediction error and development pressure | `brain/developmental/prediction_error.py` | `tests/test_developmental_prediction_error.py` | `tests/fixtures/brain/developmental_growth_loop.json` | `reports/acceptance/AGENT-008-prediction-error-runtime.json` |
| AGENT-009 | Plasticity, rewiring and pruning | `brain/developmental/plasticity.py` | `tests/test_developmental_plasticity.py` | `tests/fixtures/brain/plasticity_pruning_cycle.json` | `reports/acceptance/AGENT-009-plasticity-pruning.json` |
| AGENT-010 | Module genesis and maturity | `brain/developmental/module_genesis.py` | `tests/test_developmental_module_genesis.py` | `tests/fixtures/brain/module_birth_acceptance_gate.json` | `reports/acceptance/AGENT-010-module-genesis.json` |
| AGENT-011 | Global workspace proxy | `brain/developmental/global_workspace.py` | `tests/test_developmental_global_workspace.py` | `tests/fixtures/brain/workspace_competition_broadcast.json` | `reports/acceptance/AGENT-011-global-workspace.json` |
| AGENT-012 | Sleep, dream and consolidation | `brain/developmental/consolidation.py` | `tests/test_developmental_consolidation.py` | `tests/fixtures/brain/sleep_consolidation_cycle.json` | `reports/acceptance/AGENT-012-sleep-consolidation.json` |
| AGENT-013 | Cognitive immune system | `brain/developmental/immune.py` | `tests/test_developmental_immune.py` | `tests/fixtures/brain/immune_quarantine_recovery.json` | `reports/acceptance/AGENT-013-cognitive-immune-system.json` |
| AGENT-014 | Self-model and capability ledger | `brain/developmental/self_model.py` | `tests/test_developmental_self_model.py` | `tests/fixtures/brain/self_model_capability_update.json` | `reports/acceptance/AGENT-014-self-model.json` |
| AGENT-015 | Unknown mechanism and theory registry | `brain/developmental/theory_registry.py` | `tests/test_developmental_theory_registry.py` | `tests/fixtures/brain/unknown_mechanism_theory_competition.json` | `reports/acceptance/AGENT-015-theory-unknown-registry.json` |

## Runtime-level acceptance

The developmental intelligence spine is GO for V0 implementation because AGENT-008 through AGENT-015 now have executable code, fixtures, tests, operator surface specification, and GO/HOLD acceptance reports.

## Hard gates that remain permanent

- No external action without approval.
- No simulation can execute real-world action.
- No module activation without schema, service, fixture, test, replay and acceptance evidence.
- No source activation without rights classification and provenance.
- No capability claim without evidence, tests and acceptance references.
- No contradiction deletion.
- No uncertainty hiding.
- No developmental rewire without evidence and rollback.
- No claim that the full Brain is complete without module-by-module implementation evidence.
- No claim that the Brain is more intelligent than any existing system without benchmark evidence.

## Next developmental expansion queue

Future agents should extend this spine with richer multi-scale cognitive maps, brain-region translation layers, causal world-model learning, curriculum self-design, benchmark-driven metacognition, developmental staging, and long-horizon self-improvement dashboards. Each expansion must follow the same rule: schema + service + state machine + fixture + replay + test + dashboard + acceptance report.
