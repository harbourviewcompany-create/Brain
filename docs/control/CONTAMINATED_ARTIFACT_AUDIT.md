# CONTAMINATED_ARTIFACT_AUDIT

Status: PR 1 quarantine document. Documentation only. This file does not implement or preserve any uploaded code.

## Audit rule

The uploaded Brain artifacts, pasted SQL/TypeScript/Python snippets, generated “production-ready” scripts, generated dashboard code, generated payment/webhook snippets, generated chaos/fuzz/load scripts, and generated migration examples are contaminated reference unless independently found as actual repo code and then source-mapped.

Allowed use:

- Extract function names.
- Extract table names.
- Extract route names.
- Extract module names.
- Extract risks.
- Extract missing-component requirements.
- Extract test categories.
- Extract GO/HOLD constraints.

Forbidden use:

- Copying generated SQL.
- Copying generated TypeScript/Python.
- Copying generated webhook/payment snippets.
- Copying generated cron or job code.
- Copying generated migrations.
- Treating uploaded tests as acceptance evidence.
- Treating uploaded “complete” or “production-ready” claims as true.

## Explicitly forbidden uploaded-code patterns

The following patterns from uploaded artifacts are explicitly forbidden from being copied into the Brain repository:

1. `chaos_kill_random_connection()` and any similar chaos monkey SQL in production migrations.
2. Dynamic SQL execution via `EXECUTE p_sql` in circuit breaker functions.
3. Global `run_full_commercial_pipeline()` without tenant iteration.
4. Stripe webhook examples without `tenant_id` metadata.
5. Infinite fuzzing loops against `/api/ingest`.
6. Undo routes that mutate approval state without tenant and state-machine enforcement.
7. Raw table exports without redaction, allowlist, or expiry.
8. `run_full_self_improvement_cycle()` called globally via cron.

## Contamination categories

| Category | Classification | Action |
|---|---:|---|
| Capital SQL scripts | Contaminated reference | Extract names only; redesign tenant-safe contracts. |
| Dynamic Kelly SQL | Contaminated reference | Extract concept only; implement later with tests. |
| Meta health SQL | Contaminated reference | Reject hardcoded/placeholder health values. |
| Capital optimizer placeholders | Contaminated reference | Registry-only. |
| Reward propagation SQL | Contaminated reference | Reject global triggers; redesign idempotent tenant function. |
| Working memory SQL | Contaminated reference | Registry-only; current repo has `memory_items` but no session contract. |
| Episodic replay SQL | Contaminated reference | Registry-only. |
| Spreading activation SQL | Contaminated reference | Registry-only. |
| Pattern completion SQL | Contaminated reference | Registry-only. |
| Payment service TypeScript | Contaminated reference | Redesign after payment/webhook state machine. |
| Automated fulfillment SQL | Contaminated reference | Redesign as queued fulfillment. |
| Monitoring dashboard TSX | Contaminated reference | Registry-only panel names. |
| Auth/multi-tenant SQL from uploads | Contaminated reference | Do not copy; actual repo lacks tenant model. |
| Idempotency SQL | Contaminated reference | Redesign after actual runtime. |
| Circuit breaker SQL | Contaminated reference | Reject arbitrary dynamic SQL. |
| Outbox SQL | Contaminated reference | Registry-only. |
| Agent heartbeat SQL | Contaminated reference | Registry-only. |
| WebSocket snippets | Contaminated reference | Registry-only/deferred. |
| Undo/export routes | Contaminated reference | Replace with formal reversal/export controls. |
| k6 load tests | Contaminated reference | Use only as future test category. |
| Stripe webhook tests | Contaminated reference | Reject if tenant metadata/amount/currency not enforced. |
| Fuzzing scripts | Contaminated reference | Future bounded harness only. |
| Chaos SQL | Contaminated reference | Staging-only policy at most; never production migration. |
| Final integration scripts | Contaminated reference | Reject as acceptance evidence. |

## Repo contamination scan status

PR 1 quick inspection found actual repo code in:

- `apps/api/main.py`
- `apps/operator/main.py`
- `apps/worker/main.py`
- `db/migrations/001_init.sql`
- `db/migrations/002_cognitive_runtime.sql`
- `db/migrations/003_cognitive_security_hardening.sql`
- `pyproject.toml`
- `.env.example`
- `.github/workflows/*`

No forbidden uploaded snippet was intentionally copied in this PR.

Not fully proven in PR 1:

- Exhaustive search across every file for all contaminated patterns.
- Whether earlier repository commits contain copied contaminated snippets.
- Whether migration files after `003` contain any generated artifact material.

## Required future checks

Before implementation PRs:

- Search for forbidden identifiers and patterns.
- Search for global money-spine/self-improvement cron equivalents.
- Search for Stripe webhook handling without tenant metadata.
- Search for raw export routes.
- Search for dynamic SQL circuit breakers.
- Search for chaos/fuzz code in production paths.

## GO/HOLD

GO:

- Use uploaded artifacts as scope/corpus material.
- Preserve function/table/route/module names in registry-only docs.

HOLD:

- Copying implementation snippets.
- Treating generated code as production proof.
- Any implementation before source-map and tenant-safety contracts are approved.
