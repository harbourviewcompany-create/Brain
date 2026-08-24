# BRAIN_AUTH_RISK_REGISTER

Status: PR 1 auth and tenant risk register. Documentation only.

## Current auth model observed

| Surface | Current auth | Tenant model | Risk | GO/HOLD |
|---|---|---:|---:|---:|
| `apps/api/main.py` | API key via `x-api-key` and `BRAIN_API_KEY` | None observed | Medium-to-high | HOLD for production |
| `apps/operator/main.py` | None observed | None observed | Critical | HOLD |
| `apps/worker/main.py` | Environment/runtime only | None observed | High for multi-tenant | HOLD |
| Database migrations | RLS enabled/revokes for cognitive tables | No tenant fields observed | High | HOLD |

## Positive finding

`apps/api/main.py` includes a fail-closed API-key middleware:

- `/health` is exempt.
- Non-exempt routes require `x-api-key`.
- If `BRAIN_API_KEY` is unset, non-exempt requests return 503.

This is useful minimum protection, but it is not full authentication, session management, tenant membership, role authorization, or row-level tenant isolation.

## Critical gaps

| ID | Risk | Severity | Evidence | Required closure |
|---|---|---:|---|---|
| AUTH-001 | No tenant model observed | P0 | No `tenant` search result; no tenant fields in inspected migrations | PR 2/3 |
| AUTH-002 | No user/session model observed | P0 | API-key middleware only | PR 2 |
| AUTH-003 | No membership/role model observed | P0 | No membership tables in inspected migrations | PR 2 |
| AUTH-004 | Operator app has no auth middleware observed | P0 | `apps/operator/main.py` exposes operator JSON/HTML routes | PR 4/11 |
| AUTH-005 | API-key routes mutate/read global cognitive state | P0 | `/beliefs`, `/learn`, `/edges`, `/outcomes` | PR 3/4/10 |
| AUTH-006 | CORS wildcard in API | P1 | `allow_origins=["*"]` in `apps/api/main.py` | PR 7/security hardening |
| AUTH-007 | `BRAIN_API_KEY` missing from `.env.example` | P1 | Source uses env var; example does not include it | PR 7 |
| AUTH-008 | `BRAIN_WORKER_MODE` missing from `.env.example` | P2 | Worker uses env var; example does not include it | PR 7 |
| AUTH-009 | RLS enabled without tenant policies | P0 | `003_cognitive_security_hardening.sql` enables RLS/revokes, no tenant ownership | PR 3 |
| AUTH-010 | No system-admin/support boundary observed | P0 | No admin/support auth model in inspected source | PR 11 |

## Required target model

The target model must include:

- `tenants`
- tenant lifecycle status
- user identity/session provider
- memberships
- roles
- invites
- last-owner protection
- tenant context resolution
- tenant-scoped RLS policies
- service actor boundaries
- system-admin/support boundary
- explicit route role matrix
- audit events for sensitive actions

## Required route posture

- API `/health`: may remain public-safe.
- Cognitive read routes: tenant-authenticated and role-filtered.
- Cognitive mutation routes: tenant role-gated.
- Outcome/reward/capital/payment/fulfillment routes: tenant role-gated or service-only.
- Operator routes: never public; tenant role-gated or system-admin-only.
- Worker routes/functions: service-only with tenant iteration where appropriate.

## Required tests later

- Auth required for protected API routes.
- Missing API key fail-closed.
- Invalid API key rejected.
- Tenant A cannot read Tenant B beliefs, graph, outcomes, memory, actions, payments, exports, agent runs, or files.
- Viewer cannot approve actions or access sensitive fields.
- Operator can approve only same-tenant eligible actions.
- Last owner cannot be removed.
- Suspended tenant cannot write or execute jobs.
- System-admin/support boundaries are explicit and audited.

## GO/HOLD

GO:

- Use API-key middleware as current actual-state finding.
- Use RLS hardening as current actual-state finding.

HOLD:

- Calling current auth production-ready.
- Exposing operator surface publicly.
- Any multi-tenant implementation until PR 2/3.
