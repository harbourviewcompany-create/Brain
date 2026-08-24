# Brain Durable Developmental Evidence Ledger

Status: APPROVED IMPLEMENTATION SPEC FOR AGENT-019.

## Objective

Make AGENT-017 metacognitive history and AGENT-018 controlled improvement-experiment history durable across process restarts. Longitudinal intelligence-growth evidence must not disappear when a worker restarts.

## Storage model

The persistence model separates latest typed snapshots from append-only evidence history:

- `developmental_evidence_objects`: latest JSONB snapshot keyed by `(kind, id)`.
- `developmental_evidence_events`: ordered append-only event ledger with sequence, record kind/id, typed payload and evidence refs.

Snapshot upsert is allowed. Normal runtime update/delete of historical evidence events is not.

## Typed records

The codec supports AGENT-017/018 records including benchmarks, benchmark runs, regressions, hypotheses, learning debt, optimization plans, experiment candidates, experiments, runs, results and rollback records. UUID, datetime and enum identities are preserved.

Unknown record or enum types fail closed. The codec does not silently coerce unknown future types.

## Runtime services

- `DevelopmentalEvidenceCodec`: typed JSON-safe encode/decode.
- `InMemoryDevelopmentalEvidenceStore`: deterministic reference implementation.
- `PostgresDevelopmentalEvidenceStore`: durable snapshot + event writer/reader.
- `DevelopmentalReplayService`: ordered restart reconstruction and integrity reporting.

## Replay rules

1. Events replay strictly by sequence.
2. Sequence gaps fail closed.
3. Record identity in payload must match event identity.
4. Every event requires evidence refs.
5. Later events may replace a latest snapshot but do not remove prior events.
6. Failed, rejected and HOLD experiment evidence remains available after hydration.
7. Unresolved regressions remain visible after hydration.

## Authority boundary

This layer persists evidence only. It grants no authority to mutate source code, merge pull requests, deploy, spend, contact external parties or otherwise perform consequential action.

## Deployment boundary

Repository conformance can GO when codec, stores, migration, replay, fixtures, tests, traceability and reports pass exact-head CI. Execution of migration `011_developmental_evidence_ledger.sql` against a production database remains environment-specific deployment work.
