export type BrainCommandMode =
  | "teach"
  | "solve"
  | "inspect"
  | "challenge"
  | "build_capability"
  | "explain_change";

export interface ObservedEvidence {
  id: string;
  created_at: string;
  updated_at?: string;
  claim: string;
  source_id: string;
  reliability: number;
  observation_id?: string | null;
  supports: boolean | null;
  belief_ids: string[];
  metadata?: Record<string, unknown>;
}

export interface LearningEvent {
  id: string;
  event_type: string;
  aggregate_type: string;
  aggregate_id: string;
  occurred_at: string;
  correlation_id?: string | null;
  payload: Record<string, unknown>;
}

export interface WorkingMemoryObservation {
  observed_at: string | null;
  size: number | null;
  capacity: number | null;
  cycle_id: string | null;
  source: "cycle.completed" | "unobserved" | string;
  evicted_count: number;
  last_slot_id?: string | null;
}

export interface BrainCommandReceipt {
  id?: string;
  inbox_id?: string;
  status?: string;
  processed?: boolean;
  [key: string]: unknown;
}
