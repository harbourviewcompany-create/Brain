# Agent Task Queue

Use one ticket at a time. Every ticket requires handoff evidence.

## BRAIN-V0-001 Formula Registry

Objective: implement formula registry and formula-run logging.
Files: `brain/formulas.py`, `tests/test_formulas.py`, `docs/spec/BRAIN_FORMULA_REGISTRY.md`.
Types: `FormulaRegistryEntry`, `FormulaRun`.
Services: `FormulaRegistryService`.
Tests: deterministic, missing input, hard override.
Fixtures: formula fixture set.
Acceptance: every score can link to a formula run.
Blocked by: none.
GO/HOLD: HOLD if any score lacks trace.
Agent prompt: Build formula registry without changing formula doctrine.

## BRAIN-V0-002 Schema Registry

Objective: define canonical runtime objects.
Files: `brain/schema.py`, `tests/test_schema.py`.
Types: Source, Sensor, RawObservation, PerceptualEvent, EvidenceItem, Belief, Opportunity, CandidateAction, ApprovalRequest, Outcome, Prediction, RewardEvent, PainEvent, GraphEdge, DecisionExplanation, AcceptanceReport.
Tests: validation and enum coverage.
Fixtures: schema fixture set.
Acceptance: all objects validate.
Blocked by: BRAIN-V0-001 for formula references.
GO/HOLD: HOLD if required fields are missing.
Agent prompt: Build exact schemas with no omitted object families.

## BRAIN-V0-003 State Machines

Objective: enforce allowed transitions.
Files: `brain/state_machine.py`, `tests/test_state_machines.py`.
Services: `StateMachineService`.
Tests: allowed transitions and blocked transitions.
Fixtures: state transition fixture set.
Acceptance: no direct execution without approval.
Blocked by: BRAIN-V0-002.
GO/HOLD: HOLD if any prohibited transition passes.
Agent prompt: Implement explicit state machines and audit events.

## BRAIN-V0-004 Core Runtime Loops

Objective: wire ingestion, perception, belief, opportunity, approval, outcome, reward, graph, and acceptance loops.
Files: `brain/runtime_loops.py`, `tests/test_runtime_loops.py`.
Services: loop services from `BRAIN_RUNTIME_LOOPS.md`.
Tests: integration loop tests.
Fixtures: V0 golden fixtures.
Acceptance: source-to-outcome loop creates linked records.
Blocked by: V0-001 to V0-003.
GO/HOLD: HOLD if any loop creates unlinked objects.
Agent prompt: Implement runtime loops with formula trace and audit trail.

## BRAIN-V0-005 Golden Fixtures

Objective: implement fixture library and replay harness.
Files: `tests/fixtures/brain_v0.py`, `tests/test_replay.py`.
Tests: deterministic replay.
Fixtures: all `BRAIN_FIXTURE_LIBRARY.md` fixtures.
Acceptance: same seed produces same results.
Blocked by: V0-004.
GO/HOLD: HOLD if replay diverges.
Agent prompt: Build deterministic fixtures and replay proof.

## BRAIN-V0-006 Acceptance Reporter

Objective: generate GO/HOLD reports.
Files: `brain/reports.py`, `tests/test_acceptance_report.py`.
Services: `AcceptanceReportService`.
Tests: GO and HOLD reports.
Fixtures: passing and failing fixture runs.
Acceptance: report lists tests, fixtures, failures, and evidence.
Blocked by: V0-005.
GO/HOLD: HOLD if report omits failures.
Agent prompt: Build acceptance reporter that cannot fake completion.