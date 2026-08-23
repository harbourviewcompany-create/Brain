# MOD-008 through MOD-015 Conformance Audit Protocol

Status: CONTROL PROPOSAL
Scope: Capital Discovery Cortex MOD-008 through MOD-015
Purpose: prevent aggregate test success, implementation summaries, or broad acceptance reports from being mistaken for line-by-line specification conformance.

## Governing rule

A module is COMPLETE only when every mandatory atomic requirement derived from all controlling sources has evidence and is classified PASS. A module is not complete when any mandatory requirement is PARTIAL, FAIL, UNVERIFIED, CONTRADICTED, or NOT_TESTED.

Passing CI proves only that the committed tests and validators passed. It does not prove that every requirement was implemented or tested.

## Authoritative requirement sources

The audit MUST include, without narrowing:

1. `docs/spec/BRAIN_MODULE_MANIFEST.md` — every Purpose, Data, Services, Algorithms/Formula, State machine, Tests, Fixtures, Dashboard, and Acceptance statement for MOD-008 through MOD-015.
2. `docs/spec/CAPITAL_DISCOVERY_CORTEX.md` — every applicable doctrine, ontology, hard gate, object, service, score, workflow, control, internationalization, source-rights, attribution, compounding, and operator requirement.
3. `docs/spec/BRAIN_STATE_MACHINES.md` — every named state, allowed transition, blocked transition, approval gate, decay/expiry rule, and evidence requirement applicable to MOD-008 through MOD-015.
4. GitHub issues #12, #13, #14, and #15 — every Required scope item, Acceptance gate, fixture requirement, replay requirement, operator requirement, and GO/HOLD condition.
5. `docs/control/brain-build-rules.md` and the source-requirement registry — all control-layer requirements governing traceability, source preservation, definition of done, and GO/HOLD.
6. Any later APPROVED specification that explicitly extends MOD-008 through MOD-015. Later sources may add requirements; they may not silently erase earlier requirements.

## Atomic requirement rule

Each source statement MUST be decomposed into the smallest independently verifiable claims.

Example:

`Data: CounterpartyProfile, LiquidityPreference, CounterpartyInteraction.`

becomes three independent requirements:

- MOD-010-DATA-001 `CounterpartyProfile` exists as a canonical runtime/persistence object.
- MOD-010-DATA-002 `LiquidityPreference` exists as a canonical runtime/persistence object.
- MOD-010-DATA-003 `CounterpartyInteraction` exists as a canonical runtime/persistence object.

A single implementation object may satisfy more than one requirement only when evidence demonstrates that it preserves every required semantic independently. Similarity of names is not conformance.

## Required evidence dimensions

Every atomic requirement MUST be evaluated against all applicable dimensions:

- `code`: actual implementation symbol/path and behavior.
- `schema`: canonical object definition and durable persistence representation where persistence is required.
- `service`: runtime service/API boundary named or semantically equivalent to the requirement.
- `state_machine`: states, transitions, guards, decay/expiry, approval/HOLD behavior.
- `fixture`: committed deterministic fixture exercising the requirement.
- `test`: committed test asserting positive and, where applicable, negative/fail-closed behavior.
- `api`: operator or machine API surface when required.
- `operator_surface`: human-visible control/inspection surface when required.
- `replay`: deterministic replay evidence when required.
- `acceptance`: committed acceptance evidence that references the atomic requirement, not only the parent module.
- `traceability`: source requirement -> implementation -> test -> evidence linkage.

If a dimension is not applicable, it MUST be explicitly marked `N/A` with rationale. Missing evidence may not be silently treated as N/A.

## Status vocabulary

- `PASS`: complete implementation and required evidence exist.
- `PARTIAL`: some but not all required semantics/evidence exist.
- `FAIL`: implementation conflicts with or omits the requirement.
- `UNVERIFIED`: evidence is insufficient to determine conformance.
- `CONTRADICTED`: evidence demonstrates behavior opposite to the requirement.
- `NOT_TESTED`: implementation may exist but required test/fixture/replay evidence does not.
- `N/A`: dimension is demonstrably not applicable; rationale required.

Only `PASS` satisfies a mandatory atomic requirement.

## Evidence quality rules

Evidence MUST identify exact repository paths and, where practical, symbols/test names. Search-result absence is supporting evidence for a likely omission but is not alone sufficient for PASS/FAIL when code may implement the requirement under a different name. Semantic inspection is required before final FAIL.

An acceptance report that says a broad criterion is GO is not sufficient evidence for a more specific missing requirement.

A test named after a requirement is not evidence unless the assertions actually test the required semantics.

A dataclass/schema declaration without persistence evidence does not satisfy a requirement explicitly requiring persistence.

An API endpoint without a tested operator workflow does not satisfy a dashboard/control-plane requirement.

A state enum without transition guards and negative tests does not satisfy a state-machine requirement.

## Closure rule

For issues #12–#15:

- If every mandatory atomic requirement mapped to the issue is PASS: issue may be closed `completed`.
- If any mandatory requirement is PARTIAL/FAIL/UNVERIFIED/CONTRADICTED/NOT_TESTED: issue MUST remain open or be reopened.
- The issue must contain or link the latest conformance report and list all non-PASS requirement IDs.

Issue closure is therefore a derived state, not a subjective judgment.

## Module GO/HOLD rule

`GO` requires:

1. 100% mandatory atomic requirements PASS.
2. Zero unresolved hard-gate failures.
3. All required fixtures and negative tests committed.
4. Deterministic replay PASS where required.
5. Acceptance evidence generated from the current code head.
6. Control policy, tests, and lint passing on the same evidence-bearing head.

Anything else is `HOLD`, even if CI is green.

## Audit sequence

1. Pin exact `main` commit SHA.
2. Snapshot authoritative source text.
3. Enumerate every MOD-008–015 statement.
4. Split statements into atomic requirements.
5. Deduplicate only exact semantic duplicates; preserve source aliases.
6. Map each atomic requirement to issue #12/#13/#14/#15 as applicable.
7. Search repository for candidate evidence.
8. Open and inspect candidate code/tests/fixtures/replay/acceptance records.
9. Record evidence by dimension.
10. Assign atomic status with rationale.
11. Run tests and control validators.
12. Produce module summaries from atomic statuses; never infer atomic PASS from module GO.
13. Reopen falsely closed issues.
14. Create repair issues or append exact missing IDs to the governing issue.
15. After repairs, rerun the entire audit against the new exact head; do not mark only repaired rows PASS without checking regressions.

## Anti-false-positive rules

The auditor MUST NOT:

- count a generic `EconomicRuntime` method as satisfying every named service automatically;
- treat a JSONB generic ledger as proof that every required canonical object exists semantically;
- infer state-machine completeness from a subset of states;
- infer fixture coverage from unrelated fixtures;
- infer dashboard completeness from a read-only summary endpoint;
- infer provenance from an explanation string unless source/evidence identities are preserved;
- infer decay/expiry from timestamps unless runtime behavior and tests enforce it;
- infer capital/attribution learning gates from score fields unless promotion/rewiring/reallocation is actually blocked below threshold;
- mark a requirement PASS because it is planned, documented, or named in an acceptance report;
- close an issue while any mandatory requirement remains non-PASS.

## Audit outputs

Every audit run must generate:

- `reports/conformance/MOD-008-015-conformance.json` — machine-readable atomic matrix.
- `reports/conformance/MOD-008-015-conformance.md` — operator-readable full matrix.
- `reports/conformance/MOD-008-015-gap-register.json` — only non-PASS rows with owner issue and repair target.
- issue state corrections for #12–#15.
- a summary with counts per module and evidence dimension.

## Current known correction

Issue #13 was closed after aggregate runtime acceptance even though its required scope explicitly includes `LiquidityPreference`, `CounterpartyInteraction`, response-history weighting, complete disposition semantics, and opportunity decay/expiry. Repository search and implementation review identified missing or incomplete coverage. Issue #13 has therefore been reopened pending the atomic conformance audit.
