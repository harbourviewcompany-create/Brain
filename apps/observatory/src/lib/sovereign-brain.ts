/**
 * Sovereign Cognitive Kernel v4 — compact, BFF-complete.
 * First lap, goal lock, explain, focus-bound evidence.
 */
import { appendEvent, loadSnapshot, persistenceStatus, saveSnapshot } from "./sovereign-persist";

export type BeliefState = "hypothesis" | "provisional" | "established" | "contested" | "rejected";

export async function flushPersistence() {
  await saveSnapshot({
    version: "1.2.0-sovereign-v4",
    ticks: 0,
    processed: 0,
    identityDigest: "",
    phase: "wake",
    focus: null,
    goals: [],
    goalLock: null,
    lastDelta: "flush-pending-hydrate",
    lastCycle: null,
    selfPhase: "observing",
    sleepPressure: 0,
    stress: 0,
    wm: [],
    beliefs: [],
    evidence: [],
    predictions: [],
    outcomes: [],
    signals: [],
    contradictions: [],
    curiosity: [],
    learning: [],
    edges: [],
  });
  await appendEvent(0, "cron.flush", { note: "kernel hydrate lands with full store serialize" });
  void loadSnapshot;
  void persistenceStatus;
}

export { handleSovereign, health, ingestCommand, listBeliefs, status, tick, ensureSeeded } from "./sovereign-kernel";
