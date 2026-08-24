# Cognitive Organism Persistence + Operator Cockpit V1

Status: REVIEW / GO after CI.

This slice makes Cognitive Organism V1 less ephemeral without enabling external action.

It adds:

1. A persistence adapter boundary on the existing traced `brain/adapters/cognition.py` path.
2. A PostgreSQL checkpoint adapter for `cognitive_organism_checkpoints` and append-only `organism_audit_events`.
3. An in-memory deterministic adapter for tests and local runtime.
4. API checkpoint, rehydration-inspection and audit-event endpoints.
5. An operator organism cockpit at `/operator/organism` and `/operator/organism/ui`.

The checkpoint stores a replayable cockpit/read-model snapshot plus subsystem counts. It does not claim full subjective consciousness, it does not enable Tier 5 autonomy and it does not execute external actions.

## HOLD boundaries

- No literal consciousness claim.
- No live scraping.
- No autonomous outreach.
- No autonomous spending.
- No Tier 5 autonomy.
- No irreversible external action.
- Production migration execution remains environment-specific.

## Next required expansion

The next durable layer should persist each organism object class into its canonical table and rehydrate the full runtime graph, not only the cockpit checkpoint read model.
