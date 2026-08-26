# PR #126 Canonical BUILD-READY Traceability Extension

Status: REVIEW-ONLY / HOLD for runtime modules.

This is a required canonical extension of `docs/control/module-build-ready-traceability.md`. It exists to preserve the historical matrix while adding the runtime modules introduced by PR #126. It is not a supplemental exemption: every row below is subject to the same BUILD-READY rule and remains HOLD until all evidence is present.

Required fields for every module: owner object, schema, runtime service, state machine, fixtures, tests, acceptance criteria, audit events, GO/HOLD status.

| Module path | Owner object | Schema | Runtime service | State machine | Fixtures / tests | Acceptance evidence | Audit events | GO/HOLD |
|---|---|---|---|---|---|---|---|---|
| apps/api/tenant_app.py | tenant-aware production API boundary | signed TenantContext + membership-derived role + tenant-local service bundle | apps.api.tenant_app | health/readiness -> API key -> signed tenant identity -> durable membership -> scoped route; unsafe role/RLS topology fails closed | tests/test_tenant_runtime.py; tests/test_api_key_auth.py; tenant RLS integration | partial; production runtime-role and rollout evidence missing | partial | HOLD |
| apps/operator/secure_main.py | secured tenant-aware operator plane | tenant identity + durable membership + tenant-partitioned operator state | apps.operator.secure_main | public health/readiness -> API key -> signed identity -> membership -> scoped operator route | tests/test_secure_operator.py; tests/test_tenant_runtime.py | partial; production operator deployment evidence missing | partial | HOLD |
| brain/developmental/scheduler.py | resource-bounded developmental scheduler | DevelopmentSchedule, DevelopmentBudget, DevelopmentQueueItem, DevelopmentRun | DevelopmentalSchedulerService | due -> priority -> budget gate -> queued -> claimed -> success/backoff/HOLD -> replay reconstruction | tests/test_developmental_scheduler.py | partial; continuous production integration missing | present | HOLD |
| brain/tenant_auth.py | tenant, membership, invite and lifecycle domain | Tenant, TenantMembership, TenantInvite, TenantAuditEvent | TenantAuthService | tenant create -> membership/invite lifecycle -> role/status mutation -> audit | tests/test_tenant_auth.py; tests/test_tenant_auth_migration.py | partial; PostgreSQL-backed lifecycle administration and transactional last-owner enforcement missing | partial | HOLD |
| brain/tenant_context.py | trusted tenant context and role enforcement | TenantContext + TenantRole authorization contract | trusted_tenant_context / TenantContext role checks | verified identity -> trusted context -> role requirement -> allow/deny | tests/test_tenant_context.py | partial; production identity authority evidence missing | partial | HOLD |
| brain/tenant_runtime.py | tenant request security, DB scoping and runtime topology | TenantIdentity, signed context, scoped pool, role topology, tenant-partitioned bundles | TenantRequestSecurity, PostgresTenantMembershipResolver, TenantScopedConnectionPool | signature -> membership -> scoped DB transaction -> RLS; unsafe DB role or cross-tenant access fails closed | tests/test_tenant_runtime.py; tools/verify_tenant_rls_release.py; tenant RLS integration | partial; live non-owner/non-BYPASSRLS evidence missing | partial | HOLD |

## Source preservation statement

These rows add only the new PR #126 runtime surfaces. Existing rows in the historical canonical matrix remain authoritative and unchanged. NEURO-007 rich memory is intentionally not repeated here because it was already canonical on protected `main` before PR #126 merged.
