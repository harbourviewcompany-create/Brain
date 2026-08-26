# Cross-Cutting Cognitive Architecture Implementation Sequence

Phases sequence execution; they do not narrow preserved Brain scope.

1. Reconcile existing runtime/control surfaces and register deltas.
2. Define shared protocol envelope, epistemic state, provenance edge, transition, conflict, KnowledgeGap, CognitiveAffordance, ProjectionDecision, LearningEvent, ReplayBundle and DevelopmentalPlasticityDelta contracts.
3. Implement deterministic protocol services through the existing cognitive-object persistence layer.
4. Add state-transition validation and provenance continuity checks.
5. Add deterministic fixture for evidence→belief/gap→affordance→projection→outcome→learning→replay.
6. Add unit/integration/replay/invariant tests.
7. Extend machine-readable module/schema/formula/state/traceability/acceptance registries.
8. Add operator-surface specification for epistemic state, provenance, conflict/gap, affordance, projection, learning and replay.
9. Integrate adapters into existing belief, curiosity, memory, planning, action/governance and developmental services.
10. Preserve protected-main Theory of Mind, Executive Control and Affect implementations and add shared-protocol adapters only with per-organ replay evidence.
11. Preserve #139 automatic prediction creation and outcome attribution as the canonical runtime learning path; cross-cutting LearningEvent contracts must compose with it rather than replace it.
12. Preserve #141 durable edge reads while routing the Railway compatibility surface through the tenant-aware API boundary.
13. Release tenant/RLS migrations 019–022 only through the canonical migration runner after separate migrator/API/worker roles, non-owner/non-BYPASSRLS checks, two-tenant isolation, migration hashes/idempotence and legacy-row handling pass.
14. Produce production restart/deployment evidence before advancing any production-facing runtime row from HOLD.

## Current repository frontier

Steps 1–8 and a bounded integration into `CognitiveGrowthRuntime` are implemented. Protected-main cognitive organs, #139 learning and #141 edge reads are existing authority. Steps 9–10 remain partial where broad organ adapters are missing. Tenant/RLS release mechanics have production-realistic CI coverage, but actual production migration/application, durable tenant lifecycle administration, worker tenant-by-tenant scheduling, secure-operator deployment and production restart evidence remain HOLD.
