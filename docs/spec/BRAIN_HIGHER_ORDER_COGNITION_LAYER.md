# Brain Higher-Order Cognition Layer

Status: AGENT-016 implementation control and runtime spec.

This layer extends the Developmental Intelligence Runtime V0 with a higher-order cognition substrate. It does not replace the commercial money spine, developmental runtime, approval gates, source-rights gates, cognitive immune system, self-model, or unknown-mechanism registry.

## Purpose

The goal is to make the Brain more capable over time by giving it explicit runtime objects for:

- multi-scale cognition maps;
- brain-region translation as bounded runtime analogy, not biological equivalence;
- causal world-model hypotheses with preserved alternatives;
- curriculum self-design that creates learning tasks only;
- benchmark-driven metacognition;
- long-horizon developmental stage tracking.

## Hard boundaries

The layer may not claim that the Brain is biologically equivalent to a human brain. It may not claim consciousness. It may not claim superior intelligence without benchmark evidence. It may not execute external actions. It may not activate a new module without schema, service, fixture, replay, tests, dashboard and acceptance evidence.

## Runtime file

`brain/developmental/higher_order_cognition.py`

## Primary objects

- `ScaleNode`
- `ScaleLink`
- `BrainRegionMapping`
- `CausalHypothesis`
- `CurriculumTask`
- `BenchmarkRecord`
- `DevelopmentalStageRecord`

## Services

`HigherOrderCognitionService` owns:

- multi-scale node creation;
- cross-scale evidence links;
- brain-region mapping boundary checks;
- causal hypothesis registration;
- curriculum task proposal;
- benchmark evidence recording;
- developmental stage entry;
- claim-boundary reporting.

## Required tests

`tests/test_developmental_higher_order_cognition.py` verifies:

- scale nodes require source refs;
- scale links require existing nodes and evidence;
- unsupported neuroscience equivalence claims are blocked;
- causal hypotheses preserve alternatives;
- curriculum tasks cannot execute external action;
- benchmark claims require evidence;
- advanced developmental stage transitions require capability evidence.

## Fixture

`tests/fixtures/brain/higher_order_cognition_cycle.json`

## Operator surface

`docs/operator-surfaces/higher-order-cognition-dashboard.json`

## GO/HOLD

GO for AGENT-016 when runtime, tests, fixture, dashboard and acceptance report exist.

HOLD for any claim that the Brain is complete, conscious, biologically equivalent to a brain, or more intelligent than all existing systems without external benchmark evidence.
