# Cross-Cutting Cognitive Architecture Implementation Sequence

Phases sequence execution; they do not narrow preserved Brain scope.

1. Reconcile existing runtime/control/PR surfaces and register deltas.
2. Define shared protocol envelope, epistemic state, provenance edge, transition, conflict, KnowledgeGap, CognitiveAffordance, ProjectionDecision, LearningEvent, ReplayBundle and DevelopmentalPlasticityDelta contracts.
3. Implement deterministic in-memory protocol service plus persistence through existing PR #105 cognitive-object store.
4. Add state transition validation and provenance continuity checks.
5. Add deterministic fixture for evidence→belief/gap→affordance→projection→outcome→learning→replay.
6. Add unit/integration/replay/invariant tests.
7. Extend machine-readable module/schema/formula/state/traceability/acceptance/task registries.
8. Add operator-surface specification for epistemic state, provenance, conflict/gap, affordance, projection, learning and replay.
9. Integrate adapters into existing belief, curiosity, memory, planning, action/governance and developmental services.
10. Reconcile PR #108 Theory of Mind, #109 Executive Control and #110 Affect as consumers/producers without copying/conflicting implementations.
11. Add PostgreSQL schema/event persistence if generic PR #105 cognitive-object persistence proves insufficient for query/replay constraints; do not create parallel canonical storage.
12. Produce replay/acceptance evidence and only then advance individual integration rows from HOLD/PARTIAL.

## Current branch frontier
This branch executes steps 1–8 and a bounded integration into `CognitiveGrowthRuntime`. Steps 9–12 beyond that integration remain HOLD/PARTIAL until every affected organ has fixtures, replay evidence and acceptance proof.