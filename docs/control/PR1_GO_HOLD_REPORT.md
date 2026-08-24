# PR1_GO_HOLD_REPORT

Status: PR 1 source discovery and quarantine report. Documentation-only PR.

## Scope executed

PR 1 created control documentation only. It did not modify runtime code, migrations, dependencies, deployment settings, environment values, application behavior, tests, or CI workflows.

## Files added

- `docs/control/ACTUAL_SOURCE_MAP.md`
- `docs/control/PUBLIC_PRIVATE_ROUTE_REGISTER.md`
- `docs/control/DATA_CLASSIFICATION_MATRIX.md`
- `docs/control/BRAIN_TABLE_INVENTORY.md`
- `docs/control/BRAIN_ROUTE_INVENTORY.md`
- `docs/control/BRAIN_FUNCTION_INVENTORY.md`
- `docs/control/BRAIN_FUNCTION_REGISTRY_DELTA.md`
- `docs/control/CONTAMINATED_ARTIFACT_AUDIT.md`
- `docs/control/BRAIN_AUTH_RISK_REGISTER.md`
- `docs/control/BRAIN_V0_DEFERRED_SURFACES.md`
- `docs/control/PR1_GO_HOLD_REPORT.md`

## Files inspected for this source-discovery pass

- Repository metadata for `harbourviewcompany-create/Brain`
- Root contents
- `pyproject.toml`
- `.env.example`
- `README.md`
- `apps/api/main.py`
- `apps/operator/main.py`
- `apps/worker/main.py`
- `db/migrations/001_init.sql`
- `db/migrations/002_cognitive_runtime.sql`
- `db/migrations/003_cognitive_security_hardening.sql`
- `db/migrations` listing
- `docs` listing
- `docs/control` listing
- `.github` listing
- `.github/workflows` listing

## Confirmed findings

### Runtime/framework

- Python project named `brain-runtime`.
- Requires Python `>=3.12`.
- Uses FastAPI, Uvicorn, Pydantic, psycopg, Neo4j driver, Temporal SDK, and httpx.
- Uses pytest and ruff for dev/test tooling.

### Applications

- `apps/api/main.py`: primary FastAPI API.
- `apps/operator/main.py`: economic operator FastAPI/HTML surface.
- `apps/worker/main.py`: continuous cognition worker.

### Database

- SQL migrations under `db/migrations`.
- PostgreSQL extensions observed: `vector`, `pgcrypto`.
- RLS hardening migration exists, but no tenant ownership model was observed.
- Duplicate migration number prefix exists: `006_money_spine.sql` and `006_working_memory_predictions_learning.sql`.

### Auth/security

- `apps/api/main.py` has fail-closed API-key middleware using `BRAIN_API_KEY` and `x-api-key`.
- `/health` is exempt.
- Operator app auth was not observed.
- No tenant, membership, invite, or role schema was observed in inspected files.
- No `tenant_id` field was observed in inspected migrations.

### Routes

- API routes exist for beliefs, learning, graph edges, predictions, outcomes, money lanes, revenue signal scoring/packaging, experiments, and daily revenue reports.
- Operator routes exist for snapshot, pressure, money paths, counterparties, transactions, sources, and HTML UI.
- Current routes are not tenant-safe based on inspected files.

### CI

- GitHub workflows observed: `test.yml`, `control-policy.yml`, `repository-hardening.yml`.

## GO decisions

GO for:

- Preserving all Brain concepts in registry/control docs.
- Treating uploaded artifacts as concept sources only.
- Using current repo evidence to scope PR 2 and PR 3.
- Keeping this PR documentation-only.
- Moving to PR 2 only after this PR is reviewed and accepted.

## HOLD decisions

HOLD for:

- Runtime code changes.
- Migrations.
- Dependencies.
- Deployment/config changes.
- Payment/webhook/fulfillment implementation.
- Auth/tenant implementation before PR 2.
- RLS tenant enforcement before PR 3.
- Agent/job scheduler changes before PR 6.
- Storage/export/cache/log/rate-limit implementation before PR 7.
- Capital/reward/meta-brain implementation before PR 10.
- Copying any uploaded pseudo-code.

## Highest-risk blockers

| Blocker | Severity | Reason | Close in |
|---|---:|---|---:|
| No tenant model observed | P0 | Cannot safely build multi-tenant Brain without tenants/memberships/roles | PR 2 |
| No tenant_id in inspected cognitive tables | P0 | RLS exists but tenant ownership is absent | PR 3 |
| Operator app appears unauthenticated | P0 | `/operator/*` surfaces expose economic/operator state if deployed | PR 4/11 |
| API routes mutate global cognitive state | P0 | Belief/graph/outcome/revenue functions lack tenant context | PR 3/10 |
| Duplicate migration prefix `006` | P1 | Migration ordering ambiguity | PR 2/3 planning |
| `BRAIN_API_KEY` missing from `.env.example` | P1 | Runtime auth env var not documented in example | PR 7 |
| Wildcard CORS | P1 | Needs production policy before exposure | PR 7 |
| Uploaded code contamination risk | P0 | Pasted snippets include unsafe/global/placeholder patterns | Ongoing; first controlled in PR 1 |

## Remaining unknowns

- Full inventory of all `brain/*.py` files.
- Full inventory of migrations `004` through `011`.
- Full inventory of tests under `tests/`.
- Whether any contaminated artifact snippet exists elsewhere in repo history or uninspected files.
- Actual production deployment state.
- Actual production database schema/state.
- Actual branch protection state beyond files observed.

## Recommended PR 2 scope

PR 2 should be narrow and foundational:

- Define tenant/auth/membership/invite/lifecycle contracts.
- Add or update documentation/specs first if implementation is not yet approved.
- If implementation is authorized later, only implement tenant/auth foundation after design review.
- Do not touch payment, fulfillment, agent runtime, reward propagation, capital, exports, or Meta Brain yet.

## Acceptance checklist for this PR

- [x] Documentation-only files added.
- [x] No runtime files modified.
- [x] No migrations added or modified.
- [x] No dependencies added or modified.
- [x] No deployment settings modified.
- [x] No uploaded implementation snippets copied.
- [x] Route register added.
- [x] Table inventory added.
- [x] Function inventory added.
- [x] Data classification matrix added.
- [x] Contaminated artifact audit added.
- [x] Auth risk register added.
- [x] Deferred surface register added.
- [x] GO/HOLD report added.

## Final PR 1 decision

GO for review of PR 1 documentation.

HOLD for PR 2 execution until PR 1 is reviewed and accepted.
