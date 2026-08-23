# Brain Developmental Intelligence Architecture

Status: canonical build-control expansion.

Purpose: define the next optimization target for the Brain: a system that does not remain static after implementation, but grows, differentiates, repairs, consolidates, prunes, and improves its own internal cognitive organization through evidence, replay, reward/pain, prediction error, contradiction pressure, theory competition, sleep/consolidation cycles, self-modeling, and governance gates.

This document is not a claim that the Brain is complete or more intelligent than any existing system. It is the execution architecture for building toward a self-developing intelligence system without allowing agents to make unauthorized scope decisions.

## Core doctrine

The Brain must develop like a living cognitive system by adding structure only when evidence, replay, acceptance, and governance allow it. Growth is not uncontrolled autonomy. Growth is controlled plasticity.

Development means:

- new sensors are proposed, not silently activated;
- new modules are born as hypotheses, not assumed correct;
- useful pathways are reinforced by attributed outcomes;
- harmful pathways are weakened, quarantined, or killed;
- contradictions are preserved until reviewed;
- unknown mechanisms are registered rather than hidden;
- dreams/simulations generate candidate rewires, not external actions;
- consolidation converts repeated success into durable memory, schemas, and services;
- pruning removes or suppresses low-yield, noisy, stale, unsafe, or overfit structures;
- the system maintains a self-model of what it knows, what it can do, what it cannot do, what it is uncertain about, and what evidence is missing.

## Intelligence growth loops

### 1. Prediction-error loop

Every belief, opportunity, source, formula, module, and strategy must be able to emit predictions. Outcomes generate prediction error. Prediction error updates calibration, confidence, attention, and development pressure.

Required objects:

- PredictionRecord
- PredictionError
- CalibrationTrace
- DevelopmentPressure

Required service:

- PredictionErrorService

GO only when prediction error can alter attention, confidence, and curriculum priority through an audited state transition.

### 2. Plasticity loop

The Brain needs a controlled equivalent of synaptic plasticity. Connections between sources, signals, beliefs, opportunities, actions, outcomes, formulas, agents, modules, and strategies gain or lose weight based on attributed reward, pain, surprise, reliability, contradiction, and age.

Required objects:

- CognitiveEdge
- PlasticityEvent
- RewireProposal
- PruningDecision

Required services:

- PlasticityService
- GraphRewireService
- PruningService

GO only when all rewires are replayable, reversible, and attached to evidence.

### 3. Neurogenesis/module-birth loop

The Brain must create new internal structures when repeated patterns cannot be represented by existing modules. A proposed new module starts as a ModuleHypothesis, must define its owner objects, schemas, services, formulas, fixtures, tests, dashboards, and GO/HOLD gates, and cannot become active until acceptance evidence exists.

Required objects:

- ModuleHypothesis
- ModuleBirthRecord
- ModuleMaturityRecord
- ModuleRetirementRecord

Required services:

- ModuleGenesisService
- ModuleMaturityService

GO only when module birth is gated by source traceability and acceptance evidence.

### 4. Developmental-stage loop

The Brain must not treat every capability as equally mature. Each subsystem progresses through developmental stages.

Stages:

1. reflex: deterministic rule or fixture exists;
2. perceptual: the system can detect and normalize signals;
3. associative: the system links signals, beliefs, and outcomes;
4. predictive: the system can forecast outcomes and record error;
5. strategic: the system can compare plans under risk;
6. metacognitive: the system can explain its limits and uncertainty;
7. self-repairing: the system can propose internal improvements under governance;
8. consolidated: repeated evidence promotes the capability into durable runtime.

No stage may be skipped silently.

### 5. Global workspace proxy

The Brain needs a working-memory competition layer where candidate signals, opportunities, contradictions, risks, and internal questions compete for limited attention. The global workspace is not a consciousness claim. It is an operator-grade control surface for what becomes globally visible to other modules.

Required objects:

- WorkspaceItem
- AttentionCoalition
- BroadcastEvent
- SuppressionEvent

Required services:

- WorkspaceCompetitionService
- BroadcastService

GO only when a workspace broadcast includes why it won, what it suppressed, what evidence supports it, and which modules consumed it.

### 6. Sleep, dream, and consolidation loop

The Brain needs offline cycles that simulate paths, compress memories, detect repeated patterns, propose rewires, update schemas, and archive or prune low-value material. Dreams cannot execute external actions. They can only produce proposals.

Required objects:

- DreamScenario
- ConsolidationRun
- MemoryCompression
- RehearsalTrace
- DreamRewireProposal

Required services:

- DreamSimulationService
- ConsolidationService
- MemoryCompressionService

GO only when dream outputs are labeled simulated and cannot bypass approval gates.

### 7. Cognitive immune system

The Brain needs an immune layer that detects hallucination risk, data poisoning, stale evidence, unlicensed source use, approval bypass, overconfidence, circular reinforcement, reward hacking, unsafe external action, source contamination, and contradiction deletion.

Required objects:

- ImmuneAlert
- QuarantineRecord
- ContaminationTrace
- RecoveryPlan

Required services:

- CognitiveImmuneService
- QuarantineService
- RecoveryService

GO only when unsafe growth is blocked and recoverable.

### 8. Unknown-mechanism and theory registry

The Brain must never hide uncertainty. Unknown mechanisms, speculative ideas, unsupported theories, unresolved contradictions, and unbuildable-yet concepts must be preserved in registries with status, evidence, tests needed, implementation risk, and review path.

Required objects:

- UnknownMechanism
- TheoryRecord
- TheoryCompetition
- OpenQuestion

Required services:

- UnknownMechanismRegistryService
- TheoryRegistryService
- TheoryCompetitionService

GO only when uncertainty is represented explicitly rather than collapsed into confident prose.

## Development scorecard

Every module receives a DevelopmentScore made of:

- evidence volume;
- evidence quality;
- prediction accuracy;
- calibration trend;
- replay coverage;
- fixture coverage;
- reward attribution;
- pain attribution;
- contradiction burden;
- immune alerts;
- operator interventions;
- source rights status;
- governance maturity;
- overfitting risk;
- consolidation status;
- pruning status.

A high score does not automatically authorize external action. External action remains approval-gated.

## Growth gates

A module may grow only when:

- source traceability exists;
- schemas exist;
- services exist;
- formulas are owned and audited;
- fixtures exist;
- replay is deterministic;
- acceptance report exists;
- immune scan passes;
- rollback path exists;
- dashboard surface exists;
- GO/HOLD verdict is explicit.

## Prohibited agent behavior

Agents must not:

- claim intelligence superiority as achieved;
- delete uncertainty;
- collapse developmental scope into V0;
- let simulations execute real actions;
- add autonomous external action;
- activate a connector without source rights and provenance;
- create a module without tests, fixtures, and acceptance evidence;
- mark a developmental stage complete without replay evidence;
- silently resolve contradictions;
- optimize for neatness over scope preservation.

## Next build target

The next build target is the Developmental Intelligence Spine:

- developmental stage state machine;
- prediction error runtime;
- plasticity and pruning runtime;
- module genesis workflow;
- global workspace proxy;
- sleep/dream/consolidation runtime;
- cognitive immune system;
- self-model and capability ledger;
- unknown-mechanism/theory registry;
- developmental benchmark suite.

GO/HOLD: GO for control specification. HOLD for implementation until code, fixtures, replay evidence, dashboards, and acceptance reports exist for each developmental subsystem.
