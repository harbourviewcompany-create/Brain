# General Conflict Arbitration Model

Purpose: generalize existing contradiction/debate/executive surfaces without replacing them.

## Conflict classes
belief_conflict, evidence_conflict, perceptual_conflict, memory_conflict, prediction_conflict, causal_model_conflict, goal_conflict, value_conflict, action_policy_conflict, self_model_conflict, social_model_conflict, resource_conflict.

## Conflict object
A conflict records competing object IDs, conflict class, detection evidence, severity, unresolved dimensions, candidate resolutions, arbitration method, selected resolution if any, lifecycle state, provenance, and audit references.

## Arbitration principles
- Competing states coexist until explicitly resolved.
- Resolution can be partial or unresolved.
- Arbitration may request more evidence rather than force a winner.
- Resolution must not delete the losing representation; it changes status/weight/validity and preserves history.
- Executive-control implementations may resolve action-policy conflicts but do not automatically resolve underlying epistemic conflicts.
- Cognitive-immune checks may quarantine unsafe/contaminated candidates but do not convert quarantine into falsification.

## Arbitration inputs
Epistemic state, source/evidence provenance, temporal validity, causal support, prediction performance, goal/value constraints, affect/homeostatic state, control-resource availability, and governance rules.

## Outputs
resolution state, selected/retained candidates, rationale refs, evidence requests, follow-up knowledge gaps, and transition/audit events.