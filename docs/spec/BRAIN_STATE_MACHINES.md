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

## MOD-008 Pressure state machine

Allowed states: `hypothesized -> supported -> active -> easing -> resolved`, with `invalidated` reachable from hypothesized, supported, active, or easing.

Hard gates:
- no PressureEvent may be created without evidence IDs;
- active pressure must remain evidence-backed and time-valid;
- decayed or contradicted pressure is re-verified, eased, resolved, or invalidated rather than silently retained.

## MOD-009 Money-path state machine

Allowed states: `generated -> verified -> qualified`, with `rejected` or `expired` terminal alternatives.

Hard gates:
- generated -> verified requires payer/payment-path review;
- verified -> qualified requires an identifiable verified payer and payment mechanism;
- stale or invalidated paths cannot remain qualified.

## MOD-010 Counterparty state machine

Allowed states: `discovered -> verified -> reachable -> active`, with `dormant` and `blocked` branches.

Hard gates:
- inferred roles are not equivalent to verified roles;
- ranked counterparties preserve selection explanations;
- blocked counterparties cannot be routed into consequential action.

## MOD-011 Opportunity portfolio state machine

Economic opportunities are scored with a registered formula run, then receive one of:

`ACT_NOW, VERIFY_FIRST, WATCH, ARCHIVE, KILL, AUTOMATE, DELEGATE, BUILD_AS_ASSET`.

Hard gates:
- no surfaced opportunity without formula trace;
- no opportunity without a qualified money path may pass hostile commercial review;
- operator-attention limits suppress lower-priority work without deleting provenance.

## MOD-012 Transaction-control state machine

Allowed states: `detected -> qualified -> protected -> approved -> contacted -> negotiation -> won/lost`, with `abandoned` available from pre-close stages.

Hard gates:
- detected -> approved is blocked;
- fee-sensitive external action requires jurisdiction review plus sufficient fee/origination control;
- protected -> approved requires explicit operator approval;
- legal enforceability is never inferred from a generic control flag.

## MOD-013 Source-rights state machine

Canonical source lifecycle: `candidate -> reviewed -> approved -> active -> degraded -> suspended/prohibited`.

Hard gates implemented by SourceRightsProfile:
- `PROHIBITED` forces collection, storage, and commercial-use permissions false;
- collection or storage denial blocks activation;
- terms-sensitive, scrape-sensitive, PII-sensitive, or regulated sources require explicit review notes before activation;
- every active source preserves jurisdiction and rights-profile linkage.

## MOD-014 Attribution and capital state machines

Attribution lifecycle: `provisional -> supported -> accepted`, with `disputed -> revised -> supported/accepted`.

Capital allocation lifecycle: `proposed -> operator_approved -> reserved/deployed -> reconciled`.

Hard gates:
- major economic learning is blocked below the configured attribution-confidence threshold;
- revenue and net profit are distinct fields;
- FX normalization requires an explicit positive rate, timestamp, source currency, target currency, and source key;
- capital allocation cannot exceed deployable capital and requires operator approval.

## MOD-015 Compounding and business-model state machine

Allowed states: `observed -> hypothesized -> validated -> build_candidate -> approved -> operating`, with `rejected` available before operation.

Hard gates:
- repeated-transaction patterns require multiple occurrences;
- validated offers require repeated evidence, multiple payers, and positive unit economics;
- product build candidates require validated offers, repeatable delivery, and positive expected margin;
- marketplace build candidates require buyer and seller liquidity plus successful and paid match proof;
- business-model build candidates require repeated evidence, multiple payers, expected net value, and a resource estimate.

## Required transition record

Every transition must include trigger, required evidence, formula run if scored, actor, timestamp, audit event, and acceptance test reference. Economic transitions persist in `public.economic_transitions`; economic score traces persist in `public.economic_formula_runs`.
