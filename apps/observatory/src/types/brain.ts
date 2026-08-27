/** Canonical Brain control-plane types aligned with brain/schemas.py + organism layer */

export type UUID = string;

export type BeliefState =
  | "hypothesis"
  | "provisional"
  | "established"
  | "contested"
  | "rejected"
  | "dormant";

export type ApprovalState = "requested" | "approved" | "rejected" | "expired";
export type OpportunityStatus =
  | "candidate"
  | "research"
  | "recommendation"
  | "approved"
  | "rejected"
  | "closed";
export type ContradictionStatus =
  | "open"
  | "under_investigation"
  | "user_decision_required"
  | "resolved_with_note";
export type SourceStatus = "active" | "monitor" | "blocked" | "retired" | "quarantined";
export type MemoryKind =
  | "working"
  | "episodic"
  | "semantic"
  | "procedural"
  | "emotional"
  | "social";
export type CommercialDisposition =
  | "act_now"
  | "verify_first"
  | "watch"
  | "archive"
  | "kill"
  | "automate"
  | "delegate"
  | "build_as_asset";

export interface ProvenanceRef {
  source_id: string;
  source_location?: string | null;
  excerpt_hash?: string | null;
}

export interface BrainObjectBase {
  id: UUID;
  created_at: string;
  updated_at?: string;
  valid_from?: string | null;
  known_at?: string | null;
  source_refs?: string[];
  provenance?: ProvenanceRef[];
  metadata?: Record<string, unknown>;
}

export interface Belief extends BrainObjectBase {
  statement: string;
  confidence: number;
  state: BeliefState;
  evidence_ids?: string[];
  contradiction_ids?: string[];
  version?: number;
}

export interface EvidenceItem extends BrainObjectBase {
  claim: string;
  source_id: string;
  reliability: number;
  supports: boolean;
  observation_id?: string | null;
  evidence_strength?: number;
}

export interface Signal extends BrainObjectBase {
  source_id: string;
  evidence_ids: string[];
  novelty: number;
  urgency: number;
  commercial_upside: number;
  attention_score: number;
  formula_run_id?: string | null;
}

export interface PerceptualEvent extends BrainObjectBase {
  observation_id: string;
  summary: string;
  salience_score: number;
  attention_route: string;
  formula_run_id?: string | null;
}

export interface Opportunity extends BrainObjectBase {
  title: string;
  belief_ids: string[];
  status: OpportunityStatus;
  expected_value: number;
  risk_score: number;
  expected_net_value?: number | null;
  time_to_cash_days?: number | null;
  conversion_probability?: number | null;
  fee_protected?: boolean | null;
  disposition?: CommercialDisposition | null;
  money_path_ids?: string[];
}

export interface CandidateAction extends BrainObjectBase {
  description: string;
  opportunity_id?: string | null;
  expected_value: number;
  uncertainty: number;
  external: boolean;
  state: "draft" | "simulated" | "approval_required" | "approved" | "blocked";
  trust_adjusted_value?: number | null;
  formula_run_id?: string | null;
}

export interface ApprovalRequest extends BrainObjectBase {
  action_id: string;
  state: ApprovalState;
  required_approver: string;
  external_consequence: boolean;
}

export interface Outcome extends BrainObjectBase {
  action_id: string;
  value_created: number;
  prediction_accuracy: number;
  operator_time_cost: number;
  trust_impact: number;
  legal_risk: number;
  prediction_id?: string | null;
}

export interface Prediction extends BrainObjectBase {
  belief_id?: string | null;
  statement?: string;
  forecast_probability: number;
  expected_value?: number;
  actual_outcome?: boolean | null;
  brier_score?: number | null;
  resolve_by?: string | null;
  status?: "open" | "resolved" | "expired";
}

export interface RewardEvent extends BrainObjectBase {
  outcome_id: string;
  score: number;
  attributed_to: string[];
  confidence: number;
  attribution_id?: string | null;
}

export interface PainEvent extends BrainObjectBase {
  outcome_id: string;
  score: number;
  attributed_to: string[];
  mitigation_required: boolean;
  attribution_id?: string | null;
}

export interface FormulaRun extends BrainObjectBase {
  formula_id: string;
  owner_object_id: string;
  owner_object_type: string;
  inputs: Record<string, number>;
  output: number;
  service: string;
  table_store: string;
  dashboard: string;
  decision_consequence: string;
}

export interface Contradiction extends BrainObjectBase {
  belief_ids: string[];
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  status: ContradictionStatus;
  resolution_note?: string | null;
  investigation_pressure?: number;
}

export interface CuriosityTask extends BrainObjectBase {
  title: string;
  linked_object_type: string;
  linked_object_id: string;
  priority: number;
  status: "open" | "in_progress" | "completed" | "dismissed";
  suggested_action?: string;
}

export interface Source extends BrainObjectBase {
  name: string;
  kind: string;
  trust_score: number;
  status: SourceStatus;
  quarantine_reason?: string | null;
}

export interface MemoryObject extends BrainObjectBase {
  memory_type: MemoryKind;
  content: string;
  salience: number;
  linked_object_ids?: string[];
}

export interface GraphNode extends BrainObjectBase {
  kind: string;
  key: string;
  properties?: Record<string, unknown>;
}

export interface GraphEdge extends BrainObjectBase {
  source: string;
  target: string;
  relation: string;
  weight: number;
  confidence: number;
  evidence_ids?: string[];
  formula_run_id?: string | null;
}

export interface AcceptanceReport extends BrainObjectBase {
  report_id: string;
  ticket_id: string;
  verdict: "GO" | "HOLD";
  tests: string[];
  fixtures: string[];
  evidence: string[];
  unresolved_items?: string[];
}

export interface AgencyAttribution extends BrainObjectBase {
  outcome_id: string;
  prediction_id?: string | null;
  reward_score: number;
  prediction_error?: number;
  attributed_sources: string[];
  attributed_edges: string[];
  attributed_formulas: string[];
  confidence: number;
  rationale?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  beliefs: number;
  events?: number;
  predictions?: number;
  money_lanes?: number;
  database?: string;
  persistence?: string;
  heartbeat?: {
    ticks?: number;
    total_processed?: number;
    inbox?: number;
    working_memory_size?: number;
  };
}

export interface ListResponse<T> {
  items: T[];
  next_cursor?: string | null;
  total?: number;
}

// --- Cognitive organism layer ---

export interface OrganismSelfState {
  current_focus_summary?: string;
  belief_count?: number;
  event_count?: number;
  prediction_count?: number;
  opportunity_count?: number;
  uncertainty_load?: number;
  contradiction_load?: number;
  curiosity_pressure?: number;
  revenue_pressure?: number;
  risk_pressure?: number;
  memory_pressure?: number;
  action_backlog_pressure?: number;
  [key: string]: unknown;
}

export interface OrganismCuriosityTask {
  id?: string;
  question?: string;
  trigger_type?: string;
  expected_value?: number;
  uncertainty?: number;
  cost?: number;
  status?: string;
  [key: string]: unknown;
}

export interface OrganismAgencyAction {
  id?: string;
  action_type?: string;
  proposal?: string;
  tier?: string;
  /** AgencyState: observed | ... | approval_required | approved | executed | ... */
  state?: string;
  /** "approval_required" until an operator approves, then "approved". */
  approval_status?: string;
  approved_by?: string | null;
  risk_score?: number;
  [key: string]: unknown;
}

export interface OrganismQuarantineItem {
  id?: string;
  item_type?: string;
  item_ref?: string;
  reason?: string;
  [key: string]: unknown;
}

export interface OrganismCockpit {
  self_state?: OrganismSelfState;
  workspace?: unknown;
  curiosity?: { items?: OrganismCuriosityTask[] } | OrganismCuriosityTask[];
  agency?: { items?: OrganismAgencyAction[] } | OrganismAgencyAction[];
  quarantine?: { items?: OrganismQuarantineItem[] } | OrganismQuarantineItem[];
  goals?: unknown;
  [key: string]: unknown;
}

export interface OrganismPersistenceStatus {
  store?: string;
  checkpoint_name?: string;
  has_startup_checkpoint?: boolean;
  autonomy_boundary?: string;
}
