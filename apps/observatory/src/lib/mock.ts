/**
 * Deterministic mock data for CP-0 / CP-1 when backend list endpoints are not yet live.
 * Shape matches brain/schemas.py.
 */

import type {
  Belief,
  Contradiction,
  CuriosityTask,
  FormulaRun,
  Opportunity,
  ApprovalRequest,
  Prediction,
  Signal,
  Source,
  AcceptanceReport,
} from "@/types/brain";

export const MOCK_HEALTH = {
  status: "ok",
  version: "0.4.0",
  beliefs: 3,
  events: 12,
  predictions: 1,
};

export const MOCK_BELIEFS: Belief[] = [
  {
    id: "b-001",
    created_at: "2026-08-22T14:00:00Z",
    updated_at: "2026-08-23T09:10:00Z",
    valid_from: "2026-08-20T00:00:00Z",
    known_at: "2026-08-22T14:00:00Z",
    statement: "A market is expanding in regulated healthcare procurement",
    confidence: 0.62,
    state: "provisional",
    evidence_ids: ["e-001", "e-002"],
    contradiction_ids: ["c-001"],
    version: 2,
    source_refs: ["src-filings"],
  },
  {
    id: "b-002",
    created_at: "2026-08-21T11:00:00Z",
    updated_at: "2026-08-21T11:00:00Z",
    statement: "Counterparty X has budget authority this quarter",
    confidence: 0.41,
    state: "hypothesis",
    evidence_ids: ["e-003"],
    contradiction_ids: [],
    version: 1,
  },
  {
    id: "b-003",
    created_at: "2026-08-19T08:00:00Z",
    updated_at: "2026-08-23T08:00:00Z",
    statement: "Source registry yield is declining due to duplication",
    confidence: 0.78,
    state: "established",
    evidence_ids: ["e-004"],
    contradiction_ids: [],
    version: 3,
  },
];

export const MOCK_SIGNALS: Signal[] = [
  {
    id: "s-001",
    created_at: "2026-08-23T08:30:00Z",
    source_id: "src-filings",
    evidence_ids: ["e-001"],
    novelty: 0.7,
    urgency: 0.55,
    commercial_upside: 12000,
    attention_score: 0.81,
    formula_run_id: "fr-attn-001",
  },
  {
    id: "s-002",
    created_at: "2026-08-23T07:15:00Z",
    source_id: "src-jobs",
    evidence_ids: ["e-003"],
    novelty: 0.4,
    urgency: 0.3,
    commercial_upside: 4000,
    attention_score: 0.42,
    formula_run_id: "fr-attn-002",
  },
];

export const MOCK_CONTRADICTIONS: Contradiction[] = [
  {
    id: "c-001",
    created_at: "2026-08-23T09:00:00Z",
    belief_ids: ["b-001"],
    supporting_evidence_ids: ["e-001"],
    contradicting_evidence_ids: ["e-005"],
    status: "user_decision_required",
    investigation_pressure: 0.72,
    valid_from: "2026-08-22T00:00:00Z",
    known_at: "2026-08-23T09:00:00Z",
  },
];

export const MOCK_CURIOSITY: CuriosityTask[] = [
  {
    id: "cu-001",
    created_at: "2026-08-23T09:05:00Z",
    title: "Resolve budget-authority contradiction for Counterparty X",
    linked_object_type: "contradiction",
    linked_object_id: "c-001",
    priority: 0.88,
    status: "open",
    suggested_action: "Request primary-source corroboration",
  },
  {
    id: "cu-002",
    created_at: "2026-08-22T16:00:00Z",
    title: "Reduce uncertainty on market-expansion belief",
    linked_object_type: "belief",
    linked_object_id: "b-001",
    priority: 0.64,
    status: "in_progress",
    suggested_action: "Pull latest procurement notices",
  },
];

export const MOCK_OPPORTUNITIES: Opportunity[] = [
  {
    id: "o-001",
    created_at: "2026-08-22T15:00:00Z",
    title: "Healthcare procurement introduction path",
    belief_ids: ["b-001"],
    status: "research",
    expected_value: 18000,
    risk_score: 0.35,
    expected_net_value: 12000,
    time_to_cash_days: 45,
    conversion_probability: 0.28,
    fee_protected: true,
    disposition: "verify_first",
  },
];

export const MOCK_APPROVALS: ApprovalRequest[] = [
  {
    id: "ar-001",
    created_at: "2026-08-23T08:00:00Z",
    action_id: "act-001",
    state: "requested",
    required_approver: "tyler",
    external_consequence: true,
  },
];

export const MOCK_PREDICTIONS: Prediction[] = [
  {
    id: "p-001",
    created_at: "2026-08-20T10:00:00Z",
    belief_id: "b-001",
    statement: "Procurement volume will rise >10% next 30 days",
    forecast_probability: 0.58,
    expected_value: 0.58,
    status: "open",
    resolve_by: "2026-09-20T00:00:00Z",
  },
];

export const MOCK_SOURCES: Source[] = [
  {
    id: "src-filings",
    created_at: "2026-08-01T00:00:00Z",
    name: "Regulatory filings feed",
    kind: "registry",
    trust_score: 0.86,
    status: "active",
  },
  {
    id: "src-noise",
    created_at: "2026-08-10T00:00:00Z",
    name: "Unverified social aggregator",
    kind: "social",
    trust_score: 0.22,
    status: "quarantined",
    quarantine_reason: "Elevated false-positive rate; immune review",
  },
];

export const MOCK_FORMULA_RUNS: FormulaRun[] = [
  {
    id: "fr-attn-001",
    created_at: "2026-08-23T08:30:00Z",
    formula_id: "F-003",
    owner_object_id: "s-001",
    owner_object_type: "Signal",
    inputs: {
      upside: 0.7,
      novelty: 0.7,
      urgency: 0.55,
      source_quality: 0.86,
      contradiction: 0.4,
      noise: 0.1,
    },
    output: 0.81,
    service: "AttentionAllocatorService",
    table_store: "attention_decision",
    dashboard: "perception_inbox",
    decision_consequence: "process",
  },
];

export const MOCK_ACCEPTANCE: AcceptanceReport[] = [
  {
    id: "acc-001",
    created_at: "2026-08-23T06:00:00Z",
    report_id: "acc-001",
    ticket_id: "AGENT-006",
    verdict: "GO",
    tests: ["traceability_completeness_validation"],
    fixtures: [],
    evidence: ["docs/spec/source-to-build-traceability.json"],
    unresolved_items: [],
  },
];
