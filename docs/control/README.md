# Brain Control Layer

This directory contains the operating rules for AI agents building The Brain.

Agents must read these documents before planning, implementing, reviewing, committing, or reporting Brain work.

## Files

- `brain-build-rules.md` — root build rules and non-negotiable agent posture.
- `source-authority.md` — source classification labels and promotion rules.
- `go-hold-protocol.md` — GO/HOLD/REVIEW/BLOCKED action control.
- `definition-of-done.md` — completion requirements by artifact type.
- `agent-build-instructions.md` — step-by-step agent workflow.
- `forbidden-agent-behaviors.md` — prohibited scope, source, implementation, review, and reporting behavior.
- `traceability-rules.md` — source-to-test traceability requirements.
- `acceptance-evidence-template.md` — standard completion and PR evidence template.

## Root Principle

Tyler defines The Brain. Agents preserve, structure, implement, test, and report.

Agents classify material instead of deleting it, and they do not treat difficulty, novelty, speculation, contradiction, or lack of current implementation as permission to narrow scope.

## Required Preflight

Before any Brain build task, an agent must confirm:

```text
Control layer read: yes/no
Source authority classified: yes/no
GO/HOLD status known: yes/no
Traceability plan exists: yes/no
Acceptance evidence path exists: yes/no
```

If any answer is `no`, the task status is HOLD or BLOCKED until resolved.
