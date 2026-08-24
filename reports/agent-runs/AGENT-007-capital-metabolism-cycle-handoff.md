# AGENT-007 Capital Metabolism Cycle Handoff

## Issue

#130 — Wire CapitalLedger metabolism into cognitive homeostasis and scheduling.

## Work completed

This implementation closes the gap between isolated metabolism tests and the running cognitive cycle.

Changed runtime files:

- `brain/cycle.py`
- `brain/cognitive_state.py`
- `brain/metabolism.py` remains the source of `CapitalLedger` and `MetabolismEngine`.

## Runtime behavior

A `CognitiveCycle` can now receive an optional `CapitalLedger`. When present:

1. every `process()` tick calls `MetabolismEngine.metabolize()`;
2. emitted metabolism events are correlated to the cycle;
3. the current ledger deficit becomes `HomeostaticState.budget_pressure`;
4. `HomeostasisEngine.regulate()` updates scheduler-relevant neuromodulators;
5. starvation adds an internal `pursue_capital_recovery` cognitive task;
6. positive `capital_outcome_amount` on a stimulus credits the ledger through `capital.fed`.

## Dilution resolution

The prior known defect was that one starving budget dimension was diluted to roughly one-sixth of stress. This pass explicitly treats capital scarcity as hunger by applying asymmetric budget weighting in `HomeostaticState.stress_index`. A starved ledger can now dominate scheduling without requiring unrelated uncertainty or operator-load pressure.

## Tests

Added/updated `tests/test_metabolism.py` coverage for:

- capital pressure reaching `CognitiveCycle` at runtime;
- starvation dominating action selection without compounding pressure;
- outcome credit feeding the ledger through a tested path;
- prior isolated metabolism behavior remaining intact.

## Fixture

Added `tests/fixtures/brain/capital_starvation_cycle.json`.

## Acceptance evidence

Added:

- `reports/acceptance/AGENT-007-capital-metabolism-cycle.json`
- `reports/go-hold/AGENT-007-CAPITAL-METABOLISM-GO-HOLD.json`

## HOLD boundaries

- No external action is introduced.
- No autonomous spend is introduced.
- Production persistence for live ledger state remains separate deployment work.
- Full Brain completion remains HOLD.
