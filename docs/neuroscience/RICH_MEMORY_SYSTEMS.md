# NEURO-007 Rich Memory Systems

Status: APPROVED for bounded software-control implementation. HOLD for human-memory equivalence, perfect recall, autobiographical consciousness and unverified memory-as-fact claims.

## Purpose

Rich Memory Systems define the Brain control layer for encoding, retrieving, consolidating, reconsolidating, decaying, forgetting and quarantining memory-like records.

This is not a biological-equivalence claim. It is a provenance-bound software memory architecture that distinguishes what was observed, inferred, rehearsed, imagined, dreamed, contradicted, failed or quarantined.

## Required memory systems

- iconic
- echoic
- sensory trace
- working
- episodic
- semantic
- procedural
- emotional
- spatial
- autobiographical
- prospective
- source
- relational
- social
- skill
- habit
- threat
- preference
- contradiction
- uncertainty
- failure
- dream hypothesis
- quarantined

## Required objects

- MemoryRecord
- MemorySystemKind
- MemoryLifecycleState
- MemoryConsolidationEvent
- MemoryRetrievalCue
- MemoryProvenanceTrace
- MemoryInterferenceRecord
- MemoryDecayPolicy
- MemoryQuarantineDecision

## Executable runtime anchor

NEURO-007 adds `brain.neuro.memory_systems.RichMemorySystemService` and `RichMemoryValidationService` as the first neuroscience-layer memory runtime. Existing core memory modules remain preserved; this layer supplies typed neuroscience-control records and validation boundaries.

## State machine

`encoded -> retrievable -> consolidated -> reconsolidated -> decay_candidate -> forgotten`.

Quarantine path:

`encoded/retrievable/consolidated -> quarantined -> operator_review -> retained_as_quarantined | rejected | restored_with_evidence`.

Invalid transitions:

- No memory without evidence references.
- No memory without source references.
- No memory without provenance.
- No quarantined memory with GO status.
- No forgotten memory that still requires replay.
- No unsupported or fabricated memory promoted as fact.

## Acceptance criteria

- Every required memory system appears in the machine-readable registry.
- Encoded memory requires evidence references, source references and provenance.
- Retrieval can match by cue while excluding forgotten and quarantined records.
- Consolidation requires evidence.
- Quarantine forces HOLD and requires a reason.
- Fabricated, unsupported or invented memory cannot remain GO.
- Persistence tables exist for memory records, consolidation events, links and quarantine decisions.
- The layer does not claim perfect recall, consciousness or human-memory equivalence.
