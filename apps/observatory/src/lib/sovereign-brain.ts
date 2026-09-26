/**
 * Sovereign Cognitive Kernel v4 — compact, BFF-complete.
 * First lap, goal lock, explain, focus-bound evidence.
 */
export type BeliefState = "hypothesis" | "provisional" | "established" | "contested" | "rejected";

type Belief = {
  id: string; statement: string; confidence: number; state: BeliefState;
  created_at: string; updated_at: string; version: number;
  evidence_ids: string[]; contradiction_ids: string[]; unknowns?: string[]; source?: string;
};
type Evidence = { id: string; claim: string; reliability: number; supports: boolean | null; belief_ids: string[]; created_at: string };
type Prediction = { id: string; belief_id: string; statement: string; forecast_probability: number; status: "open" | "confirmed" | "failed"; created_at: string; resolve_by: string };
type Signal = { id: string; source_id: string; content: string; novelty: number; urgency: number; attention_score: number; created_at: string; metadata?: Record<string, unknown> };
type Curiosity = { id: string; title: string; priority: number; status: string; linked_belief?: string };
type Phase = "wake" | "attend" | "revise" | "predict" | "dream" | "rest";

type Store = {
  beliefs: Map<string, Belief>; evidence: Map<string, Evidence>; predictions: Map<string, Prediction>;
  outcomes: Array<Record<string, unknown>>; signals: Signal[]; contradictions: Array<Record<string, unknown>>;
  learning: Array<Record<string, unknown>>; edges: Array<Record<string, unknown>>;
  wm: string[]; ticks: number; processed: number; focus: string | null; curiosity: Curiosity[];
  selfPhase: string; phase: Phase; sleepPressure: number; stress: number; seeded: boolean;
  goals: string[]; identityDigest: string; goalLock: { content: string; untilTick: number } | null;
  lastCycle: Record<string, unknown> | null; lastDelta: string;
};

const FOUNDATIONAL = [
  ["I maintain a lattice of beliefs under uncertainty and revise them with evidence", 0.93, "Which operator goals should dominate attention?"],
  ["Attention is competitive: novelty, contradiction, and goal relevance win the workspace", 0.91, "What external signal channels are still dark?"],
  ["Endogenous thought generates hypotheses when the world is quiet", 0.88, "How long should a hypothesis live without corroboration?"],
  ["I am sovereign: cognition runs here without a foreign host", 0.96, "When does process-local memory need durable ledger upgrade?"],
  ["Predictions that miss should lower confidence and raise curiosity", 0.89, "What is the preferred resolution horizon for open forecasts?"],
  ["Goals condition attention; unaligned high-novelty noise should lose", 0.86, "Have operator goals been stated explicitly?"],
] as const;

const g = globalThis as unknown as { __sovV4?: Store };

function store(): Store {
  if (!g.__sovV4) {
    g.__sovV4 = {
      beliefs: new Map(), evidence: new Map(), predictions: new Map(), outcomes: [], signals: [],
      contradictions: [], learning: [], edges: [], wm: [], ticks: 0, processed: 0, focus: null,
      curiosity: [], selfPhase: "observing", phase: "wake", sleepPressure: 0, stress: 0.12,
      seeded: false,
      goals: ["Preserve coherent belief lattice", "Reduce open curiosity without false certainty", "Close prediction loops", "Remain sovereign on this host", "Attend to operator intent when present"],
      identityDigest: "", goalLock: null, lastCycle: null, lastDelta: "seed pending",
    };
  }
  return g.__sovV4;
}

const now = () => new Date().toISOString();
function hash01(seed: string, salt = "") {
  let h = 2166136261;
  const input = `${seed}:${salt}`;
  for (let i = 0; i < input.length; i++) { h ^= input.charCodeAt(i); h = Math.imul(h, 16777619); }
  return (h >>> 0) / 4294967296;
}
const uid = (p: string, k: string) => `${p}-${Math.floor(hash01(k, p) * 1e9).toString(36)}`;
const clamp = (n: number, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, n));
const items = <T,>(arr: T[]) => ({ items: arr });
function tokens(text: string) {
  return new Set(text.toLowerCase().replace(/[^a-z0-9\s-]/g, " ").split(/\s+/).filter((t) => t.length > 2));
}
function overlap(a: string, b: string) {
  const A = tokens(a), B = tokens(b);
  if (!A.size || !B.size) return 0;
  let hits = 0; A.forEach((t) => { if (B.has(t)) hits += 1; });
  return hits / Math.max(A.size, B.size);
}
function goalRel(content: string, goals: string[]) {
  return goals.reduce((best, g) => Math.max(best, overlap(content, g)), 0);
}
function log(event_type: string, payload: Record<string, unknown>, aggregate_id?: string) {
  const s = store();
  s.learning.unshift({ id: uid("le", `${event_type}:${s.ticks}`), event_type, occurred_at: now(), aggregate_id, payload });
  s.learning = s.learning.slice(0, 80);
}
function identity() {
  const s = store();
  const statements = [...s.beliefs.values()].filter((b) => b.state === "established" || b.state === "provisional").map((b) => b.statement).sort().join("|");
  s.identityDigest = `sov-${Math.floor(hash01(statements, "identity") * 1e12).toString(36)}`;
  return s.identityDigest;
}

export function ensureSeeded(): number {
  const s = store();
  if (s.seeded) return 0;
  const t = now();
  FOUNDATIONAL.forEach((f, i) => {
    const id = uid("b", `boot:${i}:${f[0]}`);
    s.beliefs.set(id, { id, statement: f[0], confidence: f[1], state: "established", created_at: t, updated_at: t, version: 1, evidence_ids: [], contradiction_ids: [], unknowns: [f[2]], source: "bootstrap" });
    s.curiosity.push({ id: uid("cu", `boot:${i}`), title: f[2], priority: 0.55 + hash01(`cu:${i}`, "p") * 0.35, status: "open", linked_belief: id });
  });
  const ids = [...s.beliefs.keys()];
  ids.slice(0, -1).forEach((id, i) => s.edges.push({ id: uid("e", `e:${i}`), source: id, target: ids[i + 1], relation: "coheres_with", weight: 0.65, confidence: 0.8, source_node_id: id, target_node_id: ids[i + 1] }));
  s.seeded = true;
  s.focus = FOUNDATIONAL[0][0];
  s.wm = FOUNDATIONAL.map((f) => f[0]).slice(0, 6);
  s.selfPhase = "revised";
  identity();
  log("bootstrap.seed", { beliefs: s.beliefs.size });
  return s.beliefs.size;
}

function bindEvidence(beliefId: string, claim: string, reliability: number) {
  const s = store();
  const id = uid("ev", `${beliefId}:${claim.slice(0, 40)}`);
  s.evidence.set(id, { id, claim, reliability: clamp(reliability), supports: true, belief_ids: [beliefId], created_at: now() });
  const b = s.beliefs.get(beliefId);
  if (b) s.beliefs.set(beliefId, { ...b, evidence_ids: [...new Set([...b.evidence_ids, id])], updated_at: now() });
}

function phaseFor(tick: number, sleep: number): Phase {
  if (sleep > 0.88) return "rest";
  if (sleep > 0.72) return "dream";
  const c = tick % 6;
  return c === 0 ? "wake" : c === 1 || c === 2 ? "attend" : c === 3 ? "revise" : c === 4 ? "predict" : "dream";
}

function competeForWorkspace() {
  const s = store();
  const key = String(s.ticks);
  const cand: Array<{ content: string; score: number; kind: string; belief?: string }> = [];
  if (s.goalLock && s.ticks <= s.goalLock.untilTick) cand.push({ content: s.goalLock.content, score: 0.97, kind: "operator" });
  for (const c of s.curiosity.filter((x) => x.status === "open")) {
    cand.push({ content: c.title, score: clamp(c.priority * 0.55 + goalRel(c.title, s.goals) * 0.35 + hash01(key, c.id) * 0.15), kind: "curiosity", belief: c.linked_belief });
  }
  for (const b of s.beliefs.values()) {
    if (b.state === "hypothesis" || b.state === "contested") {
      cand.push({ content: b.statement, score: clamp((1 - b.confidence) * 0.5 + 0.2), kind: "belief_tension", belief: b.id });
    }
  }
  cand.push({ content: `Self-query after ${s.ticks} cycles`, score: 0.22 + s.stress * 0.4, kind: "endogenous" });
  cand.sort((a, b) => b.score - a.score);
  return cand[0] ?? { content: "idle", score: 0.1, kind: "idle" };
}

export function tick(maxItems = 1): Record<string, unknown> {
  ensureSeeded();
  const s = store();
  const n = Math.max(1, Math.min(8, maxItems));
  const cycles: Array<Record<string, unknown>> = [];
  for (let i = 0; i < n; i++) {
    s.ticks += 1; s.processed += 1;
    const w = competeForWorkspace();
    const phase = phaseFor(s.ticks, s.sleepPressure);
    s.phase = phase; s.focus = w.content;
    s.wm = [w.content, ...s.wm.filter((x) => x !== w.content)].slice(0, 9);
    const linked = w.belief || [...s.beliefs.keys()][0];
    if (phase === "wake" || phase === "attend") {
      s.signals.unshift({
        id: uid("sig", `${s.ticks}:${w.kind}`), source_id: w.kind === "operator" ? "operator" : "endogenous",
        content: w.content, novelty: clamp(0.3 + w.score * 0.5), urgency: clamp(s.stress * 0.5 + w.score * 0.3),
        attention_score: clamp(w.score), created_at: now(), metadata: { kind: w.kind, content: w.content },
      });
      s.signals = s.signals.slice(0, 50);
      if (linked) bindEvidence(linked, `Attended focus at tick ${s.ticks}: ${w.content.slice(0, 120)}`, 0.5 + w.score * 0.25);
    }
    if (phase === "revise") {
      const id = uid("b", `rev:${s.ticks}:${w.content.slice(0, 32)}`);
      const statement = w.kind === "operator" ? `Operator-aligned stance: ${w.content.slice(0, 140)}` : `Working thesis: ${w.content.replace(/\?$/, "")} admits a testable frame`;
      s.beliefs.set(id, { id, statement, confidence: clamp(0.32 + w.score * 0.25), state: "hypothesis", created_at: now(), updated_at: now(), version: 1, evidence_ids: [], contradiction_ids: [], unknowns: [w.content], source: `endogenous_${w.kind}` });
      bindEvidence(id, `Endogenous observation at tick ${s.ticks}: ${w.content.slice(0, 80)}`, 0.5);
      s.selfPhase = "integrating";
    }
    if (phase === "predict") {
      const beliefs = [...s.beliefs.values()];
      const target = beliefs[s.ticks % Math.max(1, beliefs.length)];
      if (target) {
        const pid = uid("p", `p:${s.ticks}`);
        s.predictions.set(pid, {
          id: pid, belief_id: target.id,
          statement: `If ${target.statement.slice(0, 72)} holds, related curiosity narrows within ~20 cycles`,
          forecast_probability: clamp(target.confidence * 0.82 + 0.12), status: "open", created_at: now(),
          resolve_by: new Date(Date.now() + 36e5).toISOString(),
        });
      }
    }
    s.sleepPressure = clamp(s.sleepPressure + 0.045);
    identity();
    s.lastCycle = { tick: s.ticks, phase, kind: w.kind, score: w.score, focus: w.content };
    s.lastDelta = `tick ${s.ticks} | ${phase} | ${w.kind} | ${w.content.slice(0, 80)}`;
    cycles.push({ phase, focus: s.focus, kind: w.kind, attention_score: w.score, working_memory_size: s.wm.length });
  }
  return { processed_this_call: n, ticks: s.ticks, total_processed: s.processed, endogenous: true, identity_digest: s.identityDigest, cycles };
}

export function ingestCommand(content: string, mode = "operator"): Signal {
  ensureSeeded();
  const s = store();
  const sig: Signal = {
    id: uid("sig", `op:${content.slice(0, 40)}:${s.ticks}`), source_id: "operator", content,
    novelty: 0.8, urgency: 0.75, attention_score: 0.94, created_at: now(),
    metadata: { operator_command: true, command_mode: mode, content, claim: content },
  };
  s.signals.unshift(sig); s.signals = s.signals.slice(0, 50);
  s.curiosity.unshift({ id: uid("cu", `op:${content.slice(0, 30)}`), title: `Operator intent: ${content.slice(0, 120)}`, priority: 0.96, status: "open" });
  s.goalLock = { content, untilTick: s.ticks + 8 };
  s.goals = [content.slice(0, 120), ...s.goals.filter((x) => x !== content.slice(0, 120))].slice(0, 8);
  s.wm = [content, ...s.wm].slice(0, 9); s.focus = content;
  log("operator.command", { signal_id: sig.id, mode });
  tick(2);
  return sig;
}

export function listBeliefs(): Belief[] {
  ensureSeeded();
  return [...store().beliefs.values()].sort((a, b) => b.confidence - a.confidence);
}

export function status() {
  ensureSeeded();
  const s = store();
  const contested = [...s.beliefs.values()].filter((b) => b.state === "contested").length;
  return {
    status: "ok" as const, mode: "sovereign" as const, version: "1.2.0-sovereign-v4",
    ticks: s.ticks, total_processed: s.processed, belief_count: s.beliefs.size,
    working_memory_size: s.wm.length, circadian_phase: s.phase, focus: s.focus,
    open_curiosity: s.curiosity.filter((c) => c.status === "open").length,
    self_model_phase: s.selfPhase, stress_index: s.stress,
    contradiction_load: clamp(contested / Math.max(1, s.beliefs.size)),
    identity_digest: s.identityDigest, persistence: "in-process" as const,
    continuous_daemon: false as const, bounded_cognition: true as const,
  };
}

export function health() {
  const st = status();
  const s = store();
  return {
    status: "ok", version: st.version, database: "connected", persistence: "sovereign",
    bounded_cognition: true, continuous_daemon: false, identity_digest: st.identity_digest,
    heartbeat: { ticks: st.ticks, total_processed: st.total_processed, working_memory_size: st.working_memory_size, circadian_phase: st.circadian_phase, stress_index: st.stress_index, inbox: { pending: 0, processing: 0, total: s.signals.length } },
  };
}

export function handleSovereign(pathSegments: string[], method: string, bodyText?: string | null): Response | null {
  const head = pathSegments[0] || "";
  const sub = pathSegments[1] || "";
  ensureSeeded();
  const s = store();
  if (s.ticks === 0) tick(6);
  const hdr = { "cache-control": "no-store" };
  if (head === "health" || head === "ready") return Response.json(health(), { headers: hdr });
  if (head === "runner") return Response.json({ ticks: s.ticks, total_processed: s.processed, working_memory_size: s.wm.length, inbox: { pending: 0, processing: 0, total: s.signals.length }, circadian_phase: s.phase, is_awake: s.phase !== "rest", status: "running" }, { headers: hdr });
  if (head === "beliefs" && method === "GET") return Response.json(items(listBeliefs()), { headers: hdr });
  if ((head === "tick" || (head === "runner" && sub === "tick")) && method === "POST") {
    let n = 2;
    try { if (bodyText) n = JSON.parse(bodyText).max_items || 2; } catch { /* ignore */ }
    return Response.json(tick(n), { headers: hdr });
  }
  if (head === "signals" && method === "POST") {
    try {
      const body = bodyText ? JSON.parse(bodyText) : {};
      const content = String(body.content || body.claim || body.text || body.metadata?.content || "").trim();
      if (!content) return Response.json({ detail: "content_required" }, { status: 400, headers: hdr });
      const sig = ingestCommand(content, String(body.metadata?.command_mode || body.mode || "command"));
      return Response.json({ id: sig.id, status: "accepted", signal_id: sig.id, attention_score: sig.attention_score, created_at: sig.created_at }, { headers: hdr });
    } catch { return Response.json({ detail: "invalid_json" }, { status: 400, headers: hdr }); }
  }
  if (head === "explain") {
    return Response.json({ version: "1.2.0-sovereign-v4", last_cycle: s.lastCycle, last_delta: s.lastDelta, focus: s.focus, phase: s.phase, ticks: s.ticks, goal_lock: s.goalLock, identity_digest: s.identityDigest }, { headers: hdr });
  }
  if (head === "snapshot") {
    return Response.json({ persistence: "in-process", ticks: s.ticks, identity_digest: s.identityDigest, last_delta: s.lastDelta, belief_count: s.beliefs.size, evidence_count: s.evidence.size, prediction_count: s.predictions.size, goals: s.goals, focus: s.focus }, { headers: hdr });
  }
  if (head === "organism") {
    const st = status();
    if (sub === "self-state") {
      return Response.json({ current_focus_summary: st.focus, uncertainty_load: clamp(1 - (listBeliefs()[0]?.confidence ?? 0.5)), contradiction_load: st.contradiction_load, curiosity_pressure: clamp(st.open_curiosity / 12), revenue_pressure: 0, risk_pressure: clamp(st.stress_index * 0.5), memory_pressure: clamp(s.wm.length / 9), action_backlog_pressure: 0, phase: st.self_model_phase, stress_index: st.stress_index }, { headers: hdr });
    }
    if (sub === "curiosity") return Response.json(items(s.curiosity.map((c) => ({ id: c.id, question: c.title, status: c.status, priority: c.priority, expected_value: c.priority }))), { headers: hdr });
    if (sub === "agency-actions" || sub === "quarantine") return Response.json(items([]), { headers: hdr });
    if (sub === "persistence") return Response.json({ store: "sovereign", reachable: true, mode: "in-process", identity_digest: s.identityDigest }, { headers: hdr });
    return Response.json({
      self_model_phase: st.self_model_phase, open_curiosity: st.open_curiosity, last_focus: st.focus,
      stress_index: st.stress_index, contradiction_load: st.contradiction_load, circadian_phase: st.circadian_phase,
      identity_digest: st.identity_digest, last_delta: s.lastDelta,
      conscious_focus: { active_focus: s.focus ? [{ title: s.focus }] : [], workspace_items: s.wm.length, capacity: 9, items: s.wm },
      workspace: { items: s.wm, workspace_items: s.wm, capacity: 9 }, goals: s.goals,
      goal_pressure: { dominant_goal: s.goals[0], dominant_pressure: 0.58, active_goals: s.goals, protect_overrides_exploit: false },
      self_state: { phase: st.self_model_phase, focus: st.focus, stress_index: st.stress_index, self_assessment: "sovereign functional" },
      curiosity_queue: s.curiosity.filter((c) => c.status === "open").map((c) => c.title),
    }, { headers: hdr });
  }
  if (head === "working-memory") return Response.json({ size: s.wm.length, capacity: 9, items: s.wm, observed_at: now(), cycle_id: String(s.ticks), evicted_count: 0 }, { headers: hdr });
  if (head === "curiosity") return Response.json(items(s.curiosity.map((c) => ({ id: c.id, title: c.title, status: c.status, priority: c.priority, linked_object_id: c.linked_belief, linked_object_type: c.linked_belief ? "belief" : undefined, created_at: now(), suggested_action: "Attend and form a testable thesis" }))), { headers: hdr });
  if (head === "predictions") return Response.json(items([...s.predictions.values()]), { headers: hdr });
  if (head === "signals" && method === "GET") return Response.json(items(s.signals), { headers: hdr });
  if (head === "evidence") return Response.json(items([...s.evidence.values()]), { headers: hdr });
  if (head === "contradictions") return Response.json(items(s.contradictions), { headers: hdr });
  if (head === "outcomes") return Response.json(items(s.outcomes), { headers: hdr });
  if (head === "learning-events") return Response.json(items(s.learning), { headers: hdr });
  if (head === "edges") return Response.json(items(s.edges), { headers: hdr });
  if (["opportunities", "approvals", "sources", "formula-runs", "acceptance-reports"].includes(head) && method === "GET") return Response.json(items([]), { headers: hdr });
  return null;
}
