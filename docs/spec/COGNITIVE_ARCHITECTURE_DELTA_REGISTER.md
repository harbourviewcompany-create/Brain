# Cognitive Architecture Delta Register

Classification vocabulary: ALREADY_COMPLETE, PARTIAL, CONCEPT_MISSING, SPEC_MISSING, CONTRACT_MISSING, SOURCE_MAP_MISSING, IMPLEMENTATION_MISSING, TEST_MISSING, EVIDENCE_MISSING, CONFLICTING, DEFERRED.

| Target | Concept | Spec | Contract | Runtime | Tests | Evidence | Current status |
|---|---|---|---|---|---|---|---|
| Cognitive Object Protocol | present | present | merged shared envelope | merged generic persistence | present | bounded | PARTIAL |
| Epistemic State | confidence/calibration/contradiction + multi-axis protocol state | present | present | merged protocol runtime | present | bounded | PARTIAL |
| Provenance Graph | source/evidence traceability + typed lineage | present | present | merged protocol runtime | present | bounded | PARTIAL |
| Lifecycle Framework | per-module state machines + shared transition envelope | present | present | merged protocol runtime | present | bounded | PARTIAL |
| Conflict Arbitration | contradiction/debate/executive surfaces + shared conflict object | present | present | partial integration | present | bounded | PARTIAL |
| Knowledge Gaps | curiosity + unknown mechanisms + KnowledgeGap | present | present | merged protocol runtime | present | bounded | PARTIAL |
| Cognitive Affordance | economic affordance/action candidates + CognitiveAffordance | present | present | merged protocol runtime | present | bounded | PARTIAL |
| Projection Boundary | action/governance gates + ProjectionDecision | present | present | merged protocol runtime | present | bounded | PARTIAL |
| Experience→Learning | outcomes/reward/attribution + LearningEvent + #139 automatic prediction/outcome attribution | present | present | merged | present | bounded | PARTIAL |
| Replay Standard | event sourcing + ReplayBundle | present | present | merged protocol runtime | present | bounded | PARTIAL |
| Developmental Plasticity | developmental runtime + DevelopmentalPlasticityDelta | present | present | partial integration | present | bounded | PARTIAL |
| Tenant/RLS isolation | tenant/auth + migrations 019–022 | present | present | repository implementation present | production-realistic CI added | production evidence missing | PARTIAL |
| Operator Observability | dashboards, secure operator boundary and observability | present | partial | partial | partial | production evidence missing | PARTIAL |

## Dependency rules

1. Protocol envelopes precede broad organ wiring.
2. Provenance, epistemic state and lifecycle metadata are shared concerns, not replacement modules.
3. Knowledge gaps feed curiosity; they do not replace curiosity.
4. Cognitive affordances feed planning/executive/action selection; they do not replace economic affordances.
5. Projection policy wraps existing governance gates rather than bypassing them.
6. Replay reads canonical event/persistent state and graph projections; it does not create a competing source of truth.
7. Developmental plasticity records changes; self-modification remains subject to benchmark, immune, rollback and approval controls.
8. Tenant/RLS production rollout requires an explicit release gate, separate migrator/runtime/worker roles and cross-tenant evidence; repository merge alone is insufficient.

## Integrated ancestry and remaining HOLDs

The previously separate PR #100/#104/#105/#108/#109/#110 ancestry is already incorporated into protected-main history and is no longer an unmerged dependency register. Theory of Mind, Executive Control and Affect are present on main; their remaining gap is broad protocol adapter/replay evidence, not PR adoption. Tenant/auth code and migrations 019–022 are also on main, but production application remains HOLD until role topology, migration hashes, two-tenant isolation, legacy-row ownership and deployment evidence pass the release gates.
