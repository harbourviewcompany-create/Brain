import type {
  ApprovalRequest,
  Belief,
  Contradiction,
  CuriosityTask,
  HealthResponse,
  Opportunity,
  OrganismAgencyAction,
  OrganismCockpit,
  OrganismCuriosityTask,
  OrganismPersistenceStatus,
  OrganismQuarantineItem,
  OrganismSelfState,
  Outcome,
  Prediction,
  Signal,
  Source,
} from "@/types/brain";
import type { LearningEvent, ObservedEvidence, WorkingMemoryObservation } from "@/types/living-brain";

export type SceneKind =
  | "organism"
  | "signal"
  | "belief"
  | "prediction"
  | "outcome"
  | "contradiction"
  | "curiosity"
  | "source"
  | "approval"
  | "opportunity"
  | "agency"
  | "quarantine"
  | "goal"
  | "debate"
  | "idea"
  | "dream"
  | "development";

export type SceneLayer = "cognitive" | "organism" | "diagnostic";

export interface InboxStatus {
  pending?: number;
  processing?: number;
  completed?: number;
  failed?: number;
  total?: number;
  [key: string]: unknown;
}

export interface RunnerStatus {
  ticks?: number;
  total_processed?: number;
  inbox?: number | InboxStatus;
  working_memory_size?: number;
  [key: string]: unknown;
}

export interface ObservedGraphEdge {
  id?: string;
  source?: string;
  target?: string;
  source_node_id?: string;
  target_node_id?: string;
  relation?: string;
  weight?: number;
  confidence?: number;
  evidence_ids?: string[];
  created_at?: string;
  [key: string]: unknown;
}

export interface ObservatorySnapshot {
  capturedAt: string;
  health: HealthResponse | null;
  runner: RunnerStatus | null;
  signals: Signal[];
  evidence: ObservedEvidence[];
  workingMemory: WorkingMemoryObservation | null;
  beliefs: Belief[];
  predictions: Prediction[];
  edges: ObservedGraphEdge[];
  contradictions: Contradiction[];
  curiosity: CuriosityTask[];
  sources: Source[];
  approvals: ApprovalRequest[];
  opportunities: Opportunity[];
  outcomes: Outcome[];
  learningEvents: LearningEvent[];
  organism: OrganismCockpit | null;
  selfState: OrganismSelfState | null;
  organismCuriosity: OrganismCuriosityTask[];
  agencyActions: OrganismAgencyAction[];
  quarantine: OrganismQuarantineItem[];
  persistence: OrganismPersistenceStatus | null;
  errors: string[];
  signature: string;
}

export interface SceneMetric {
  label: string;
  value: string;
  tone?: "neutral" | "attention" | "future" | "warning" | "danger" | "success";
}

export interface SceneNode {
  id: string;
  objectId: string;
  kind: SceneKind;
  layer: SceneLayer;
  label: string;
  summary: string;
  x: number;
  y: number;
  size: number;
  importance: number;
  timestamp?: string;
  state?: string;
  route?: string;
  metrics: SceneMetric[];
  payload: Record<string, unknown>;
}

export interface SceneEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  strength: number;
  tension?: boolean;
}

export interface SceneZone {
  id: "perception" | "belief" | "curiosity" | "prediction" | "learning" | "agency" | "diagnostic";
  label: string;
  count: number;
  state: "active" | "quiet" | "unformed" | "clear";
  detail: string;
}

export interface OrganismProfile {
  focus: string | null;
  phase: string | null;
  assessment: string | null;
  stress: number;
  dominantGoal: string | null;
  dominantGoalPressure: number;
  protectOverridesExploit: boolean;
  activeGoals: string[];
  workspaceItems: number;
  workspaceCapacity: number;
  pressures: {
    uncertainty: number;
    contradiction: number;
    curiosity: number;
    revenue: number;
    risk: number;
    memory: number;
    action: number;
  };
}

export interface CognitiveScene {
  nodes: SceneNode[];
  edges: SceneEdge[];
  chronology: SceneNode[];
  activity: number;
  workingMemorySize: number;
  memoryPressure: number;
  counts: Record<SceneKind, number>;
  cognitiveCount: number;
  diagnosticCount: number;
  zones: SceneZone[];
  organism: OrganismProfile;
}
