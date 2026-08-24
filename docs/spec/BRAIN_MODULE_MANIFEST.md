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

## Capital Discovery Cortex modules

These modules extend, rather than replace, the general cognitive substrate. The complete doctrine is in `CAPITAL_DISCOVERY_CORTEX.md`.

### MOD-008 Economic Asymmetry and Pressure
Purpose: represent monetizable gaps, market friction, pain, scarcity, urgency, and commercial pressure.
Data: EconomicAsymmetry, PressureEvent.
Services: AsymmetryDetectionService, PressureInferenceService.
Algorithms: asymmetry classification, pressure magnitude/confidence, pressure decay.
State machine: hypothesized -> supported -> active -> easing -> resolved/invalidated.
Tests: classification, evidence provenance, decay, invalidation.
Fixtures: multi-source expansion, distress, supply-gap, and false-positive cases.
Dashboard: pressure map and asymmetry inbox.
Acceptance: no active pressure without traceable evidence and confidence.

### MOD-009 Economic Affordance and Money Paths
Purpose: translate entities/events/pressures into possible value-capture actions and invoice paths.
Data: EconomicAffordance, MoneyPath, PaymentModel.
Services: AffordanceGenerationService, MoneyPathGenerationService.
Algorithms: capital grammar mapping, payment-model ranking, fastest/highest/lowest-capital/lowest-risk path comparison.
State machine: generated -> verified -> qualified -> rejected/expired.
Tests: one-to-many affordance generation, payment path preservation, stale-path invalidation.
Fixtures: equipment, hiring, facility permit, regulatory change, and fragmented-market cases.
Dashboard: money-path explorer.
Acceptance: qualified opportunity has at least one explicit payer/payment mechanism or is marked non-monetizable.

### MOD-010 Counterparty and Liquidity Cognition
Purpose: maintain buyer/seller/provider/investor roles, needs, assets, trust, reachability, decision authority, and reusable market liquidity.
Data: CounterpartyProfile, LiquidityPreference, CounterpartyInteraction.
Services: CounterpartyProfileService, BuyerMatchService, SellerMatchService, LiquidityGraphService.
Algorithms: counterparty-role inference, reachability/trust weighting, ranked buyer/seller matching.
State machine: discovered -> verified -> reachable -> active -> dormant/blocked.
Tests: role persistence, buyer matching, trust/reachability weighting, stale-contact handling.
Fixtures: active buyer, latent buyer, distressed seller, conflicting-role, and unreachable-decision-maker cases.
Dashboard: buyer/seller liquidity graph.
Acceptance: ranked match explains why each counterparty is selected and preserves provenance.

### MOD-011 Commercial Kill and Portfolio
Purpose: eliminate weak opportunities, prioritize scarce operator attention, and maintain risk-adjusted opportunity portfolios.
Data: EconomicOpportunity, CommercialDisposition, KillDecision, OpportunityPortfolio.
Services: EconomicOpportunityScoringService, CommercialSkepticService, PortfolioAllocationService.
Formula: risk-adjusted economic priority score with value, conversion, urgency, access, evidence, repeatability, compounding, capital, time, risk, complexity, and decay inputs.
State machine: detected -> verifying -> qualified -> act_now/watch/build_as_asset/delegate/automate -> won/lost/killed/expired.
Tests: high-value/low-cost ranking, kill rules, attention budgets, decay.
Fixtures: obvious crowded opportunity, inaccessible payer, zero-payment path, micro-cash opportunity, large strategic mandate.
Dashboard: act-now/verify/watch/kill operator board.
Acceptance: every surfaced opportunity has disposition, score trace, evidence state, and next action or kill reason.

### MOD-012 Transaction and Fee Control
Purpose: model how economic value is captured and protect origination economics before external commitment.
Data: Transaction, Mandate, IntroductionRecord, FeeAgreement, ReferralAgreement, ExclusivityRecord, OriginationEvidence.
Services: TransactionStateService, FeeProtectionService, MandateService.
Algorithms: fee-protection requirement, transaction-control sufficiency, jurisdiction-aware HOLD rules.
State machine: detected -> qualified -> protected -> approved -> contacted -> negotiation -> won/lost/abandoned.
Tests: approval bypass blocking, unprotected sensitive disclosure HOLD, origination evidence, transaction close/loss.
Fixtures: success-fee introduction, exclusive mandate, unprotected bypass risk, regulated brokerage review.
Dashboard: transaction pipeline and fee-control status.
Acceptance: consequential transaction action cannot execute without approval and required control state.

### MOD-013 Global Source Mesh and Source Rights
Purpose: register international source planes, legal/terms classifications, permitted collection methods, refresh policy, cost, reliability, and commercial yield.
Data: SourcePlane, SourceRightsProfile, JurisdictionProfile, SourceEconomics, SourceCandidate.
Services: SourcePlaneRegistryService, SourceRightsService, SourceEconomicsService, SourceDiscoveryService.
Algorithms: source reliability, source ROI, source-promotion gating, source-discovery proposal.
State machine: candidate -> reviewed -> approved -> active -> degraded -> suspended/prohibited.
Tests: prohibited-source rejection, terms-sensitive HOLD, jurisdiction labels, revenue attribution to sources.
Fixtures: public registry, paid licensed feed, scrape-sensitive site, PII-sensitive dataset, prohibited source.
Dashboard: source mesh, rights status, ROI, and health.
Acceptance: no active connector lacks rights classification, jurisdiction, refresh policy, and provenance.

### MOD-014 Revenue, Profit, and Capital Attribution
Purpose: attribute realized economic outcomes backwards to transaction, opportunity, money path, signal, observation, source, action, and operator/compute cost.
Data: RevenueAttribution, ProfitEvent, SourceROI, ActionROI, OpportunityROI, CapitalState.
Services: EconomicAttributionService, ProfitNormalizationService, SourceROIService, CapitalStateService.
Algorithms: attribution confidence, net-profit normalization, currency/FX normalization, capital efficiency.
State machine: provisional -> supported -> accepted -> disputed/revised.
Tests: low-attribution learning block, profit vs revenue, multi-source attribution, capital state invariants.
Fixtures: profitable deal, high-revenue low-profit deal, ambiguous attribution, multi-currency case.
Dashboard: profit attribution and capital ledger.
Acceptance: major source/strategy/capital promotion is blocked below attribution threshold.

### MOD-015 Compounding Assets and Business-Model Mutation
Purpose: detect when repeated opportunities produce proprietary assets, offers, products, marketplaces, businesses, or acquisition candidates.
Data: CompoundingAsset, RepeatedTransactionPattern, OfferHypothesis, ProductHypothesis, MarketplaceHypothesis, BusinessModelHypothesis.
Services: CompoundingAssetService, ProductizationService, MarketplaceEmergenceService, BusinessModelMutationService.
Algorithms: repeatability thresholding, liquidity thresholding, strategic-asset scoring.
State machine: observed -> hypothesized -> validated -> build_candidate -> approved/rejected -> operating.
Tests: repeated-problem detection, false repetition, marketplace liquidity threshold, productization evidence.
Fixtures: repeated buyer matching, repeated market-entry requests, one-off non-repeatable deal.
Dashboard: compounding-assets and build-candidates board.
Acceptance: no build candidate is promoted without repeated evidence, payer evidence, and resource estimate.

### MOD-016 Capital Source Intelligence Registry
Purpose: convert source discovery from a static list into a durable commercial-intelligence source registry with scoring, ingestion controls, source lifecycle, legal/access status, compounding-source relationships, evidence requirements, and downstream opportunity/action mappings.
Data: SourceIntelligenceRecord, SourceScore, SourceCluster, IngestionPolicy, SourceCategory, SignalType, LegalAccessStatus, SourceLifecycleStatus, OperationalDisposition.
Services: SourceIntelligenceRegistryService, SourceTriageService, SourceClusterService, IngestionPolicyService.
Algorithms: source priority score `(signal_value * 3) + freshness + reliability - extraction_difficulty`, legal/access HOLD routing, ranked source triage, cluster false-positive control.
State machine: discovered -> queued -> reviewed -> approved -> active/monitored -> degraded/broken -> retired/rejected/prohibited.
Tests: tests/test_source_intelligence_registry.py.
Fixtures: source_intelligence_registry.
Dashboard: Source Intelligence Registry, Source Health, Signal Inbox, Evidence Viewer, Opportunity Board.
Acceptance: source records validate required fields, priority scores match formula, legal/access HOLD states block automation, clusters include false-positive controls, and ingestion policies preserve provenance/compliance requirements.

## Later cognitive modules

Memory, dreaming, theory of mind, active inference, social cognition, strategy mutation, consciousness-adjacent layers, richer international market models, and advanced autonomous source discovery remain preserved and staged V1 to V4. Staging is not deletion.