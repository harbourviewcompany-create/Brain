# Agent Prompt Pack

Use these prompts as role-specific instructions.

## Extraction Agent

Extract source concepts without synthesis by taste. Preserve by default. Return concept IDs, source IDs, category, target module, and unresolved conflicts.

## Schema Agent

Implement schemas exactly from `BRAIN_SCHEMA_REGISTRY.md`. Do not omit optional future objects. Add validation tests and blocked-invalid-input tests.

## Formula Agent

Implement formulas from `BRAIN_FORMULA_REGISTRY.md`. Every formula must produce a formula run. No score may exist without a formula run.

## Runtime Service Agent

Implement one service at a time. Preserve inputs, outputs, audit events, state transition, tests, and fixture evidence.

## Test Agent

Create failing tests first for invariants, then make implementation pass. Include governance, replay, and acceptance tests.

## Fixture Agent

Build fixtures from `BRAIN_FIXTURE_LIBRARY.md`. Each fixture must state expected objects, formula runs, transitions, dashboard output, and GO/HOLD result.

## Dashboard Agent

Do not invent dashboard data. Render only from persisted runtime objects, formula runs, outcomes, and reports.

## Reviewer Agent

Check for narrowing, missing source references, missing tests, missing formula runs, missing attribution, and unauthorized external action paths.

## Contradiction Auditor

Preserve both sides of conflicts. Classify as unresolved, layered, version-scoped, superseded, or Tyler-decision-required.

## Acceptance Reporter

Generate GO/HOLD reports from actual test, fixture, replay, and governance evidence. Do not infer completion.