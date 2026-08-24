# BRAIN_FUNCTION_INVENTORY

Status: PR 1 function/service inventory. Documentation only.

## Actual API/service functions observed

### `apps/api/main.py`

| Symbol | Source | Role | Tenant scope | Classification | Risk | Next PR |
|---|---|---|---:|---:|---:|---:|
| `_require_api_key` | `apps/api/main.py` | API-key middleware | No | Canonical minimum auth | Medium | PR 2 |
| `_configure_from_env` | `apps/api/main.py` | Select Postgres adapters when `DATABASE_URL` exists | No | Canonical runtime config | Medium | PR 7 |
| `health` | `apps/api/main.py` | Health summary | No | Public-safe | Low | PR 1 |
| `list_beliefs` | `apps/api/main.py` | Belief listing | No | Canonical but unscoped | High | PR 3/4 |
| `get_belief` | `apps/api/main.py` | Belief read | No | Canonical but unscoped | High | PR 3/4 |
| `create_belief` | `apps/api/main.py` | Belief creation | No | Canonical but unscoped | High | PR 3 |
| `learn` | `apps/api/main.py` | Belief update from evidence | No | Canonical but unscoped | High | PR 3/10 |
| `upsert_edge` | `apps/api/main.py` | Graph node/edge mutation | No | Canonical but unscoped | High | PR 3/4/10 |
| `list_predictions` | `apps/api/main.py` | Prediction listing | No | Canonical but unscoped | High | PR 3/4 |
| `create_prediction` | `apps/api/main.py` | Prediction creation | No | Canonical but unscoped | High | PR 3/10 |
| `get_prediction` | `apps/api/main.py` | Prediction read | No | Canonical but unscoped | High | PR 3/4 |
| `record_outcome` | `apps/api/main.py` | Outcome/reward learning entry | No | Canonical but unscoped | Critical | PR 10 |
| `list_money_lanes` | `apps/api/main.py` | Money lane read | No | Canonical but unscoped | High | PR 4/10 |
| `score_revenue_signal` | `apps/api/main.py` | Score revenue signal | No | Canonical but unscoped | High | PR 10 |
| `package_revenue_signal` | `apps/api/main.py` | Package offer from revenue signal | No | Canonical but unscoped | Critical | PR 5/10 |
| `evaluate_revenue_experiment` | `apps/api/main.py` | Evaluate revenue experiment | No | Canonical but unscoped | High | PR 10 |
| `daily_revenue_report` | `apps/api/main.py` | Validate daily revenue report | No | Canonical but unscoped | Medium | PR 10 |

### `apps/operator/main.py`

| Symbol | Source | Role | Tenant scope | Classification | Risk | Next PR |
|---|---|---|---:|---:|---:|---:|
| `_configure_from_env` | `apps/operator/main.py` | Select Postgres economic runtime when `DATABASE_URL` exists | No | Canonical runtime config | Medium | PR 7 |
| `health` | `apps/operator/main.py` | Operator app health | No | Public-safe | Low | PR 1 |
| `operator_snapshot` | `apps/operator/main.py` | Economic operator summary | No | Deprecated/unscoped | Critical | PR 4/11 |
| `pressure_map` | `apps/operator/main.py` | Pressure map read | No | Deprecated/unscoped | Critical | PR 4/11 |
| `money_paths` | `apps/operator/main.py` | Money path read | No | Deprecated/unscoped | Critical | PR 4/11 |
| `counterparties` | `apps/operator/main.py` | Counterparty read | No | Deprecated/unscoped | Critical | PR 4/11 |
| `transactions` | `apps/operator/main.py` | Transaction read | No | Deprecated/unscoped | Critical | PR 4/11 |
| `sources` | `apps/operator/main.py` | Source plane read | No | Deprecated/unscoped | Critical | PR 4/11 |
| `operator_ui` | `apps/operator/main.py` | HTML operator dashboard | No | Deprecated/unscoped | Critical | PR 4/11 |

### `apps/worker/main.py`

| Symbol | Source | Role | Tenant scope | Classification | Risk | Next PR |
|---|---|---|---:|---:|---:|---:|
| `build_runner` | `apps/worker/main.py` | Build continuous cognition runner from `DATABASE_URL` | No | Canonical worker entry | High | PR 6 |
| `build_learning` | `apps/worker/main.py` | Build learning service from Postgres stores | No | Canonical worker entry | High | PR 6/10 |
| `run_forever_with_maintenance` | `apps/worker/main.py` | Run cognition and expire predictions during idle | No | Canonical but unscoped | High | PR 6 |
| `main` | `apps/worker/main.py` | Select worker mode by `BRAIN_WORKER_MODE` | No | Canonical entrypoint | Medium | PR 6 |

## Actual core functions/classes referenced but not fully inventoried in PR 1

The following source symbols are imported or referenced and require deeper inventory in a later source-map refinement:

- `brain.adapters.learning_store.InMemoryLearningStore`
- `brain.adapters.learning_store.PostgresAttributionStore`
- `brain.adapters.learning_store.PostgresEdgeStore`
- `brain.adapters.learning_store.PostgresPredictionStore`
- `brain.adapters.learning_store.PostgresSourceStore`
- `brain.adapters.postgres.PostgresEventStore`
- `brain.adapters.postgres.ProjectionCheckpointStore`
- `brain.adapters.cognition.PostgresSensoryInbox`
- `brain.adapters.cognition.CognitiveCycleRunStore`
- `brain.domain.Edge`
- `brain.domain.Evidence`
- `brain.domain.Node`
- `brain.domain.Outcome`
- `brain.learning.LearningService`
- `brain.memory.InMemoryBrainStore`
- `brain.money_spine.MoneySpineService`
- `brain.money_spine.RevenueSignal`
- `brain.money_spine.DailyRevenueReport`
- `brain.prediction.PredictionEngine`
- `brain.runtime.BrainRuntime`
- `brain.cycle.CognitiveCycle`
- `brain.runner.ContinuousCognitionRunner`
- `brain.economic_runtime.EconomicRuntime`
- `brain.economic_runtime.InMemoryEconomicStore`

## Uploaded corpus function concepts retained as registry-only

These are not repo functions unless later confirmed in source. Do not copy uploaded implementation snippets.

- Advanced capital metrics: Sharpe, Sortino, Calmar, Omega, Information Ratio, Treynor, Jensen's Alpha, Modigliani, max drawdown, upside potential, gain-to-pain, recovery factor, drawdown duration, skewness, diversification.
- Capital decisioning: allocation decision, portfolio optimizer, reallocation proposals, approval, compounding snapshot, explanation.
- Reward/pain: reward config, reward scoring, propagation, belief/source/action propagation, reversal, audit.
- Cognitive missing modules: working memory sessions, episodic replay, spreading activation, pattern completion, inhibition/forgetting, counterfactual simulation, hierarchical planning, counterparty intent, meta-cognition, abductive reasoning, salience filtering, intrinsic motivation, homeostasis, urgency scheduling, instruction following, joint attention, explainability, confidence calibration, self-model, governance constraints, action reversal.
- Payments/revenue: refund, partial refund, dispute, invoice, subscription events, payment retry, attribution reversal.
- Resilience: idempotency, dead letters, circuit breakers, outbox, retention, partitioning, agent heartbeat/timeouts, resource pressure, cognitive throttling.

## GO/HOLD

GO:

- Use this as the initial function inventory for PR planning.

HOLD:

- Implementation of any registry-only function.
- Treating current functions as tenant-safe.
- Payment/webhook/fulfillment additions.
