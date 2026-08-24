# PUBLIC_PRIVATE_ROUTE_REGISTER

Status: PR 1 discovery register. Documentation only. No implementation authority.

## Classification key

- Public: callable without auth.
- Public-safe dynamic: unauthenticated but bounded and safe.
- Authenticated system/API-key: protected by API key or equivalent, but not tenant-aware.
- Authenticated tenant: requires tenant identity and membership.
- Tenant role-gated: requires tenant role.
- Service-only: internal worker/service call.
- Webhook-only: external provider webhook endpoint.
- System-admin-only: global administrative surface.
- Deprecated/unscoped: route exists but lacks required auth/tenant/role scope for intended production use.
- Unknown: not enough source evidence.

## Actual route inventory

| Route | Source | Current classification | Intended classification | Risk | GO/HOLD | Recommended PR |
|---|---|---:|---:|---:|---:|---:|
| `GET /health` | `apps/api/main.py` | Public | Public-safe dynamic | Low | GO | PR 1 inventory only |
| `GET /beliefs` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant | High: no tenant scoping observed | HOLD | PR 3/4 |
| `GET /beliefs/{belief_id}` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant | High: no tenant scoping observed | HOLD | PR 3/4 |
| `POST /beliefs` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant role-gated | High: creates cognitive state without tenant | HOLD | PR 2/3 |
| `POST /learn` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant role-gated | High: mutates belief state without tenant | HOLD | PR 3/10 |
| `POST /edges` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant role-gated | High: graph mutation without tenant | HOLD | PR 3/4/10 |
| `GET /predictions` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant | High: prediction list unscoped | HOLD | PR 3/4 |
| `POST /predictions` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant role-gated | High: creates prediction without tenant | HOLD | PR 3/10 |
| `GET /predictions/{prediction_id}` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant | High: direct ID lookup without tenant | HOLD | PR 3/4 |
| `POST /outcomes` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant role-gated/service | Critical: outcome/reward mutation without tenant | HOLD | PR 3/10 |
| `GET /money-lanes` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant | High: money lanes unscoped | HOLD | PR 4/10 |
| `POST /revenue-signals/score` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant role-gated | High: revenue signal scoring unscoped | HOLD | PR 4/10 |
| `POST /revenue-signals/package` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant role-gated | Critical: offer/package generation unscoped | HOLD | PR 5/10 |
| `POST /revenue-experiments/evaluate` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant role-gated | High: experiment/outcome unscoped | HOLD | PR 10 |
| `POST /daily-revenue-report` | `apps/api/main.py` | Authenticated system/API-key | Authenticated tenant role-gated | Medium: reporting unscoped | HOLD | PR 4/10 |
| `GET /health` | `apps/operator/main.py` | Public | Public-safe dynamic | Low | GO | PR 1 inventory only |
| `GET /operator` | `apps/operator/main.py` | Deprecated/unscoped | Tenant role-gated or system-admin-only | Critical: no auth observed | HOLD | PR 4/11 |
| `GET /operator/pressure` | `apps/operator/main.py` | Deprecated/unscoped | Tenant role-gated | Critical: no auth observed | HOLD | PR 4/11 |
| `GET /operator/money-paths` | `apps/operator/main.py` | Deprecated/unscoped | Tenant role-gated | Critical: no auth observed | HOLD | PR 4/11 |
| `GET /operator/counterparties` | `apps/operator/main.py` | Deprecated/unscoped | Tenant role-gated | Critical: no auth observed | HOLD | PR 4/11 |
| `GET /operator/transactions` | `apps/operator/main.py` | Deprecated/unscoped | Tenant role-gated | Critical: no auth observed | HOLD | PR 4/11 |
| `GET /operator/sources` | `apps/operator/main.py` | Deprecated/unscoped | Tenant role-gated | Critical: no auth observed | HOLD | PR 4/11 |
| `GET /operator/ui` | `apps/operator/main.py` | Deprecated/unscoped | Tenant role-gated | Critical: no auth observed | HOLD | PR 4/11 |

## Planned route names preserved as registry-only

These are not implemented routes. They are planned route concepts from the Brain corpus and Appendix Z.

| Planned route | Intended class | Status |
|---|---:|---:|
| `/api/tenants/[tenantId]/agents/runs/heartbeat` | Service-only tenant | Registry-only |
| `/api/tenants/[tenantId]/agents/debate` | Tenant role-gated | Registry-only |
| `/api/tenants/[tenantId]/capital/reallocate/approve` | Tenant role-gated | Registry-only |
| `/api/tenants/[tenantId]/webhooks/events` | Tenant admin | Registry-only |
| `/api/tenants/[tenantId]/exports/download/[exportId]` | Tenant role-gated | Registry-only |
| `/api/tenants/[tenantId]/fulfillment/jobs/approve` | Tenant role-gated | Registry-only |
| `/api/admin/system/tenant-jobs` | System-admin-only | Registry-only |

## GO/HOLD

GO:

- Preserve this register as PR 1 route baseline.

HOLD:

- Any route implementation.
- Any public exposure of operator surfaces.
- Any tenant route naming finalization until tenant model exists.
