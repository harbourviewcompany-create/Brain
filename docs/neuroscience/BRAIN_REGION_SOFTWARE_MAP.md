# Brain Region Software Map

Status: Slice NEURO-002 region translation map.

This document translates brain regions and large-scale neural systems into software responsibilities. It is a functional engineering map, not a claim of literal biological equivalence.

## Non-claim rule

Every region entry must say what the software analogue does, what it does not claim, how it fails, where it is stored, which service owns it and which dashboard exposes it. Region analogies may guide implementation but may not be used as evidence that the Brain is conscious, sentient or equivalent to a biological brain.

## Required region fields

Each region row maps to:

- region_id
- name
- biological_scope
- software_equivalent
- owner_object
- runtime_service
- database_table
- signals_handled
- implemented_state
- does_not_claim_literal_equivalence
- failure_modes
- dashboard
- acceptance_criteria

## Required region/system coverage

| Region/system | Software role | Dashboard |
|---|---|---|
| prefrontal_cortex | goal management, planning, task switching and executive inhibition | Action Selection Console |
| orbitofrontal_cortex | context-sensitive value comparison and reversal learning | Value/Choice Console |
| anterior_cingulate_cortex | conflict, error, effort and uncertainty pressure monitoring | Contradiction Inbox |
| insula | interoception, risk pressure and internal state awareness | Affect/Homeostasis Console |
| hippocampus | episodic indexing, context binding and replay | Memory Systems Console |
| entorhinal_cortex | coordinate systems for concepts, place, relationships and route finding | Cognitive Map Console |
| amygdala | threat salience, urgency and relevance tagging | Threat/Relevance Console |
| basal_ganglia | action gating, habit loops and go/no-go selection | Action Selection Console |
| dopamine_system | prediction error, motivation, salience and exploration pressure | Affect/Homeostasis Console |
| serotonin_system | patience, inhibition, stability and harm avoidance | Affect/Homeostasis Console |
| norepinephrine_system | alertness, surprise, volatility response and attention reset | Affect/Homeostasis Console |
| acetylcholine_system | precision weighting, attention and sensory learning | Perception Pipeline Console |
| thalamus | routing, gating and relay between cognitive services | Routing Console |
| hypothalamus | homeostasis, drive regulation and survival-resource priority | Affect/Homeostasis Console |
| brainstem_arousal | arousal floor, wake/sleep switching and emergency activation | Arousal Console |
| cerebellum | prediction correction, timing, error smoothing and skill refinement | Calibration Console |
| default_mode_network | autobiographical simulation, narrative self and future/social modeling | Self-Model Console |
| salience_network | switching between internal and external attention based on relevance | Salience Console |
| executive_control_network | task execution, working control and deliberate reasoning | Executive Control Console |
| language_networks | semantic parsing, discourse memory, pragmatics and narrative construction | Language Cognition Console |
| motor_planning_system | action assembly, execution plan and feedback expectation | Action Selection Console |
| somatosensory_interoceptive_system | body/tool/environment state representation | Body/Tool State Console |

## Acceptance rule

A region map receives GO only when required regions are represented, each has a software equivalent, no row claims literal equivalence, each row has failure modes and every row maps to a dashboard/control surface.
