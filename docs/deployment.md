# Brain deployment state

## Supabase

- Project: `Brain`
- Project ref: `fkvwjhevjjfoiyoaeuzf`
- Region: `ca-central-1`
- API URL: `https://fkvwjhevjjfoiyoaeuzf.supabase.co`
- Canonical memory: PostgreSQL
- Event ledger: `public.brain_events`
- Current schema migrations: `001` through `004`

Secrets are never committed. Runtime workers must receive `DATABASE_URL` through their deployment environment or secret manager.

## Database invariants

1. `brain_events` is append-only at the database layer.
2. Cognitive tables have RLS enabled.
3. `anon` and `authenticated` have direct table privileges revoked.
4. No client-facing RLS policies exist yet; backend cognitive services use privileged server-side database credentials only.
5. Current-state projections are disposable and rebuildable from the event ledger.

## Next infrastructure

1. Deploy API and worker with `DATABASE_URL`.
2. Start Temporal Cloud namespace and worker.
3. Add Neo4j Aura projection adapter.
4. Add continuous observation -> event -> projection workflow.
