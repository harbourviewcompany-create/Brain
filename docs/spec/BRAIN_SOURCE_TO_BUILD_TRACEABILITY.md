# Brain Source-to-Build Traceability

Status: GO for issues #3-#8.

This file maps preserved Brain source concepts to the implementation/control artifacts used by the agent execution pass.

| Concept family | Source basis | Module | Schema | Service | Formula | Test | Fixture | Dashboard | Acceptance |
|---|---|---|---|---|---|---|---|---|---|
| Source to signal | Brain loop: source → signal → evidence → belief | Source Registry | Source, Sensor, Signal | SourceRegistryService, PerceptionService | source_priority_score, attention_score | tests/test_schemas.py, tests/test_replay_harness.py | source_signal_evidence_belief | Source Console, Perception Inbox | ACC-001 |
| Formula runtime | Formula and equation corpus | Formula Registry | FormulaRun | FormulaRegistry | attention_score, reward_score, pain_score, graph_weight_update | tests/test_formulas.py | formula_run_attention_reward | Formula Audit Dashboard | ACC-002 |
| Belief truth maintenance | How the Brain Forms Beliefs | Belief and Truth Maintenance | EvidenceItem, Belief, Prediction | BeliefUpdateService, TruthMaintenanceService | bayesian_belief_update, brier_score | tests/test_replay_harness.py | source_signal_evidence_belief | Belief Ledger | ACC-003 |
| Approval-gated action | Governance / Risk and Trust | Action Simulation | CandidateAction, ApprovalRequest | ActionGateService, ApprovalQueueService | trust_adjusted_value | test_approval_gate_blocks_external_action | approval_gate_external_action | Approval Inbox | ACC-004 |
| Reward/pain rewiring | How the Brain Learns From Outcomes | Reward Pain Learning | Outcome, RewardEvent, PainEvent, GraphEdge | RewardPainService, GraphLearningService | reward_score, pain_score, graph_weight_update | test_reward_pain_reallocation_replay | outcome_reward_pain_learning | Learning Console | ACC-005 |
| Contradiction review | Contradictions and Open Questions | Contradiction Review | ContradictionReviewItem | ContradictionReviewService | contradiction_value | tests/test_contradiction_queue.py | contradiction_review | Contradiction Inbox | ACC-006 |
| Agent GO/HOLD control | Tests, Fixtures and Acceptance | Governance and Acceptance | AcceptanceReport | validate_agent_control | go_no_go_score | tools/validate_agent_control.py | acceptance_gate_go_hold | GO/HOLD Console | ACC-007 |

No row may be removed by agent preference. Any future module must extend this matrix rather than replacing it.
