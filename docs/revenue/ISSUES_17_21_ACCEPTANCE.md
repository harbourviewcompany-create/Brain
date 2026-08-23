# Revenue Spine Issues 17-21 Acceptance Evidence

## Scope

This implementation connects the V1 Money Spine to deterministic revenue-registry generation, fixture-backed source connectors, a provider-neutral model cortex, an operator cockpit control plane and GO/HOLD issue reconciliation checks.

## Issue #17

Acceptance evidence:
- `tools/revenue_spine_17_21.py`
- `tools/import_opportunity_registry.py`
- `data/opportunities/opportunity_registry_manifest.json`
- `tests/test_revenue_spine_17_21.py`

The 10,000-lane registry is generated from committed deterministic source dimensions. The first-500 fast-cash queue is ranked by priority, time-to-cash and risk. Malformed rows fail validation.

## Issue #18

Acceptance evidence:
- `FixtureConnectorRunner`
- `SourceConnectorInput`
- `RevenueSignalCandidate`
- `tests/test_revenue_spine_17_21.py`

Manual text, job-board, procurement and auction fixture connectors emit normalized candidates with source ID, evidence refs, access status, extraction method and content hash. Prohibited or review-required sources are blocked before ingestion.

## Issue #19

Acceptance evidence:
- `DeterministicModelCortex`
- `MoneyHypothesis`
- `CortexResult`
- `tests/test_revenue_spine_17_21.py`

The model cortex is provider-neutral and fixture-tested. Ambiguous or high-risk inputs return objections and remain approval-required.

## Issue #20

Acceptance evidence:
- `RevenueCockpit`
- `CockpitAction`
- `CockpitOutcome`
- `tests/test_revenue_spine_17_21.py`

The operator cockpit executes signal -> packaged offer -> approval -> sent outreach -> outcome -> source-score learning. It separates research backlog from today's revenue queue and blocks outreach until approval.

## Issue #21

Acceptance evidence:
- `docs/control/go_hold_issue_reconciliation.json`
- `load_go_hold_reconciliation`
- `reconcile_go_hold`
- `tests/test_revenue_spine_17_21.py`

The reconciliation rule fails when a GO report references an open issue without an explicit open reason or when issue/report evidence is missing. Issues #3-#8 are documented as closed with matching acceptance evidence.

## GO/HOLD

GO for these executable slices when CI passes. HOLD remains for live external connectors, production persistence, real provider-backed model calls and real operator deployment.
