# Brain Architecture

## Non-negotiable separation

The Brain is not an LLM. Models are replaceable cognitive instruments. The persistent Brain is the combination of its event history, evidence, identity model, beliefs, graph topology, learned weights, policies, outcomes, and resource state.

## Cloud topology

- **Supabase/PostgreSQL** — canonical event ledger, observations, evidence, beliefs, outcomes, auth, object references and pgvector retrieval.
- **Neo4j AuraDB** — materialized relationship topology and graph algorithms. PostgreSQL remains canonical so the graph can be rebuilt.
- **Temporal Cloud** — durable workflows: source sensing, research tasks, decay, dreams, debate, action follow-up, outcome collection and reprocessing.
- **Python workers** — cognitive organs and model adapters.
- **Vercel/Next.js control plane (next build slice)** — inspection, approvals, interventions, graph/belief exploration.
- **Object storage** — immutable raw artifacts and large evidence payloads.

## Event-sourced cognition

Never overwrite the past. Every meaningful state change creates a BrainEvent. Materialized tables are projections. This permits replay, alternate cognitive policies, rollback, counterfactual evaluation, and forensic audit.

## Cognitive organs

1. Sensing / ingestion
2. Salience and attention
3. Perception / extraction
4. Entity resolution
5. Episodic memory
6. Semantic memory
7. Working memory
8. Beliefs and uncertainty
9. Contradiction detection
10. Prediction
11. Rewiring / plasticity
12. Curiosity / information seeking
13. Offline recombination / dreaming
14. Internal debate
15. Planning
16. Action selection
17. Outcome sensing
18. Reward / punishment
19. Resource state
20. Capital allocation / capability growth
21. Governance / executive inhibition

## Unique architectural choices

### Attention is an internal market
Stimuli bid for finite compute using expected value, novelty, urgency, contradiction value, source quality, uncertainty reduction, noise probability, and operator burden.

### Contradiction is a first-class object
Conflicts do not disappear into a confidence average. They create investigation pressure and curiosity tasks.

### Dreams cannot become facts directly
Offline recombination can only create hypotheses. Dreams require new evidence before promotion.

### Rewiring is explicit
Every topology change is represented as a reversible RewireEvent, preserving the previous and new state and evidence responsible.

### Models are cortex, not identity
Multiple reasoning models can come and go. Brain continuity belongs to memory + topology + policies + event history, preventing vendor/model identity lock-in.
