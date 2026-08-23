# Brain State Machines

State transitions are governance controls.

## Opportunity states

Allowed: detected, evidence_pending, scored, watch, candidate_action_generated, approval_pending, approved, simulated_executed, outcome_pending, outcome_logged, learned, archived, blocked, killed.

Allowed transitions include detected -> evidence_pending -> scored -> watch or candidate_action_generated -> approval_pending -> approved -> simulated_executed -> outcome_pending -> outcome_logged -> learned -> archived.

Blocked transitions: detected -> approved, scored -> executed_without_approval, blocked -> external_action, outcome_logged -> major_learning_without_attribution.

## Candidate action states

Allowed: drafted, simulated, gated, approval_pending, approved, rejected, executed_simulated, outcome_pending, closed.

Blocked: drafted -> executed, gated_block -> approval_bypass, approval_pending -> external_send_without_approval.

## Evidence states

Allowed: captured, scored, admitted, quarantined, contradicted, archived.

Blocked: quarantined -> semantic_update, restricted -> formula_influence, corrupted -> belief_update.

## Learning states

Allowed: outcome_logged, prediction_resolved, attribution_pending, attribution_scored, reward_pain_created, graph_update_pending, graph_updated, review_required.

Blocked: outcome_logged -> reward_without_attribution, reward_pain_created -> graph_update_without_formula_run.

## Required transition record

Every transition must include trigger, required evidence, formula run if scored, actor, timestamp, audit event, and acceptance test reference.