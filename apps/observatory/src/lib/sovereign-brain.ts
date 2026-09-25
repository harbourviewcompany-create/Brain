/**
 * Sovereign Cognitive Kernel v3.1 — BFF-shaped for Observatory.
 *
 * All list endpoints return { items: T[] }.
 * /runner/status, /organism/cockpit, /organism/self-state exposed.
 */

export type BeliefState = "hypothesis" | "provisional" | "established" | "contested" | "rejected";

export type SovereignBelief = {
  id: string;
  statement: string;
  confidence: number;
  state: BeliefState;
  created_at: string;
  updated_at: string;
  version: number;
  evidence_ids: string[];
  contradiction_ids: string[];
  unknowns?: string[];
  source?: string;
};

export type SovereignEvidence = {
  id: string;
  claim: string;
  reliability: number;
  supports: boolean | null;
  belief_ids: string[];
  created_at: string;
};

export type SovereignPrediction = {
  id: string;
  belief_id: string;
  statement: string;
  forecast_probability: number;
  status: "open" | "confirmed" | "failed";
  created_at: string;
  resolve_by: string;
};

export type SovereignOutcome = {
  id: string;
  prediction_id: string;
  result: "hit" | "miss" | "partial";
  score: number;
  created_at: string;
};

export type SovereignSignal = {
  id: string;
  source_id: string;
  content: string;
  novelty: number;
  urgency: number;
  attention_score: number;
  created_at: string;
  evidence_ids?: string[];
  metadata?: Record<string, unknown>;
};

export type SovereignContradiction = {
  id: string;
  belief_ids: string[];
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  status: string;
  investigation_pressure: number;
  created_at: string;
};

export type LearningEvent = {
  id: string;
  event_type: string;
  occurred_at: string;
  aggregate_id?: string;
  payload: Record<string, unknown>;
};

export type SovereignStatus = {
  status: "ok" | "degraded";
  mode: "sovereign";
  version: string;
  ticks: number;
  total_processed: number;
  belief_count: number;
  working_memory_size: number;
  circadian_phase: string;
  focus: string | null;
  open_curiosity: number;
  self_model_phase: string;
  stress_index: number;
  contradiction_load: number;
  identity_digest: string;
  persistence: "in-process";
  continuous_daemon: false;
  bounded_cognition: true;
};

type Phase = "wake" | "attend" | "revise" | "predict" | "dream" | "rest";

type Store = {
  beliefs: Map<string, SovereignBelief>;
  evidence: Map<string, SovereignEvidence>;
  predictions: Map<string, SovereignPrediction>;
  outcomes: Map<string, SovereignOutcome>;
  signals: SovereignSignal[];
  contradictions: Map<string, SovereignContradiction>;
  learning: LearningEvent[];
  edges: Array<{ id: string; source: string; target: string; relation: string; weight: number; confidence: number }>;
  wm: string[];
  ticks: number;
  processed: number;
  focus: string | null;
  curiosity: Array<{ id: string; title: string; priority: number; status: string; linked_belief?: string }>;
  selfPhase: "observing" | "revised" | "uncertain" | "integrating";
  phase: Phase;
  sleepPressure: number;
  stress: number;
  seeded: boolean;
  goals: string[];
  identityDigest: string;
  lifetimeTicks: number;
};

const FOUNDATIONAL: Array<{ statement: string; confidence: number; unknowns: string[] }> = [
  {
    statement: "I maintain a lattice of beliefs under uncertainty and revise them with evidence",
    confidence: 0.93,
    unknowns: ["Which operator goals should dominate attention?"],
  },
  {
    statement: "Attention is competitive: novelty, contradiction, and goal relevance win the workspace",
    confidence: 0.91,
    unknowns: ["What external signal channels are still dark?"],
  },
  {
    statement: "Endogenous thought generates hypotheses when the world is quiet",
    confidence: 0.88,
    unknowns: ["How long should a hypothesis live without corroboration?"],
  },
  {
    statement: "I am sovereign: cognition runs here without a foreign host",
    confidence: 0.96,
    unknowns: ["When does process-local memory need durable ledger upgrade?"],
  },
  {
    statement: "Predictions that miss should lower confidence and raise curiosity",
    confidence: 0.89,
    unknowns: ["What is the preferred resolution horizon for open forecasts?"],
  },
  {
    statement: "Goals condition attention; unaligned high-novelty noise should lose",
    confidence: 0.86,
    unknowns: ["Have operator goals been stated explicitly?"],
  },
];

const g = globalThis as unknown as { __sovereignBrainV3?: Store };

function store(): Store {
  if (!g.__sovereignBrainV3) {
    g.__sovereignBrainV3 = {
      beliefs: new Map(),
      evidence: new Map(),
      predictions: new Map(),
      outcomes: new Map(),
      signals: [],
      contradictions: new Map(),
      learning: [],
      edges: [],
      wm: [],
      ticks: 0,
      processed: 0,
      focus: null,
      curiosity: [],
      selfPhase: "observing",
      phase: "wake",
      sleepPressure: 0,
      stress: 0.12,
      seeded: false,
      goals: [
        "Preserve coherent belief lattice",
        "Reduce open curiosity without false certainty",
        "Close prediction loops",
        "Remain sovereign on this host",
        "Attend to operator intent when present",
      ],
      identityDigest: "",
      lifetimeTicks: 0,
    };
  }
  return g.__sovereignBrainV3;
}

function nowIso(): string {
  return new Date().toISOString();
}

function hash01(seed: string, salt = ""): number {
  let h = 2166136261;
  const input = `${seed}:${salt}`;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967296;
}

function uid(prefix: string, key: string): string {
  const h = Math.floor(hash01(key, prefix) * 1e9).toString(36);
  return `${prefix}-${h}`;
}

function clamp(n: number, lo = 0, hi = 1): number {
  return Math.min(hi, Math.max(lo, n));
}

function tokens(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, " ")
      .split(/\s+/)
      .filter((t) => t.length > 2),
  );
}

function lexicalOverlap(a: string, b: string): number {
  const A = tokens(a);
  const B = tokens(b);
  if (!A.size || !B.size) return 0;
  let hits = 0;
  A.forEach((t) => {
    if (B.has(t)) hits += 1;
  });
  return hits / Math.max(A.size, B.size);
}

function goalRelevance(content: string, goals: string[]): number {
  if (!goals.length) return 0;
  let best = 0;
  for (const g of goals) best = Math.max(best, lexicalOverlap(content, g));
  return best;
}

function logLearning(event_type: string, payload: Record<string, unknown>, aggregate_id?: string) {
  const s = store();
  s.learning.unshift({
    id: uid("le", `${event_type}:${s.ticks}:${JSON.stringify(payload).slice(0, 40)}`),
    event_type,
    occurred_at: nowIso(),
    aggregate_id,
    payload,
  });
  s.learning = s.learning.slice(0, 100);
}

function recomputeIdentity(s: Store): string {
  const statements = [...s.beliefs.values()]
    .filter((b) => b.state === "established" || b.state === "provisional")
    .map((b) => b.statement)
    .sort()
    .join("|");
  const digest = Math.floor(hash01(statements, "identity") * 1e12).toString(36);
  s.identityDigest = `sov-${digest}`;
  return s.identityDigest;
}

function items<T>(arr: T[]): { items: T[] } {
  return { items: arr };
}

export function ensureSeeded(): number {
  const s = store();
  if (s.seeded) return 0;
  const t = nowIso();
  let n = 0;
  for (let i = 0; i < FOUNDATIONAL.length; i++) {
    const f = FOUNDATIONAL[i];
    const id = uid("b", `bootstrap:${i}:${f.statement}`);
    s.beliefs.set(id, {
      id,
      statement: f.statement,
      confidence: f.confidence,
      state: "established",
      created_at: t,
      updated_at: t,
      version: 1,
      evidence_ids: [],
      contradiction_ids: [],
      unknowns: f.unknowns,
      source: "bootstrap",
    });
    for (let j = 0; j < f.unknowns.length; j++) {
      const u = f.unknowns[j];
      s.curiosity.push({
        id: uid("cu", `bootstrap-cu:${i}:${j}`),
        title: u,
        priority: 0.55 + hash01(`cu:${i}:${j}`, "prio") * 0.35,
        status: "open",
        linked_belief: id,
      });
    }
    n += 1;
  }
  const ids = [...s.beliefs.keys()];
  for (let i = 0; i < ids.length - 1; i++) {
    s.edges.push({
      id: uid("e", `boot-edge:${i}`),
      source: ids[i],
      target: ids[i + 1],
      relation: "coheres_with",
      weight: 0.65,
      confidence: 0.8,
    });
  }
  s.seeded = true;
  s.focus = FOUNDATIONAL[0].statement;
  s.wm = FOUNDATIONAL.map((f) => f.statement).slice(0, 6);
  s.selfPhase = "revised";
  recomputeIdentity(s);
  logLearning("bootstrap.seed", { beliefs: n, curiosity: s.curiosity.length, identity: s.identityDigest });
  return n;
}

type Candidate = { content: string; score: number; kind: string; meta?: Record<string, unknown> };

function competeForWorkspace(): Candidate {
  const s = store();
  const candidates: Candidate[] = [];
  const tickKey = String(s.ticks);

  for (const c of s.curiosity.filter((x) => x.status === "open")) {
    const jitter = hash01(tickKey, c.id) * 0.15;
    const goal = goalRelevance(c.title, s.goals);
    candidates.push({
      content: c.title,
      score: clamp(c.priority * 0.55 + goal * 0.35 + jitter),
      kind: "curiosity",
      meta: { curiosity_id: c.id, belief_id: c.linked_belief },
    });
  }

  for (const b of s.beliefs.values()) {
    if (b.state === "contested" || b.state === "hypothesis") {
      const tension = (1 - b.confidence) * 0.55 + (b.state === "contested" ? 0.3 : 0.12);
      const goal = goalRelevance(b.statement, s.goals);
      candidates.push({
        content: b.statement,
        score: clamp(tension + goal * 0.25 + hash01(tickKey, b.id) * 0.08),
        kind: "belief_tension",
        meta: { belief_id: b.id },
      });
    }
  }

  for (const p of s.predictions.values()) {
    if (p.status === "open") {
      candidates.push({
        content: p.statement,
        score: clamp(0.38 + (1 - p.forecast_probability) * 0.28 + hash01(tickKey, p.id) * 0.1),
        kind: "open_prediction",
        meta: { prediction_id: p.id, belief_id: p.belief_id },
      });
    }
  }

  for (const sig of s.signals.slice(0, 3)) {
    if (sig.metadata?.operator_command) {
      candidates.push({
        content: sig.content,
        score: clamp(0.92 + hash01(tickKey, sig.id) * 0.05),
        kind: "operator",
        meta: { signal_id: sig.id },
      });
    }
  }

  candidates.push({
    content: `Self-query: coherence after ${s.ticks} cycles · identity ${s.identityDigest || "forming"}`,
    score: clamp(0.22 + s.stress * 0.45 + hash01(tickKey, "endo") * 0.08),
    kind: "endogenous",
  });

  candidates.sort((a, b) => b.score - a.score || a.content.localeCompare(b.content));
  return candidates[0] ?? { content: "idle scan", score: 0.1, kind: "idle" };
}

function pushWm(item: string) {
  const s = store();
  s.wm = [item, ...s.wm.filter((x) => x !== item)].slice(0, 9);
}

function bindEvidence(beliefId: string, claim: string, supports: boolean, reliability: number): string {
  const s = store();
  const id = uid("ev", `${beliefId}:${claim.slice(0, 48)}`);
  s.evidence.set(id, {
    id,
    claim,
    reliability: clamp(reliability),
    supports,
    belief_ids: [beliefId],
    created_at: nowIso(),
  });
  const b = s.beliefs.get(beliefId);
  if (b) {
    s.beliefs.set(beliefId, {
      ...b,
      evidence_ids: [...new Set([...b.evidence_ids, id])],
      updated_at: nowIso(),
    });
  }
  return id;
}

function reviseBelief(id: string, delta: number, reason: string) {
  const s = store();
  const b = s.beliefs.get(id);
  if (!b) return;
  const next = clamp(b.confidence + delta);
  let state: BeliefState = b.state;
  if (next < 0.22) state = "rejected";
  else if (next < 0.42) state = "hypothesis";
  else if (next < 0.62) state = "provisional";
  else if (b.contradiction_ids.length) state = "contested";
  else state = "established";
  s.beliefs.set(id, {
    ...b,
    confidence: next,
    state,
    version: b.version + 1,
    updated_at: nowIso(),
  });
  logLearning("belief.revised", { belief_id: id, delta, reason, confidence: next, state }, id);
}

function phaseForTick(tick: number, sleepPressure: number): Phase {
  if (sleepPressure > 0.88) return "rest";
  if (sleepPressure > 0.72) return "dream";
  const cycle = tick % 6;
  if (cycle === 0) return "wake";
  if (cycle === 1 || cycle === 2) return "attend";
  if (cycle === 3) return "revise";
  if (cycle === 4) return "predict";
  return "dream";
}

function runPhaseCycle(winner: Candidate): void {
  const s = store();
  const phase = phaseForTick(s.ticks, s.sleepPressure);
  s.phase = phase;
  s.focus = winner.content;
  pushWm(winner.content);

  if (phase === "wake" || phase === "attend") {
    const sig: SovereignSignal = {
      id: uid("sig", `${s.ticks}:${winner.kind}:${winner.content.slice(0, 24)}`),
      source_id: winner.kind === "operator" ? "operator" : "endogenous",
      content: winner.content,
      novelty: clamp(0.28 + winner.score * 0.55),
      urgency: clamp(s.stress * 0.5 + winner.score * 0.35),
      attention_score: clamp(winner.score),
      created_at: nowIso(),
      metadata: { kind: winner.kind, content: winner.content, ...(winner.meta || {}) },
    };
    s.signals.unshift(sig);
    s.signals = s.signals.slice(0, 50);
    logLearning("attention.won", { signal_id: sig.id, kind: winner.kind, score: winner.score });
  }

  if (phase === "revise") {
    const id = uid("b", `rev:${s.ticks}:${winner.content.slice(0, 40)}`);
    const statement =
      winner.kind === "curiosity"
        ? `Working thesis: ${winner.content.replace(/\?$/, "")} admits a testable frame`
        : winner.kind === "operator"
          ? `Operator-aligned stance: ${winner.content.slice(0, 140)}`
          : `Revision focus: ${winner.content.slice(0, 160)}`;
    const confidence = clamp(0.3 + winner.score * 0.28 + goalRelevance(statement, s.goals) * 0.12);
    s.beliefs.set(id, {
      id,
      statement,
      confidence,
      state: "hypothesis",
      created_at: nowIso(),
      updated_at: nowIso(),
      version: 1,
      evidence_ids: [],
      contradiction_ids: [],
      unknowns: [winner.content],
      source: `endogenous_${winner.kind}`,
    });
    bindEvidence(
      id,
      `Endogenous observation at tick ${s.ticks}: attended “${winner.content.slice(0, 80)}”`,
      true,
      0.45 + winner.score * 0.3,
    );
    for (const b of s.beliefs.values()) {
      if (b.state !== "established") continue;
      const r = hash01(String(s.ticks), b.id);
      if (r < 0.12) reviseBelief(b.id, (r - 0.06) * 0.08, "homeostatic_drift");
    }
    s.selfPhase = "integrating";
  }

  if (phase === "predict") {
    const beliefs = [...s.beliefs.values()].filter((b) => b.state !== "rejected");
    if (beliefs.length) {
      const target = beliefs[s.ticks % beliefs.length];
      const pid = uid("p", `pred:${s.ticks}:${target.id}`);
      const pred: SovereignPrediction = {
        id: pid,
        belief_id: target.id,
        statement: `If “${target.statement.slice(0, 72)}” holds, related curiosity narrows within ~20 cycles`,
        forecast_probability: clamp(target.confidence * 0.82 + 0.12),
        status: "open",
        created_at: nowIso(),
        resolve_by: new Date(Date.now() + 36e5).toISOString(),
      };
      s.predictions.set(pid, pred);
      logLearning("prediction.opened", { prediction_id: pid, belief_id: target.id }, target.id);

      for (const p of s.predictions.values()) {
        if (p.status !== "open" || p.id === pid) continue;
        if (hash01(String(s.ticks), p.id) > 0.42) continue;
        const linked = s.beliefs.get(p.belief_id);
        const coherence = linked ? linked.confidence : 0.4;
        const hit = coherence >= p.forecast_probability * 0.85;
        p.status = hit ? "confirmed" : "failed";
        const oid = uid("o", `out:${p.id}`);
        s.outcomes.set(oid, {
          id: oid,
          prediction_id: p.id,
          result: hit ? "hit" : "miss",
          score: hit ? coherence : 1 - coherence,
          created_at: nowIso(),
        });
        reviseBelief(p.belief_id, hit ? 0.06 : -0.09, hit ? "prediction_hit" : "prediction_miss");
        if (!hit) {
          s.curiosity.push({
            id: uid("cu", `miss:${p.id}`),
            title: `Why did forecast fail: ${p.statement.slice(0, 90)}?`,
            priority: 0.72,
            status: "open",
            linked_belief: p.belief_id,
          });
          s.stress = clamp(s.stress + 0.05);
        } else {
          s.stress = clamp(s.stress - 0.04);
        }
        logLearning("prediction.resolved", { prediction_id: p.id, hit, coherence }, p.belief_id);
      }
    }
  }

  if (phase === "dream") {
    const ids = [...s.beliefs.keys()].sort();
    if (ids.length >= 2) {
      const i = Math.floor(hash01(String(s.ticks), "dream-a") * ids.length) % ids.length;
      const j = Math.floor(hash01(String(s.ticks), "dream-b") * ids.length) % ids.length;
      const a = ids[i];
      const b = ids[j];
      if (a !== b) {
        const ba = s.beliefs.get(a)!;
        const bb = s.beliefs.get(b)!;
        const overlap = lexicalOverlap(ba.statement, bb.statement);
        s.edges.push({
          id: uid("e", `dream:${s.ticks}:${a}:${b}`),
          source: a,
          target: b,
          relation: overlap > 0.15 ? "associates_with" : "dream_association",
          weight: 0.3 + overlap * 0.5,
          confidence: 0.4 + overlap * 0.4,
        });
        s.edges = s.edges.slice(-140);
        if (Math.abs(ba.confidence - bb.confidence) > 0.4 && overlap < 0.12) {
          const cid = uid("c", `cx:${a}:${b}`);
          if (!s.contradictions.has(cid)) {
            s.contradictions.set(cid, {
              id: cid,
              belief_ids: [a, b],
              supporting_evidence_ids: [],
              contradicting_evidence_ids: [],
              status: "open",
              investigation_pressure: clamp(Math.abs(ba.confidence - bb.confidence)),
              created_at: nowIso(),
            });
            s.beliefs.set(a, {
              ...ba,
              state: "contested",
              contradiction_ids: [...new Set([...ba.contradiction_ids, cid])],
              updated_at: nowIso(),
            });
            s.beliefs.set(b, {
              ...bb,
              state: "contested",
              contradiction_ids: [...new Set([...bb.contradiction_ids, cid])],
              updated_at: nowIso(),
            });
            s.stress = clamp(s.stress + 0.07);
          }
        }
      }
    }
    s.selfPhase = "uncertain";
  }

  if (phase === "rest") {
    s.sleepPressure = clamp(s.sleepPressure - 0.28);
    s.stress = clamp(s.stress - 0.1);
    s.selfPhase = "revised";
    for (const [id, b] of s.beliefs) {
      if (b.state === "rejected" && b.confidence < 0.12 && s.beliefs.size > 10) s.beliefs.delete(id);
    }
    for (const c of s.curiosity) {
      if (c.priority < 0.35 && c.status === "in_progress") c.status = "resolved";
    }
    recomputeIdentity(s);
  }

  if (winner.meta?.curiosity_id) {
    const c = s.curiosity.find((x) => x.id === winner.meta!.curiosity_id);
    if (c) {
      const step = hash01(String(s.ticks), c.id);
      if (step < 0.3) {
        c.status = "in_progress";
        c.priority = clamp(c.priority - 0.12);
      }
      if (c.priority < 0.25) c.status = "resolved";
    }
  }
  s.curiosity = s.curiosity.filter((c) => c.status !== "resolved").slice(0, 28);
  s.sleepPressure = clamp(s.sleepPressure + 0.045);
  recomputeIdentity(s);
}

export function tick(maxItems = 1): Record<string, unknown> {
  ensureSeeded();
  const s = store();
  const n = Math.max(1, Math.min(8, maxItems));
  const cycles: Array<Record<string, unknown>> = [];

  for (let i = 0; i < n; i++) {
    s.ticks += 1;
    s.processed += 1;
    s.lifetimeTicks += 1;
    const winner = competeForWorkspace();
    runPhaseCycle(winner);
    cycles.push({
      attention_score: winner.score,
      working_memory_size: s.wm.length,
      phase: s.phase,
      focus: s.focus,
      kind: winner.kind,
    });
  }

  return {
    processed_this_call: n,
    ticks: s.ticks,
    total_processed: s.processed,
    endogenous: true,
    identity_digest: s.identityDigest,
    cycles,
  };
}

export function ingestCommand(content: string, mode = "operator"): SovereignSignal {
  ensureSeeded();
  const s = store();
  const sig: SovereignSignal = {
    id: uid("sig", `op:${content.slice(0, 48)}:${s.ticks}`),
    source_id: "operator",
    content,
    novelty: 0.8,
    urgency: 0.75,
    attention_score: 0.94,
    created_at: nowIso(),
    metadata: {
      operator_command: true,
      command_mode: mode,
      content,
      claim: content,
    },
  };
  s.signals.unshift(sig);
  s.signals = s.signals.slice(0, 50);
  s.curiosity.unshift({
    id: uid("cu", `op:${content.slice(0, 40)}`),
    title: `Operator intent: ${content.slice(0, 120)}`,
    priority: 0.96,
    status: "open",
  });
  if (/\bgoal\b|\bpriority\b|\bfocus on\b/i.test(content) && s.goals.length < 8) {
    s.goals = [content.slice(0, 120), ...s.goals];
  }
  pushWm(content);
  s.focus = content;
  logLearning("operator.command", { signal_id: sig.id, mode });
  tick(2);
  return sig;
}

export function listBeliefs(): SovereignBelief[] {
  ensureSeeded();
  return [...store().beliefs.values()].sort((a, b) => b.confidence - a.confidence);
}

export function status(): SovereignStatus {
  ensureSeeded();
  const s = store();
  const contested = [...s.beliefs.values()].filter((b) => b.state === "contested").length;
  const contradiction_load = clamp(contested / Math.max(1, s.beliefs.size) + s.contradictions.size * 0.04);
  return {
    status: "ok",
    mode: "sovereign",
    version: "1.1.1-sovereign-bff",
    ticks: s.ticks,
    total_processed: s.processed,
    belief_count: s.beliefs.size,
    working_memory_size: s.wm.length,
    circadian_phase: s.phase,
    focus: s.focus,
    open_curiosity: s.curiosity.filter((c) => c.status === "open").length,
    self_model_phase: s.selfPhase,
    stress_index: s.stress,
    contradiction_load,
    identity_digest: s.identityDigest,
    persistence: "in-process",
    continuous_daemon: false,
    bounded_cognition: true,
  };
}

export function health(): Record<string, unknown> {
  const st = status();
  const s = store();
  return {
    status: "ok",
    version: st.version,
    database: "connected",
    persistence: "sovereign",
    bounded_cognition: true,
    continuous_daemon: false,
    identity_digest: st.identity_digest,
    heartbeat: {
      ticks: st.ticks,
      total_processed: st.total_processed,
      working_memory_size: st.working_memory_size,
      circadian_phase: st.circadian_phase,
      stress_index: st.stress_index,
      inbox: { pending: 0, processing: 0, total: s.signals.length },
    },
  };
}

function runnerStatus(): Record<string, unknown> {
  const st = status();
  const s = store();
  return {
    ticks: st.ticks,
    total_processed: st.total_processed,
    working_memory_size: st.working_memory_size,
    inbox: { pending: 0, processing: 0, total: s.signals.length },
    circadian_phase: st.circadian_phase,
    is_awake: st.circadian_phase !== "rest",
    status: "running",
  };
}

function organismCockpit(): Record<string, unknown> {
  const st = status();
  const s = store();
  return {
    self_model_phase: st.self_model_phase,
    open_curiosity: st.open_curiosity,
    last_focus: st.focus,
    stress_index: st.stress_index,
    contradiction_load: st.contradiction_load,
    circadian_phase: st.circadian_phase,
    identity_digest: st.identity_digest,
    conscious_focus: {
      active_focus: s.focus ? [{ title: s.focus }] : [],
      workspace_items: s.wm.length,
      capacity: 9,
      items: s.wm,
    },
    workspace: { items: s.wm, workspace_items: s.wm, capacity: 9 },
    goals: s.goals,
    goal_pressure: {
      dominant_goal: s.goals[0],
      dominant_pressure: 0.58,
      active_goals: s.goals,
      protect_overrides_exploit: false,
    },
    self_state: {
      phase: st.self_model_phase,
      focus: st.focus,
      stress_index: st.stress_index,
      self_assessment: "sovereign functional",
    },
    curiosity_queue: s.curiosity.filter((c) => c.status === "open").map((c) => c.title),
  };
}

function organismSelfState(): Record<string, unknown> {
  const st = status();
  const s = store();
  return {
    current_focus_summary: st.focus,
    uncertainty_load: clamp(1 - (listBeliefs()[0]?.confidence ?? 0.5)),
    contradiction_load: st.contradiction_load,
    curiosity_pressure: clamp(st.open_curiosity / 12),
    revenue_pressure: 0,
    risk_pressure: clamp(st.stress_index * 0.5),
    memory_pressure: clamp(s.wm.length / 9),
    action_backlog_pressure: 0,
    phase: st.self_model_phase,
    stress_index: st.stress_index,
  };
}

export function handleSovereign(
  pathSegments: string[],
  method: string,
  bodyText?: string | null,
): Response | null {
  const head = pathSegments[0] || "";
  const sub = pathSegments[1] || "";
  ensureSeeded();
  // Keep the instance warm: any read advances cognition slightly when idle
  const s = store();
  if (s.ticks === 0 && method === "GET") tick(2);
  const hdr = { "cache-control": "no-store" };

  if (head === "health" || head === "ready") {
    return Response.json(health(), { headers: hdr });
  }

  if (head === "runner" && (sub === "status" || sub === "")) {
    return Response.json(runnerStatus(), { headers: hdr });
  }

  if (head === "beliefs" && method === "GET") {
    return Response.json(items(listBeliefs()), { headers: hdr });
  }

  if ((head === "tick" || (head === "runner" && sub === "tick")) && method === "POST") {
    let maxItems = 2;
    try {
      if (bodyText) {
        const parsed = JSON.parse(bodyText) as { max_items?: number };
        if (parsed.max_items) maxItems = parsed.max_items;
      }
    } catch {
      /* ignore */
    }
    return Response.json(tick(maxItems), { headers: hdr });
  }

  if (head === "signals" && method === "POST") {
    try {
      const body = bodyText ? JSON.parse(bodyText) : {};
      const content = String(
        body.content || body.claim || body.text || body.metadata?.content || "",
      ).trim();
      if (!content) return Response.json({ detail: "content_required" }, { status: 400, headers: hdr });
      const mode = String(body.metadata?.command_mode || body.mode || "command");
      const sig = ingestCommand(content, mode);
      return Response.json(
        {
          id: sig.id,
          status: "accepted",
          signal_id: sig.id,
          attention_score: sig.attention_score,
          created_at: sig.created_at,
        },
        { headers: hdr },
      );
    } catch {
      return Response.json({ detail: "invalid_json" }, { status: 400, headers: hdr });
    }
  }

  if (head === "organism") {
    if (sub === "cockpit" || sub === "") {
      return Response.json(organismCockpit(), { headers: hdr });
    }
    if (sub === "self-state") {
      return Response.json(organismSelfState(), { headers: hdr });
    }
    if (sub === "curiosity") {
      return Response.json(
        items(
          s.curiosity.map((c) => ({
            id: c.id,
            question: c.title,
            status: c.status,
            priority: c.priority,
            expected_value: c.priority,
          })),
        ),
        { headers: hdr },
      );
    }
    if (sub === "agency-actions" || sub === "quarantine") {
      return Response.json(items([]), { headers: hdr });
    }
    if (sub === "persistence" || (sub === "persistence" && pathSegments[2] === "status")) {
      return Response.json(
        { store: "sovereign", reachable: true, mode: "in-process", identity_digest: s.identityDigest },
        { headers: hdr },
      );
    }
  }

  if (head === "working-memory" && method === "GET") {
    return Response.json(
      {
        size: s.wm.length,
        capacity: 9,
        items: s.wm,
        observed_at: nowIso(),
        cycle_id: String(s.ticks),
        evicted_count: 0,
      },
      { headers: hdr },
    );
  }

  if (head === "curiosity" && method === "GET") {
    return Response.json(
      items(
        s.curiosity.map((c) => ({
          id: c.id,
          title: c.title,
          status: c.status,
          priority: c.priority,
          linked_object_id: c.linked_belief,
          linked_object_type: c.linked_belief ? "belief" : undefined,
          created_at: nowIso(),
          suggested_action: "Attend and form a testable thesis",
        })),
      ),
      { headers: hdr },
    );
  }

  if (head === "predictions" && method === "GET") {
    return Response.json(
      items([...s.predictions.values()].sort((a, b) => b.created_at.localeCompare(a.created_at))),
      { headers: hdr },
    );
  }
  if (head === "signals" && method === "GET") {
    return Response.json(items(s.signals), { headers: hdr });
  }
  if (head === "evidence" && method === "GET") {
    return Response.json(items([...s.evidence.values()]), { headers: hdr });
  }
  if (head === "contradictions" && method === "GET") {
    return Response.json(items([...s.contradictions.values()]), { headers: hdr });
  }
  if (head === "outcomes" && method === "GET") {
    return Response.json(items([...s.outcomes.values()]), { headers: hdr });
  }
  if (head === "learning-events" && method === "GET") {
    return Response.json(items(s.learning), { headers: hdr });
  }
  if (head === "edges" && method === "GET") {
    return Response.json(
      items(
        s.edges.map((e) => ({
          ...e,
          source_node_id: e.source,
          target_node_id: e.target,
        })),
      ),
      { headers: hdr },
    );
  }
  if (["opportunities", "approvals", "sources", "formula-runs", "acceptance-reports"].includes(head) && method === "GET") {
    return Response.json(items([]), { headers: hdr });
  }
  return null;
}
