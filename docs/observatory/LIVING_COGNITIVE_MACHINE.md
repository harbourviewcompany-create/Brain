# Brain Living Cognitive Machine

Status: production UI authority for the Brain Observatory visual/interaction layer as of 2026-08-27.

This document supersedes the visual-direction language in `BRAIN_OBSERVATORY.md` where the two conflict. The underlying evidence, authentication, persistence, polling, BFF and runtime contracts remain governed by the existing Observatory architecture.

## Product contract

The Observatory is presented as an inspectable living cognitive machine. The visual may be anatomical, luminous and biomechanical, but every displayed cognitive claim must remain evidence-backed. Visual intensity must never imply data that the runtime did not expose.

The primary cognitive flow is:

`operator input → attention → working memory → evidence retrieval → competing hypotheses → predictions → agency/action → outcomes/feedback → learning`

The large central Brain is the navigation and explanatory surface, not decorative art. Persistent knowledge and live computation must be visually distinct. Missing state renders as unavailable or empty rather than as invented percentages, memories, actions or learning events.

## Canonical data mapping

| Visual region | Canonical source |
| --- | --- |
| Command intake/history | `POST /signals` with `operator_command` / `command_mode` metadata, then durable `signal.enqueued` events exposed by `GET /signals` |
| Attention | live `Signal.attention_score` and organism focus/self-state |
| Working memory | latest durable `cycle.completed.working_memory_size`; capacity only when observed in a `memory.working_stored` event |
| Memory retrieval | durable evidence from `GET /evidence`; Observatory retrieval score is explicitly a deterministic lexical + source-reliability projection |
| Hypotheses/conflict | beliefs plus contradiction/evidence links |
| Reasoning pathways | graph edges and their real weights/confidence/evidence links |
| Prediction | persisted Brain predictions |
| Action | cognitive-organism agency actions and approval/execution state |
| Feedback | durable `outcome.recorded` events exposed by `GET /outcomes` |
| Learning/evolution | durable attribution, rewire, resolution, outcome, memory, attention, cycle and night-phase events exposed by `GET /learning-events` |
| System health | health, durable runner counters, persistence state, self-state pressures, quarantine and read errors |

The standalone `MultiSystemMemory` retrieval engine is not presented as live production memory retrieval until it is actually wired into the canonical API runtime. The UI therefore labels its current retrieval surface as durable evidence search and explains the scoring formula.

## Command semantics

The quick actions (`Teach`, `Solve`, `Inspect`, `Challenge`, `Build Capability`, `Explain What Changed`) are operator-intent metadata on the canonical `POST /signals` event. They do not silently alter source reliability, evidence stance, urgency or other cognition weights. `process_now` remains false from this UI so the existing durable cognition worker/inline runner processes the command through the normal queue.

Binary attachment and voice ingestion controls may be visually present only as unavailable/disabled until canonical backend ingestion exists. They must not simulate successful ingestion.

## Traceability

A conclusion trace may connect only relationships that are explicitly stored:

- belief → linked supporting/contradicting evidence;
- belief → graph pathways with matching node IDs;
- belief → predictions by `belief_id`;
- prediction → outcome by `prediction_id`;
- outcome/pathway/prediction → learning event when the event payload explicitly references that ID.

No missing causal link may be inferred for presentation. The interface states this directly: missing links remain zero instead of being inferred.

## Responsive behavior

- Mobile preserves the selected vertical cognitive-machine composition and command intake near the top.
- Tablet keeps the central working-memory structure dominant while allowing retrieval/hypothesis regions to rebalance around it.
- Desktop expands the Brain spatially rather than converting the experience into a generic card dashboard.
- Deep inspection is available from whole brain → region → pathway → node → memory/evidence.
- The existing cognitive graph remains available as a full-screen whole-brain inspection layer.

## Accessibility and performance

- All cognitive regions and inspection objects are keyboard-focusable native controls.
- Essential information is never hover-only.
- Command result/error state uses an `aria-live` surface.
- Motion respects `prefers-reduced-motion` and also provides explicit Auto / Reduced / Off controls persisted as a local UI preference.
- No spatial or state animation may use `Math.random()` or fabricate runtime values.
- Loading, error and empty states remain distinguishable.

## Verification gates

A release is GO only when:

1. Observatory lint and TypeScript checks pass.
2. `test:observatory` confirms the BFF, real-data, command, evidence and learning-history contracts.
3. targeted API tests prove evidence stance/provenance and durable outcome/learning event projections.
4. the production build passes.
5. browser verification covers at least mobile, tablet and desktop widths, command submission error/success behavior, empty/degraded states, inspection depth, reduced motion and the full graph overlay.
6. no upstream API secret is exposed to the browser and the existing operator-session/BFF boundary remains intact.
