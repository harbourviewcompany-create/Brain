# BRAIN_V0_DEFERRED_SURFACES

Status: PR 1 V0/deferred-surface register. Documentation only.

## Rule

Deferred does not mean deleted. Deferred means preserved in the Brain corpus and registry, but not implemented until its dependencies and safety gates exist.

## V0 required before production-like use

| Surface | Reason | Dependency | Recommended PR |
|---|---|---|---:|
| Tenant/auth/membership lifecycle | Required for multi-tenant Brain | Source map | PR 2 |
| Tenant ID/RLS/sensitive views | Required for data isolation | Auth/tenant schema | PR 3 |
| Tenant-safe cockpit reads | Required for operator control | RLS/data classification | PR 4 |
| Approval gate/action state machine | Required for external-action governance | Role matrix/audit | PR 5 |
| Tenant-safe job runner | Required for cognition at scale | Tenant model | PR 6 |
| Storage/export/cache/secrets/logs/quotas/rate limits | Required for deployment safety | Data classification | PR 7 |
| Payment dry-run/webhook safety | Required before accepting payment | Idempotency/tenant metadata | PR 8 |
| Fulfillment queue | Required before automated fulfillment | Payment state machine | PR 9 |
| Outcomes/reward/capital/belief history/meta aggregate safety | Required for learning and money-spine correctness | Tenant events/jobs | PR 10 |
| System-admin/support boundary | Required for ops access | Auth/tenant model | PR 11 |
| Browser QA/CI/evidence gate | Required before release | All prior PRs | PR 12 |

## Deferred to V0+ or V1

| Surface | Status | Reason |
|---|---:|---|
| Agent Debate Memory | Deferred | Useful but not required for tenant isolation. |
| Agent Conflict Resolution | Deferred/V1 | Requires deterministic escalation protocol and working memory. |
| Episodic Replay | Deferred/V1 | Requires stable outcomes, reward propagation, retention, and replay scoring. |
| Associative Spreading Activation | Deferred/V1 | Requires tenant-safe graph tissue and traversal limits. |
| Pattern Completion | Deferred/V1 | Requires mature embeddings/perception model. |
| Inhibition/Forgetting | Deferred/V1 unless retention needed earlier | Must be governed by retention policy, not silent deletion. |
| Counterfactual Simulation | V0+ candidate | Valuable for approval preflight, but depends on action/offer state machines. |
| Hierarchical Planning | Deferred/V1 | Depends on goal/plan model. |
| Theory of Mind / Counterparty Intent | Deferred/V1 | Depends on entity/evidence model and must avoid overclaiming. |
| Meta-Cognition beyond health score | Deferred/V1 | Depends on explainability/evaluation. |
| Abductive Reasoning | Deferred/V1 | Depends on evidence and explanation model. |
| Salience Queue | V0+ candidate | Current schema has salience-like fields, but protocol/queue missing. |
| Intrinsic Motivation | Deferred/V1 | Current tasks include novelty/utility fields; complete driver model later. |
| Homeostasis Regulation | Deferred/V1 | Current snapshots exist; regulation policy missing. |
| Urgency/Arousal scheduling | Deferred/V1 | Current task urgency exists; scheduler policy missing. |
| Instruction-following command parser | Deferred/V1 | Depends on role-gated action commands. |
| Joint Attention | Deferred/V1 | Depends on cockpit and working memory. |
| Explainability Engine | V0+ candidate | Needed for trust/debugging; depends on audit/event contracts. |
| Confidence Calibration | V0+ candidate | Needed for agents/capital/beliefs; depends on outcome evaluation. |
| Self-Model Snapshots | Deferred/V1 | Depends on source map and telemetry. |
| Governance Constraints Engine | V0 required baseline, full engine V1 | Basic action gates in PR 5; richer policy engine later. |
| Action Reversal Plans | V0+ or V1 | Depends on action/payment/fulfillment state machines. |
| Subscription Lifecycle | Deferred/V1 | Not V0 unless recurring billing is selected. |
| Invoice Generator | Deferred/V1 | Can be manual until B2B billing scope is chosen. |
| Public Offer Pages | Deferred/V1 | Requires public route isolation and no tenant leakage. |
| Regret Logger | Deferred/V1 | Useful for Meta Brain but not release blocker. |
| Exploration Framework | Deferred/V1 | Requires approval gates and experimental budget controls. |
| Transfer Learning | Deferred/V1+ | Requires anonymization, consent, and tenant privacy policy. |
| Observational Learning | Deferred/V1+ | Same cross-tenant privacy dependency. |
| Few-shot Learning | Deferred/V1+ | Requires evaluation/calibration. |
| Continual Learning Anti-forgetting | Deferred/V1+ | Requires replay/evaluation. |
| Multimodal Binding | Deferred/V1+ | Stabilize text pipeline first. |
| Predictive Coding | Deferred/V1+ | Requires mature perception layer. |
| Parallel Action Execution | Deferred/V1 | Requires single-action lifecycle, job runner, quotas. |
| Real-time Notifications | Deferred/V1 | Requires tenant auth and realtime provider. |
| Chaos Testing | Deferred/V1+ staging-only | Never production migration; staging-only with explicit guardrails. |
| Tenant Backup/Restore | Deferred | Platform operations scope. |

## Registry-only dashboard surfaces

- `CapitalAllocationPanel`
- `AgentPerformancePanel`
- `WebhookEventMonitor`
- `JobQueueMonitor`
- `ExportRequestPanel`
- Capital Health Panel
- Capital Metrics Drilldown
- Dynamic Kelly Confidence Interval Panel
- Reward/Pain Propagation Trace
- Working Memory Session Viewer
- Counterfactual Simulation Comparison View
- Salience Queue
- Decision Explanation Drawer
- Self-Model Snapshot Panel
- Refund/Revenue Reversal Panel
- Resource Pressure Panel
- Dead Letter Queue Panel
- Outbox Worker Panel

## GO/HOLD

GO:

- Preserve every surface as part of the Brain scope.

HOLD:

- Implementing deferred surfaces before their dependencies.
- Removing deferred surfaces from the Brain scope.
