# Brain Runtime

A cloud-native, event-sourced, self-rewiring cognitive runtime.

## What this repository is

This repository is the first executable substrate for the Brain discussed in the project: evidence-backed beliefs, explicit uncertainty, a mutable relationship topology, attention allocation, contradiction handling, curiosity, offline recombination, outcome reward, resource allocation, and human-governed external action.

It is intentionally **not** an LLM wrapper. Language/reasoning models are replaceable tools used by cognitive organs; they are not the Brain's persistent identity.

## Why this architecture

Human-brain equivalence cannot currently be specified honestly because neuroscience does not yet explain every brain function mechanistically. The design therefore supports an expanding registry of cognitive functions instead of pretending unknown functions are solved.

## Recommended production cloud

1. Supabase/PostgreSQL: canonical event ledger and structured memory.
2. Neo4j AuraDB: graph projection / associative topology.
3. Temporal Cloud: durable cognition workflows.
4. Python workers: cognition and model adapters.
5. Vercel + Next.js: operator control plane.
6. Object storage: raw evidence/artifacts.

PostgreSQL is canonical. Neo4j is rebuildable. This prevents the graph engine from becoming a single irreversible source of truth.

## Local start

```bash
docker compose -f infra/docker-compose.yml up -d
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn apps.api.main:app --reload
```

Test:

```bash
pytest
```

Minimal cognitive loop:

```bash
curl -X POST http://127.0.0.1:8000/beliefs \
  -H 'content-type: application/json' \
  -d '{"statement":"A market is expanding","confidence":0.6}'
```

Then POST evidence to `/learn` using the returned belief ID.

## Build sequence

### Slice 1 — executable substrate (included)
- Domain objects
- In-memory executable runtime
- Belief updating
- Contradiction detection
- Attention scoring
- Rewiring primitives
- Curiosity tasks
- Dream hypotheses
- Debate shell
- Reward system
- Capital allocation primitive
- Governance gate
- PostgreSQL schema

### Slice 2 — persistence
- Postgres event-store adapter
- Supabase auth/RLS
- Neo4j projection writer
- projection rebuild command
- outbox pattern

### Slice 3 — durable cognition
- Temporal workflows for sensing, evidence processing, belief decay, dreams and outcomes
- source connector SDK
- task scheduling / retry / idempotency

### Slice 4 — model cortex
- provider-neutral model interface
- extraction model
- entity-resolution model
- hypothesis generator
- skeptic / judge evaluators
- calibration logging

### Slice 5 — control plane
- Graph explorer
- Belief ledger
- Contradiction inbox
- Curiosity queue
- Approval queue
- Rewire timeline
- Resource/cost telemetry

### Slice 6 — research expansion
- causal simulation
- counterfactuals
- working memory
- homeostasis
- social cognition
- richer neuromodulatory state
- embodied sensor/action adapters where useful

## Guardrail

The Brain may autonomously modify internal belief and graph state under bounded, reversible rules. Consequential external actions remain permissioned unless explicitly enabled by policy.

## Agent Build Control Docs

The Brain is being built primarily by AI agents. These documents are the agent-executable control layer.

### Agent control

- [Agent Build Master](docs/agent-control/AGENT_BUILD_MASTER.md)
- [Agent Rules](docs/agent-control/AGENT_RULES.md)
- [Agent Task Queue](docs/agent-control/AGENT_TASK_QUEUE.md)
- [Agent File Map](docs/agent-control/AGENT_FILE_MAP.md)
- [Agent Prompt Pack](docs/agent-control/AGENT_PROMPT_PACK.md)
- [Agent Acceptance Protocol](docs/agent-control/AGENT_ACCEPTANCE_PROTOCOL.md)
- [Agent Handoff Template](docs/agent-control/AGENT_HANDOFF_TEMPLATE.md)
- [Issue Generation](docs/agent-control/ISSUE_GENERATION.md)

### Build specs

- [Canonical Scope](docs/spec/BRAIN_CANONICAL_SCOPE.md)
- [Module Manifest](docs/spec/BRAIN_MODULE_MANIFEST.md)
- [Formula Registry](docs/spec/BRAIN_FORMULA_REGISTRY.md)
- [Schema Registry](docs/spec/BRAIN_SCHEMA_REGISTRY.md)
- [State Machines](docs/spec/BRAIN_STATE_MACHINES.md)
- [Runtime Loops](docs/spec/BRAIN_RUNTIME_LOOPS.md)
- [Fixture Library](docs/spec/BRAIN_FIXTURE_LIBRARY.md)
- [Acceptance Matrix](docs/spec/BRAIN_ACCEPTANCE_MATRIX.md)
- [Source-to-Build Traceability](docs/spec/BRAIN_SOURCE_TO_BUILD_TRACEABILITY.md)
- [Capital Source Intelligence Registry](docs/spec/CAPITAL_SOURCE_INTELLIGENCE_REGISTRY.md)

### Machine-readable control files

- [agent-control.json](docs/agent-control/agent-control.json)
- [task-queue.json](docs/agent-control/task-queue.json)
- [module-manifest.json](docs/spec/module-manifest.json)
- [formula-registry.json](docs/spec/formula-registry.json)
- [schema-registry.json](docs/spec/schema-registry.json)
- [acceptance-matrix.json](docs/spec/acceptance-matrix.json)
- [source-to-build-traceability.json](docs/spec/source-to-build-traceability.json)
- [source-intelligence-registry.json](docs/spec/source-intelligence-registry.json)

### Reports and fixtures

- [Agent Run Reports](reports/agent-runs/README.md)
- [Acceptance Reports](reports/acceptance/README.md)
- [GO/HOLD Reports](reports/go-hold/README.md)
- [Brain Fixtures](tests/fixtures/brain/)

### CI gate

Agent-control validation runs in CI through:

```bash
python tools/validate_agent_control.py
```

This gate proves control artifacts are present and internally linked. It does not prove the Brain is fully built.

## v0.2 cognitive substrate

Version 0.2 adds memory-class primitives, bitemporal cognition, neuromodulator state, homeostasis, finite cognitive-budget scheduling, replayable projections, and cognitive experimentation. See `docs/build-plan.md`.

Run tests:

```bash
python -m pytest -q
```

Focused source-intelligence verification result: 12 tests passing.
