# NEURO-006 Global Workspace Proxy

Status: APPROVED for bounded software proxy implementation. HOLD for consciousness, sentience, phenomenal experience and human-brain equivalence claims.

## Purpose

The Global Workspace Proxy is the Brain control layer for what becomes globally available to downstream cognitive services during a bounded cognition step.

It is not a consciousness claim. It is an access, competition, suppression, broadcast and traceability mechanism.

## Required objects

- GlobalWorkspaceFrame
- WorkspaceItem
- WorkspaceCompetition
- WorkspaceBroadcast
- SuppressedAlternative
- AttentionAccessDecision
- WorkspaceTrace

## Executable runtime anchor

NEURO-006 uses the existing `brain.developmental.global_workspace.GlobalWorkspaceService` runtime as the first executable service. It records candidate items, requires evidence references, selects the highest-priority candidate, preserves suppressed alternatives and broadcasts to explicit consumer modules with `consciousness_claim = False`.

## Required frame fields

- frame_id
- active_goals
- active_memories
- active_conflicts
- top_signals
- selected_interpretation
- suppressed_alternatives
- uncertainty_map
- affective_or_modulatory_state
- available_actions
- approval_constraints
- predicted_consequences
- current_self_state
- current_world_state
- explanation_trace

## State machine

`candidate_registered -> competition_open -> winner_selected -> alternatives_suppressed -> broadcast_recorded -> frame_archived`.

Invalid transitions:

- No broadcast without candidates.
- No broadcast without consumers.
- No candidate without evidence.
- No consciousness or sentience claim.
- No external action execution from workspace broadcast.

## Acceptance criteria

- Workspace candidates require evidence references.
- Winner selection is deterministic by priority for a fixed candidate set.
- Suppressed alternatives are preserved.
- Broadcasts record consumer modules and evidence references.
- Broadcasts explicitly set `consciousness_claim` to false.
- Workspace records can be persisted in global workspace tables.
- Future memory, perception, action, affect, self-model and immune layers can consume the frame without narrowing scope.
