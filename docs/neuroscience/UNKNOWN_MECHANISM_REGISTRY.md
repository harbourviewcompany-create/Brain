# Unknown Mechanism Registry

This registry preserves neuroscience unknowns, disputed mechanisms and speculative mechanisms as first-class control objects.

The point is not to solve unknown neuroscience by naming it. The point is to prevent agents from silently converting uncertainty into implementation claims.

## Rule

Any biological mechanism that is unknown, disputed, speculative or not directly measurable must remain `HOLD` until evidence, claim boundaries and operator approval justify a different status.

## Required fields

Each unknown mechanism must define:

- unknown id
- name
- kind
- related abstraction ids
- current claim boundary
- forbidden claims
- allowed software uses
- evidence needed
- research questions
- owner object
- runtime service
- database table
- fixture id
- test id
- dashboard
- GO/HOLD status

## Non-claims

The Brain must not claim consciousness, sentience, human emotion, personhood or literal brain equivalence from any unknown mechanism record.

## Runtime service

`UnknownMechanismRegistryService` and `UnknownMechanismValidationService` validate that unknowns remain bounded, mapped and held.

## Machine-readable artifact

`json/unknown-mechanism-registry.json`

## Acceptance

A registry entry is accepted only when it preserves uncertainty, names forbidden claims, defines allowed software uses and has executable validation evidence.
