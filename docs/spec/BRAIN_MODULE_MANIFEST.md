# Brain Module Manifest

Each module must map to data, service, formula or algorithm, state machine, test, fixture, dashboard, and acceptance criteria.

## V0 required modules

### MOD-001 Formula Registry
Purpose: register formulas and log formula runs.
Data: FormulaRegistryEntry, FormulaRun.
Services: FormulaRegistryService.
Tests: formula trace tests.
Fixtures: formula fixtures.
Dashboard: formula audit.
Acceptance: every score has trace.

### MOD-002 Schema Registry
Purpose: validate canonical objects.
Data: all runtime objects.
Services: SchemaValidationService.
Tests: schema validation.
Fixtures: schema fixtures.
Dashboard: object health.
Acceptance: invalid objects fail closed.

### MOD-003 State Machine
Purpose: block invalid transitions.
Data: StateTransition, AuditEvent.
Services: StateMachineService.
Tests: allowed and blocked transitions.
Fixtures: transition fixtures.
Dashboard: transition log.
Acceptance: no execution without approval.

### MOD-004 Source and Perception
Purpose: convert observations into perceptual events.
Data: Source, Sensor, RawObservation, PerceptualEvent.
Services: SourceRegistryService, PerceptionService.
Tests: ingestion and perception.
Fixtures: source fixtures.
Dashboard: perception inbox.
Acceptance: every event has source and route.

### MOD-005 Belief and Evidence
Purpose: score evidence and update beliefs.
Data: EvidenceItem, Entity, Belief.
Services: EvidenceScoringService, BeliefUpdateService.
Tests: Bayesian update and contradiction.
Fixtures: evidence fixtures.
Dashboard: belief ledger.
Acceptance: blocked evidence cannot update belief.

### MOD-006 Opportunity and Action
Purpose: score opportunities and simulate actions.
Data: Signal, Opportunity, CandidateAction, ActionSimulation.
Services: OpportunityScoringService, ActionSimulationService.
Tests: opportunity and action tests.
Fixtures: opportunity fixtures.
Dashboard: opportunity board.
Acceptance: external action routes to approval.

### MOD-007 Outcome and Learning
Purpose: link outcomes to predictions and update weights.
Data: Outcome, Prediction, RewardEvent, PainEvent, GraphEdge.
Services: OutcomeLoggerService, RewardPainService, GraphLearningService.
Tests: attribution and learning.
Fixtures: outcome fixtures.
Dashboard: learning console.
Acceptance: no major learning without attribution.

## Later modules

Memory, dreaming, theory of mind, active inference, social cognition, strategy mutation, capital allocation, and consciousness-adjacent layers remain preserved and staged V1 to V4.