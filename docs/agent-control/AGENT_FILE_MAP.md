# Agent File Map

## Source references

- `docs/brain-readable-concept-manual.md`: source-readable Brain corpus reference.
- `docs/spec/*`: executable agent specs.
- `docs/agent-control/*`: build governance and agent handoffs.
- `docs/architecture.md`, `docs/brain-function-map.md`, `docs/build-plan.md`: existing runtime context.

## Implementation modules

- `brain/domain.py`: current domain primitives.
- `brain/beliefs.py`: belief logic.
- `brain/attention.py`: attention scoring.
- `brain/rewiring.py`: graph rewiring primitives.
- `brain/reward.py`: reward logic.
- `brain/governance.py`: approval and permission gates.
- `brain/cycle.py`: cognitive cycle.
- `brain/runner.py`: continuous cognition runner.

## New target modules

- `brain/formulas.py`: formula registry and runs.
- `brain/schema.py`: canonical object validation.
- `brain/state_machine.py`: allowed transitions.
- `brain/runtime_loops.py`: named loops.
- `brain/reports.py`: acceptance reports.

## Tests

- `tests/test_formulas.py`
- `tests/test_schema.py`
- `tests/test_state_machines.py`
- `tests/test_runtime_loops.py`
- `tests/test_replay.py`
- `tests/test_acceptance_report.py`

## Fixtures

- `tests/fixtures/brain_v0.py`
- fixture names must match `docs/spec/BRAIN_FIXTURE_LIBRARY.md`.

## Reports

- generated reports belong under `reports/brain/` once the reporter exists.

## Dashboards

- dashboard surfaces are specified in `docs/spec/BRAIN_MODULE_MANIFEST.md` and implemented only after runtime objects and fixture data exist.