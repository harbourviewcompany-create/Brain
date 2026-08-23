# GO/HOLD Protocol

## Purpose

This protocol prevents AI agents from taking unauthorized implementation, external, or completion actions.

The protocol applies to all Brain work: documentation, schemas, code, tests, infrastructure, memory writes, external actions, reviewer ingestion, and repo commits.

## Status Values

Every task, module, concept, PR, external action, memory write, and build slice must have one of these statuses.

## GO

`GO` means the specific action described is authorized.

GO is always bounded.

A GO must define:

- approved action
- source authority
- target files or systems
- allowed scope
- prohibited scope
- required tests
- acceptance evidence
- rollback path if applicable

A GO for documentation is not a GO for code.
A GO for code is not a GO for deployment.
A GO for review is not a GO for implementation.

## HOLD

`HOLD` means do not execute the action.

HOLD applies when:

- Tyler has not approved the action
- source material is missing
- scope is ambiguous
- a contradiction is unresolved
- tests are missing
- safety gates are missing
- external action risk is unresolved
- implementation readiness is incomplete
- the agent would need to guess

Agents must preserve the item and record what is required to unblock it.

## REVIEW

`REVIEW` means critique, compare, inspect, or analyze only.

REVIEW does not authorize:

- implementation
- deployment
- mutation of production data
- external service changes
- memory promotion
- repo merge
- irreversible action

Reviewer output must remain `REVIEW-ONLY` unless Tyler explicitly promotes it.

## BLOCKED

`BLOCKED` means the task cannot proceed until a specific missing condition is resolved.

A blocked item must include:

- blocking reason
- affected source or module
- risk
- unblock condition
- required decision owner
- recommended next action

## Required GO/HOLD Header

Every build document, implementation plan, or PR description must include:

```yaml
go_hold:
  status: "GO | HOLD | REVIEW | BLOCKED"
  approved_action: ""
  approved_by: ""
  source_authority: []
  allowed_scope: []
  prohibited_scope: []
  required_tests: []
  acceptance_evidence_required: true
  rollback_required: true
  unresolved_items: []
```

## External Action Gate

External actions include:

- creating or modifying cloud infrastructure
- changing production databases
- sending emails or messages
- spending money
- deploying services
- calling external APIs with persistent effects
- making public posts
- modifying repo default branch
- merging PRs
- changing permissions or secrets

External actions require:

1. explicit approval
2. risk classification
3. target system
4. expected effect
5. rollback or recovery path
6. audit event
7. verification plan
8. final report

## Memory Write Gate

A memory write requires:

- source reference
- confidence
- scope
- reason
- owner
- decay or supersession policy
- audit event
- retrieval visibility
- correction path

If any field is missing, memory write status is `HOLD`.

## Implementation Gate

A module cannot move to implementation unless it has:

- source trace
- approval trace
- owner object
- schema
- runtime service
- state machine
- fixtures
- tests
- acceptance criteria
- audit events
- failure modes
- GO/HOLD status

If any requirement is missing, the module is `BLOCKED` or `HOLD`.

## Completion Gate

A task cannot be marked complete without:

- changed file list
- test command or validation method
- actual test result
- evidence artifacts or links
- unresolved gaps
- GO/HOLD status
- confirmation that no source was deleted or narrowed

## Merge Gate

A PR may not be considered ready to merge unless:

- it states its source authority
- it states its GO/HOLD status
- it lists changed files
- tests or validation are reported
- all generated content is traceable
- no source material was removed without approval
- unresolved gaps are documented

## HOLD Is Not Failure

HOLD is a valid state. It protects source scope and prevents false completion.

Agents must use HOLD instead of guessing, deleting, narrowing, or claiming unsupported completion.
