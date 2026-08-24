# MOD-008 through MOD-015 Atomic Repair Implementation

Status: implementation evidence for issues #54 through #62 and governing issues #12 through #15.

This file is a repair overlay for the conformance audit. It does not delete or replace prior acceptance reports. It supersedes the older aggregate GO/HOLD contradiction by tying each missing atomic requirement to executable code, tests, fixture evidence, operator surfaces and conformance validation.

## Implemented runtime

`brain/economic_conformance.py` adds the missing V0 runtime boundaries that were called out by the atomic audit:

- pressure activation evidence and time-validity enforcement;
- money-path comparison across fastest, highest-value, lowest-capital, lowest-risk, repeatability and compounding dimensions;
- first-class `LiquidityPreference` and `CounterpartyInteraction` objects;
- counterparty role inference, verification, response-history weighting and stale-contact detection;
- durable opportunity disposition semantics for act, verify, watch, kill, archive, automate, delegate and non-monetizable outcomes;
- transaction close/loss/abandon lifecycle objects;
- source activation policy with rights class, collection method, provenance and jurisdiction gates;
- jurisdiction cognition object and movement/change detector;
- `ProfitEvent`, net-profit calculation and `ProfitNormalizationService`;
- full causal attribution chain from profit through transaction, opportunity, money path, pressure, signal, observation, source, sensor and action;
- attribution-confidence promotion gate;
- capital deployment and reconciliation lifecycle;
- repeated-transaction pattern detection;
- strategic-asset scoring;
- build-candidate resource-estimate gate;
- complete deterministic fixture-universe validator;
- complete operator-surface conformance validator.

## Tests

`tests/test_mod_008_015_conformance_repairs.py` covers the repair gates:

- pressure activation requires evidence and time-validity;
- money paths rank across required dimensions;
- counterparty liquidity graph tracks preferences, interactions and stale-contact state;
- opportunity lifecycle includes archive, automate, delegate and non-monetizable disposition;
- transaction lifecycle supports close/loss/abandon with evidence;
- source lifecycle and policy fail closed for PII-sensitive and prohibited source use;
- movement detection produces auditable change signals;
- profit normalization separates gross revenue from net profit;
- causal attribution chain contains every required identity link;
- capital deploy/reconcile requires evidence;
- repeated transaction pattern, strategic asset scoring and build-candidate gates require payer evidence and resource estimate;
- fixture universe and operator surface are complete.

## Fixture universe

`tests/fixtures/brain/mod_008_015_complete_fixture_universe.json` includes every scenario required by issue #60:

- expansion, distress, supply-gap and false-positive;
- equipment, hiring, facility permit, regulatory change and fragmented market;
- active buyer, latent buyer, distressed seller, conflicting role and unreachable decision maker;
- crowded obvious, inaccessible payer, zero-payment, micro-cash and strategic mandate;
- success-fee intro, exclusive mandate and regulated brokerage;
- public registry, paid licensed, scrape-sensitive, PII-sensitive and prohibited source;
- profitable deal, high-revenue-low-profit deal, ambiguous attribution and multi-currency case;
- repeated buyer matching, repeated market-entry and one-off non-repeatable case.

## Operator surface

`docs/operator-surfaces/mod-008-015-complete-operator-surfaces.json` defines the complete required surface set:

- pressure map;
- money-path explorer;
- liquidity graph;
- kill board;
- transaction pipeline;
- source mesh;
- profit/capital ledger;
- compounding board.

Every consequential operation remains approval gated.

## Validation

`tools/validate_mod_008_015_conformance.py` validates the conformance report and fails closed unless:

- verdict is GO;
- every module MOD-008 through MOD-015 is GO;
- every mandatory requirement status is PASS;
- no gap remains open;
- repair evidence paths exist;
- superseded historical aggregate GO/HOLD contradictions are explicitly reconciled.

## Permanent boundaries

This repair does not claim biological brain equivalence, consciousness, unrestricted autonomy, legal enforceability, or superior intelligence over every external system. It establishes repository evidence that the audited MOD-008 through MOD-015 requirements have a V0 executable implementation path with tests, fixtures, operator surfaces and validation gates.
