# Traceability Rules

## Purpose

Traceability prevents source loss, unauthorized scope decisions, and false implementation claims.

Every Brain concept must be traceable from source to classification to design to implementation to test evidence.

## Traceability Chain

Every implemented item must support this chain:

```text
Source -> Classification -> Approval -> Design Artifact -> Implementation Artifact -> Test Fixture -> Test Result -> Acceptance Evidence
```

If any link is missing, the item is not complete.

## Required IDs

Agents must assign stable IDs where possible.

Recommended formats:

```text
SRC-000        source record
REQ-000        requirement
CONCEPT-000    preserved concept
CONFLICT-000   source conflict
MODULE-000     module
STATE-000      state object
EVENT-000      audit event
ERR-000        error code
FIXTURE-000    test fixture
TEST-000       test case
SLICE-000      build slice
PR-000         pull request trace
```

## Source Trace Requirements

Every derived item must record:

- source ID
- source path or citation
- source authority label
- preserving agent
- transformation type
- date created
- unresolved source gaps

## Requirement Trace Requirements

Every requirement must record:

- requirement ID
- source ID
- source wording or exact pointer
- classification label
- affected module
- required behavior
- forbidden behavior
- test requirement
- GO/HOLD status

## Module Trace Requirements

Every module must record:

- module ID
- source IDs
- requirement IDs
- owner object
- schemas
- runtime services
- state machines
- audit events
- tests
- acceptance criteria
- implementation phase
- GO/HOLD status

## Memory Trace Requirements

Every memory write must record:

- source ID
- confidence
- scope
- timestamp
- author or agent
- reason
- decay policy
- supersession policy
- audit event ID
- retrieval visibility
- correction path

## External Action Trace Requirements

Every external action must record:

- action ID
- approval ID
- target system
- requested effect
- risk class
- permission gate
- rollback path
- verification method
- audit event
- result

## Test Trace Requirements

Every test must record:

- test ID
- requirement ID
- module ID
- fixture ID
- command
- expected result
- actual result
- pass/fail/block status
- evidence path

## Conflict Trace Requirements

Every conflict must record:

- conflict ID
- source A
- source B
- conflict summary
- affected module or requirement
- risk
- proposed options
- Tyler decision status
- current GO/HOLD status

## PR Trace Requirements

Every PR must include:

- build slice ID
- source authority labels
- changed files
- requirement IDs addressed
- tests or validation run
- acceptance evidence
- unresolved gaps
- external actions taken
- memory writes made
- GO/HOLD status

## Traceability Matrix Template

```markdown
| ID | Type | Source | Classification | Artifact | Test | Status | Notes |
|---|---|---|---|---|---|---|---|
| REQ-000 | requirement | SRC-000 | APPROVED | path/file.md | TEST-000 | GO | |
```

## No Orphan Rule

No implementation artifact may be orphaned.

An artifact is orphaned if it lacks:

- source trace
- requirement trace
- owner module
- validation path
- GO/HOLD status

Orphaned artifacts must be marked BLOCKED until traceability is restored.

## No Summary Replacement Rule

A summary can support navigation, but it cannot replace source.

Every summary must point to preserved source. If the preserved source is missing, the summary must be labeled incomplete and BLOCKED.

## Traceability Enforcement

Agents must check traceability before claiming completion.

Required statement:

```text
Traceability checked: yes/no.
Missing trace links: none/list.
```

If traceability is incomplete, completion status must be HOLD or BLOCKED.
