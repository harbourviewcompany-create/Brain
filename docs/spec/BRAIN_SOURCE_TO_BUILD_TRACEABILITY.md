# Brain Source-to-Build Traceability

Status: required control artifact.

Purpose: map source concepts from `docs/brain-readable-concept-manual.md` to executable build targets. Agents must not build from memory or preference. Every implementation ticket must point to source basis, module, schema, service, formula, test, fixture, dashboard surface, and acceptance rule.

| Concept family | Source section | Module | Schemas | Services | Formulas | Tests | Fixtures | Dashboard | Acceptance |
|---|---|---|---|---|---|---|---|---|---|
| source_to_signal | Brain in One Loop / Source and Signal | Source Registry | Source, Sensor, Signal | SourceRegistryService, SensorRunnerService, PerceptionService | source_priority_score, attention_score | test_source_registry, test_perception_salience | source_signal_evidence_belief | Source Console, Perception Inbox | ACC-001 |
| belief_truth_maintenance | How the Brain Forms Beliefs | Belief and Truth Maintenance | EvidenceItem, Belief, Prediction | BeliefUpdateService, TruthMaintenanceService, CalibrationService | bayesian_belief_update, brier_score | test_belief_update_trace | source_signal_evidence_belief, contradiction_review | Belief Ledger | ACC-003 |
| approval_gated_action | Approval / Governance / Risk and Trust | Opportunity and Action Simulation | CandidateAction, ActionSimulation, ApprovalRequest | ActionSimulationService, ActionGateService, ApprovalQueueService | expected_utility, EVPI, EVSI, trust_adjusted_value | test_approval_gate_blocks_external_action | approval_gate_external_action | Approval Inbox | ACC-004 |
| reward_pain_rewiring | How the Brain Learns From Outcomes | Outcome, Reward, Pain and Rewiring | Outcome, RewardEvent, PainEvent, GraphEdge | OutcomeLoggerService, RewardPainService, GraphLearningService | reward_score, pain_score, graph_weight_update, regret_score | test_reward_pain_reallocation_replay | outcome_reward_pain_learning | Learning Console, Rewire Timeline | ACC-005 |
| contradictions_open_questions | Contradictions and Open Questions | Contradiction Review | ContradictionReviewItem | TruthMaintenanceService, ContradictionReviewService | contradiction_value | test_contradictions_are_preserved | contradiction_review | Contradiction Inbox | ACC-006 |
| agent_go_hold_control | Tests, Fixtures and Acceptance | Governance, Audit and Acceptance | AcceptanceReport | AcceptanceReportService | go_no_go_score | tools/validate_agent_control.py | acceptance_gate_go_hold | GO/HOLD Console | ACC-007 |

GO/HOLD: HOLD if any build task lacks a traceability row or if any traceability row lacks a test/fixture/acceptance rule, except intentional documentation-only entries explicitly marked `no_fixture_required`.
