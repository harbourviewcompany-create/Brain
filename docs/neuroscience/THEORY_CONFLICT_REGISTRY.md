# Theory Conflict Registry

This registry prevents agents from collapsing competing neuroscience theories into one preferred implementation story.

Brain can use theories as bounded software heuristics, but it cannot treat any theory as proof of full biological equivalence, consciousness, sentience or solved cognition.

## Rule

Competing theories must remain explicit. A theory can guide implementation only when its claim boundary, evidence state, implementation posture and conflict relationships are recorded.

## Required fields

Each theory record must define:

- theory id
- name
- mechanism area
- claim
- status
- implementation posture
- competing theory ids
- linked unknown ids
- supporting evidence
- contradicting evidence
- claim boundary
- owner object
- runtime service
- fixture id
- test id
- dashboard
- acceptance criteria
- GO/HOLD status

Each conflict record must define:

- conflict id
- theory ids
- conflict summary
- resolution rule
- operator surface
- acceptance criteria

## Runtime service

`TheoryRegistryService` and `TheoryValidationService` validate conflict references, missing conflicts, unsafe implementation posture and missing evidence boundaries.

## Machine-readable artifact

`json/theory-conflict-registry.json`

## Acceptance

A theory registry entry is accepted only when it preserves conflict, does not erase contradictory evidence and does not permit unbounded implementation.
