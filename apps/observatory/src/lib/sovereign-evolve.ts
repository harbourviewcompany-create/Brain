/**
 * Endogenous evolution pass. Runs after every tick batch.
 * Deterministic. No external model host.
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
];

export function evolveAfterTick() {
  const s = store();
  const t = now();
  const tickKey = String(s.ticks);

  for (const b of s.beliefs.values()) {
    const ev = b.evidence_ids.length;
    if (b.state === "hypothesis" && ev >= 2) {
      s.beliefs.set(b.id, { ...b, state: "provisional", confidence: clamp(b.confidence + 0.08), updated_at: t, version: b.version + 1 });
    } else if (b.state === "provisional" && ev >= 4 && b.confidence >= 0.55) {
      s.beliefs.set(b.id, { ...b, state: "established", confidence: clamp(b.confidence + 0.06), updated_at: t, version: b.version + 1 });
    } else if (b.state === "hypothesis" && s.ticks - 12 > 0 && ev === 0 && b.confidence < 0.4) {
      s.beliefs.set(b.id, { ...b, state: "contested", updated_at: t, version: b.version + 1 });
    }
  }

  const openPreds = [...s.predictions.values()].filter((p) => p.status === "open");
  if (openPreds.length && s.ticks % 3 === 0) {
    const p = openPreds[0];
    const linked = s.beliefs.get(p.belief_id);
    const ok = (linked?.confidence ?? 0.4) >= 0.5 && (linked?.evidence_ids.length ?? 0) > 0;
    s.predictions.set(p.id, { ...p, status: ok ? "confirmed" : "failed" });
    s.outcomes.unshift({
      id: `out-${s.ticks}`,
      prediction_id: p.id,
      result: ok ? "confirmed" : "failed",
      occurred_at: t,
    });
    s.outcomes = s.outcomes.slice(0, 40);
    if (linked) {
      const delta = ok ? 0.04 : -0.07;
      s.beliefs.set(linked.id, { ...linked, confidence: clamp(linked.confidence + delta), updated_at: t, version: linked.version + 1 });
    }
  }

  if (s.phase === "dream" || s.ticks % 5 === 0) {
    const q = SELF_QUERIES[s.ticks % SELF_QUERIES.length];
    const exists = s.curiosity.some((c) => c.title === q);
    if (!exists) {
      s.curiosity.unshift({
        id: `cu-ev-${s.ticks}`,
        title: q,
        priority: clamp(0.42 + hash01(`${tickKey}:${q}`) * 0.4),
        status: "open",
      });
      s.curiosity = s.curiosity.slice(0, 24);
    }
  }

  if (s.phase === "rest") {
    s.sleepPressure = clamp(s.sleepPressure - 0.22);
    s.selfPhase = "resting";
  } else if (s.phase === "revise") {
    s.selfPhase = "integrating";
  } else if (s.phase === "attend") {
    s.selfPhase = "attending";
  }

  if (s.beliefs.size < 8) {
    const statement = `Continuity requires a durable ledger after ${s.ticks} endogenous cycles`;
    const id = `b-ev-${s.ticks}`;
    if (![...s.beliefs.values()].some((b) => b.statement === statement)) {
      s.beliefs.set(id, {
        id,
        statement,
        confidence: 0.48,
        state: "hypothesis",
        created_at: t,
        updated_at: t,
        version: 1,
        evidence_ids: [],
        contradiction_ids: [],
        unknowns: ["Has the snapshot row been written?"],
        source: "endogenous_evolve",
      });
    }
  }

  s.lastDelta = `evolve ${s.ticks} | ${s.phase} | beliefs ${s.beliefs.size} | curiosity ${s.curiosity.filter((c) => c.status === "open").length}`;
}
