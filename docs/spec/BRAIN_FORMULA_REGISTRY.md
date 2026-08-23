# Brain Formula Registry

This registry is the build-control seed. Agents must expand it from the canonical formula corpus before claiming formula completeness.

Each formula requires expression, variables, owner object, service, storage, dashboard, decision consequence, and tests.

## Required formula families

### F-001 source_priority_score
Expression: `(signal_value * 3) + freshness + reliability - extraction_difficulty`.
Owner: Source.
Service: SourceScoringService.
Store: source registry.
Dashboard: source console.
Decision: source watch frequency.
Test: deterministic score and range.

### F-002 sensor_yield_score
Expression: `outcome_value + prediction_gain + early_detection + corroboration + diversity - false_positive_cost - review_burden - duplication - latency`.
Owner: Sensor.
Service: SensorScoringService.
Store: sensor registry.
Dashboard: source console.
Decision: promote or demote sensor.
Test: noisy sensor demotion.

### F-003 attention_score
Expression: `upside + novelty + urgency + source_quality + contradiction + mandate_proximity + timing + learning + trust_risk_if_ignored - noise - stale_context - duplication - operator_load - burden`.
Owner: PerceptualEvent.
Service: AttentionAllocatorService.
Store: attention decision.
Dashboard: perception inbox.
Decision: ignore, watch, process, escalate.
Test: high-trust-risk route.

### F-004 Bayesian belief update
Expression: `posterior = (prior * L) / ((prior * L) + (1 - prior))`.
Owner: Belief.
Service: BeliefUpdateService.
Store: belief ledger.
Dashboard: belief ledger.
Decision: belief confidence.
Test: reliable evidence increases confidence.

### F-005 expected_utility
Expression: `cash_probability*cash_value + pipeline_probability*pipeline_value + learning + asset + option + trust_gain - time_cost - capital_cost - fulfillment_cost - trust_risk - legal_risk - opportunity_cost`.
Owner: CandidateAction.
Service: ActionEvaluationService.
Store: candidate action.
Dashboard: approval inbox.
Decision: action ranking.
Test: negative utility blocks action.

### F-006 trust_adjusted_value
Expression: `expected_utility - trust_damage_risk - reputation_damage_risk - legal_or_access_risk`.
Owner: CandidateAction.
Service: TrustRiskService.
Store: candidate action.
Dashboard: approval inbox.
Decision: approve, verify, or block.
Test: severe trust risk blocks cash upside.

### F-007 reward_score and pain_score
Expression: source-preserved reward/pain formula families.
Owner: Outcome.
Service: RewardPainService.
Store: reward and pain events.
Dashboard: learning console.
Decision: reinforce or weaken pathways.
Test: attribution required.

### F-008 graph_weight_update
Expression: `new_weight = old_weight + reward_score * learning_rate * attribution_confidence * path_credit`.
Owner: GraphEdge.
Service: GraphLearningService.
Store: graph update log.
Dashboard: learning console.
Decision: rewire graph.
Test: low attribution blocks major update.

### F-009 risk-adjusted metrics
Includes Sharpe-like, Sortino-like, Calmar-like, Omega-like, profit factor, hit rate, drawdown risk, Kelly, half-life, regret, EVPI, EVSI, composite intelligence, confidence threshold, and go/no-go score.
Status: preserved; expand exact rows before implementation claims.