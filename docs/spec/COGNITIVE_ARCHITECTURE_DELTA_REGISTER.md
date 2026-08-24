# Cognitive Architecture Delta Register

Classification vocabulary: ALREADY_COMPLETE, PARTIAL, CONCEPT_MISSING, SPEC_MISSING, CONTRACT_MISSING, SOURCE_MAP_MISSING, IMPLEMENTATION_MISSING, TEST_MISSING, EVIDENCE_MISSING, CONFLICTING, DEFERRED.

| Target | Concept | Spec | Contract | Runtime | Tests | Evidence | Current status |
|---|---|---|---|---|---|---|---|
| Cognitive Object Protocol | present across schema/module docs | new unified spec required | missing unified envelope | generic persistence exists on PR #105 | partial | partial | PARTIAL |
| Epistemic State | confidence/calibration/contradiction exist | multi-axis model missing | missing | partial in belief systems | partial | partial | PARTIAL |
| Provenance Graph | source/evidence traceability exists | lineage standard missing | typed edges missing | source_refs + graph primitives exist | partial | partial | PARTIAL |
| Lifecycle Framework | many state machines exist | cross-object contract missing | transition envelope missing | state services exist | partial | partial | PARTIAL |
| Conflict Arbitration | contradiction/debate/executive surfaces exist | general taxonomy missing | conflict contract missing | partial | partial | partial | PARTIAL |
| Knowledge Gaps | curiosity + unknown mechanisms exist | runtime ignorance model missing | missing | missing | missing | missing | IMPLEMENTATION_MISSING |
| Cognitive Affordance | economic affordance/action candidates exist | general affordance model missing | missing | missing | missing | missing | IMPLEMENTATION_MISSING |
| Projection Boundary | action/governance gates exist | explicit internal→external stages missing | missing | partial | partial | partial | PARTIAL |
| Experience→Learning | outcomes/reward/attribution exist | general lineage contract missing | missing | partial | partial | partial | PARTIAL |
| Replay Standard | event sourcing/replay-safe workflow exist | cognitive reconstruction standard missing | missing | partial | partial | partial | PARTIAL |
| Developmental Plasticity | developmental runtime exists | cross-object delta contract missing | missing | partial | partial | partial | PARTIAL |
| Operator Observability | dashboards and observability exist | cross-cutting surfaces missing | missing | partial | partial | partial | PARTIAL |

## Dependency rules

1. Protocol envelopes precede broad organ wiring.
2. Provenance, epistemic state and lifecycle metadata are shared concerns, not modules.
3. Knowledge gaps feed curiosity; they do not replace curiosity.
4. Cognitive affordances feed planning/executive/action selection; they do not replace economic affordances.
5. Projection policy wraps existing governance gates rather than bypassing them.
6. Replay reads canonical event/persistent state and graph projections; it does not create a competing source of truth.
7. Developmental plasticity records changes; any self-modification remains subject to existing benchmark, immune, rollback and approval controls.

## Unmerged dependency register

- PR #105: dependency/base for generic cognitive persistence and growth runtime.
- PR #108: Theory of Mind; future consumer/producer of epistemic/provenance/conflict contracts.
- PR #109: Executive Control; future arbitration implementation surface.
- PR #110: Affect Appraisal; future epistemic/attention/plasticity input surface.
- Tenant PR stack #100/#104: orthogonal persistence isolation work; this branch does not supersede it.