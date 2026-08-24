# BRAIN_ROUTE_INVENTORY

Status: PR 1 route inventory. Documentation only.

## Actual route surfaces found

### `apps/api/main.py`

| Route | Method | Function | Input model | Current protection | Tenant scope | Classification | GO/HOLD |
|---|---:|---|---|---|---:|---:|---:|
| `/health` | GET | `health` | None | Exempt from API key | No | Public-safe | GO |
| `/beliefs` | GET | `list_beliefs` | None | API key middleware | No | Authenticated system/API-key | HOLD |
| `/beliefs/{belief_id}` | GET | `get_belief` | Path UUID string | API key middleware | No | Authenticated system/API-key | HOLD |
| `/beliefs` | POST | `create_belief` | `CreateBeliefRequest` | API key middleware | No | Authenticated system/API-key mutation | HOLD |
| `/learn` | POST | `learn` | `LearnRequest` | API key middleware | No | Authenticated system/API-key mutation | HOLD |
| `/edges` | POST | `upsert_edge` | `UpsertEdgeRequest` | API key middleware | No | Authenticated system/API-key graph mutation | HOLD |
| `/predictions` | GET | `list_predictions` | None | API key middleware | No | Authenticated system/API-key read | HOLD |
| `/predictions` | POST | `create_prediction` | `CreatePredictionRequest` | API key middleware | No | Authenticated system/API-key mutation | HOLD |
| `/predictions/{prediction_id}` | GET | `get_prediction` | Path UUID string | API key middleware | No | Authenticated system/API-key read | HOLD |
| `/outcomes` | POST | `record_outcome` | `RecordOutcomeRequest` | API key middleware | No | Authenticated system/API-key outcome mutation | HOLD |
| `/money-lanes` | GET | `list_money_lanes` | None | API key middleware | No | Authenticated system/API-key revenue read | HOLD |
| `/revenue-signals/score` | POST | `score_revenue_signal` | `RevenueSignalRequest` | API key middleware | No | Authenticated system/API-key revenue scoring | HOLD |
| `/revenue-signals/package` | POST | `package_revenue_signal` | `RevenueSignalRequest` | API key middleware | No | Authenticated system/API-key offer packaging | HOLD |
| `/revenue-experiments/evaluate` | POST | `evaluate_revenue_experiment` | `ExperimentResultRequest` | API key middleware | No | Authenticated system/API-key experiment mutation | HOLD |
| `/daily-revenue-report` | POST | `daily_revenue_report` | `DailyRevenueReportRequest` | API key middleware | No | Authenticated system/API-key report | HOLD |

Notes:

- `apps/api/main.py` uses a global API-key middleware. This is a good fail-closed minimum but not sufficient for tenant isolation.
- CORS currently permits wildcard origins; this must be reviewed before production exposure.
- The runtime can use in-memory stores or Postgres-backed adapters depending on `DATABASE_URL`.

### `apps/operator/main.py`

| Route | Method | Function | Current protection | Tenant scope | Classification | GO/HOLD |
|---|---:|---|---|---:|---:|---:|
| `/health` | GET | `health` | None observed | No | Public-safe | GO |
| `/operator` | GET | `operator_snapshot` | None observed | No | Deprecated/unscoped operator surface | HOLD |
| `/operator/pressure` | GET | `pressure_map` | None observed | No | Deprecated/unscoped operator surface | HOLD |
| `/operator/money-paths` | GET | `money_paths` | None observed | No | Deprecated/unscoped operator surface | HOLD |
| `/operator/counterparties` | GET | `counterparties` | None observed | No | Deprecated/unscoped operator surface | HOLD |
| `/operator/transactions` | GET | `transactions` | None observed | No | Deprecated/unscoped operator surface | HOLD |
| `/operator/sources` | GET | `sources` | None observed | No | Deprecated/unscoped operator surface | HOLD |
| `/operator/ui` | GET | `operator_ui` | None observed | No | Deprecated/unscoped HTML operator surface | HOLD |

Notes:

- This file contains its own FastAPI app and separate economic runtime.
- It selects Postgres-backed runtime when `DATABASE_URL` is set; otherwise uses in-memory economic store.
- No API-key middleware, user auth, tenant auth, or role gating was observed in this file during PR 1 inspection.

## Planned routes retained as registry-only

The following routes were preserved from the Brain corpus/Appendix Z and are not implemented in this PR:

- `/api/tenants/[tenantId]/agents/runs/heartbeat`
- `/api/tenants/[tenantId]/agents/debate`
- `/api/tenants/[tenantId]/capital/reallocate/approve`
- `/api/tenants/[tenantId]/webhooks/events`
- `/api/tenants/[tenantId]/exports/download/[exportId]`
- `/api/tenants/[tenantId]/fulfillment/jobs/approve`
- `/api/admin/system/tenant-jobs`

## Missing route categories from current implementation

| Category | Status | Recommended PR |
|---|---:|---:|
| Tenant-scoped API root | Missing | PR 2/3 |
| Membership/invite routes | Missing | PR 2 |
| Approval queue route | Missing or not confirmed | PR 5 |
| Payment session route | Missing or not confirmed | PR 8 |
| Webhook routes | Missing or not confirmed | PR 8 |
| Refund/invoice/subscription routes | Missing/deferred | PR 10/V1 |
| Fulfillment job routes | Missing or not confirmed | PR 9 |
| Export/download routes | Missing or not confirmed | PR 7 |
| System-admin route boundary | Missing or not confirmed | PR 11 |

## GO/HOLD

GO:

- Keep `/health` public-safe.
- Use route list to plan PR 2/3/4/5.

HOLD:

- Treating API-key routes as tenant-safe.
- Operator route production exposure.
- Any new route implementation.
