# Source Authority

## Purpose

This document defines how agents must classify Brain source material and implementation candidates.

The classification system exists to prevent unauthorized scope decisions. Agents classify material; they do not delete or narrow it.

## Required Labels

Every material concept, requirement, module, proposed primitive, review suggestion, schema, runtime action, or implementation claim must use one or more of the labels below.

## SOURCE

`SOURCE` means the material was supplied by Tyler, uploaded source, archived thread content, committed repository material, or directly extracted from preserved source packets.

Rules:

- Preserve exactly before transformation.
- Do not treat as automatically approved for implementation.
- Do not delete.
- Do not rewrite without retaining the original.
- Every derived artifact must trace back to the source location.

Required metadata:

- source ID
- source path or citation
- source type
- ingestion date
- preserving agent
- transformation status

## APPROVED

`APPROVED` means Tyler explicitly approved the item for a specific use, build slice, implementation phase, external action, or repo change.

Rules:

- Approval is specific, not global.
- Approval does not automatically apply to adjacent concepts.
- Preserve the exact approval instruction.
- Link the approval to the affected files, modules, schemas, or tickets.

Required metadata:

- approval statement
- approver
- approval timestamp
- approved action
- boundaries of approval
- expiration or review condition if any

## PROPOSAL

`PROPOSAL` means the material is suggested architecture, suggested implementation, review output, generated plan, or future candidate not yet approved for build.

Rules:

- Preserve.
- Do not implement unless converted to `APPROVED` or `BUILD-READY` through the required process.
- Mark dependencies, risks, and open questions.

Required metadata:

- proposing source
- target module or domain
- rationale
- unresolved assumptions
- required approval

## SPECULATIVE

`SPECULATIVE` means the item is theoretical, future-facing, experimental, biologically inspired without complete engineering specification, or not currently proven.

Rules:

- Preserve.
- Do not present as established fact.
- Do not convert into production behavior without approval and tests.
- Separate biological analogy from software behavior.

Required metadata:

- speculation type
- supporting source
- unknowns
- risks
- suggested validation path

## REVIEW-ONLY

`REVIEW-ONLY` means the item is intended for critique, comparison, red-team analysis, Claude/Grok/ChatGPT review, or discussion. It is not implementation authority.

Rules:

- Preserve reviewer content.
- Do not silently promote to build scope.
- Record critique and conflicts.
- Track accepted/rejected status only after Tyler direction.

Required metadata:

- reviewer
- review target
- review date
- suggestion summary
- Tyler decision status

## BLOCKED

`BLOCKED` means the item cannot proceed to implementation or external action because it lacks approval, source traceability, acceptance criteria, schema, tests, owner, state machine, safety decision, or conflict resolution.

Rules:

- Preserve.
- State the blocking reason.
- State the minimum unblock condition.
- Do not implement as production behavior.

Required metadata:

- blocker ID
- blocking condition
- affected module
- required resolver
- unblock criteria

## BUILD-READY

`BUILD-READY` means the item has enough detail to implement as a controlled repo slice.

An item is `BUILD-READY` only if it has:

- source trace
- approval trace
- owner object
- schema
- runtime service
- state machine
- input/output contract
- fixtures
- tests
- acceptance criteria
- audit events
- failure modes
- rollback or correction path where applicable
- GO/HOLD status

Rules:

- Build only the approved slice.
- Do not expand scope during implementation.
- File gaps separately instead of guessing.
- Provide acceptance evidence before completion.

## Label Promotion Rules

Material may move between labels only through documented action:

- `SOURCE` to `PROPOSAL`: extracted into a candidate design.
- `PROPOSAL` to `APPROVED`: Tyler explicitly approves.
- `APPROVED` to `BUILD-READY`: all implementation-readiness requirements are satisfied.
- `REVIEW-ONLY` to `PROPOSAL`: Tyler requests further structuring.
- `SPECULATIVE` to `PROPOSAL`: a bounded, non-factual design candidate is written.
- Any label to `BLOCKED`: required information, approval, safety, or tests are missing.

No agent may promote material to `APPROVED` by inference.

## Required Source Record Format

```yaml
source_record:
  id: "SRC-000"
  label: "SOURCE | APPROVED | PROPOSAL | SPECULATIVE | REVIEW-ONLY | BLOCKED | BUILD-READY"
  title: ""
  source_path: ""
  source_type: "instruction | upload | repo_file | review | generated_artifact | external_reference"
  supplied_by: "Tyler | agent | reviewer | repository"
  preserved_original: true
  transformed_artifacts: []
  approval_trace: null
  blocked_reason: null
  go_hold_status: "GO | HOLD | REVIEW | BLOCKED"
```

## Forbidden Classification Behavior

Agents must not:

- classify unapproved material as build-ready
- discard speculative material
- collapse contradictions
- treat reviewer content as approval
- treat current implementation as full scope
- treat absence from code as absence from The Brain
- treat a summary as a replacement for original source
