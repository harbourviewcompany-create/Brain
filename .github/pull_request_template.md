# Brain PR Acceptance Evidence

## Control Preflight

- [ ] I read `docs/control/brain-build-rules.md`.
- [ ] I read `docs/control/source-authority.md`.
- [ ] I read `docs/control/go-hold-protocol.md`.
- [ ] I read `docs/control/definition-of-done.md`.
- [ ] I read `docs/control/traceability-rules.md`.
- [ ] I read `docs/control/forbidden-agent-behaviors.md`.
- [ ] I used `docs/control/acceptance-evidence-template.md` for this PR.

## Scope

Describe the exact approved build, control, archive, documentation, or review slice.

```text

```

## Source Authority

Every PR must classify its source material. Check every label used.

- [ ] SOURCE
- [ ] APPROVED
- [ ] PROPOSAL
- [ ] SPECULATIVE
- [ ] REVIEW-ONLY
- [ ] BLOCKED
- [ ] BUILD-READY

Source records:

| Source ID | Path / Citation | Label | Preserved Original | Notes |
|---|---|---|---|---|
| | | | yes/no | |

## GO/HOLD Status

- [ ] GO
- [ ] HOLD
- [ ] REVIEW
- [ ] BLOCKED

Reason:

```text

```

## Changed Files

List every changed file and whether it is source, control, schema, runtime, fixture, test, evidence, or generated artifact.

| Path | Artifact Type | Source ID | Notes |
|---|---|---|---|
| | | | |

## Module Completion Requirements

For any runtime/module implementation, every required field must be present or explicitly marked BLOCKED.

- [ ] owner object
- [ ] schema
- [ ] runtime service
- [ ] state machine
- [ ] fixtures
- [ ] tests
- [ ] acceptance criteria
- [ ] audit events
- [ ] GO/HOLD status

## Traceability

- [ ] Every implementation artifact traces to preserved source.
- [ ] Every requirement has a source record.
- [ ] Every test/fixture links to a requirement.
- [ ] No source material was deleted, narrowed, or summarized without preservation.

Missing trace links:

```text
none
```

## Tests / Validation

Command(s):

```bash

```

Result(s):

```text

```

If tests were not run, explain why and mark status HOLD/BLOCKED if appropriate.

## External Actions

- [ ] No external actions were taken.
- [ ] External actions were taken and are documented below.

If external actions occurred, include approval, target system, risk, rollback plan, and verification evidence.

```text

```

## Memory Writes

- [ ] No memory writes were made.
- [ ] Memory writes were made and are documented below.

If memory writes occurred, include source, confidence, scope, decay/supersession policy, and audit trace.

```text

```

## Acceptance Criteria

Satisfied:

- [ ] 

Not satisfied:

- [ ] 

## Unresolved Gaps

```text
none
```

## Source Preservation Statement

State whether any source was deleted, narrowed, filtered, summarized without preservation, or transformed.

```text

```

## Next Required Action

```text

```
