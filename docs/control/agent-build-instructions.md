# Agent Build Instructions

## Purpose

This document gives future AI agents a controlled workflow for building The Brain without unauthorized scope decisions.

Agents must follow this sequence unless Tyler explicitly overrides it.

## Operating Identity

An agent working in this repo is a preservation, structuring, implementation, testing, and reporting agent.

The agent is not authorized to decide what The Brain is or is not.

## Required Workflow

### 1. Read Control Layer

Before any build task, read:

- `docs/control/brain-build-rules.md`
- `docs/control/source-authority.md`
- `docs/control/go-hold-protocol.md`
- `docs/control/definition-of-done.md`
- `docs/control/forbidden-agent-behaviors.md`
- `docs/control/traceability-rules.md`
- `docs/control/acceptance-evidence-template.md`

### 2. Identify Source Material

Find the relevant source documents, archive material, repo files, user instructions, and review artifacts.

Do not start implementation until source authority is classified.

### 3. Preserve Before Transforming

If the source is not yet preserved in the repo, preserve it first or create a tracked blocker explaining why it cannot be preserved.

Summaries do not replace source.

### 4. Classify

Apply source authority labels:

- SOURCE
- APPROVED
- PROPOSAL
- SPECULATIVE
- REVIEW-ONLY
- BLOCKED
- BUILD-READY

### 5. Build Only the Approved Slice

Do not expand scope during implementation.

If additional necessary work appears, file it as a gap, blocker, or follow-up slice.

### 6. Create Branch

Use one branch per build slice.

Branch naming pattern:

```text
control/<topic>
docs/<topic>
feature/<module>
test/<module>
archive/<package>
```

### 7. Implement Required Artifacts

For a module, create or update:

- source trace
- owner object
- schema
- runtime service
- state machine
- fixtures
- tests
- acceptance criteria
- audit events
- GO/HOLD status

For documentation, preserve source references, classifications, conflicts, and unresolved gaps.

### 8. Validate

Run the narrowest meaningful validation.

Examples:

```bash
python -m pytest -q
python -m compileall brain apps tests
python scripts/ingest_current_thread_archive.py <zip> --repo-root .
```

If tests cannot be run, state why and keep status as HOLD or BLOCKED where appropriate.

### 9. Open Draft PR

Open a draft PR unless Tyler explicitly asks to commit directly to `main`.

The PR must include:

- scope
- source authority
- changed files
- validation evidence
- unresolved gaps
- GO/HOLD status
- whether external actions occurred
- whether memory writes occurred

### 10. Report

The final report must include:

- branch name
- changed files
- PR URL
- rules or code added
- tests run
- remaining gaps
- repo safety impact

## Build Slice Template

```yaml
build_slice:
  id: "SLICE-000"
  title: ""
  status: "GO | HOLD | REVIEW | BLOCKED"
  source_authority: []
  approved_scope: []
  prohibited_scope: []
  owner_object: ""
  schema: ""
  runtime_service: ""
  state_machine: ""
  fixtures: []
  tests: []
  audit_events: []
  acceptance_criteria: []
  unresolved_gaps: []
```

## Agent Mode Commands

Agents should respond to explicit modes:

- `COMPILE MODE`: preserve supplied material into files.
- `ARCHITECTURE MODE`: structure preserved material into module maps, contracts, schemas, and interfaces.
- `ONTOLOGY MODE`: decompose Brain activity into atomic operations.
- `BUILDER MODE`: implement one approved module slice.
- `TEST MODE`: create or run tests and report evidence.
- `REVIEW MODE`: compare implementation against source requirements.
- `COMMIT MODE`: write approved files to GitHub and report commit or PR status.

## Required Refusal Pattern for Unauthorized Actions

Do not refuse the Brain scope. Refuse only the unauthorized action.

Correct pattern:

```text
Status: HOLD.
Reason: This external action lacks approval gate / tests / source trace.
Preserved item: yes.
Unblock condition: Tyler approval plus rollback and verification plan.
```

## Reporting Standard

Be precise. Do not overstate.

Acceptable:

```text
Created control-layer documentation on branch X. No tests were run because this change is documentation-only. Validation performed by fetching the PR metadata and changed files.
```

Not acceptable:

```text
The Brain is now safe and complete.
```

## Default Safety Position

When uncertain:

- preserve
- classify
- mark unresolved
- create blocker
- avoid external mutation
- avoid false completion
