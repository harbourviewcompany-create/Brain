> Canonical Brain copy. Source preserved from `harbourviewcompany-create/brain-control-plane@03e3c462ff8f8233033457fc703c418d21200b32`. Paths beginning with `src/` refer to `apps/observatory/src/` in the consolidated repository.

# Brain Observatory — Product and Interaction Architecture

Status: implementation authority for `feat/brain-observatory-v1-20260824`.

## Mission

Replace the dashboard metaphor with a production-grade observatory for the live Brain runtime. The interface must show what Brain is actually processing and retaining, not decorate empty state with fake cognition. Every visible node, relation, pulse, warning, count, label, or motion must derive from a real API response, a deterministic relation between real objects, or a clearly labeled client-observed snapshot diff.

The core interaction is **Observe → Inspect → Understand → Intervene**.

## Current backend contract used by the observatory

The browser remains isolated from upstream credentials and calls same-origin `/api/brain/*`. The existing BFF remains authoritative and continues to use Vercel deployment OIDC as the primary upstream identity with server-only `BRAIN_API_KEY` fallback.

The observatory consumes only existing Brain surfaces:

- `/health`
- `/runner/status`
- `/signals`
- `/beliefs`
- `/predictions`
- `/edges`
- `/contradictions`
- `/curiosity`
- `/sources`
- `/approvals`
- `/opportunities`
- `/outcomes`
- `/organism/cockpit`
- `/organism/self-state`
- `/organism/curiosity`
- `/organism/agency-actions`
- `/organism/quarantine`
- `/organism/persistence/status`

No Brain migration, runtime route, authentication rule, database semantics, or Railway deployment configuration is changed by this frontend rebuild.

## Information architecture

### 1. Cognitive Field

The home route becomes a full-viewport spatial read model instead of a grid of panels.

Semantic zones are deterministic:

- **Perception rim** — durable `Signal` objects enter at the field perimeter.
- **Belief lattice** — persisted `Belief` objects form the central stable knowledge structure.
- **Contradiction tension** — open contradiction objects create explicit tension relations to affected beliefs.
- **Curiosity frontier** — unresolved curiosity tasks occupy the outer exploratory arc.
- **Prediction horizon** — predictions project to the right/future side of the field.
- **Outcome return path** — outcomes resolve from the prediction horizon back toward learning/central state.
- **Agency gate** — approvals and organism agency actions appear at the lower action boundary.
- **Source perimeter** — observed sources live at the outer left boundary and connect to signals when an exact source identity is available.
- **Memory depth** — the field renders working-memory pressure and memory pressure as depth bands. Individual memory objects are not fabricated because there is currently no compatible live memory-object list endpoint.
- **Organism center** — organism/self-state is the center of gravity when available. If unavailable, the center is explicitly labeled as runtime state rather than inventing a self-model.

Coordinates are deterministic from object IDs and semantic category. Objects never jump randomly between renders.

### 2. System Pulse

A compact instrumentation strip replaces the old `B / E / P` header.

It shows only observable state:

- connection/runtime status;
- Brain version and persistence mode;
- heartbeat tick count;
- inbox and working-memory size;
- current focus summary when Brain reports one;
- active pressure signals derived from contradiction, curiosity, quarantine, and approval state;
- live/scrubbed timeline mode.

State labels:

- `DEGRADED` when health/BFF reads fail;
- `ACTIVE` when the latest durable signal is recent, runner inbox is non-zero, or live cognitive pressure is non-zero;
- `QUIET` when connected but no current activity evidence exists;
- `OBSERVING` while the first snapshot is loading.

The UI does not call the Brain “thinking” unless an explicit backend state says so.

### 3. Thought Inspector

Selecting any rendered object opens a contextual inspector rather than navigating away.

The inspector exposes:

- human-readable primary meaning first;
- object type and ID second;
- timestamps and source/provenance identifiers;
- confidence/attention/priority/probability values as applicable;
- linked object IDs and deterministic visible relations;
- raw metadata only behind a disclosure layer;
- route links to existing deep pages when they provide a real intervention or detailed record view.

Desktop: right-side floating sheet.

Mobile: bottom sheet with safe-area spacing and large touch targets.

### 4. Cognition Timeline

The first release provides two truthful temporal layers:

1. **Object chronology** from real `created_at` / `updated_at` timestamps exposed by current APIs.
2. **Observed-session replay** captured by the browser as timestamped live snapshots during the current session.

The timeline never claims full historical Brain event replay because a complete event-history endpoint is not currently exposed through the production BFF.

Scrubbing freezes the Cognitive Field to an observed snapshot. Returning to `LIVE` resumes polling.

### 5. Intervene dock

The dock provides deliberate exits to existing real operator surfaces:

- Perception
- Beliefs
- Predictions
- Curiosity
- Approvals
- Organism
- Sources

It is navigation, not fabricated cognitive control.

Desktop: left-side vertical rail with semantic labels.

Mobile: four-primary-action bottom dock plus an expandable `MORE` sheet.

## Data-to-visual mapping

| Brain data | Visual meaning |
|---|---|
| signal attention score | glyph radius + local halo intensity |
| signal novelty | outer ring eccentricity / label metric |
| signal urgency | pulse cadence only when urgency > 0 |
| belief confidence | structural opacity + core radius |
| belief state | stroke grammar, never position alone |
| contradiction pressure | explicit tension edge amplitude |
| curiosity priority | frontier distance and arc weight |
| prediction confidence/probability | horizon trajectory opacity |
| prediction status | trajectory endpoint grammar |
| outcome prediction accuracy | return-path solidity |
| source trust score | source glyph opacity |
| quarantined source | isolated boundary marker |
| runner inbox | perception-rim load indicator |
| heartbeat ticks | system pulse number; no fake heartbeat animation from wall-clock time |
| working memory size | central working-memory band thickness |
| organism memory pressure | depth-field density |
| organism current focus summary | System Pulse focus text |

Animation is state-driven. Reduced-motion mode removes path travel and pulsing while preserving all semantic distinctions.

## Visual system

The product should feel like a scientific instrument for a non-biological cognitive runtime, not an anatomical brain and not a neon cyberpunk dashboard.

### Palette

- near-black graphite field;
- cool white for stable structure;
- electric blue for perception/attention;
- violet for beliefs/memory association;
- cyan for predictions/future projection;
- amber for uncertainty/curiosity;
- vermilion only for active contradiction/quarantine/failure;
- green only for validated healthy state or resolved outcomes.

Color is never the only carrier of meaning.

### Typography

- system grotesk for interpretation and labels;
- system mono for IDs, timestamps, numeric metrics and machine state;
- human-readable content always precedes identifiers.

### Geometry

- no global card grid;
- thin reference lines and depth rings;
- asymmetric spatial composition;
- contextual sheets float over the field without boxing every datum;
- secondary legacy pages inherit the new global palette but remain available for detailed records.

## Component architecture

- `BrainObservatory` — orchestration, selected object, live/scrub state.
- `useBrainObservatory` — polling, normalization, session snapshots, read errors.
- `buildCognitiveScene` — pure deterministic data-to-scene transformation.
- `CognitiveField` — Canvas 2D renderer plus accessible DOM hit targets/labels.
- `SystemPulse` — runtime/heartbeat/focus instrumentation.
- `ThoughtInspector` — contextual semantic record inspection.
- `CognitionTimeline` — observed-session snapshots and object chronology.
- `ObservatoryDock` — navigation/intervention boundary.

Canvas 2D is intentionally used instead of WebGL/R3F for V1 because the current production object volume is low, the semantic topology is primarily planar, mobile accessibility matters, and Canvas avoids adding a GPU-heavy dependency before the data volume justifies it. The renderer is isolated so it can be replaced by WebGL later without changing the normalized scene contract.

## Polling and snapshot model

- default live poll: 5 seconds;
- concurrent endpoint reads via `Promise.allSettled`;
- partial failures preserve successful data and surface exact read degradation;
- snapshot history is bounded to 120 snapshots in memory;
- identical snapshots are coalesced so a quiet Brain does not produce fake timeline activity;
- hidden tabs reduce polling frequency;
- scrubbing pauses live scene replacement but background refresh may continue so `LIVE` can resume immediately.

## Mobile architecture

Mobile is not a stacked desktop dashboard.

- Cognitive Field fills the screen beneath a compact System Pulse.
- Labels are aggressively reduced; selected objects get full meaning in the bottom Thought Inspector.
- DPR is capped at 1.5.
- Canvas redraw rate is capped and stops when document visibility is hidden.
- touch targets are minimum 44px.
- bottom dock honors `env(safe-area-inset-bottom)`.
- timeline becomes a horizontal scrub strip above the dock.
- no hover-only interaction.

## Accessibility

- every scene object is mirrored as a keyboard-focusable DOM target;
- inspector state is announced with semantic headings;
- all metrics have textual values;
- reduced motion is respected;
- focus rings remain visible;
- contrast remains readable without glow;
- Canvas is supplemental visualization, never the sole source of information.

## Performance

- Canvas renderer uses one animation loop only when state requires motion;
- deterministic positions are cached by scene key;
- device pixel ratio capped at 2 desktop / 1.5 mobile;
- node count is bounded visually with density aggregation only after full data remains available to inspector/search;
- no random particle systems;
- no perpetual animation during dormant state;
- observer disconnects and animation frames are cleaned up on unmount.

## Empty and dormant states

Empty state is meaningful system state, not placeholder UI.

Examples:

- `PERCEPTION QUIET — no durable signals returned by Brain.`
- `BELIEF FIELD UNFORMED — Brain reports zero persisted beliefs.`
- `PREDICTION HORIZON CLEAR — no predictions are currently exposed.`

A quiet Brain produces a quiet field.

## V1 implementation sequence

1. Add normalized observatory types and pure scene builder.
2. Extend browser-safe API client for runner status and graph edges.
3. Add live polling/session snapshot hook.
4. Replace root layout and root page with Observatory shell.
5. Implement Canvas Cognitive Field and accessible interaction mirror.
6. Implement System Pulse, Thought Inspector, Timeline and Dock.
7. Replace global visual system while retaining compatibility variables for existing detail routes.
8. Add verification workflow for lint, TypeScript, production build and production BFF read smoke.
9. Deploy PR preview, inspect desktop/mobile output, repair until green.

## Acceptance criteria

- no backend or BFF authentication changes;
- no mock data imported by Observatory code;
- no random or decorative activity unrelated to Brain state;
- root route is no longer a card-grid dashboard;
- field renders real signals and any available beliefs/predictions/contradictions/curiosity/outcomes;
- empty collections remain visibly meaningful;
- selected objects expose human-readable meaning and exact metrics;
- observed-session replay works without claiming durable historical replay;
- mobile is purpose-designed rather than stacked desktop layout;
- reduced-motion and keyboard interaction work;
- lint, typecheck and production build pass;
- production BFF health/signals/organism protected reads remain successful;
- Brain repository and Railway production state remain untouched.
