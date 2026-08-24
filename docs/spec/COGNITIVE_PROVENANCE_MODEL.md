# Cognitive Provenance Model

Purpose: make cognitive causality reconstructable rather than merely explainable in prose.

## Canonical lineage
Observation/Source → Evidence → Percept/Inference → Belief/Hypothesis → Prediction/Goal/Decision → Simulation/Action → Outcome → PredictionError/Attribution → LearningEvent → Model/Weight/State change.

Not every path contains every node, but every derived state must link to its immediate parents and ultimately to evidence or an explicitly labeled internal/generated source.

## Provenance edge types
observed_from, extracted_from, inferred_from, supports, contradicts, retrieved_from, attended_because, generated_from, simulated_from, selected_over, authorized_by, executed_as, produced, resolved_by, attributed_to, learned_from, supersedes, revises.

## Required edge metadata
edge_id, from_id, to_id, edge_type, created_at, source_refs/evidence_refs, actor/service, confidence when inferential, formula_run_id where scored, transition/audit reference where state-changing.

## Invariants
- Graph projections are rebuildable; canonical event/persistence history remains authority.
- Derived cognition cannot become provenance-orphaned.
- Internal generation (dream, simulation, hypothesis) must be explicitly labeled and never masquerade as external evidence.
- Conflicting provenance paths are retained.
- Replay must be able to walk upstream from decision/action/outcome and downstream from evidence/source.