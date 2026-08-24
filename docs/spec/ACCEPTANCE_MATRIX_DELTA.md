# Acceptance Matrix Delta — Cross-Cutting Cognitive Architecture

| Requirement | Evidence required | Current branch target |
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
| PostgreSQL production replay evidence | live/clean migration + restart evidence | HOLD with PR #105 deployment gates |
| Biological equivalence | external scientific evidence not available | HOLD / not claimed |

## GO rule
This branch may report PARTIAL GO when the protocol slice, persistence adapter integration, deterministic tests, fixture, replay evidence artifact and registry deltas are complete while broad organ-by-organ integration remains explicitly HOLD.

## Hard failure conditions
HOLD if provenance can be omitted, confidence erases epistemic dimensions, replay executes an external action, internal projection can bypass governance, contradictory states are destructively overwritten, or new storage competes with canonical event/PostgreSQL authority.