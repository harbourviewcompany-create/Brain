# BRAIN_FUNCTION_REGISTRY_DELTA

Status: PR 1 registry-only delta. This document preserves scope without authorizing implementation.

## Rule

All entries here are registry entries only unless an exact source file path is listed in `BRAIN_FUNCTION_INVENTORY.md`.

Do not copy uploaded SQL, TypeScript, Python, cron, WebSocket, Stripe, PayPal, chaos, migration, outbox, undo, export, fuzzing, test-runner, dashboard, or monitoring snippets into implementation PRs.

## Appendix Z container

Appendix Z is the Brain Master Corpus container for registry-only additions extracted from uploaded artifacts and recap documents. Appendix Z may contain names, signatures, responsibilities, policy requirements, tests, dashboards, GO/HOLD classifications, and PR placement. Appendix Z must not contain implementation code.

## Advanced capital metrics

| Registry function | Status | Close in |
|---|---:|---:|
| `calculate_sharpe_ratio_for_tenant(p_tenant_id, lookback_days)` | Missing contract | PR 10 |
| `calculate_sortino_ratio_for_tenant(p_tenant_id, lookback_days, target_return)` | Missing contract | PR 10 |
| `calculate_calmar_ratio_for_tenant(p_tenant_id, lookback_days)` | Missing contract | PR 10 |
| `calculate_omega_ratio_for_tenant(p_tenant_id, lookback_days, threshold)` | Missing contract | PR 10 |
| `calculate_information_ratio_for_tenant(p_tenant_id, benchmark_id, lookback_days)` | Missing contract | PR 10 |
| `calculate_treynor_ratio_for_tenant(p_tenant_id, lookback_days)` | Missing contract | PR 10 |
| `calculate_jensens_alpha_for_tenant(p_tenant_id, benchmark_id, lookback_days)` | Missing contract | PR 10 |
| `calculate_modigliani_ratio_for_tenant(p_tenant_id, lookback_days)` | Missing contract | PR 10 |
| `calculate_max_drawdown_for_tenant(p_tenant_id, lookback_days)` | Missing contract | PR 10 |
| `calculate_dynamic_kelly_with_ci_for_tenant(p_tenant_id, opportunity_id, base_k, sample_size)` | Missing contract | PR 10 |
| `calculate_risk_adjusted_capital_roi_for_tenant(p_tenant_id, lookback_days)` | Missing contract | PR 10 |
| `calculate_upside_potential_ratio_for_tenant(p_tenant_id, lookback_days, threshold)` | Missing contract | PR 10 |
| `calculate_gain_to_pain_ratio_for_tenant(p_tenant_id, lookback_days)` | Missing contract | PR 10 |
| `calculate_recovery_factor_for_tenant(p_tenant_id, lookback_days)` | Missing contract | PR 10 |
| `calculate_drawdown_duration_for_tenant(p_tenant_id, lookback_days)` | Deferred metric | V1 |
| `calculate_return_skewness_for_tenant(p_tenant_id, lookback_days)` | Deferred metric | V1 |
| `calculate_portfolio_diversification_for_tenant(p_tenant_id, lookback_days)` | Deferred metric | V1 |

## Capital decisioning

| Registry function | Status | Close in |
|---|---:|---:|
| `capital_allocation_decision_for_tenant(p_tenant_id, opportunity_id, current_allocation)` | Missing contract | PR 10 |
| `optimize_capital_portfolio_for_tenant(p_tenant_id, total_available_capital, max_single_category)` | Missing contract | PR 10 |
| `generate_capital_reallocation_proposals_for_tenant(p_tenant_id)` | Missing contract | PR 10 |
| `approve_capital_reallocation_for_tenant(p_tenant_id, proposal_id, actor_user_id)` | Missing contract | PR 10 |
| `reject_capital_reallocation_for_tenant(p_tenant_id, proposal_id, actor_user_id, reason)` | Missing contract | PR 10 |
| `record_capital_compounding_snapshot_for_tenant(p_tenant_id)` | Missing contract | PR 10 |
| `record_capital_reallocation_audit_event(p_tenant_id, proposal_id, actor_user_id, before_state, after_state)` | Missing contract | PR 10 |
| `explain_capital_allocation_decision(p_tenant_id, decision_id)` | Missing contract | PR 10 |

## Reward config and reward/pain propagation

| Registry function/table | Status | Close in |
|---|---:|---:|
| `reward_config` | Missing tenant-safe table/config model | PR 10 |
| `get_active_reward_config_for_tenant(p_tenant_id)` | Missing contract | PR 10 |
| `calculate_outcome_reward_score_for_tenant(p_tenant_id, outcome_id)` | Missing contract | PR 10 |
| `propagate_reward_pain_for_tenant(p_tenant_id, outcome_id, idempotency_key)` | Missing contract | PR 10 |
| `propagate_reward_to_action_for_tenant(p_tenant_id, outcome_id, action_id)` | Missing contract | PR 10 |
| `propagate_reward_to_opportunity_for_tenant(p_tenant_id, opportunity_id)` | Missing contract | PR 10 |
| `propagate_reward_to_beliefs_for_tenant(p_tenant_id, belief_ids)` | Missing contract | PR 10 |
| `propagate_reward_to_sources_for_tenant(p_tenant_id, source_ids)` | Missing contract | PR 10 |
| `reverse_reward_pain_for_refund_for_tenant(p_tenant_id, payment_id, refund_id)` | Missing contract | PR 10 |
| `write_reward_propagation_audit_for_tenant(p_tenant_id, outcome_id, propagation_id)` | Missing contract | PR 10 |

## Cognitive missing modules

| Module/function family | Status | Close in |
|---|---:|---:|
| Working memory sessions | Partially represented by `memory_items(kind='working')`; dedicated session contract missing | V0+ after PR 6 |
| Episodic replay | Partially represented by `memory_items(kind='episodic')`; replay protocol missing | V1 |
| Associative spreading activation | Missing contract | V1 |
| Pattern completion | Missing contract | V1 |
| Inhibition/forgetting | Missing retention/governance contract | PR 7/V1 |
| Counterfactual simulation | Missing contract | V0+ after PR 5 |
| Hierarchical planning | Missing contract | V1 |
| Theory of mind / counterparty intent modeling | Missing contract | V1 |
| Meta-cognition | Underrepresented beyond health/evaluation | PR 10/V1 |
| Abductive reasoning | Missing contract | V1 |
| Salience filtering | Underrepresented; table has `salience`, but queue/protocol missing | V0+ after PR 6/7 |
| Intrinsic motivation | Partially represented by `cognitive_tasks` fields; contract missing | V1 |
| Homeostasis | Partially represented by `homeostatic_snapshots`; regulation contract missing | PR 7/V1 |
| Urgency/arousal as scheduling priority | Partially represented by `cognitive_tasks.urgency`; scheduler contract missing | PR 6/V1 |
| Instruction following | Missing operator command contract | V1 |
| Joint attention | Missing contract | V1 |
| Explainability engine | Missing contract | V0+ |
| Confidence calibration | Missing contract | V0+ |
| Self-model snapshots | Missing contract | V1 |
| Governance constraints | Partially represented by action status/external flag; full contract missing | PR 5 |
| Action reversal plans | Missing contract | PR 5/9/V1 |

## Payments, revenue, fulfillment

| Registry function/table | Status | Close in |
|---|---:|---:|
| `webhook_events` | Missing table | PR 8 |
| `payments` | Missing/under-confirmed in inspected migrations | PR 8 |
| `handle_refund_for_tenant` | Missing contract | PR 10/V1 |
| `handle_partial_refund_for_tenant` | Missing contract | PR 10/V1 |
| `handle_dispute_for_tenant` | Missing contract | PR 10/V1 |
| `reverse_revenue_attribution_for_refund` | Missing contract | PR 10 |
| `create_invoice_for_tenant` | Deferred | V1 |
| `record_invoice_payment_for_tenant` | Deferred | V1 |
| `handle_subscription_created_for_tenant` | Deferred | V1 |
| `handle_subscription_renewed_for_tenant` | Deferred | V1 |
| `handle_subscription_cancelled_for_tenant` | Deferred | V1 |
| `retry_failed_payment_for_tenant` | Missing contract | PR 10/V1 |
| `fulfillment_jobs` | Missing table/state machine | PR 9 |
| `queue_fulfillment_for_tenant` | Missing contract | PR 9 |
| `approve_fulfillment_job_for_tenant` | Missing contract | PR 9 |
| `generate_fulfillment_artifact_for_tenant` | Missing contract | PR 9/V1 |

## Operational resilience

| Registry function/table | Status | Close in |
|---|---:|---:|
| `idempotency_keys` | Missing table/service | PR 8/10 |
| `dead_letters` | Missing table/service | PR 6/7 |
| `service_circuit_breakers` | Missing table/service | PR 7 |
| `outbox_messages` | Missing table/service | PR 7/8 |
| `retention_policies` | Missing table/service | PR 7 |
| `resource_pressure_snapshots` | Missing table; `homeostatic_snapshots` partially related | PR 7/V1 |
| Agent heartbeat/timeouts | Worker exists, tenant-aware heartbeat protocol missing | PR 6 |
| Cognitive throttling | Missing contract | PR 7/V1 |

## Planned route registry entries from Appendix Z

- `/api/tenants/[tenantId]/agents/runs/heartbeat`
- `/api/tenants/[tenantId]/agents/debate`
- `/api/tenants/[tenantId]/capital/reallocate/approve`
- `/api/tenants/[tenantId]/webhooks/events`
- `/api/tenants/[tenantId]/exports/download/[exportId]`
- `/api/tenants/[tenantId]/fulfillment/jobs/approve`
- `/api/admin/system/tenant-jobs`

## Planned dashboard panel names from Appendix Z

- `CapitalAllocationPanel`
- `AgentPerformancePanel`
- `WebhookEventMonitor`
- `JobQueueMonitor`
- `ExportRequestPanel`

## Required tests from Appendix Z

- `tests/security/idempotency.test.ts`
- `tests/security/webhook-signature.test.ts`
- `tests/jobs/tenant-job-runner.test.ts`
- `tests/security/export-redaction.test.ts`
- `tests/security/rate-limit.test.ts`
- `tests/security/agent-timeout.test.ts`
- `tests/browser/tenant-switch-cache.test.ts`
- `tests/security/reward-propagation-idempotency.test.ts`

## GO/HOLD

GO:

- Preserve all entries for scope.

HOLD:

- Implementing any entry without source-mapped schema, tenant model, state machine, tests, and evidence.
