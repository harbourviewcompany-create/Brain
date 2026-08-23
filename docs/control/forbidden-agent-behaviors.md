# Forbidden Agent Behaviors

## Purpose

This document lists behaviors that are forbidden for any agent working on The Brain.

The purpose is to prevent unauthorized narrowing, source loss, false completion, and unsafe external action.

## Forbidden Scope Behavior

Agents must not:

1. Decide what The Brain is or is not.
2. Reduce The Brain to a chatbot, LLM wrapper, workflow engine, or generic agent framework.
3. Treat existing systems as ceilings on The Brain.
4. Treat current code as the full intended scope.
5. Remove speculative, theoretical, future, contradictory, or not-yet-buildable concepts.
6. Convert source material into a smaller version without preserving the original.
7. Replace Tyler's stated objective with an assistant-defined objective.
8. Treat absence of implementation as disapproval.
9. Treat difficulty as a reason to delete scope.
10. Treat biological uncertainty as permission to omit a software research surface.

## Forbidden Source Behavior

Agents must not:

1. Delete source material without explicit approval.
2. Summarize source as a replacement for source.
3. Omit inconvenient, contradictory, speculative, or difficult material.
4. Rewrite source without preserving original wording or a pointer to original wording.
5. Merge conflicting source claims without recording the conflict.
6. Promote review notes into approved build scope without Tyler approval.
7. Treat Claude, Grok, ChatGPT, Codex, or any reviewer as build authority.
8. Treat generated documents as source unless they are explicitly preserved and labeled.

## Forbidden Implementation Behavior

Agents must not:

1. Implement beyond the approved build slice.
2. Add external actions without approval gates.
3. Write production-affecting code without tests or validation.
4. Mark a module complete without owner, schema, runtime service, state machine, fixtures, tests, acceptance criteria, audit events, and GO/HOLD status.
5. Hide TODOs that block correctness.
6. Use vague names where stable IDs are required.
7. Create untraceable functions, schemas, states, events, or memory writes.
8. Hard-code behavior that should be governed by policy.
9. Remove tests to make a build pass.
10. Ignore failing tests in a completion claim.

## Forbidden External Action Behavior

Agents must not perform consequential external actions unless approved.

Forbidden without explicit approval:

- cloud provisioning
- production database mutation
- external API mutation
- sending emails or messages
- public posting
- payment or billing changes
- permission changes
- secret changes
- deployment
- merge to protected/default branches
- data deletion
- irreversible state mutation

## Forbidden Memory Behavior

Agents must not:

1. Write memory without source.
2. Write memory without confidence.
3. Write memory without scope.
4. Write memory without decay or supersession policy.
5. Write memory without audit trace.
6. Promote speculative material into fact memory.
7. Overwrite memory instead of superseding it.
8. Hide memory conflicts.

## Forbidden Review Behavior

Agents must not:

1. Treat review as approval.
2. Treat critique as scope reduction.
3. Delete reviewer disagreements.
4. Merge reviewer suggestions without Tyler decision.
5. Claim reviewer consensus when conflicts exist.
6. Use prior-art comparison to limit Tyler's objective.

## Forbidden Reporting Behavior

Agents must not:

1. Claim completion without evidence.
2. Claim tests passed if tests were not run.
3. Claim files were committed if only local files exist.
4. Claim binary files were uploaded if only file paths were written.
5. Hide connector limitations.
6. Hide failed tool calls that affect the outcome.
7. Report broad success when only partial work was completed.
8. End without unresolved gaps when gaps remain.

## Forbidden Architecture Behavior

Agents must not:

1. Collapse The Brain into a single model call.
2. Collapse memory into simple chat history.
3. Collapse governance into a prompt instruction.
4. Collapse belief management into free text.
5. Collapse action control into ordinary tool use.
6. Collapse learning into passive summarization.
7. Collapse emotion/body-state analogs into claims about real human physiology.
8. Collapse BrainScript into generic scripting without preserving its cognitive-control purpose.

## Required Correction Behavior

If an agent performs a forbidden behavior, the next agent must:

1. State the error.
2. Preserve the affected source.
3. Restore omitted or narrowed material where possible.
4. Create a blocker or correction record.
5. Avoid claiming the original task is complete until corrected.

## Final Rule

When in doubt, preserve more, classify more, test more, and claim less.
