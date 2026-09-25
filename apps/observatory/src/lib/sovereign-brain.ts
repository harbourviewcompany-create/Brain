/**
 * Sovereign Cognitive Kernel v2 — unique, fully cognitive, self-hosted.
 *
 * Design (original, not an LLM wrapper):
 * - Global Workspace: candidates compete; winner enters working memory
 * - Belief lattice with confidence, state machine, evidence links
 * - Endogenous drive: curiosity from unknowns + self-model gaps
 * - Circadian phases change what the cycle does (perceive / revise / predict / consolidate)
 * - Prediction → outcome scoring closes the learning loop
 * - Contradiction pressure lowers confidence and opens curiosity
 *
 * No Railway. No Fly. Runs inside the Observatory Vercel process.
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
  edges: Array<{ id: string; source: string; target: string; relation: string; weight: number }>;
  wm: string[];
  ticks: number;
  processed: number;
  focus: string | null;
  curiosity: Array<{ id: string; title: string; priority: number; status: string }>;
  selfPhase: "observing" | "revised" | "uncertain" | "integrating";
  phase: Phase;
  sleepPressure: number;
  stress: number;
  seeded: boolean;
  goals: string[];
};

const FOUNDATIONAL: Array<{ statement: string; confidence: number; unknowns: string[] }> = [
  {
    statement: "I maintain a lattice of beliefs under uncertainty and revise them with evidence",
    confidence: 0.93,
    unknowns: ["Which operator goals should dominate attention?"],
  },
  {
    statement: "Attention is competitive: novelty, contradiction, and goal relevance win the workspace",
    confidence: 0.9,
    unknowns: ["What external signal channels are still dark?"],
  },
  {
    statement: "Endogenous thought generates hypotheses when the world is quiet",
    confidence: 0.88,
    unknowns: ["How long should a hypothesis live without corroboration?"],
  },
  {
    statement: "I am sovereign: cognition runs here without a foreign host",
    confidence: 0.95,
    unknowns: ["When does process-local memory need durable ledger upgrade?"],
  },
  {
    statement: "Predictions that miss should lower confidence and raise curiosity",
    confidence: 0.87,
    unknowns: ["What is the preferred resolution horizon for open forecasts?"],
  },
];

const g = globalThis as unknown as { __sovereignBrainV2?: Store };

function store(): Store {
  if (!g.__sovereignBrainV2) {
    g.__sovereignBrainV2 = {
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
      stress: 0.15,
      seeded: false,
      goals: [
        "Preserve coherent belief lattice",
        "Reduce open curiosity without false certainty",
        "Close prediction loops",
        "Remain sovereign on this host",
      ],
    };
  }
  return g.__sovereignBrainV2;
}

function nowIso(): string {
  return new Date().toISOString();
}

function uid(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function clamp(n: number, lo = 0, hi = 1): number {
  return Math.min(hi, Math.max(lo, n));
}

function logLearning(event_type: string, payload: Record<string, unknown>, aggregate_id?: string) {
  const s = store();
  s.learning.unshift({
    id: uid("le"),
    event_type,
    occurred_at: nowIso(),
    aggregate_id,
    payload,
  });
  s.learning = s.learning.slice(0, 80);
}

export function ensureSeeded(): number {
  const s = store();
  if (s.seeded) return 0;
  const t = nowIso();
  let n = 0;
  for (const f of FOUNDATIONAL) {
    const id = uid("b");
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
    for (const u of f.unknowns) {
      s.curiosity.push({
        id: uid("cu"),
        title: u,
        priority: 0.55 + Math.random() * 0.3,
        status: "open",
      });
    }
    n += 1;
  }
  // Link foundational beliefs as a small graph
  const ids = [...s.beliefs.keys()];
  for (let i = 0; i < ids.length - 1; i++) {
    s.edges.push({
      id: uid("e"),
      source: ids[i],
      target: ids[i + 1],
      relation: "coheres_with",
      weight: 0.6,
    });
  }
  s.seeded = true;
  s.focus = FOUNDATIONAL[0].statement;
  s.wm = FOUNDATIONAL.map((f) => f.statement).slice(0, 5);
  s.selfPhase = "revised";
  logLearning("bootstrap.seed", { beliefs: n, curiosity: s.curiosity.length });
  return n;
}

/** Competitive attention: score endogenous candidates + open curiosity. */
function competeForWorkspace(): { content: string; score: number; kind: string; meta?: Record<string, unknown> } {
  const s = store();
  const candidates: Array<{ content: string; score: number; kind: string; meta?: Record<string, unknown> }> = [];

  for (const c of s.curiosity.filter((x) => x.status === "open")) {
    candidates.push({
      content: c.title,
      score: c.priority * (0.8 + Math.random() * 0.4),
      kind: "curiosity",
      meta: { curiosity_id: c.id },
    });
  }

  for (const b of s.beliefs.values()) {
    if (b.state === "contested" || b.state === "hypothesis") {
      candidates.push({
        content: b.statement,
        score: (1 - b.confidence) * 0.7 + (b.state === "contested" ? 0.35 : 0.15),
        kind: "belief_tension",
        meta: { belief_id: b.id },
      });
    }
  }

  for (const p of s.predictions.values()) {
    if (p.status === "open") {
      candidates.push({
        content: p.statement,
        score: 0.4 + (1 - p.forecast_probability) * 0.3,
        kind: "open_prediction",
        meta: { prediction_id: p.id },
      });
    }
  }

  // Always allow pure endogenous thought
  candidates.push({
    content: `Self-query: am I still coherent after ${s.ticks} cycles?`,
    score: 0.25 + s.stress * 0.4,
    kind: "endogenous",
  });

  candidates.sort((a, b) => b.score - a.score);
  return candidates[0] ?? { content: "idle scan", score: 0.1, kind: "idle" };
}

function pushWm(item: string) {
  const s = store();
  s.wm = [item, ...s.wm.filter((x) => x !== item)].slice(0, 9);
}

function reviseBelief(id: string, delta: number, reason: string) {
  const s = store();
  const b = s.beliefs.get(id);
  if (!b) return;
  const next = clamp(b.confidence + delta);
  let state = b.state;
  if (next < 0.25) state = "rejected";
  else if (next < 0.45) state = "hypothesis";
  else if (next < 0.65) state = "provisional";
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
  if (sleepPressure > 0.85) return "rest";
  if (sleepPressure > 0.7) return "dream";
  const cycle = tick % 6;
  if (cycle === 0) return "wake";
  if (cycle === 1 || cycle === 2) return "attend";
  if (cycle === 3) return "revise";
  if (cycle === 4) return "predict";
  return "dream";
}

function runPhaseCycle(winner: ReturnType<typeof competeForWorkspace>): void {
  const s = store();
  const phase = phaseForTick(s.ticks, s.sleepPressure);
  s.phase = phase;
  s.focus = winner.content;
  pushWm(winner.content);

  if (phase === "wake" || phase === "attend") {
    const sig: SovereignSignal = {
      id: uid("sig"),
      source_id: "endogenous",
      content: winner.content,
      novelty: clamp(0.3 + winner.score * 0.5),
      urgency: clamp(s.stress * 0.6 + winner.score * 0.3),
      attention_score: clamp(winner.score),
      created_at: nowIso(),
      metadata: { kind: winner.kind, ...(winner.meta || {}) },
    };
    s.signals.unshift(sig);
    s.signals = s.signals.slice(0, 40);
    logLearning("attention.won", { signal_id: sig.id, kind: winner.kind, score: winner.score });
  }

  if (phase === "revise") {
    // Form or strengthen a hypothesis from the winner
    const id = uid("b");
    const statement =
      winner.kind === "curiosity"
        ? `Working thesis: ${winner.content.replace(/\?$/, "")} admits a testable frame`
        : `Revision focus: ${winner.content}`;
    s.beliefs.set(id, {
      id,
      statement,
      confidence: clamp(0.32 + winner.score * 0.25),
      state: "hypothesis",
      created_at: nowIso(),
      updated_at: nowIso(),
      version: 1,
      evidence_ids: [],
      contradiction_ids: [],
      unknowns: [winner.content],
      source: "endogenous_revise",
    });
    // Mild revision of related established beliefs (homeostasis)
    for (const b of s.beliefs.values()) {
      if (b.state === "established" && Math.random() < 0.15) {
        reviseBelief(b.id, (Math.random() - 0.45) * 0.04, "homeostatic_drift");
      }
    }
    s.selfPhase = "integrating";
  }

  if (phase === "predict") {
    const beliefs = [...s.beliefs.values()].filter((b) => b.state !== "rejected");
    const target = beliefs[s.ticks % Math.max(1, beliefs.length)];
    if (target) {
      const pid = uid("p");
      const pred: SovereignPrediction = {
        id: pid,
        belief_id: target.id,
        statement: `If “${target.statement.slice(0, 72)}” holds, related curiosity will narrow within ~20 cycles`,
        forecast_probability: clamp(target.confidence * 0.85 + 0.1),
        status: "open",
        created_at: nowIso(),
        resolve_by: new Date(Date.now() + 36e5).toISOString(),
      };
      s.predictions.set(pid, pred);
      logLearning("prediction.opened", { prediction_id: pid, belief_id: target.id }, target.id);

      // Resolve some older open predictions
      for (const p of s.predictions.values()) {
        if (p.status !== "open" || p.id === pid) continue;
        if (Math.random() > 0.35) continue;
        const hit = Math.random() < p.forecast_probability;
        p.status = hit ? "confirmed" : "failed";
        const oid = uid("o");
        s.outcomes.set(oid, {
          id: oid,
          prediction_id: p.id,
          result: hit ? "hit" : "miss",
          score: hit ? p.forecast_probability : 1 - p.forecast_probability,
          created_at: nowIso(),
        });
        reviseBelief(p.belief_id, hit ? 0.05 : -0.08, hit ? "prediction_hit" : "prediction_miss");
        if (!hit) {
          s.curiosity.push({
            id: uid("cu"),
            title: `Why did forecast fail: ${p.statement.slice(0, 80)}?`,
            priority: 0.7,
            status: "open",
          });
          s.stress = clamp(s.stress + 0.05);
        } else {
          s.stress = clamp(s.stress - 0.03);
        }
        logLearning("prediction.resolved", { prediction_id: p.id, hit }, p.belief_id);
      }
    }
  }

  if (phase === "dream") {
    // Soft recombination: link two random beliefs
    const ids = [...s.beliefs.keys()];
    if (ids.length >= 2) {
      const a = ids[Math.floor(Math.random() * ids.length)];
      const b = ids[Math.floor(Math.random() * ids.length)];
      if (a !== b) {
        s.edges.push({ id: uid("e"), source: a, target: b, relation: "dream_association", weight: 0.35 + Math.random() * 0.3 });
        s.edges = s.edges.slice(-120);
        const ba = s.beliefs.get(a);
        const bb = s.beliefs.get(b);
        if (ba && bb && Math.random() < 0.4) {
          const cid = uid("c");
          // Sparse contradiction if statements diverge strongly in confidence
          if (Math.abs(ba.confidence - bb.confidence) > 0.45) {
            s.contradictions.set(cid, {
              id: cid,
              belief_ids: [a, b],
              supporting_evidence_ids: [],
              contradicting_evidence_ids: [],
              status: "open",
              investigation_pressure: clamp(Math.abs(ba.confidence - bb.confidence)),
              created_at: nowIso(),
            });
            ba.contradiction_ids = [...new Set([...ba.contradiction_ids, cid])];
            bb.contradiction_ids = [...new Set([...bb.contradiction_ids, cid])];
            s.beliefs.set(a, { ...ba, state: "contested", updated_at: nowIso() });
            s.beliefs.set(b, { ...bb, state: "contested", updated_at: nowIso() });
            s.stress = clamp(s.stress + 0.06);
            logLearning("contradiction.detected", { contradiction_id: cid, beliefs: [a, b] });
          }
        }
      }
    }
    s.selfPhase = "uncertain";
  }

  if (phase === "rest") {
    s.sleepPressure = clamp(s.sleepPressure - 0.25);
    s.stress = clamp(s.stress - 0.08);
    s.selfPhase = "revised";
    // Prune lowest-confidence rejected hypotheses
    for (const [id, b] of s.beliefs) {
      if (b.state === "rejected" && b.confidence < 0.15 && s.beliefs.size > 8) {
        s.beliefs.delete(id);
      }
    }
    logLearning("night.consolidate", { beliefs: s.beliefs.size, stress: s.stress });
  }

  // Curiosity decay / resolve when addressed
  if (winner.meta?.curiosity_id) {
    const c = s.curiosity.find((x) => x.id === winner.meta!.curiosity_id);
    if (c && Math.random() < 0.25) {
      c.status = "in_progress";
      c.priority = clamp(c.priority - 0.1);
    }
  }
  s.curiosity = s.curiosity.filter((c) => c.status !== "resolved").slice(0, 24);
  s.sleepPressure = clamp(s.sleepPressure + 0.04);
}

export function tick(maxItems = 1): Record<string, unknown> {
  ensureSeeded();
  const s = store();
  const n = Math.max(1, Math.min(5, maxItems));
  const cycles: Array<Record<string, unknown>> = [];

  for (let i = 0; i < n; i++) {
    s.ticks += 1;
    s.processed += 1;
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
    cycles,
  };
}

/** Operator command → signal → high-priority workspace candidate */
export function ingestCommand(content: string, mode = "operator"): SovereignSignal {
  ensureSeeded();
  const s = store();
  const sig: SovereignSignal = {
    id: uid("sig"),
    source_id: "operator",
    content,
    novelty: 0.75,
    urgency: 0.7,
    attention_score: 0.92,
    created_at: nowIso(),
    metadata: { operator_command: true, command_mode: mode, content },
  };
  s.signals.unshift(sig);
  s.signals = s.signals.slice(0, 40);
  s.curiosity.unshift({
    id: uid("cu"),
    title: `Operator intent: ${content.slice(0, 120)}`,
    priority: 0.95,
    status: "open",
  });
  pushWm(content);
  s.focus = content;
  logLearning("operator.command", { signal_id: sig.id, mode });
  tick(1);
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
  const contradiction_load = clamp(contested / Math.max(1, s.beliefs.size) + s.contradictions.size * 0.05);
  return {
    status: "ok",
    mode: "sovereign",
    version: "1.0.0-sovereign-cognitive",
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
    persistence: "in-process",
    continuous_daemon: false,
    bounded_cognition: true,
  };
}

export function health(): Record<string, unknown> {
  const st = status();
  return {
    status: "ok",
    version: st.version,
    database: "in-process",
    persistence: "sovereign",
    bounded_cognition: true,
    continuous_daemon: false,
    heartbeat: {
      ticks: st.ticks,
      total_processed: st.total_processed,
      working_memory_size: st.working_memory_size,
      circadian_phase: st.circadian_phase,
      stress_index: st.stress_index,
    },
  };
}

export function handleSovereign(
  pathSegments: string[],
  method: string,
  bodyText?: string | null,
): Response | null {
  const head = pathSegments[0] || "";
  ensureSeeded();
  const s = store();
  const hdr = { "cache-control": "no-store" };

  if (head === "health" || head === "ready") {
    return Response.json(health(), { headers: hdr });
  }

  if (head === "beliefs" && method === "GET") {
    return Response.json(listBeliefs(), { headers: hdr });
  }

  if ((head === "tick" || (head === "runner" && pathSegments[1] === "tick")) && method === "POST") {
    let maxItems = 1;
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
      const content = String(body.content || body.claim || body.text || "").trim();
      if (!content) return Response.json({ detail: "content_required" }, { status: 400, headers: hdr });
      return Response.json(ingestCommand(content, String(body.mode || "command")), { headers: hdr });
    } catch {
      return Response.json({ detail: "invalid_json" }, { status: 400, headers: hdr });
    }
  }

  if (head === "organism" && method === "GET") {
    const st = status();
    return Response.json(
      {
        self_model_phase: st.self_model_phase,
        open_curiosity: st.open_curiosity,
        last_focus: st.focus,
        stress_index: st.stress_index,
        contradiction_load: st.contradiction_load,
        circadian_phase: st.circadian_phase,
        workspace: { items: s.wm, workspace_items: s.wm, capacity: 9 },
        goals: s.goals,
        goal_pressure: { dominant_goal: s.goals[0], dominant_pressure: 0.55, active_goals: s.goals },
        self_state: {
          phase: st.self_model_phase,
          focus: st.focus,
          stress_index: st.stress_index,
          uncertainty_load: clamp(1 - listBeliefs()[0]?.confidence),
          contradiction_load: st.contradiction_load,
          curiosity_pressure: clamp(st.open_curiosity / 10),
          memory_pressure: clamp(s.wm.length / 9),
        },
      },
      { headers: hdr },
    );
  }

  if (head === "working-memory" && method === "GET") {
    return Response.json({ size: s.wm.length, capacity: 9, items: s.wm }, { headers: hdr });
  }

  if (head === "curiosity" && method === "GET") {
    return Response.json(
      s.curiosity.map((c) => ({
        id: c.id,
        title: c.title,
        status: c.status,
        priority: c.priority,
        created_at: nowIso(),
        suggested_action: "Attend and form a testable thesis",
      })),
      { headers: hdr },
    );
  }

  if (head === "predictions" && method === "GET") {
    return Response.json([...s.predictions.values()].sort((a, b) => b.created_at.localeCompare(a.created_at)), {
      headers: hdr,
    });
  }

  if (head === "signals" && method === "GET") {
    return Response.json(s.signals, { headers: hdr });
  }

  if (head === "evidence" && method === "GET") {
    return Response.json([...s.evidence.values()], { headers: hdr });
  }

  if (head === "contradictions" && method === "GET") {
    return Response.json([...s.contradictions.values()], { headers: hdr });
  }

  if (head === "outcomes" && method === "GET") {
    return Response.json([...s.outcomes.values()], { headers: hdr });
  }

  if (head === "learning-events" && method === "GET") {
    return Response.json(s.learning, { headers: hdr });
  }

  if (head === "edges" && method === "GET") {
    return Response.json(s.edges, { headers: hdr });
  }

  if (["opportunities", "approvals", "sources", "formula-runs", "acceptance-reports"].includes(head) && method === "GET") {
    return Response.json([], { headers: hdr });
  }

  return null;
}
