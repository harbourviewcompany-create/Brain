# Acceptance Matrix Delta — Cross-Cutting Cognitive Architecture

| Requirement | Evidence required | Current status |
|---|---|---|
| Shared protocol does not duplicate canonical objects | reconciliation + type mappings | GO |
| Multi-axis epistemic state preserves confidence plus components | unit tests | GO |
| Provenance lineage is continuous and typed | invariant/replay test | GO |
| Contradictory states can coexist | conflict test | GO |
| Knowledge gaps are first-class and feed curiosity rationale | service test/fixture | GO |
| Cognitive affordance is distinct from EconomicAffordance | type/spec test | GO |
| Internal cognition cannot directly externalize | projection gate test | GO |
| Outcome learning requires attribution/provenance | service test | GO |
| Replay performs zero external actions | replay invariant | GO |
| Plasticity proposals retain before/after/evidence/rollback refs | unit test | GO |
| Persistence uses existing cognitive-object store | integration test | GO on PR #105 base |
| Full belief/curiosity/memory/planning/action organ wiring | per-organ integration/replay evidence | HOLD |
| PR #108/#109/#110 adoption | reconciled integration PRs | HOLD |
| Tenant-aware persistence reconciliation | PR #100/#104 integration evidence | HOLD |
| PostgreSQL production restart replay evidence for cross-cutting objects | live/clean migration + restart evidence | HOLD |
| Biological equivalence | external scientific evidence not available | HOLD / not claimed |

## Status semantics

`AGENT-XCUT-001` is a bounded acceptance unit. It is GO when its protocol, persistence integration, deterministic tests, fixture, replay invariant, acceptance report and registry deltas pass CI.

The larger twelve-capability cross-organ architecture program remains **PARTIAL GO** because the rows above marked HOLD have not yet produced their required integration/replay evidence. A GO report for the bounded slice must never be read as a claim that the full program is complete.

## Hard failure conditions

HOLD the bounded slice if provenance can be omitted, confidence erases epistemic dimensions, competing conflict states are destructively overwritten, replay executes an external action, internal projection can bypass governance, learning can occur without attribution/evidence, plasticity can be applied without rollback evidence, or new storage competes with canonical event/PostgreSQL authority.
