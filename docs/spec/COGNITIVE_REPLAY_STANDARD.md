# Cognitive Replay Standard

Purpose: reconstruct meaningful cognitive lineage from canonical persisted/event state.

## Replay questions
A valid replay can answer: what was observed; what evidence was available; what was believed and uncertain; what contradictions/gaps existed; what memories were retrieved; what held attention; what goals/drives affected selection; what affordances/plans were considered; what simulations were run; what governance gates fired; what action was selected; what outcome occurred; what was learned; what state changed afterward.

## Replay bundle
Required fields: replay_id, scope/time window, canonical event/object references, graph/provenance edges, epistemic snapshots, lifecycle transitions, retrieval/attention traces when available, candidate/selected affordances, simulation results, projection/governance decisions, action/outcome records, learning/plasticity deltas, unresolved gaps/conflicts, software/version/commit identifiers.

## Invariants
- Replay reads canonical history; it must not silently mutate live state.
- Rebuildable graph projections may support replay but cannot replace canonical persistence/event history.
- Missing telemetry is explicitly marked unavailable, not invented.
- Generated/dream/simulation content retains origin labels.
- Replay is deterministic for deterministic inputs/components; nondeterministic model calls require recorded inputs/outputs or explicit unavailable markers.
- External actions are not re-executed during replay.

## Acceptance
A fixture replay must reconstruct at least one complete evidence→belief/gap→affordance→decision/projection→outcome→learning chain and verify provenance continuity and zero external execution.