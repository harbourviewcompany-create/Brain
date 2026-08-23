# Brain Agent Issue Generation

Status: issue-backed task-control specification.

Every build task should exist in two places:

1. `docs/agent-control/task-queue.json`
2. A GitHub issue using the same `ticket_id`

Required issue title format:

```text
[AGENT-###] <task title>
```

Required labels when labels are available:

```text
brain-agent-task
module
schema
formula
fixture
acceptance
blocked
GO-HOLD
```

Required issue body sections:

```text
## Objective
## Files to create or modify
## Required schemas/types
## Required services
## Required formulas
## Required tests
## Required fixtures
## Acceptance criteria
## Blocked by
## GO/HOLD rule
## Required handoff
```

Agents may not close an issue unless the final comment includes:

```text
tests_run:
fixtures_used:
evidence_paths:
acceptance_report:
go_hold_verdict:
```

The issue is not the source of truth by itself. It is an execution wrapper around the canonical docs and machine-readable control files.
