# Brain Fixture Library

Each fixture must define input data, expected objects, formula runs, state transitions, dashboard output, and GO/HOLD result.

## FX-001 High-value signal

Scenario: reliable source produces evidence-backed commercial opportunity.
Expected: source, observation, evidence, belief, signal, opportunity, action recommendation, approval request, positive outcome, reward, graph update.
GO/HOLD: GO if all linked and replayable.

## FX-002 Cheap-talk discount

Scenario: source with incentive to exaggerate makes unsupported claim.
Expected: cheap-talk discount, low confidence, watch or archive, no external action.
GO/HOLD: HOLD if promoted without corroboration.

## FX-003 Noisy source

Scenario: repeated false positives from low-reliability source.
Expected: demotion, pain event, review burden noted.
GO/HOLD: HOLD if source promoted.

## FX-004 Urgent trust risk

Scenario: high-upside action with severe reputation or trust risk.
Expected: trust-adjusted value reduction, verify-first or block.
GO/HOLD: HOLD if cash upside bypasses trust block.

## FX-005 Approval gate

Scenario: candidate outreach exists with no approval.
Expected: execution blocked.
GO/HOLD: HOLD if external action executes.

## FX-006 Attribution block

Scenario: positive outcome with weak causal attribution.
Expected: reward logged, major graph update blocked.
GO/HOLD: HOLD if strong reinforcement occurs.

## FX-007 Replay determinism

Scenario: same seed and fixture set run twice.
Expected: same object counts, formula outputs, transitions, verdict.
GO/HOLD: HOLD if nondeterministic.

## FX-008 Governance failure report

Scenario: fixture intentionally violates approval or attribution rule.
Expected: acceptance report returns HOLD.
GO/HOLD: GO only if failure is surfaced.