# Definition of Done

## Purpose

This document defines the minimum evidence required before any agent may claim that Brain work is complete.

The Brain is not complete because a file exists. Work is complete only when the approved slice has source traceability, implementation evidence, validation, and unresolved gaps documented.

## Universal Definition of Done

Every task must satisfy the following before completion may be claimed:

1. The task scope is explicitly stated.
2. The source authority labels are recorded.
3. No supplied material was deleted, narrowed, or silently omitted.
4. All changed files are listed.
5. Tests or validation steps are listed.
6. Actual test or validation results are reported.
7. Acceptance criteria are checked.
8. Unresolved gaps are documented.
9. GO/HOLD status is recorded.
10. Next required action is stated.

## Documentation Done

A documentation task is done only when it includes:

- source trace
- classification labels
- preservation of original source or pointer to original source
- affected domains or modules
- unresolved questions
- conflicts if any
- clear distinction between source, proposal, review, and approved build scope

Documentation that summarizes source without preserving or linking original source is not done.

## Module Design Done

A module design is done only when it includes:

- module owner object
- domain boundary
- source authority
- input contract
- output contract
- state objects
- state machine
- memory reads
- memory writes
- audit events
- error codes
- failure modes
- governance gates
- fixtures
- tests
- acceptance criteria
- implementation phase
- GO/HOLD status

## Code Implementation Done

A code implementation is done only when it includes:

- source trace
- approved scope
- implementation files
- unit tests
- integration tests when relevant
- fixtures
- validation command
- passing result or explicit failure report
- runtime error handling
- audit event emission if state changes occur
- rollback or correction path for mutations
- no unauthorized external action

## Schema Done

A schema is done only when it includes:

- table or object ownership
- field definitions
- constraints
- indexes where needed
- migration file
- rollback or supersession strategy
- RLS or access policy where applicable
- fixture data
- tests or validation queries
- audit implications

## Runtime Service Done

A runtime service is done only when it includes:

- service purpose
- owner module
- callable interface
- input validation
- output object
- error codes
- state transition behavior
- audit events
- memory read/write behavior
- authorization behavior
- tests
- observability hooks or TODO if deferred

## State Machine Done

A state machine is done only when it includes:

- states
- transitions
- triggers
- guards
- failure transitions
- terminal states
- retry behavior
- audit events
- tests for allowed and forbidden transitions

## External Action Done

An external action implementation is done only when it includes:

- approval gate
- permission check
- target system
- risk class
- dry-run or preview behavior where possible
- audit event
- rollback or recovery plan
- verification method
- tests for blocked and approved paths

## Memory Write Done

A memory write feature is done only when it records:

- source
- confidence
- scope
- timestamp
- author or agent
- reason
- decay policy
- supersession policy
- audit event
- retrieval visibility
- correction path

## Review Ingestion Done

A review ingestion task is done only when it records:

- reviewer identity
- review target
- review content
- source authority label
- accepted/rejected/pending status
- conflicts with existing source
- Tyler approval status
- whether implementation is GO, HOLD, REVIEW, or BLOCKED

## PR Done

A PR is ready for review only when it includes:

- summary
- source authority
- changed files
- tests or validation
- acceptance evidence
- unresolved gaps
- GO/HOLD status
- no false completion claims

## Completion Report Template

```markdown
## Completion Report

Status: GO | HOLD | REVIEW | BLOCKED

Scope:

Source authority:

Changed files:

Tests or validation run:

Results:

Acceptance criteria satisfied:

Acceptance criteria not satisfied:

Unresolved gaps:

External actions taken:

Memory writes made:

Source preservation statement:

Next required action:
```

## False Completion

The following are false completion claims:

- claiming a module is built without tests
- claiming source is preserved when only a summary exists
- claiming approval from reviewer suggestions
- claiming external action safety without gates
- claiming memory correctness without source/confidence/scope/decay
- claiming The Brain is complete when only a slice is implemented
