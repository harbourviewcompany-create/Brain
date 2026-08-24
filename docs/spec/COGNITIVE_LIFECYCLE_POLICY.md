# Cognitive Lifecycle Policy

Existing module state machines remain authoritative. This policy defines the shared transition envelope and common lifecycle expectations.

## Shared transition record
Every state change must preserve: object_id/kind, from_state, to_state, trigger, required evidence/provenance, formula run where scored, actor/service, timestamp, audit event, reversible flag, rollback/supersession reference, and acceptance-test reference where governed.

## Common lifecycle families
Hypothesis: generated → supported/challenged → testing → provisionally_accepted/falsified/superseded → archived.
Memory: encoded → labile → consolidated → reinforced/decaying → dormant/reactivated → reconsolidated.
Goal: generated → evaluated → adopted → planned → active → blocked → satisfied/abandoned.
Conflict: detected → characterized → arbitration_pending → resolved/unresolved → reopened/archived.
KnowledgeGap: detected → prioritized → investigation_active → partially_resolved/resolved/deferred → reopened.
CognitiveAffordance: detected → evaluated → simulated → selected/rejected/deferred → acted → outcome_recorded.
Projection: internal → candidate → deliberated → governance_pending → approved/rejected → externalized/closed.
LearningEvent: observed → attribution_pending → supported → applied/proposed → validated/rolled_back.

## Invariants
Invalid transitions fail closed. Historical state is not overwritten. Reopening is explicit. Externalization cannot skip governance. Major learning cannot skip attribution. Existing module-specific lifecycles may be stricter.