# Complete Repository Reconciliation — Cross-Cutting Cognitive Architecture

Status: SOURCE/APPROVED integration analysis. This document is additive and does not replace existing Brain doctrine. “Complete repository reconciliation” describes source reconciliation, not completion of every Brain capability or production rollout.

## Current protected-main context

The previously separate cognitive-object persistence, cognitive-organ, tenant/auth and convergence branches have been incorporated into protected-main history through PR #126 and subsequent protected-main changes. They are no longer external PR dependencies. Protected main remains authoritative for existing cognitive-organ behavior, #139 automatic prediction/outcome attribution, #141 durable edge reads, revenue execution, deployment controls and later runtime fixes.

PR #126 added the cross-cutting Cognitive Object Protocol, resource-bounded developmental scheduler and tenant/RLS runtime surfaces, but those runtime surfaces remain REVIEW/HOLD until their production evidence exists. Migrations 019–022 are release-gated and are not a production GO claim.

## Existing architecture preserved

The existing module manifest defines Source/Perception, Belief/Evidence, Opportunity/Action, Outcome/Learning, Governance, neuroscience abstraction, unknown-mechanism and theory-conflict registries, and economic affordance/counterparty/source-intelligence modules. Existing state-machine and schema registries remain authoritative. Existing Cognitive Organism, developmental intelligence, rich memory, affect, homeostasis, curiosity, global-workspace, sleep/dream/consolidation and operator work are not replaced.

## Reconciliation by target capability

| Capability | Existing evidence | Classification | Remaining delta |
|---|---|---|---|
| Cognitive Object Protocol | Generic cognitive-object persistence + merged protocol runtime | PARTIAL | Broad organ-by-organ adapters and replay evidence |
| Epistemic State Model | Belief confidence, evidence, calibration, contradiction + protocol EpistemicState | PARTIAL | Per-organ adoption evidence |
| Cognitive Provenance Graph | Source/evidence/graph traceability + protocol provenance edges | PARTIAL | Broad lineage emission/adoption |
| Cognitive Lifecycle Framework | Existing state machines + protocol transition contract | PARTIAL | Per-module lifecycle adapters |
| General Conflict Arbitration | Contradiction queue, debate, executive control + protocol conflict object | PARTIAL | Cross-organ arbitration integration |
| Ignorance / Knowledge-Gap Model | Curiosity, unknown mechanisms + KnowledgeGap runtime contract | PARTIAL | Broader curiosity/planning integration |
| Cognitive Affordance | Economic affordance/action candidates + CognitiveAffordance | PARTIAL | Planning/executive integration |
| Internal→External Projection Boundary | Governance/action gates + ProjectionDecision | PARTIAL | Broader governed externalization adapters |
| Experience→Learning | outcomes/reward/attribution + LearningEvent; #139 auto prediction/outcome attribution | PARTIAL | Cross-organ learning adapters |
| Cognitive Replay Standard | event sourcing + protocol ReplayBundle | PARTIAL | production restart/replay evidence |
| Developmental Plasticity | developmental runtime + DevelopmentalPlasticityDelta | PARTIAL | production scheduler/operator integration |
| Tenant/RLS isolation | migrations 019–022 + tenant runtime + CI release verifier | PARTIAL | production role/topology/backfill evidence |
| Operator observability | control plane + secure operator boundary + dashboard specs | PARTIAL | production secure-operator deployment evidence |

## Explicit non-duplication decisions

- Do not create a second evidence store or graph database.
- Do not replace Belief, Evidence, Outcome, Prediction, Opportunity or CandidateAction.
- Do not rename EconomicAffordance; `CognitiveAffordance` remains a domain-general contract with explicit mapping where applicable.
- Do not replace contradiction queue/executive control; general conflict arbitration is a shared contract those services can implement.
- Do not create a second unknown-mechanism registry; runtime knowledge gaps reference it where the gap is biological/mechanistic.
- Do not duplicate cognitive-object persistence; the shared protocol persists through the existing store.
- Do not duplicate #139 learning behavior; automatic task predictions and outcome attribution remain protected-main authority.
- Do not duplicate #141 edge persistence/read behavior; the Railway compatibility surface inherits the tenant-aware API boundary while preserving the same durable edge store.

## Current coherent implementation frontier

The repository contains the shared protocol objects, epistemic state, provenance lineage, knowledge gaps, cognitive affordances, projection decisions, experience/outcome learning records, replay bundles, persistence, deterministic tests/fixtures, control specs and operator-surface specifications. Full wiring into every cognitive organ remains integration work. Production tenant/RLS rollout remains HOLD until the canonical migration runner proves a separate migrator, constrained non-BYPASSRLS API role, constrained trusted worker role, exact migration hashes, two-tenant cross-boundary denial, legacy-row disposition and deployment-specific evidence.
