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

## Cognitive-extension state machines

Domain-neutral (no commercial/opportunity fields), unlike the MOD-008 through MOD-015 machines above. Runtime enforcement lives in `brain/circadian.py`, `brain/executive.py`, `brain/theory_of_mind.py`, and `brain/motor.py`; schemas are registered under "Cognitive-extension objects" in `docs/spec/BRAIN_SCHEMA_REGISTRY.md`.

### Circadian phase state machine

Allowed states: `wake -> nrem -> rem -> nrem -> ... -> wake`, cycling NREM/REM while sleep pressure remains above `wake_threshold_pressure`, with `wake` re-entered either when pressure dissipates below threshold or via an explicit `force_wake` override.

Hard gates:
- sleep onset (`wake -> nrem`) requires both `pressure.ratio >= sleep_onset_pressure` AND `oscillator.wake_drive < 0.5` -- pressure alone or circadian phase alone is insufficient, matching real sleep-onset-latency behavior;
- `force_wake` is the only transition that can move directly from `nrem` or `rem` to `wake` without pressure having dissipated; it leaves residual pressure rather than clearing it, so an urgent-stimulus wake does not silently reset accumulated sleep debt;
- `encoding_rate_multiplier()`, `consolidation_rate_multiplier()`, and `dream_rate_multiplier()` are phase-gated outputs, not independently settable state -- they follow the phase, not the other way around.

Blocked transitions: `nrem -> wake` without either pressure dissipation or `force_wake`; `rem -> nrem` before `ultradian_period_ticks` has elapsed in the current stage (except via the pressure-dissipation exit).

### Executive control-resource state machine

Allowed states for `CognitiveControlResource`: `full -> partially_depleted -> depleted -> partially_depleted -> full`, a continuous resource (not discrete states) that only moves toward depletion via `spend()` and toward recovery via `recover()`.

Hard gates:
- `arbitrate()` may only return `override_succeeded=True` when `control.current >= cost` was true at spend time -- override success is never asserted independent of an actual resource check;
- a failed override attempt still spends whatever resource remained (`spend(control.current)`), so a failed override is never free; this is what produces the honest impulsive-choice fallback rather than a system that always claims control "would have" worked;
- `current` is clamped to `[0, capacity]`; recovery cannot exceed capacity and depletion cannot go negative.

Blocked transitions: `override_succeeded=True` while `control_cost > control.current` at time of check; `current` outside `[0, capacity]`.

### Theory-of-mind prediction-record state machine

Allowed states: `predicted -> resolved(correct)` or `predicted -> resolved(incorrect)`, one-way, per `PredictionRecord`.

Hard gates:
- `resolve_prediction()` is the only transition out of `predicted`; a record cannot be resolved twice or resolved before `record_prediction()` created it;
- agent `trust` updates only through the slow exponential blend in `resolve_prediction()` (`blend = 0.2`), never set directly from a single observation -- this is a deliberate hard gate against one surprising result overwriting an otherwise-reliable track record;
- `AttributedBelief` records require `evidence_refs` (enforced at construction in `attribute_belief()`); an unevidenced belief attribution cannot be created.

Blocked transitions: resolving a `PredictionRecord` with no prior `predicted_action`; setting `AgentModel.trust` directly from a single prediction outcome without the blend.

### Motor execution state machine

Allowed states: `governance_pending -> {blocked | approved} -> executed -> calibrated`, per `MotorExecutionService.execute()` call.

Hard gates:
- an action never reaches the effector (`executed`) unless `GovernanceGovernor.evaluate()` returned `allowed=True` first -- `governance_pending -> executed` directly is not a reachable transition;
- `calibrated` (the `MotorCalibration.update()` step) only runs after `executed` produces a real `actual_outcome` from the effector -- calibration is never applied to a predicted-but-unexecuted action;
- per-effector calibration gain is clamped to `[0.1, 3.0]` and per-trial step is clamped to `max_step`, so no single execution result can move calibration outside bounds or by more than the configured step.

Blocked transitions: `blocked -> executed` (governance block is terminal for that action); `executed` without a prior `allowed=True` governance decision.
