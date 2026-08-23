# Acceptance Evidence Template

## Purpose

This template defines the minimum evidence required when an agent reports Brain work as complete, blocked, review-only, or ready for Tyler approval.

Agents must copy this structure into PR descriptions, completion reports, or build-slice reports when applicable.

## Acceptance Evidence Record

```yaml
acceptance_evidence:
  task_id: ""
  title: ""
  status: "GO | HOLD | REVIEW | BLOCKED"
  branch: ""
  pull_request: ""
  source_authority:
    - "SOURCE"
    - "APPROVED"
    - "PROPOSAL"
    - "SPECULATIVE"
    - "REVIEW-ONLY"
    - "BLOCKED"
    - "BUILD-READY"
  changed_files: []
  source_records: []
  requirement_records: []
  tests_run: []
  validation_run: []
  test_results: []
  external_actions_taken: []
  memory_writes_made: []
  acceptance_criteria:
    satisfied: []
    not_satisfied: []
  unresolved_gaps: []
  blockers: []
  traceability_checked: false
  missing_trace_links: []
  source_preservation_statement: ""
  next_required_action: ""
```

## Markdown Report Template

```markdown
# Acceptance Evidence

## Status

GO | HOLD | REVIEW | BLOCKED

## Scope

Describe the exact approved task scope.

## Source Authority

List labels used:

- SOURCE:
- APPROVED:
- PROPOSAL:
- SPECULATIVE:
- REVIEW-ONLY:
- BLOCKED:
- BUILD-READY:

## Changed Files

- `path/to/file`

## Source Records

| Source ID | Path / Citation | Label | Preserved Original | Notes |
|---|---|---|---|---|

## Requirements Addressed

| Requirement ID | Source ID | Artifact | Status | Notes |
|---|---|---|---|---|

## Tests / Validation

Command:

```bash

```

Result:

```text

```

If tests were not run, explain why.

## Acceptance Criteria

Satisfied:

- [ ] criterion

Not satisfied:

- [ ] criterion

## External Actions

State whether any external actions were taken.

If yes, include approval ID, target system, risk, rollback, and verification.

## Memory Writes

State whether any memory writes were made.

If yes, include source, confidence, scope, decay/supersession policy, and audit event.

## Traceability

Traceability checked: yes/no.

Missing trace links:

- none or list

## Source Preservation Statement

State whether any source was deleted, narrowed, summarized without preservation, or transformed.

## Unresolved Gaps

- gap

## Blockers

- blocker

## Next Required Action

- action
```

## Required Validation Language

Agents must use exact language when applicable:

```text
Tests were not run because this is documentation-only. Validation consisted of verifying the branch, changed files, and PR metadata.
```

or:

```text
Tests were run with: <command>. Result: <result>.
```

## Incomplete Work Language

If work is incomplete, agents must state:

```text
Status: HOLD or BLOCKED. This task is not complete because <reason>.
```

## False Evidence Prohibited

Agents must not:

- invent test results
- hide failed tests
- claim a PR exists without verifying it
- claim source preservation without preserved source or pointer
- claim binary upload when only a file path was written
- claim approval without Tyler approval
- claim BUILD-READY without all required fields
