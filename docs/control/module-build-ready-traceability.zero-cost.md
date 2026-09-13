# Zero-Cost Runtime Canonical BUILD-READY Traceability Extension

Status: APPROVED source authority / HOLD for production runtime completion.

This canonical extension covers the zero-cost Vercel/Turso runtime modules and executable policy validator. It preserves the existing module matrix and does not claim production cutover evidence that has not been generated.

Required completion fields: owner object; schema; runtime service; state machine; fixtures; tests; acceptance criteria; audit events; GO/HOLD status.

| Module path | Owner object | Schema | Runtime service | State machine | Fixtures / tests | Acceptance criteria / evidence | Audit events | GO/HOLD |
|---|---|---|---|---|---|---|---|---|
| apps/api/turso_runtime.py | zero-cost API runtime binding | Turso runtime configuration | Vercel stateless API | validate config -> bind Turso -> serve bounded request -> fail closed | tests/test_turso_persistence.py; protected test workflow | branch runtime contracts pass; production cutover proof pending | ZERO_COST_RUNTIME_VALIDATED | HOLD |
| brain/adapters/persistence.py | provider-neutral persistence boundary | persistence protocols | Brain persistence adapter boundary | select configured adapter -> execute canonical operation -> return typed result | tests/test_turso_persistence.py | adapter contracts pass; production Turso proof pending | TURSO_PERSISTENCE_VERIFIED | HOLD |
| brain/adapters/turso.py | Turso transport/persistence adapter | libSQL/Turso records | Turso adapter | connect -> execute bounded persistence operation -> verify/fail closed | tests/test_turso_persistence.py | local/contract evidence present; production import pending | TURSO_PERSISTENCE_VERIFIED | HOLD |
| brain/adapters/turso_brain_store.py | canonical Brain state in Turso | Brain persistence tables | TursoBrainStore | encode Brain state -> persist/query -> deterministic decode | tests/test_turso_persistence.py | contract tests pass; live production population pending | TURSO_PERSISTENCE_VERIFIED | HOLD |
| brain/adapters/turso_learning_store.py | learning persistence in Turso | learning records | TursoLearningStore | validate learning record -> persist/query -> deterministic decode | tests/test_turso_persistence.py | contract tests pass; live production population pending | TURSO_PERSISTENCE_VERIFIED | HOLD |
| brain/adapters/turso_revenue_store.py | revenue persistence in Turso | revenue records | TursoRevenueStore | validate revenue record -> persist/query -> deterministic decode | tests/test_turso_persistence.py | contract tests pass; live production population pending | TURSO_PERSISTENCE_VERIFIED | HOLD |
| brain/adapters/turso_schema.py | zero-cost canonical SQLite/Turso schema | deterministic SQLite schema | Turso schema bootstrap | inspect schema -> create/verify required tables -> reject malformed runtime state | tests/test_turso_persistence.py; tests/test_railway_turso_migration.py | deterministic schema and migration fixture pass | TURSO_SCHEMA_VERIFIED | HOLD |
| brain/storage_policy.py | zero-cost storage pressure policy | 60/70/80/85 percent pressure thresholds | persistence write admission policy | observe -> compact -> prune disposable telemetry -> refuse noncanonical growth | tests/test_turso_persistence.py | 85 percent refusal threshold enforced; live storage usage pending | STORAGE_PRESSURE_ENFORCED | HOLD |
| scripts/validate_zero_cost_runtime.py | executable release policy | zero_cost_policy.json invariants | protected GitHub Actions validator | load policy/files -> validate invariants -> PASS or fail closed | protected test workflow; Python compile; Ruff | branch validation PASS; production postdeploy proof pending | ZERO_COST_POLICY_VALIDATION_PASSED | HOLD |

## Source preservation statement

Railway production state remains intact as a read-only migration source. No production Turso import, Railway deletion, paid-resource creation, Vercel production promotion, or rescue dispatch is represented as complete. Production cutover and Railway retirement remain HOLD.

<!-- SOURCE APPROVED GO HOLD -->
