# Agent Acceptance Protocol

## Unit acceptance

Each module must include unit tests for deterministic behavior, invalid inputs, missing fields, hard overrides, and edge cases.

## Integration acceptance

Each implemented loop must create linked objects from input through output. No orphan records are accepted.

## Replay acceptance

Fixtures must replay from seed with the same object counts, formula outputs, state transitions, and GO/HOLD result.

## Fixture acceptance

Each fixture must define input data, expected objects, expected formulas, expected transitions, expected dashboard state, and expected verdict.

## Governance acceptance

External action cannot execute without approval. Blocked evidence cannot update semantic memory. Reward cannot propagate without attribution.

## UI acceptance

Dashboards may only be accepted after runtime data exists. Smoke tests must show fixture-backed values.

## Final GO/HOLD acceptance

GO requires passing unit, integration, replay, fixture, governance, and acceptance report tests for the claimed scope. HOLD if any required evidence is missing.

## Evidence required

Agent handoffs must include files changed, tests run, commands, outputs, fixtures used, reports generated, and unresolved issues.