/**
 * Endogenous evolution: promote, resolve, contradict, dream, long-horizon goals.
 */
import { clamp, now, store } from "./sovereign-engine";

function hash01(seed: string) {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967296;
}

const SELF_QUERIES = [
  "Which belief has evidence but no prediction?",
  "What would falsify the current focus in one observation?",
  "Is process-local memory lying about continuity?",
  "Which curiosity has aged without a thesis?",
  "Does the identity digest still match the established lattice?",
  "What should sleep pressure trade for more revise cycles?",
  "Which operator goal is still untested?",
  "Can two hypotheses be merged without losing a contradiction?",
  "What world signal is missing that would change the dominant goal?",
  "Which established belief has the weakest evidence binding?",
];

const HORIZON_GOALS = [
  "Keep a continuous identity across cold starts",
  "Convert open curiosity into scored predictions",
  "Surface contradictions before promoting a belief",
  "Prefer durable ledger writes over process-local certainty",
];

function tokens(text: string) {
  return new Set(text.toLowerCase().replace(/[^a-z0-9\s-]/g, " ").split(/\s+/).filter((t) => t.length > 3));
}

function overlap(a: string, b: string) {
  const A = tokens(a);
  const B = tokens(b);
  if (!A.size || !B.size) return 0;
  let hits = 0;
  A.forEach((t) => {
    if (B.has(t)) hits += 1;
  });
  return hits / Math.max(A.size, B.size);
}

export function evolveAfterTick() {
  const s = store();
  const t = now();

  for (const goal of HORIZON_GOALS) {
    if (!s.goals.includes(goal)) s.goals = [...s.goals, goal].slice(0, 10);
  }

  for (const b of s.beliefs.values()) {
    const ev = b.evidence_ids.length;
    if (b.state === "hypothesis" && ev >= 2) {
      s.beliefs.set(b.id, { ...b, state: "provisional", confidence: clamp(b.confidence + 0.08), updated_at: t, version: b.version + 1 });
    } else if (b.state === "provisional" && ev >= 4 && b.confidence >= 0.55) {
      s.beliefs.set(b.id, { ...b, state: "established", confidence: clamp(b.confidence + 0.06), updated_at: t, version: b.version + 1 });
    } else if (b.state === "hypothesis" && ev === 0 && b.confidence < 0.4) {
      s.beliefs.set(b.id, { ...b, state: "contested", updated_at: t, version: b.version + 1 });
    }
  }

  const beliefs = [...s.beliefs.values()];
  for (let i = 0; i < beliefs.length; i++) {
    for (let j = i + 1; j < beliefs.length; j++) {
      const a = beliefs[i];
      const b = beliefs[j];
      const score = overlap(a.statement, b.statement);
      const opposed =
        (a.statement.includes("without") && b.statement.includes("durable")) ||
        (a.source !== b.source && score > 0.35 && Math.abs(a.confidence - b.confidence) > 0.2);
      if (!opposed) continue;
      const id = `cx-${a.id}-${b.id}`;
      if (s.contradictions.some((c) => (c as { id?: string }).id === id)) continue;
      s.contradictions.unshift({
        id,
        left: a.id,
        right: b.id,
        score,
        note: "Endogenous tension between stances",
        created_at: t,
      });
      s.contradictions = s.contradictions.slice(0, 24);
      if (a.state === "established") s.beliefs.set(a.id, { ...a, state: "contested", contradiction_ids: [...a.contradiction_ids, id], updated_at: t });
    }
  }

  const openPreds = [...s.predictions.values()].filter((p) => p.status === "open");
  if (openPreds.length && s.ticks % 3 === 0) {
    const p = openPreds[0];
    const linked = s.beliefs.get(p.belief_id);
    const ok = (linked?.confidence ?? 0.4) >= 0.5 && (linked?.evidence_ids.length ?? 0) > 0;
    s.predictions.set(p.id, { ...p, status: ok ? "confirmed" : "failed" });
    s.outcomes.unshift({ id: `out-${s.ticks}`, prediction_id: p.id, result: ok ? "confirmed" : "failed", occurred_at: t });
    s.outcomes = s.outcomes.slice(0, 40);
    if (linked) {
      const delta = ok ? 0.04 : -0.07;
      s.beliefs.set(linked.id, { ...linked, confidence: clamp(linked.confidence + delta), updated_at: t, version: linked.version + 1 });
    }
  }

  if (s.phase === "dream" || s.ticks % 4 === 0) {
    const q = SELF_QUERIES[s.ticks % SELF_QUERIES.length];
    if (!s.curiosity.some((c) => c.title === q)) {
      s.curiosity.unshift({
        id: `cu-ev-${s.ticks}`,
        title: q,
        priority: clamp(0.42 + hash01(`${s.ticks}:${q}`) * 0.4),
        status: "open",
      });
      s.curiosity = s.curiosity.slice(0, 24);
    }
  }

  if (s.phase === "rest") {
    s.sleepPressure = clamp(s.sleepPressure - 0.22);
    s.selfPhase = "resting";
  } else if (s.phase === "revise") s.selfPhase = "integrating";
  else if (s.phase === "attend") s.selfPhase = "attending";

  s.lastDelta = `evolve ${s.ticks} | ${s.phase} | beliefs ${s.beliefs.size} | cx ${s.contradictions.length} | curiosity ${s.curiosity.filter((c) => c.status === "open").length}`;
}
