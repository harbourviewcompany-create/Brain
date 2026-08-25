# Complete Repository Reconciliation — Cross-Cutting Cognitive Architecture

Status: SOURCE/APPROVED integration analysis. This document is additive and does not replace existing Brain doctrine.

## Base and branch context

This work is stacked on PR #105 (`converge/brain-runtime-agent020-20260823`) because that branch already supplies persistent cognitive objects, bitemporal world state, provenance-aware memory, planning, benchmark, observability, PostgreSQL persistence, and durable orchestration. Reimplementing those on `main` would duplicate active work. Open PRs #108-#110 also contain theory-of-mind, executive-control, and affect capabilities that remain separate HOLD integration surfaces.

## Existing architecture preserved

The existing module manifest already defines Source/Perception, Belief/Evidence, Opportunity/Action, Outcome/Learning, Governance, neuroscience abstraction, unknown-mechanism and theory-conflict registries, and economic affordance/counterparty/source-intelligence modules. Existing state-machine and schema registries remain authoritative. Existing Cognitive Organism, developmental intelligence, memory, affect, homeostasis, curiosity, global-workspace, sleep/dream/consolidation and operator work are not replaced.

## Reconciliation by target capability

| Capability | Existing evidence | Classification | Delta |
|---|---|---|---|
| Cognitive Object Protocol | Broad canonical schemas; PR #105 generic cognitive object store | PARTIAL | Shared cross-organ contract, object-family metadata, epistemic/provenance/lifecycle envelope |
| Epistemic State Model | Belief confidence, evidence, calibration, contradiction | PARTIAL | Multi-axis epistemic state that does not collapse into confidence |
| Cognitive Provenance Graph | Source/evidence/graph traceability; PR #105 source_refs | PARTIAL | Typed lineage edges from observation through learning |
| Cognitive Lifecycle Framework | Existing per-module state machines | PARTIAL | Cross-cutting lifecycle contract and transition record |
| General Conflict Arbitration | Contradiction queue, debate, executive-control PR #109 | PARTIAL | Domain-general conflict object preserving competing states |
| Ignorance / Knowledge-Gap Model | Curiosity and unknown-mechanism registry | PARTIAL | First-class runtime knowledge-gap objects connected to curiosity priority |
| Affordance Model | MOD-009 EconomicAffordance and CandidateAction | PARTIAL | Domain-general cognitive affordance distinct from economic affordance |
| Internal→External Projection Boundary | Governance/action gates | PARTIAL | Explicit projection stages separating internal cognition from externalization |
| Experience→Outcome→Learning Loop | MOD-007, reward/pain, attribution | PARTIAL | General typed experience lineage and learning delta |
| Cognitive Replay Standard | Event sourcing and PR #105 replay-safe orchestration | PARTIAL | Required reconstruction bundle and invariants |
| Developmental Plasticity | developmental modules/AGENT-017–021 | PARTIAL | Cross-object plasticity targets and learning-delta contract |
| Operator observability | control plane specs, PR #105 observability | PARTIAL | Cross-cutting inspector/replay/ignorance/conflict surfaces |

## Explicit non-duplication decisions

- Do not create a second evidence store or graph database.
- Do not replace Belief, EvidenceItem, Outcome, Prediction, Opportunity or CandidateAction.
- Do not rename EconomicAffordance; add a domain-general `CognitiveAffordance` with explicit mapping where applicable.
- Do not replace contradiction queue/executive control; general conflict arbitration is a shared contract those services can implement.
- Do not create a second unknown-mechanism registry; runtime knowledge gaps reference it where the gap is biological/mechanistic.
- Do not duplicate PR #105 persistence; the new protocol persists through its cognitive-object store.

## Current coherent implementation frontier

This branch can honestly implement the shared protocol objects, epistemic state, provenance lineage, knowledge gaps, cognitive affordances, projection decisions, experience/outcome learning records, replay bundles, persistence through the PR #105 store, deterministic tests/fixtures, control specs and operator-surface specification. Full wiring into every cognitive organ remains staged integration work and must remain PARTIAL/HOLD until each organ emits/consumes the contracts with replay evidence.