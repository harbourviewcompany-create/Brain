# Capital Source Intelligence Registry

Status: staged implementation control layer. This file converts the Source Intelligence Registry conversation into Brain build doctrine and executable acceptance expectations. It extends MOD-013 Global Source Mesh and Source Rights rather than replacing it.

## 1. Objective

The Brain must not treat source discovery as a static list-building task. It must maintain a living source intelligence registry that can become a durable company asset for opportunity detection, market intelligence, commercial research, and automated ingestion.

The operating objective is:

> Build a global source intelligence registry for a Capital Discovery Brain that detects monetizable commercial opportunities, company movement, distress signals, regulatory shifts, buyer/seller activity, investment signals, supply-chain disruption, local market opportunities, and obscure early indicators across public, semi-public, and legally accessible data sources.

The registry supports the chain:

`Sources -> Signals -> Evidence -> Intelligence -> Opportunity -> Action -> Outcome -> Source learning`

## 2. Non-negotiable framing

The registry is not a spreadsheet of URLs. It is a source intelligence operation.

Every source, source class, or source candidate must be evaluated for:

- signal value
- extraction difficulty
- freshness
- reliability
- legal/access status
- update frequency
- source lifecycle status
- downstream intelligence use case
- best ingestion method
- compounding source relationships
- false-positive risk
- evidence and provenance requirements
- commercial action paths

A source that cannot produce a traceable downstream signal, evidence item, intelligence claim, opportunity, or risk-control value remains staged or rejected.

## 3. Required taxonomy

The registry must support at least these source categories:

- government registries
- corporate registries
- licensing databases
- regulatory portals
- court and insolvency records
- procurement portals
- grant and subsidy databases
- real estate and property records
- import/export, customs, and trade data
- patent and trademark databases
- scientific and academic databases
- clinical trial registries
- job boards and hiring signals
- company websites and press releases
- local news and industry newsletters
- social platforms and community forums
- event calendars and conference exhibitor lists
- product directories and app stores
- review platforms
- satellite, geospatial, weather, and environmental sources
- shipping, logistics, energy, and grid data
- financial filings
- investor and M&A databases
- bankruptcy, distress, and liquidation sources
- marketplace listings and equipment resale markets
- municipal records, building permits, zoning, and planning records
- FOI/open-data portals
- NGO and think-tank reports
- standards bodies and certification databases
- enforcement, recall, sanctions, and watchlist sources
- domain, DNS, web-change, and technology-stack signals
- traffic/ranking datasets
- advertising libraries
- payment and commercial infrastructure signals

## 4. Required signal ontology

Every source must map to one or more signal types. Current required signal types:

- expansion
- distress
- hiring
- capital raise
- regulatory change
- supply-demand imbalance
- asset sale
- buyer intent
- seller intent
- license movement
- procurement
- litigation
- market entry
- closure
- consolidation
- product launch
- enforcement
- supply-chain disruption
- local market movement
- domain/web change
- commercial infrastructure change

Signals must not be promoted to intelligence without evidence rules, confidence scoring, timestamping, and contradiction handling.

## 5. Required registry fields

Every source record must carry:

1. source name
2. source category
3. URL or access path
4. jurisdiction / market coverage
5. what data it contains
6. signal type
7. commercial value
8. signal freshness
9. update frequency
10. access method
11. extraction difficulty
12. legal/access status
13. noise level
14. reliability level
15. best downstream use case
16. example intelligence questions it can answer
17. best way to ingest it
18. compounding sources to pair it with
19. priority score
20. notes / risks
21. lifecycle status
22. owner role
23. review cadence
24. provenance requirements

## 6. Scoring model

The canonical registry priority score is:

`priority_score = (signal_value * 3) + freshness + reliability - extraction_difficulty`

Signal value:

- 5 = high-value, commercially actionable, early signal
- 4 = strong supporting intelligence
- 3 = useful context
- 2 = occasional value
- 1 = weak or generic value

Extraction difficulty:

- 1 = easy download/API
- 2 = searchable public database
- 3 = scrapeable with moderate work
- 4 = fragmented/manual or anti-bot friction
- 5 = difficult, restricted, messy, or high-maintenance

Freshness:

- 5 = real-time or daily
- 4 = weekly
- 3 = monthly
- 2 = quarterly
- 1 = stale/irregular

Reliability:

- 5 = official/primary source
- 4 = reputable structured source
- 3 = mixed but useful
- 2 = noisy/unverified
- 1 = unreliable unless corroborated

Persisted scores require formula-run or equivalent audit evidence before consequential routing.

## 7. Source lifecycle

Every source must have one lifecycle status:

- discovered
- queued
- reviewed
- approved
- rejected
- active
- monitored
- degraded
- broken
- retired
- prohibited

No source may become active without legal/access classification, jurisdiction/market coverage, refresh policy, and provenance requirements.

## 8. Access and legal-control states

Required legal/access classifications:

- public_permitted
- open_license
- paid_licensed
- terms_review_required
- pii_sensitive
- rate_limited
- manual_only
- prohibited

Control rules:

- `prohibited` is HOLD and cannot be ingested.
- `terms_review_required` is HOLD until reviewed.
- `pii_sensitive` is HOLD for legal/privacy review.
- `paid_licensed` requires license metadata and cost tracking.
- `rate_limited` requires refresh throttling and failure monitoring.
- `manual_only` cannot be represented as automated ingestion.

## 9. Intelligence clusters

The source registry must support compound clusters. Minimum required clusters:

### Company distress detection

Detects: distress, litigation, closures, asset sales, restructuring, credit pressure, urgent liquidity, and possible buyer/seller or advisory opportunities.

Typical inputs:

- court/insolvency records
- corporate registries
- marketplace listings
- local news
- job changes or layoffs
- enforcement records

False-positive controls:

- stale filings cannot act alone
- promotional articles require corroboration
- legal filings must be distinguished from confirmed commercial intent

Commercial actions:

- distressed-asset brief
- buyer map
- restructuring or advisory introduction
- mandate proposal, if fee-control gates are satisfied

### Hiring and expansion

Detects: geographic expansion, channel buildout, market entry, product launch preparation, and capability investment.

Typical inputs:

- job postings
- licensing databases
- municipal permits
- company websites
- event/conference participation

False-positive controls:

- one generic job post is not enough
- role seniority and location must be verified
- company-controlled claims require independent corroboration before consequential outreach

Commercial actions:

- market-entry memo
- buyer/distributor/partner list
- expansion-monitoring queue
- paid brief candidate

### Regulatory and supply-gap detection

Detects: new rules, recalls, enforcement actions, supply constraints, import/export shifts, licensing movement, and compliance-driven opportunities.

Typical inputs:

- regulatory portals
- enforcement and recall sources
- import/export and customs data
- procurement portals
- industry newsletters

False-positive controls:

- proposed rules and adopted rules must remain separate
- effective dates must be explicit
- regulated commercial action requires review

Commercial actions:

- regulatory-change alert
- compliance advisory candidate
- replacement supplier sourcing
- supply-gap brief

## 10. Ingestion policy

Every source class must define:

- permitted ingestion methods
- refresh cadence
- storage target
- normalization fields
- deduplication keys
- evidence/provenance requirements
- failure monitoring
- compliance caution

Supported ingestion methods:

- API
- CSV/download
- RSS/feed
- HTML scrape
- PDF extraction
- manual analyst review
- email/newsletter capture
- browser automation
- search alert
- third-party enrichment
- web-change monitor

## 11. Entity graph requirements

The source registry must feed the Brain entity graph. Minimum entities:

- company
- person
- investor
- regulator
- license
- facility
- product
- asset
- market
- buyer
- seller
- distributor
- importer
- supplier
- address
- domain
- job post
- filing
- court case
- tender
- shipment
- article
- event

A source-derived observation that cannot attach to at least one entity, evidence item, or intelligence question remains raw/unpromoted.

## 12. Evidence rules

Every derived intelligence claim must preserve:

- source ID
- source URL/access path
- observed timestamp
- retrieval timestamp
- extract hash or snapshot ID
- source legal/access status
- evidence strength
- confidence score
- contradiction state
- freshness state
- analyst notes where manual review is involved

The registry must preserve the distinction between:

- source-backed claim
- inference
- hypothesis
- verified fact
- analyst opinion

## 13. Operator workflow

Minimum workflow:

1. discover source candidate
2. classify category, jurisdiction, signal types, and legal/access status
3. score signal value, extraction difficulty, freshness, and reliability
4. assign lifecycle state
5. define ingestion method and provenance requirements
6. pair with compounding sources
7. route to automate, manual review, watch, reject, or HOLD
8. ingest observations
9. promote observations into evidence only when rules pass
10. generate intelligence clusters and opportunity candidates
11. route consequential actions to approval and fee-control gates
12. track outcomes and update source ROI

## 14. Revenue mapping

Every material source must map to at least one monetization path or a documented non-monetizable justification.

Allowed revenue path classes:

- advisory retainer
- market-entry brief
- sourcing mandate
- buyer/seller introduction
- equipment or asset marketplace fee
- licensing support
- transaction support
- investor matching
- paid intelligence report
- subscription alert product
- done-for-you business-development campaign

## 15. Initial build artifacts

Implemented/staged files for this layer:

- `brain/source_intelligence.py`
- `tests/test_source_intelligence_registry.py`
- `tests/fixtures/brain/source_intelligence_registry.json`
- `docs/spec/source-intelligence-registry.json`
- `docs/spec/CAPITAL_SOURCE_INTELLIGENCE_REGISTRY.md`

## 16. GO/HOLD acceptance

GO requires:

- source record has required fields
- priority score matches formula
- legal/access HOLD states block automation
- source clusters have false-positive controls and commercial action paths
- ingestion policies include provenance and compliance cautions
- fixture demonstrates ranked source records

HOLD conditions:

- source lacks legal/access status
- source lacks jurisdiction/market coverage
- source has no downstream use case
- source cannot preserve provenance
- source action would collect prohibited or unreviewed sensitive data
- score is asserted without formula evidence
- intelligence claim conflates inference with verified fact

## 17. Deferred work

Deferred implementation items:

- persistent PostgreSQL tables for source registry, source scores, source health checks, and ingestion runs
- operator UI for source registry, source health, signal inbox, evidence viewer, opportunity board, analyst approval queue, and action generator
- source ROI attribution from realized revenue/profit
- automated source-discovery proposal service
- jurisdiction-specific legal/access registry
- full global source list population

These are deferred, not deleted. Agents must not claim the full source intelligence operation is production-complete until persistence, UI, automation, governance, tests, fixtures, replay evidence, and acceptance reports exist.
