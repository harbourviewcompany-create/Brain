# Cognitive Affordance Model

Purpose: represent possible investigations, simulations, communications or actions without conflating them with the existing commercial `EconomicAffordance`.

## CognitiveAffordance
Fields: id, kind, target_refs, rationale, evidence_refs, goal_refs, expected_utility, expected_information_gain, uncertainty_reduction, risk, resource_cost, reversibility, novelty, time_sensitivity, governance_requirement, lifecycle_state, created_at.

Kinds may include observe, investigate, query, retrieve, simulate, test, ask_human, communicate, act_internal, propose_external_action, defer, ignore.

## Rules
- Detection does not authorize execution.
- External/consequential affordances must pass projection/governance.
- Economic affordances may map to CognitiveAffordance but retain their specialized semantics and money-path controls.
- Planning/executive control can rank affordances using separate score components rather than one opaque score.
- Outcome records feed back into future affordance estimates.

## Integration
Curiosity creates investigative affordances; knowledge gaps raise expected information gain; planning simulates affordances; executive control selects among them; governance controls externalization; outcomes and learning update future estimates.