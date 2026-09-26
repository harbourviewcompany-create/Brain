import { appendEvent, loadSnapshot, persistenceStatus, saveSnapshot, type SnapshotPayload } from "./sovereign-persist";
import { clamp, ensureSeeded, health, ingestCommand, items, listBeliefs, now, status, store, tick } from "./sovereign-engine";

function toPayload(): SnapshotPayload {
  const s = store();
  return {
    version: "1.2.0-sovereign-v4",
    ticks: s.ticks,
    processed: s.processed,
    identityDigest: s.identityDigest,
    phase: s.phase,
    focus: s.focus,
    goals: s.goals,
    goalLock: s.goalLock,
    lastDelta: s.lastDelta,
    lastCycle: s.lastCycle,
    selfPhase: s.selfPhase,
    sleepPressure: s.sleepPressure,
    stress: s.stress,
    wm: s.wm,
    beliefs: [...s.beliefs.values()],
    evidence: [...s.evidence.values()],
    predictions: [...s.predictions.values()],
    outcomes: s.outcomes,
    signals: s.signals.slice(0, 40),
    contradictions: s.contradictions,
    curiosity: s.curiosity,
    learning: s.learning.slice(0, 40),
    edges: s.edges,
  };
}

function applyPayload(snap: SnapshotPayload) {
  const s = store();
  s.ticks = snap.ticks || 0;
  s.processed = snap.processed || snap.ticks || 0;
  s.identityDigest = snap.identityDigest || s.identityDigest;
  if (snap.phase) s.phase = snap.phase as typeof s.phase;
  s.focus = snap.focus ?? s.focus;
  if (snap.goals?.length) s.goals = snap.goals;
  s.goalLock = snap.goalLock ?? null;
  s.lastDelta = snap.lastDelta || s.lastDelta;
  s.lastCycle = snap.lastCycle ?? s.lastCycle;
  s.selfPhase = snap.selfPhase || s.selfPhase;
  s.sleepPressure = snap.sleepPressure ?? s.sleepPressure;
  s.stress = snap.stress ?? s.stress;
  if (snap.wm?.length) s.wm = snap.wm;
  const fill = <T extends { id: string }>(rows: unknown[] | undefined, map: Map<string, T>) => {
    if (!Array.isArray(rows)) return;
    map.clear();
    for (const raw of rows) {
      const row = raw as T;
      if (row?.id) map.set(row.id, row);
    }
  };
  fill(snap.beliefs as never, s.beliefs);
  fill(snap.evidence as never, s.evidence);
  fill(snap.predictions as never, s.predictions);
  if (Array.isArray(snap.outcomes)) s.outcomes = snap.outcomes as typeof s.outcomes;
  if (Array.isArray(snap.signals)) s.signals = snap.signals as typeof s.signals;
  if (Array.isArray(snap.contradictions)) s.contradictions = snap.contradictions as typeof s.contradictions;
  if (Array.isArray(snap.curiosity)) s.curiosity = snap.curiosity as typeof s.curiosity;
  if (Array.isArray(snap.learning)) s.learning = snap.learning as typeof s.learning;
  if (Array.isArray(snap.edges)) s.edges = snap.edges as typeof s.edges;
  s.seeded = s.beliefs.size > 0;
}

async function hydrateFromDb() {
  const s = store();
  if (s.hydrated) return;
  s.hydrated = true;
  const snap = await loadSnapshot();
  if (snap && snap.ticks > 0 && Array.isArray(snap.beliefs) && snap.beliefs.length) applyPayload(snap);
}

function persistSoon(eventType = "snapshot.flush") {
  const s = store();
  void saveSnapshot(toPayload());
  void appendEvent(s.ticks, eventType, { focus: s.focus, phase: s.phase, ticks: s.ticks });
}

export async function flushPersistence() {
  const s = store();
  await saveSnapshot(toPayload());
  await appendEvent(s.ticks, "cron.flush", { focus: s.focus, phase: s.phase, ticks: s.ticks });
}

export async function handleSovereign(pathSegments: string[], method: string, bodyText?: string | null): Promise<Response | null> {
  const head = pathSegments[0] || "";
  const sub = pathSegments[1] || "";
  ensureSeeded();
  await hydrateFromDb();
  const s = store();
  if (s.ticks === 0) {
    tick(6);
    persistSoon("bootstrap.first_lap");
  }
  const hdr = { "cache-control": "no-store" };
  if (head === "health" || head === "ready") return Response.json(health(), { headers: hdr });
  if (head === "runner") return Response.json({ ticks: s.ticks, total_processed: s.processed, working_memory_size: s.wm.length, inbox: { pending: 0, processing: 0, total: s.signals.length }, circadian_phase: s.phase, is_awake: s.phase !== "rest", status: "running" }, { headers: hdr });
  if (head === "beliefs" && method === "GET") return Response.json(items(listBeliefs()), { headers: hdr });
  if ((head === "tick" || (head === "runner" && sub === "tick")) && method === "POST") {
    let n = 2;
    try { if (bodyText) n = JSON.parse(bodyText).max_items || 2; } catch { /* ignore */ }
    const out = tick(n);
    persistSoon("tick");
    return Response.json(out, { headers: hdr });
  }
  if (head === "signals" && method === "POST") {
    try {
      const body = bodyText ? JSON.parse(bodyText) : {};
      const content = String(body.content || body.claim || body.text || body.metadata?.content || "").trim();
      if (!content) return Response.json({ detail: "content_required" }, { status: 400, headers: hdr });
      const sig = ingestCommand(content, String(body.metadata?.command_mode || body.mode || "command"));
      persistSoon("operator.command");
      return Response.json({ id: sig.id, status: "accepted", signal_id: sig.id, attention_score: sig.attention_score, created_at: sig.created_at }, { headers: hdr });
    } catch { return Response.json({ detail: "invalid_json" }, { status: 400, headers: hdr }); }
  }
  if (head === "explain") {
    return Response.json({ version: "1.2.0-sovereign-v4", last_cycle: s.lastCycle, last_delta: s.lastDelta, focus: s.focus, phase: s.phase, ticks: s.ticks, goal_lock: s.goalLock, identity_digest: s.identityDigest }, { headers: hdr });
  }
  if (head === "snapshot") {
    return Response.json({ persistence: persistenceStatus().mode, persist: persistenceStatus(), ticks: s.ticks, identity_digest: s.identityDigest, last_delta: s.lastDelta, belief_count: s.beliefs.size, evidence_count: s.evidence.size, prediction_count: s.predictions.size, goals: s.goals, focus: s.focus }, { headers: hdr });
  }
  if (head === "organism") {
    const st = status();
    if (sub === "self-state") {
      return Response.json({ current_focus_summary: st.focus, uncertainty_load: clamp(1 - (listBeliefs()[0]?.confidence ?? 0.5)), contradiction_load: st.contradiction_load, curiosity_pressure: clamp(st.open_curiosity / 12), revenue_pressure: 0, risk_pressure: clamp(st.stress_index * 0.5), memory_pressure: clamp(s.wm.length / 9), action_backlog_pressure: 0, phase: st.self_model_phase, stress_index: st.stress_index }, { headers: hdr });
    }
    if (sub === "curiosity") return Response.json(items(s.curiosity.map((c) => ({ id: c.id, question: c.title, status: c.status, priority: c.priority, expected_value: c.priority }))), { headers: hdr });
    if (sub === "agency-actions" || sub === "quarantine") return Response.json(items([]), { headers: hdr });
    if (sub === "persistence") return Response.json({ store: "sovereign", reachable: true, mode: persistenceStatus().mode, identity_digest: s.identityDigest, last_error: persistenceStatus().lastError, last_saved_at: persistenceStatus().lastSavedAt }, { headers: hdr });
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
