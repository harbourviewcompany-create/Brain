# Brain Schema Registry

Agents must implement exact schemas before runtime loops are accepted.

## Required cognitive objects

Source, Sensor, RawObservation, PerceptualEvent, SalienceAssessment, AttentionDecision, EvidenceItem, Entity, Belief, BeliefContradiction, Signal, Opportunity, CandidateAction, ActionSimulation, ApprovalRequest, ApprovalDecision, ExecutedAction, Outcome, Prediction, AgencyAttribution, RewardEvent, PainEvent, GraphNode, GraphEdge, GraphWeightUpdate, MemoryObject, FormulaRegistryEntry, FormulaRun, DecisionExplanation, AcceptanceReport, AuditEvent.

## Required economic-cognition objects

Current executable slice:

- EconomicAsymmetry
- PressureEvent
- EconomicAffordance
- MoneyPath
- EconomicOpportunity
- CounterpartyProfile
- Transaction
- RevenueAttribution
- CapitalState

Canonical staged objects:

- SourcePlane
- SourceRightsProfile
- JurisdictionProfile
- SourceEconomics
- SourceCandidate
- MovementEvent
- LiquidityPreference
- CounterpartyInteraction
- KillDecision
- OpportunityPortfolio
- Mandate
- IntroductionRecord
- FeeAgreement
- ReferralAgreement
- ExclusivityRecord
- OriginationEvidence
- DealRoom
- ProfitEvent
- SourceROI
- ActionROI
- OpportunityROI
- CompoundingAsset
- RepeatedTransactionPattern
- OfferHypothesis
- ProductHypothesis
- MarketplaceHypothesis
- BusinessModelHypothesis

Staged means preserved but not necessarily implemented. Runtime loops may not claim these objects exist until code, storage, tests, fixtures, replay evidence, and acceptance evidence exist.

## Economic enum registries

### EconomicAsymmetry.kind

`information, timing, access, trust, liquidity, execution, compliance, fragmentation, pricing, capability, attention, relationship`

### PressureEvent.kind

`cash, inventory, hiring, compliance, time, regulatory, competitive, customer, supply, demand, debt, reputation, expansion, exit, operational, technology, distribution, licensing, relationship`

### EconomicAffordance.verb / capital grammar

`buy, sell, broker, refer, recruit, source, verify, package, automate, advise, license, publish, introduce, finance, aggregate, arbitrage, resell, monitor, negotiate, match, build, acquire, rent, lease, liquidate, consolidate, insure, certify, train, route, rank, alert`

### EconomicOpportunity.kind

`micro, service, brokerage, arbitrage, recruiting, procurement, market_entry, distress, expansion, supply_gap, demand_gap, automation, acquisition, investment, relationship, data_product, marketplace, strategic_asset`

### MoneyPath.payment_model

`finders_fee, referral_fee, retainer, project_fee, success_fee, brokerage_spread, commission, subscription, sponsorship, listing_fee, data_product, lead_pack, revenue_share, equity, option, exclusive_mandate, paid_introduction, implementation_fee, maintenance_fee, licensing_fee, marketplace_take_rate`

### CounterpartyProfile.roles

`buyer, seller, supplier, distributor, importer, exporter, investor, lender, operator, recruiting_client, candidate, consultant, broker, facility_owner, manufacturer, service_provider`

### Commercial disposition

`act_now, verify_first, watch, archive, kill, automate, delegate, build_as_asset`

## Current economic object minimums

### EconomicAsymmetry

Required: `id, created_at, entity_id, kind, magnitude, confidence, evidence_ids`.

### PressureEvent

Required: `id, created_at, entity_id, kind, magnitude, confidence, direction, evidence_ids`.
Optional: `valid_until, metadata`.

### EconomicAffordance

Required: `id, created_at, entity_id, verb, rationale, confidence, evidence_ids`.

### MoneyPath

Required: `id, created_at, verb, payment_model, expected_gross_value, expected_net_value, time_to_cash_days, conversion_probability, collection_risk, fee_protection_required`.
Optional: `buyer_entity_id, metadata`.

### EconomicOpportunity

Required: `id, created_at, kind, entity_id, money_path_ids, gross_value, net_value, conversion_probability, urgency, access_advantage, evidence_confidence, repeatability, strategic_compounding_value, required_capital, required_operator_hours, legal_reputation_risk, operational_complexity, time_decay`.

Every persisted score derived from these fields requires a formula-run reference in the persistence representation even when the pure in-memory dataclass exposes a calculation helper.

### CounterpartyProfile

Required: `id, updated_at, entity_id, roles`.
Supported: `needs, assets, budget_estimate, urgency, trust, reachability, decision_authority, response_rate, metadata`.

### Transaction

Required: `id, created_at, opportunity_id, payment_model, expected_revenue, expected_profit, capital_at_risk, fee_protected, status`.
Supported: `buyer_entity_id, seller_entity_id, metadata`.

### RevenueAttribution

Required: `id, created_at, transaction_id, opportunity_id, source_ids, gross_revenue, net_profit, operator_hours, data_compute_cost, attribution_confidence`.

### CapitalState

Required: `id, updated_at, available_capital, reserved_capital, risk_capital, operating_budget, reinvestment_budget, currency`.
Derived: `deployable_capital >= 0`.

## Common required fields

- `id`
- `created_at` or `updated_at` according to object semantics
- `status` where the object participates in a state machine
- `source_ids` where applicable
- `parent_id` where applicable
- `formula_run_ids` where scored
- `audit_event_ids` where transitioned

## TypeScript pattern

```ts
export interface BrainObject {
  id: string;
  created_at: string;
  status: string;
}
```

## Zod pattern

```ts
export const BrainObjectSchema = z.object({
  id: z.string().min(1),
  created_at: z.string(),
  status: z.string().min(1)
});
```

## Validation rules

- IDs are required.
- Scores require formula runs when persisted or used for consequential decisions.
- Outcomes require action links.
- Reward and pain require attribution.
- Major economic learning, source promotion, strategy promotion, and capital reallocation require attribution.
- External actions require approval.
- Blocked evidence cannot update semantic memory.
- Qualified commercial opportunities require an explicit money path or a recorded non-monetizable disposition.
- Active source connectors require a source-rights classification once MOD-013 is implemented.
- Transaction action cannot bypass approval or required fee-control HOLD gates.
- Inference, hypothesis, source-backed claim, and verified fact must remain distinguishable.

## Storage

V0 may use in-memory or JSON-backed storage. Production targets PostgreSQL as canonical event ledger with graph projection rebuildable from events. Economic objects must preserve event provenance sufficient to trace realized revenue/profit back through transactions, opportunities, money paths, signals, observations, sources, and sensors.
