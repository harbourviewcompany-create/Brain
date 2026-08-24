# Ignorance and Curiosity Model

Purpose: make ignorance first-class runtime state and connect it to the existing curiosity system.

## Knowledge-gap classes
UNKNOWN, UNCERTAIN, UNDEROBSERVED, CONTRADICTED, UNTESTED, UNEXPLAINED, UNCALIBRATED, MODEL_GAP, MECHANISM_UNKNOWN.

## KnowledgeGap object
Required: id, gap_type, target_refs, statement/description, detected_at, lifecycle_state, epistemic_state, evidence_refs, expected_information_gain, importance, downstream_dependency_count, investigation_cost, priority_score, curiosity_task_refs.

## Priority logic
The runtime may rank gaps using importance, uncertainty, downstream dependency count, expected information gain, novelty/time sensitivity, and investigation cost. Any consequential priority score must retain its component trace.

## Integration
- Curiosity consumes high-value KnowledgeGap objects rather than generating only free-form questions.
- Unknown biological mechanisms link to MOD-NEURO-004 rather than claiming a solution.
- Contradicted gaps may be created from the conflict system.
- Replay records why a curiosity task was generated.
- Resolution may be partial; evidence can reopen a gap.

## Guardrails
A gap is not evidence. A hypothesis generated to resolve a gap is not a fact. `MECHANISM_UNKNOWN` cannot be silently converted into a biological-equivalence claim.