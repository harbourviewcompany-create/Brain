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
| Persistence uses the existing cognitive-object store | integration test | GO for bounded repository slice |
| Protected-main cognitive organs are preserved | exact-head regression tests | GO |
| #139 automatic prediction/outcome attribution remains authoritative | tests/test_cycle_auto_learning.py + learning regressions | GO |
| Full belief/curiosity/memory/planning/action protocol adapters | per-organ integration/replay evidence | HOLD |
| Tenant-aware persistence schema 019–022 | canonical runner + non-owner two-tenant RLS evidence | GO only in isolated CI; production HOLD |
| Production API/cockpit runtime role | non-owner, non-superuser, non-BYPASSRLS, non-service role evidence | HOLD until deployment evidence |
| Production worker role | separate constrained trusted-service role or tenant-by-tenant scheduler evidence | HOLD until deployment evidence |
| Durable tenant lifecycle administration | PostgreSQL-backed create/invite/membership/last-owner transaction tests | HOLD |
| Legacy tenant_id IS NULL ownership resolution | table-by-table ownership/backfill evidence | HOLD |
| PostgreSQL production restart replay evidence for cross-cutting objects | live migration + restart evidence | HOLD |
| Biological equivalence | external scientific evidence not available | HOLD / not claimed |

## Status semantics

`AGENT-XCUT-001` remains a bounded acceptance unit. Its protocol, persistence integration, deterministic tests, fixture, replay invariant and acceptance evidence may be GO without implying that every cognitive organ or tenant/deployment surface is complete.

The previously separate PR #100/#104/#105/#108/#109/#110 ancestry is now incorporated into protected-main history. Those PR numbers are no longer dependencies. The remaining HOLD is integration and production evidence: broad organ adapters, tenant/RLS deployment topology, durable tenant administration, worker tenant-by-tenant scheduling, legacy-row ownership and production restart replay.

## Hard failure conditions

HOLD the bounded slice if provenance can be omitted, confidence erases epistemic dimensions, competing conflict states are destructively overwritten, replay executes an external action, internal projection can bypass governance, learning can occur without attribution/evidence, plasticity can be applied without rollback evidence, or new storage competes with canonical event/PostgreSQL authority.

HOLD production tenant/RLS rollout if migrations 019–022 can apply without an explicit release gate, a separate migration identity, a non-owner/non-BYPASSRLS API runtime, a separately constrained worker identity, exact migration hashes, two-tenant cross-boundary denial and a documented legacy-row disposition.
