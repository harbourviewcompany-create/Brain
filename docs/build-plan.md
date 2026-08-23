# Brain Build Plan — v0.2 onward

## Build principle

The project does not reduce the Brain to an LLM or one algorithm. The implementation surface remains open to every identified biological/cognitive function. Known mechanisms can be implemented now; partially understood mechanisms support competing implementations; unknown mechanisms remain explicit research surfaces rather than being silently omitted.

## What v0.2 adds

- Versioned cognitive event protocol.
- Replayable state projections.
- Sensory, working, episodic, semantic, procedural, and prospective memory primitives.
- Bitemporal representation: world-valid time separated from knowledge-acquisition time.
- Neuromodulator state for global cognitive modulation.
- Homeostatic pressure and regulation.
- Finite cognitive-budget scheduler where cognitive processes compete for execution.
- Experiment harness for replaying cognitive history under alternate policies.
- Persistence migration for these concepts.

## Immediate cloud sequence

1. Provision Supabase/PostgreSQL as the canonical ledger and memory database.
2. Apply migrations 001 and 002 to a private schema; expose only control-plane views that require access.
3. Implement a `PostgresBrainStore` adapter behind the existing memory/store interface.
4. Add projection workers that rebuild materialized current-state views from `brain_events`.
5. Provision Temporal Cloud and move long-lived cognition (curiosity follow-ups, prediction resolution, consolidation, decay, dreams) into workflows.
6. Provision Neo4j AuraDB only as a materialized associative projection. Every graph mutation must originate from a ledger event so the graph remains rebuildable.
7. Implement working-memory sessions and memory consolidation/decay.
8. Implement the cortex/model interface so reasoning models remain replaceable.
9. Add prediction objects and explicit prediction-error events.
10. Add graph activation/spreading activation and plasticity rules.
11. Add homeostatic snapshots and neuromodulator updates to every cognitive cycle.
12. Add evaluation suites before autonomous external actions.

## Infrastructure staging

### Stage A — start now

- Supabase/PostgreSQL
- Temporal Cloud
- Neo4j AuraDB
- AWS S3
- Python workers on ECS/Fargate or equivalent managed containers
- FastAPI control API
- OpenTelemetry

### Stage B — after measurable throughput pressure

- Redpanda Cloud for high-volume replayable sensory streams
- Ray for large parallel simulations, dream workloads, and distributed model execution
- GPU workers / vLLM when local inference economics justify it

Adding Redpanda and Ray before workload measurements increases operational complexity without improving the cognitive model.

## Non-negotiable invariants

- History is append-only.
- Current state is a projection and may be destroyed/rebuilt.
- Models are replaceable.
- Graph topology is rebuildable.
- Dreams create hypotheses, never facts directly.
- Consequential rewiring retains provenance and rollback information.
- Reward signals cannot mutate protected goals or governance policies.
- Every autonomous cognitive process must have cost, observability, cancellation, and outcome measurement.
