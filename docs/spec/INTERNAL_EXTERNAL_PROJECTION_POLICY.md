# Internal-to-External Cognitive Projection Policy

Purpose: enforce the distinction between internal cognition and external expression/action.

## Projection stages
internal → candidate → deliberated → governance_pending → approved/rejected → externalized/closed.

## Internal-only classes by default
Dream content, counterfactual simulations, unreviewed hypotheses, unresolved conflicts, low-support beliefs, raw memory retrievals, private self-model state, cognitive-immune quarantine, knowledge gaps, and generated plans are internal unless explicitly projected.

## Projection decision
A projection decision records content/object refs, target channel/action, epistemic state, evidence/provenance refs, sensitivity/risk, reversibility, governance requirement, approval refs, state and timestamps.

## Hard gates
- No internal object directly executes consequential external action.
- Approval remains required wherever existing Brain governance requires it.
- Simulation/dream/hypothesis origin must remain visible through provenance.
- Projection cannot transform uncertainty into certainty.
- Rejected/blocked projections remain auditable.
- Existing ActionGateService/CognitiveImmuneService remain enforcement surfaces; this policy does not bypass them.

## Externalization outputs
Communication, API mutation, connector action, spend, transaction, publication, outreach, deployment, repository mutation or other consequential effects must retain the projection/governance lineage when performed by Brain runtime.