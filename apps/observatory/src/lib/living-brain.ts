import type { Belief, Outcome, Prediction, Signal } from "@/types/brain";
import type { LearningEvent, ObservedEvidence } from "@/types/living-brain";
import type { CognitiveScene, ObservatorySnapshot } from "@/types/observatory";

export interface CommandHistoryItem {
  id: string;
  content: string;
  mode: string;
  createdAt: string;
  attention: number;
}

export interface RetrievalItem {
  evidence: ObservedEvidence;
  score: number;
  lexical: number;
  reason: string[];
}

export interface HypothesisItem {
  belief: Belief;
  supporting: number;
  contradicting: number;
}

export interface LivingBrainModel {
  state: "observing" | "active" | "quiet" | "degraded";
  commandHistory: CommandHistoryItem[];
  focus: string | null;
  attentionScore: number | null;
  attentionSignal: Signal | null;
  workingMemorySize: number | null;
  workingMemoryCapacity: number | null;
  workingMemoryPressure: number | null;
  workspaceItems: string[];
  retrieval: RetrievalItem[];
  hypotheses: HypothesisItem[];
  predictions: Prediction[];
  outcomes: Outcome[];
  learningEvents: LearningEvent[];
  goals: string[];
  goalTension: number | null;
  warnings: Array<{ label: string; detail: string; severity: "warning" | "danger" }>;
  health: Array<{ label: string; value: string }>;
  trace: {
    conclusion: Belief | null;
    evidence: ObservedEvidence[];
    pathways: Array<{ id: string; relation: string; weight: number; confidence: number; source: string; target: string }>;
    predictions: Prediction[];
    outcomes: Outcome[];
    learning: LearningEvent[];
  };
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function numberOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function text(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed || null;
}

function signalContent(signal: Signal): string {
  const metadata = signal.metadata ?? {};
  return text(metadata.content) ?? text(metadata.claim) ?? `Signal from ${signal.source_id}`;
}

function commandMode(signal: Signal): string {
  const raw = text(signal.metadata?.command_mode);
  return raw?.replaceAll("_", " ") ?? "command";
}

function isCommandSignal(signal: Signal): boolean {
  return signal.metadata?.operator_command === true || Boolean(text(signal.metadata?.command_mode));
}

function terms(value: string | null): Set<string> {
  if (!value) return new Set();
  return new Set(
    value
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, " ")
      .split(/\s+/)
      .map((part) => part.trim())
      .filter((part) => part.length > 2),
  );
}

function lexicalScore(query: Set<string>, value: string): number {
  if (!query.size) return 0;
  const haystack = terms(value);
  let hits = 0;
  query.forEach((term) => {
    if (haystack.has(term)) hits += 1;
  });
  return hits / query.size;
}

function workspaceItems(snapshot: ObservatorySnapshot): string[] {
  const workspace = asRecord(snapshot.organism?.workspace);
  if (!workspace) return [];
  const candidates = [workspace.items, workspace.active, workspace.focus, workspace.workspace_items];
  const out: string[] = [];
  for (const candidate of candidates) {
    if (!Array.isArray(candidate)) continue;
    for (const item of candidate) {
      if (typeof item === "string") out.push(item);
      else {
        const record = asRecord(item);
        const label = text(record?.title) ?? text(record?.content) ?? text(record?.summary);
        if (label) out.push(label);
      }
    }
  }
  return [...new Set(out)].slice(0, 6);
}

function goalData(snapshot: ObservatorySnapshot): { goals: string[]; tension: number | null } {
  const raw = snapshot.organism?.goals;
  if (Array.isArray(raw)) {
    return {
      goals: raw
        .map((item) => (typeof item === "string" ? item : text(asRecord(item)?.description) ?? text(asRecord(item)?.name)))
        .filter((item): item is string => Boolean(item))
        .slice(0, 6),
      tension: null,
    };
  }
  const record = asRecord(raw);
  const items = Array.isArray(record?.items) ? record.items : [];
  return {
    goals: items
      .map((item) => (typeof item === "string" ? item : text(asRecord(item)?.description) ?? text(asRecord(item)?.name)))
      .filter((item): item is string => Boolean(item))
      .slice(0, 6),
    tension: numberOrNull(record?.tension),
  };
}

function inboxActive(snapshot: ObservatorySnapshot): number {
  const inbox = snapshot.runner?.inbox;
  if (typeof inbox === "number") return inbox;
  if (inbox && typeof inbox === "object") {
    return Number(inbox.pending ?? 0) + Number(inbox.processing ?? 0);
  }
  return 0;
}

export function buildLivingBrainModel(snapshot: ObservatorySnapshot | null, scene: CognitiveScene): LivingBrainModel {
  if (!snapshot) {
    return {
      state: "observing",
      commandHistory: [],
      focus: null,
      attentionScore: null,
      attentionSignal: null,
      workingMemorySize: null,
      workingMemoryCapacity: null,
      workingMemoryPressure: null,
      workspaceItems: [],
      retrieval: [],
      hypotheses: [],
      predictions: [],
      outcomes: [],
      learningEvents: [],
      goals: [],
      goalTension: null,
      warnings: [],
      health: [],
      trace: { conclusion: null, evidence: [], pathways: [], predictions: [], outcomes: [], learning: [] },
    };
  }

  const commandHistory = snapshot.signals
    .filter(isCommandSignal)
    .map((signal) => ({
      id: signal.id,
      content: signalContent(signal),
      mode: commandMode(signal),
      createdAt: signal.created_at,
      attention: signal.attention_score,
    }))
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
    .slice(0, 12);

  const attentionSignal = [...snapshot.signals].sort((a, b) => b.attention_score - a.attention_score)[0] ?? null;
  const focus = text(snapshot.selfState?.current_focus_summary) ?? commandHistory[0]?.content ?? (attentionSignal ? signalContent(attentionSignal) : null);
  const query = terms(commandHistory[0]?.content ?? focus);

  // This is intentionally an Observatory projection over persisted evidence,
  // not a claim that MultiSystemMemory.retrieve_episodes is wired to production.
  // The score is fully disclosed so operators can distinguish UI ranking from
  // Brain-native memory retrieval: 70% lexical overlap + 30% source reliability.
  const retrieval = snapshot.evidence
    .map((evidence) => {
      const lexical = lexicalScore(query, evidence.claim);
      const reliability = Math.max(0, Math.min(1, evidence.reliability));
      const score = query.size ? lexical * 0.7 + reliability * 0.3 : reliability;
      return {
        evidence,
        lexical,
        score,
        reason: [`lexical ${(lexical * 100).toFixed(0)}%`, `source reliability ${(reliability * 100).toFixed(0)}%`],
      };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 8);

  const hypotheses = snapshot.beliefs
    .filter((belief) => ["hypothesis", "provisional", "contested", "rejected"].includes(belief.state))
    .map((belief) => {
      const linkedEvidence = snapshot.evidence.filter((item) => item.belief_ids.includes(belief.id));
      const contradiction = snapshot.contradictions.find((item) => item.belief_ids.includes(belief.id));
      return {
        belief,
        supporting:
          linkedEvidence.filter((item) => item.supports === true).length ||
          contradiction?.supporting_evidence_ids.length ||
          belief.evidence_ids?.length ||
          0,
        contradicting:
          linkedEvidence.filter((item) => item.supports === false).length ||
          contradiction?.contradicting_evidence_ids.length ||
          0,
      };
    })
    .sort((a, b) => b.belief.confidence - a.belief.confidence);

  const conclusion = hypotheses.find((item) => item.belief.state !== "rejected")?.belief ?? snapshot.beliefs[0] ?? null;
  const linkedContradictions = conclusion ? snapshot.contradictions.filter((item) => item.belief_ids.includes(conclusion.id)) : [];
  const evidenceIds = new Set<string>(conclusion?.evidence_ids ?? []);
  linkedContradictions.forEach((item) => {
    item.supporting_evidence_ids.forEach((id) => evidenceIds.add(id));
    item.contradicting_evidence_ids.forEach((id) => evidenceIds.add(id));
  });
  const traceEvidence = snapshot.evidence.filter((item) => evidenceIds.has(item.id) || item.belief_ids.includes(conclusion?.id ?? ""));
  const pathways = conclusion
    ? snapshot.edges
        .filter((edge) => edge.source === conclusion.id || edge.target === conclusion.id || edge.source_node_id === conclusion.id || edge.target_node_id === conclusion.id)
        .map((edge, index) => ({
          id: edge.id ?? `${edge.source ?? edge.source_node_id ?? "?"}:${edge.target ?? edge.target_node_id ?? "?"}:${index}`,
          relation: edge.relation ?? "related",
          weight: Number(edge.weight ?? 0),
          confidence: Number(edge.confidence ?? 0),
          source: edge.source ?? edge.source_node_id ?? "unknown",
          target: edge.target ?? edge.target_node_id ?? "unknown",
        }))
    : [];
  const tracePredictions = conclusion ? snapshot.predictions.filter((item) => item.belief_id === conclusion.id) : [];
  const predictionIds = new Set(tracePredictions.map((item) => item.id));
  const traceOutcomes = snapshot.outcomes.filter((item) => item.prediction_id && predictionIds.has(item.prediction_id));
  const outcomeIds = new Set(traceOutcomes.map((item) => item.id));
  const pathwayIds = new Set(pathways.map((item) => item.id));
  const traceLearning = snapshot.learningEvents.filter((event) => {
    const payload = event.payload ?? {};
    const predictionId = text(payload.prediction_id);
    const outcomeId = text(payload.outcome_id);
    const edgeIds = Array.isArray(payload.edge_ids) ? payload.edge_ids.map(String) : [];
    return Boolean(
      (predictionId && predictionIds.has(predictionId)) ||
        (outcomeId && outcomeIds.has(outcomeId)) ||
        edgeIds.some((id) => pathwayIds.has(id)) ||
        (conclusion && event.aggregate_id === conclusion.id),
    );
  });

  const workingMemorySize =
    numberOrNull(snapshot.workingMemory?.size) ??
    numberOrNull(snapshot.runner?.working_memory_size) ??
    numberOrNull(snapshot.health?.heartbeat?.working_memory_size);
  const workingMemoryCapacity = numberOrNull(snapshot.workingMemory?.capacity);
  const workingMemoryPressure = numberOrNull(snapshot.selfState?.memory_pressure);
  const goal = goalData(snapshot);

  const warnings: LivingBrainModel["warnings"] = [];
  if (snapshot.errors.length) warnings.push({ label: "READ DEGRADATION", detail: `${snapshot.errors.length} live surface${snapshot.errors.length === 1 ? "" : "s"} degraded`, severity: "danger" });
  if ((workingMemoryPressure ?? 0) >= 0.75) warnings.push({ label: "MEMORY PRESSURE", detail: `${Math.round((workingMemoryPressure ?? 0) * 100)}% reported by self-state`, severity: "warning" });
  const contradictionLoad = numberOrNull(snapshot.selfState?.contradiction_load);
  if ((contradictionLoad ?? 0) >= 0.5) warnings.push({ label: "CONFLICT", detail: `${Math.round((contradictionLoad ?? 0) * 100)}% contradiction load`, severity: "warning" });
  if (snapshot.quarantine.length) warnings.push({ label: "QUARANTINE", detail: `${snapshot.quarantine.length} isolated item${snapshot.quarantine.length === 1 ? "" : "s"}`, severity: "danger" });

  const isActive = inboxActive(snapshot) > 0 || scene.activity > 0 || Boolean(focus);
  const state: LivingBrainModel["state"] = snapshot.errors.length ? "degraded" : isActive ? "active" : "quiet";
  const health = [
    { label: "Runtime", value: snapshot.health?.status ?? "unknown" },
    { label: "Persistence", value: snapshot.persistence?.store ?? snapshot.health?.persistence ?? "unknown" },
    { label: "Cycles", value: String(snapshot.runner?.ticks ?? snapshot.health?.heartbeat?.ticks ?? 0) },
    { label: "Processed", value: String(snapshot.runner?.total_processed ?? snapshot.health?.heartbeat?.total_processed ?? 0) },
    { label: "Beliefs", value: String(snapshot.beliefs.length) },
    { label: "Evidence", value: String(snapshot.evidence.length) },
  ];

  return {
    state,
    commandHistory,
    focus,
    attentionScore: attentionSignal?.attention_score ?? null,
    attentionSignal,
    workingMemorySize,
    workingMemoryCapacity,
    workingMemoryPressure,
    workspaceItems: workspaceItems(snapshot),
    retrieval,
    hypotheses: hypotheses.slice(0, 8),
    predictions: [...snapshot.predictions].sort((a, b) => (b.forecast_probability ?? 0) - (a.forecast_probability ?? 0)).slice(0, 6),
    outcomes: [...snapshot.outcomes].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 6),
    learningEvents: [...snapshot.learningEvents].sort((a, b) => b.occurred_at.localeCompare(a.occurred_at)).slice(0, 12),
    goals: goal.goals,
    goalTension: goal.tension,
    warnings,
    health,
    trace: { conclusion, evidence: traceEvidence, pathways, predictions: tracePredictions, outcomes: traceOutcomes, learning: traceLearning },
  };
}
