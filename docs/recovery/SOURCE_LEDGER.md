# Source Ledger

Status: recovery-stage ledger. This file preserves the source-state split produced during the Brain source-recovery pass.

## Object families

| Family | Current state | Treatment |
|---|---|---|
| Brain-Corpus | Missing / HOLD | Do not implement until canonical corpus artifacts are recovered |
| Brain-Registry | Missing / HOLD | Do not update canonical registry until registry and source handoff are recovered |
| Brain-Beta | Referenced but inaccessible / HOLD | Treat only as possible fixture or demo pending source recovery |
| Brain-Manual | Referenced but inaccessible / HOLD | Treat only as reference pending manual recovery and mapping |
| Shared-Brain | Partially recovered / GO for audit only | Use as coordination/control source only |

## Recovered control sources

| ID | Source | Classification | Allowed use |
|---|---|---|---|
| SRC-025 | Notion HARBOURVIEW SHARED BRAIN | Canonical for coordination | Audit coordination structure only |
| SRC-026 | Notion SHARED MEMORY | Canonical for current project state | Use for state and blockers only |
| SRC-027 | Linear HAR-70 | Canonical for execution constraints | Use for gates and evidence rules |
| SRC-028 | Airtable PRJ-BRAIN-001 | Canonical project-control row | Use for HOLD and acceptance framing |

## Missing or inaccessible blocking sources

| ID | Artifact | Family | Status |
|---|---|---|---|
| SRC-003 | BRAIN_MULTI_MODEL_SYNTHESIS_PACKAGE | Brain-Corpus | Missing |
| SRC-004 | Brain Master Corpus | Brain-Corpus | Missing |
| SRC-005 | Brain Function Registry | Brain-Registry | Missing |
| SRC-006 | BRAIN_FORMULA_COMPLETENESS_PATCH.md | Brain-Corpus | Missing |
| SRC-007 | BRAIN_V0_IMPLEMENTATION_TICKETS.md | Implementation plan | Missing |
| SRC-008 | BRAIN_EXACT_SCHEMAS_AND_STATE_MACHINES.md | Contract/spec | Missing |
| SRC-009 | BRAIN_GOLDEN_FIXTURE_LIBRARY.md | Testing/fixtures | Missing |
| SRC-010 | BRAIN_SECURITY_GOVERNANCE_APPENDIX.md | Governance | Missing |
| SRC-011 | BRAIN_COST_BUDGET_CONTROL_APPENDIX.md | Cost governance | Missing |
| SRC-012 | BRAIN_DECISION_EXPLANATION_SCHEMA.md | Explainability | Missing |
| SRC-013 | BRAIN_OUTCOME_ATTRIBUTION_MODEL.md | Learning loop | Missing |
| SRC-014 | BRAIN_CALIBRATION_BACKTESTING_PLAN.md | Validation | Missing |
| SRC-015 | Brain Missing Components Register v2 | Gap control | Missing |
| SRC-016 | PR 1 source-discovery handoff | Source governance | Missing |
| SRC-017 | Contaminated SQL/TypeScript snippets | Contaminated reference | Unavailable; do-not-copy default |
| SRC-018 | Appendix Z / registry-delta refinements | Brain-Registry | Missing |
| SRC-019 | Compact forbidden-code list | Source exclusion | Missing |
| SRC-020 | Exact route/RLS/test/dashboard names | Registry metadata | Missing |
| SRC-021 | Brain Beta source package | Brain-Beta | Inaccessible |
| SRC-022 | Brain Beta audit report | Brain-Beta | Referenced but inaccessible |
| SRC-023 | Brain Master Manual V2 | Brain-Manual | Referenced but inaccessible |
| SRC-024 | Brain Master Manual V3 builder/source | Brain-Manual | Referenced but inaccessible |

## Default rule

Anything not recovered remains HOLD. Do not infer source authority from memory, summaries, or absence from the current repo.
