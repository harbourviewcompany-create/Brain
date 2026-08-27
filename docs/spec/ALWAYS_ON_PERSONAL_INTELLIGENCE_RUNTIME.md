# Always-On Personal Intelligence Runtime

## Source authority

```yaml
source_record:
  id: SRC-BRAIN-ALWAYS-ON-20260827
  label: SOURCE
  source_type: instruction
  supplied_by: Tyler
  preserving_agent: ChatGPT
  transformed_artifacts:
    - brain/heartbeat.py
    - brain/adapters/cognition.py
    - tests/test_always_on_durable_runtime.py
  approval_trace: SRC-BRAIN-EXECUTE-20260827
  go_hold_status: GO
```

```yaml
source_record:
  id: SRC-BRAIN-EXECUTE-20260827
  label: APPROVED
  source_type: instruction
  supplied_by: Tyler
  approved_action: Execute the engineering required to advance the Brain toward the preserved always-on personal-intelligence objective.
  boundaries_of_approval: Repository implementation and verification are approved by the current instruction. New paid services, credentials, billing changes, destructive production changes, and unverified production migration expansion remain separate decisions.
  go_hold_status: GO
```

## Preserved source

The following operator instructions are preserved verbatim as implementation authority and scope; this document does not replace the conversation source.

> “This should be constantly running. It’s supposed to be learning and developing on its own. It’s a brain. It should never stop. I want this brain to be my own assistant that will get smarter and better over time. It will do what I program it to do but it’s capable of learning on it own so I want it to be teaching itself how to get more intelligent”

> “I want it to start seeding data from everything. News, sports, history, the world. I want it to start making predictions if I want. I want it to know what’s happening everywhere and keep my updated. I want it to be commercially intelligent if I need it to be. This needs to be a super intelligent brain that does what I ask it to do. But I want it already capable and super intelligent”

> “You are the world most elite designer and full stack developer. Execute this engineering better than Ai ever does”

## Canonical objective

The Brain is a persistent personal intelligence system whose default state is active cognition. It combines pretrained model capability with durable memory, evidence-backed world state, continuous perception, prediction, outcome learning, metacognition, self-directed curriculum and specialist capabilities. It must remain general rather than being reduced to a chatbot, a single commercial-intelligence product, a sports system, or a single model call.

Process restarts are expected infrastructure events. “Never stop” is implemented as cognitive continuity: durable state, automatic restart/recovery, resumable work and truthful liveness measurement rather than an impossible claim that one operating-system process can never terminate.

## Preserved full-scope requirements

| Requirement ID | Required behavior | Status in this slice |
|---|---|---|
| REQ-ALWAYS-ON-001 | Cognition runs continuously without requiring an operator HTTP request. | implementation in progress |
| REQ-ALWAYS-ON-002 | API ingress and cognition workers use one durable sensory stream. | implemented by this slice |
| REQ-ALWAYS-ON-003 | Cognitive cycle history survives process restarts and is visible to observability surfaces. | implemented by this slice |
| REQ-ALWAYS-ON-004 | Durable beliefs are rehydrated without duplicating bootstrap beliefs on restart. | implemented by this slice |
| REQ-ALWAYS-ON-005 | Predictions, outcomes and learning use durable stores when PostgreSQL is configured. | implemented by this slice for HeartbeatService; worker-maintenance convergence remains follow-up |
| REQ-WORLD-001 | Seed and continuously update a broad world model spanning news, government/regulation, business, markets, sports, science/technology, history, geography/physical-world events, geopolitics, health, law, employment, supply chains and culture using authorized accessible sources. | preserved; not narrowed; follow-up runtime slice |
| REQ-WORLD-002 | Every material world claim carries provenance, observed time, relevant world-valid time, confidence and contradiction state. | preserved; existing world/source systems to be extended |
| REQ-WORLD-003 | Coverage and freshness gaps are measured rather than hidden. | preserved; follow-up observability slice |
| REQ-PRED-001 | Brain can create explicit probabilistic predictions on request and autonomously when policy warrants. | preserved; existing prediction engine present |
| REQ-PRED-002 | Predictions have resolution criteria/horizon and are scored against outcomes for calibration. | preserved; follow-up prediction-ledger convergence |
| REQ-COMM-001 | Commercial intelligence is a high-performance specialist capability of the general Brain, not the Brain’s identity ceiling. | preserved |
| REQ-SELF-001 | Brain identifies capability weaknesses, creates a curriculum, tests candidate improvements against benchmarks and retains improvements only when measured performance improves. | preserved; existing developmental/metacognitive modules present |
| REQ-ASSIST-001 | Brain serves as the operator’s general assistant and follows operator-programmed objectives and permissions. | preserved |
| REQ-OBS-001 | Observatory distinguishes API health from cognition liveness and shows real durable change: cycles, observations, beliefs, predictions, learning, development, source coverage and freshness. | preserved; follow-up observability slice |
| REQ-MODEL-001 | Foundation/reasoning models are replaceable cognitive resources; accumulated Brain memory and learned state remain independent of a single provider. | preserved |

## Build slice: SLICE-ALWAYS-ON-P0

Owner object: `HeartbeatService` / `ContinuousCognitionRunner` runtime boundary.

Schema: existing `public.sensory_inbox` and `public.cognitive_cycle_runs` from the continuous-cognition migration; existing durable belief/prediction/learning schemas remain authoritative.

Runtime service: API heartbeat and worker heartbeat converge on PostgreSQL-backed queue/run/learning adapters when a database is configured.

State machine: sensory item `pending -> processing -> completed | pending(retry) | failed`; cognition continues into endogenous work when the external queue is empty.

Audit/events: existing `signal.enqueued`, cognitive-cycle events, belief events and prediction/learning events remain authoritative.

Failure behavior: a configured durable runtime must not silently report successful queue/cycle state solely from volatile in-process data.

Rollback: revert the P0 commits/PR; no new database migration is introduced by this slice.

GO/HOLD: **GO for repository implementation and CI verification.** Production topology expansion, new paid feeds/model providers, credentials, or migration scope above the currently approved production ceiling require separate verified execution gates.

## Acceptance criteria for SLICE-ALWAYS-ON-P0

1. A PostgreSQL-backed heartbeat selects `PostgresSensoryInbox` rather than the in-memory queue.
2. API `perceive()` inserts exactly one durable queue item and preserves its UUID in the API contract.
3. Queue status has a consistent `pending/processing/completed/failed/total` contract across memory and PostgreSQL adapters.
4. Completed cognitive cycles are written to `CognitiveCycleRunStore` when PostgreSQL is configured.
5. `build_default_heartbeat()` selects durable prediction, edge, attribution and source stores when PostgreSQL is configured.
6. Bootstrap is idempotent against already-hydrated foundational belief statements.
7. Existing in-memory tests continue to work.
8. Required repository CI passes before merge.

## Explicitly unresolved implementation work

This P0 slice fixes a root persistence/wiring defect; it is not a claim that the full Brain objective is complete. The next implementation slices must converge the dedicated 24/7 worker, prediction maintenance, world-source registry/ingestion, historical seeding, temporal world model, coverage control, model routing, metacognitive benchmark loop and Observatory truth surface. Those requirements remain in scope above and must not be discarded merely because they are sequenced after P0.
