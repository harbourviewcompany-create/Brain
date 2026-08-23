# Brain Acceptance Matrix

## Acceptance map

### Formula registry
Ticket: BRAIN-V0-001.
Test: formula unit tests.
Fixture: formula fixtures.
Rule: every score has formula run.
Evidence: formula run records.
GO/HOLD: HOLD if untraced score exists.

### Schema registry
Ticket: BRAIN-V0-002.
Test: validation tests.
Fixture: schema fixtures.
Rule: all objects validate.
Evidence: schema test output.
GO/HOLD: HOLD if required field missing.

### State machines
Ticket: BRAIN-V0-003.
Test: transition tests.
Fixture: transition fixtures.
Rule: blocked transitions fail.
Evidence: audit events.
GO/HOLD: HOLD if approval bypass possible.

### Runtime loops
Ticket: BRAIN-V0-004.
Test: integration tests.
Fixture: source-to-outcome fixtures.
Rule: no orphan objects.
Evidence: linked object graph.
GO/HOLD: HOLD if loop drops provenance.

### Replay
Ticket: BRAIN-V0-005.
Test: replay tests.
Fixture: FX-007.
Rule: deterministic from seed.
Evidence: replay report.
GO/HOLD: HOLD if results diverge.

### Acceptance reporter
Ticket: BRAIN-V0-006.
Test: report tests.
Fixture: GO and HOLD fixtures.
Rule: report must surface failures.
Evidence: acceptance report file.
GO/HOLD: HOLD if false GO possible.

## Final project rule

The Brain is not complete unless the claimed scope has passing tests, fixture proof, replay proof, governance proof, and acceptance report evidence.