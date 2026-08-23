# V1 Money Spine

## Purpose

The Money Spine turns The Brain from a cognitive substrate into a daily revenue machine.

It does not replace the cognitive architecture. It gives the Brain a survival loop:

Signal -> money lane -> named buyer/seller/contact -> packaged offer -> outreach approval -> action -> outcome -> learning -> reallocation.

The rule is: no passive research day. Each operating day must produce at least one commercial action, sellable asset, follow-up, or measured revenue experiment.

## Non-negotiable project framing

The Brain is not cannabis-exclusive, not Harbourview-specific, not a CRM, not a scraper, and not a dashboard-first app.

The Brain is a standalone adaptive opportunity organism. Its first job is revenue. Its deeper job is to learn how opportunity forms and to automate only the patterns that prove value.

## What V1 adds

V1 introduces explicit commercial objects:

- `MoneyLane`: a repeatable path to cash.
- `RevenueSignal`: a raw signal that may indicate pain, demand, supply, distress, urgency, mispricing, or inefficiency.
- `NoFantasyFilter`: a rejection gate for interesting but noncommercial signals.
- `ScoredOpportunity`: a scored candidate with actionability and rejection reasons.
- `PackagedOffer`: an outreach-ready commercial wrapper around a scored opportunity.
- `RevenueExperiment`: a structured lane test with success and kill thresholds.
- `RevenueExperimentResult`: measured reply, meeting, paid conversion, revenue, and decision evidence.
- `DailyRevenueReport`: daily quota enforcement so the system does not drift into passive research.

## Actionable opportunity rule

A signal is not allowed into the active revenue queue unless it has:

1. A named buyer, seller, or decision-maker.
2. Visible pain, urgency, or a plausible payment path.
3. A contact channel.
4. Evidence references.
5. Acceptable legal/access risk.
6. Fast enough time-to-cash for the current operating mode.

If it fails, it is backlog/research, not today's money queue.

## Initial money lanes

### High-Intent Lead Pack

Buyer: B2B service provider, agency, consultant, or founder selling into a defined market.

Target: companies or people publicly showing buying intent, pain, expansion, or urgent need.

First 48-hour action: build 25 sourced leads, identify decision-makers, draft offer-specific outreach, and ask whether the buyer wants the full pack.

Starter price: $150 to $500.

### Buyer/Seller Match Sprint

Buyer: broker, seller, operator, asset owner, investor, or distributor.

Target: known buyer or seller with asset, inventory, service, company, or demand.

First 48-hour action: verify the asset or demand, identify 20 likely counterparties, and queue controlled intro outreach for approval.

Starter price: $500 to $2,500.

### Procurement / RFP Match Pack

Buyer: vendor, consultant, agency, contractor, or service provider eligible to bid.

Target: government, institution, nonprofit, or company publishing a buying requirement.

First 48-hour action: extract requirements, find 10 qualified vendors, and pitch the opportunity brief or bid-support intro.

Starter price: $250 to $1,500.

## Scoring model

The V1 score uses:

- commercial value x 25
- urgency x 20
- buyer/seller clarity x 20
- contactability x 15
- confidence x 10
- lane repeatability x 10
- execution difficulty x -15
- legal/access risk x -20
- time delay x -10

The score is not a truth claim. It is an attention and execution allocation mechanism.

## Daily quota

The default daily quota is:

- 50 raw signals reviewed
- 20 signals logged
- 10 qualified opportunities
- 5 prioritized opportunities
- 3 direct revenue actions
- 1 sellable asset created
- 1 lesson recorded

A day fails if it has research but no commercial action.

## Experiment rules

Each money lane must be tested as an experiment with:

- hypothesis
- buyer type
- offer
- price
- outreach target
- reply threshold
- paid conversion threshold
- kill threshold
- measured result
- scale/modify/kill/continue decision

Default starter test:

- send 30 targeted messages
- success if 3 replies or 1 paid conversion
- kill or radically reframe after 50 targeted messages without enough response

## Automation rules

Automation is permitted only after proof.

Automate when:

- a source repeatedly produces useful signals
- a signal class repeatedly leads to replies or revenue
- an offer gets at least one paid conversion
- a workflow repeats at least three times
- manual execution becomes the bottleneck
- data structure is stable
- legal/access risk is acceptable

Do not automate curiosity. Automate proven money paths.

## Human approval gates

Human approval remains required for:

- outreach
- introductions
- paid offers
- public claims
- sensitive claims
- external actions with legal, financial, reputational, or privacy consequences

The Brain can score, package, and recommend. Execution remains permissioned unless an explicit policy later allows otherwise.

## Build status

Implemented in this branch:

- `brain/money_spine.py`
- `tests/test_money_spine.py`
- `db/migrations/006_money_spine.sql`

Still missing:

- operator UI
- source connectors
- model extraction/cortex
- outreach approval screen
- follow-up queue
- outcome dashboard
- 10,000-lane CSV loader
- persistent adapter for MoneySpineService
- production automation scheduler
