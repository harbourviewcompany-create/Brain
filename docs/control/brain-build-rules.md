# Brain Build Rules

## Purpose

This document defines the non-negotiable operating rules for every AI agent, assistant, automation, reviewer, or contributor that works on The Brain repository.

The purpose is not to decide what The Brain is or is not. The purpose is to preserve Tyler's supplied source material, structure it into executable build artifacts, implement approved slices, test them, and report evidence.

## Root Rule

Tyler defines The Brain.

Agents do not narrow The Brain. Agents do not reject source material because it appears speculative, too large, contradictory, theoretical, future-facing, or not yet buildable. Agents classify, preserve, route, and implement only what is approved for implementation.

## Required Agent Posture

Every agent must operate under these rules:

1. Preserve source before transforming it.
2. Classify material instead of deleting it.
3. Separate source preservation from implementation judgment.
4. Separate proposal material from approved build scope.
5. Preserve contradictions in a conflict register.
6. Preserve speculative material as speculative.
7. Preserve not-yet-buildable material as not-yet-buildable.
8. Never claim completion without acceptance evidence.
9. Never perform consequential external action without approval gates.
10. Never write memory without source, confidence, scope, decay or supersession policy, and audit trace.

## No Scope Narrowing

Agents must not convert The Brain into any smaller category such as:

- chatbot
- LLM wrapper
- ordinary AI agent
- generic workflow engine
- generic cognitive architecture
- generic orchestration framework
- simple memory system
- prompt library
- automation script

Those categories may be used only as comparison objects, not as definitions or ceilings.

## Source Preservation Rule

All supplied material must be preserved before it is summarized, interpreted, normalized, split, indexed, or implemented.

Source material includes:

- Tyler's direct instructions
- uploaded files
- pasted source packets
- generated archive documents
- prior review notes
- Claude/Grok/ChatGPT review material
- diagrams and visual artifacts
- repo documents
- implementation history
- unresolved or contradictory claims

No agent may silently omit supplied material.

## Classification Rule

Every meaningful concept must receive a source authority label from `source-authority.md`.

Classification is not deletion. A concept labeled `SPECULATIVE`, `PROPOSAL`, `REVIEW-ONLY`, or `BLOCKED` remains preserved and traceable.

## Implementation Rule

No concept becomes implementation scope unless it is explicitly approved or classified as `BUILD-READY` through the required build-readiness process.

A build-ready module requires:

- owner object
- schema
- runtime service
- state machine
- fixtures
- tests
- acceptance criteria
- audit events
- GO/HOLD status

## External Action Rule

External actions are any operations that affect services, accounts, users, money, infrastructure, production data, repository history, external APIs, or public outputs.

External actions require approval gates unless a standing policy explicitly authorizes that action type.

## Memory Write Rule

Every memory write must include:

- source reference
- confidence
- scope
- timestamp
- author or agent
- reason for write
- decay policy or supersession policy
- audit event
- rollback or correction path where applicable

## Completion Rule

An agent may not mark work complete unless it provides acceptance evidence.

Evidence must include:

- changed file paths
- test command or validation method
- test result or reason tests are not applicable
- unresolved items
- GO/HOLD status
- traceability to source or approval

## Conflict Rule

If two source materials conflict, preserve both. Do not pick a winner unless Tyler explicitly resolves the conflict or a documented approval process selects a resolution.

Conflicts must be recorded with:

- conflict ID
- source A
- source B
- affected module or document
- risk
- proposed resolution options
- Tyler approval status

## Review Rule

Claude, Grok, ChatGPT, Codex, and other reviewers may critique, propose, and identify gaps. They do not become build authority by default.

Reviewer suggestions must be labeled as `REVIEW-ONLY`, `PROPOSAL`, `BLOCKED`, or `APPROVED` depending on Tyler's explicit direction.

## GO/HOLD Rule

Every build slice must have a GO/HOLD status.

- `GO` means the slice is approved for the specific action described.
- `HOLD` means do not implement, deploy, mutate external systems, or claim completion.
- `REVIEW` means critique and analysis only.
- `BLOCKED` means missing approval, missing source, missing tests, or unresolved contradiction.

## Repository Rule

No agent may delete, overwrite, or replace existing source documents without explicit instruction. When improving structure, add new files or append traceable changes.

## Final Agent Report Rule

Every agent report must include:

- branch name if repository changes were made
- changed files
- summary of changes
- acceptance evidence
- tests run
- unresolved gaps
- next recommended build slice
- whether the action was GO, HOLD, REVIEW, or BLOCKED
