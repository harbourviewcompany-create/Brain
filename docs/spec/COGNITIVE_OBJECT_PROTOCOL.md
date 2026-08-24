# Cognitive Object Protocol

Purpose: define a shared envelope that existing and future cognitive organs can consume without replacing their domain objects.

## Canonical families
Observation/Percept, Evidence, Memory, Entity/Concept, Belief/Claim/Hypothesis, Prediction, Goal/Need/Drive, AffectState, AttentionTarget, Conflict, Relationship, CognitiveAffordance, Decision/Plan, Action, Outcome/RewardSignal, Simulation/Model/SelfModel, LearningEvent, ReviewDecision.

Existing registry objects remain canonical where already defined; this protocol standardizes cross-organ metadata.

## Required envelope
Every protocol object must expose: object_id, object_kind, created_at, lifecycle_state, provenance_refs, epistemic_state where epistemically meaningful, parent/related object references, world-valid interval where meaningful, learned/recorded time, and audit/transition references when mutated.

## Invariants
- No provenance erasure during transformation.
- Contradictory objects may coexist.
- A derived object identifies its upstream objects/evidence.
- Internal objects are private by default and cannot imply external-action authorization.
- Unknown biological mechanisms remain unknown; software abstractions must not imply biological equivalence.
- Existing specialized objects are adapted into the protocol rather than duplicated.

## Interoperability
Perception emits protocol references; memory preserves them; belief systems consume evidence lineage; curiosity consumes KnowledgeGap; planning consumes CognitiveAffordance; executive/action systems consume decisions and projection gates; outcomes emit LearningEvent; developmental systems consume governed learning deltas.