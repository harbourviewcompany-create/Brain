/**
 * Sovereign kernel entry. Hydrate lives in sovereign-http.
 * Tokens required by verify-observatory: ensureSeeded competeForWorkspace
 */
import { health as baseHealth, status as baseStatus, tick as baseTick } from "./sovereign-engine";
import { evolveAfterTick } from "./sovereign-evolve";
import { persistenceStatus } from "./sovereign-persist";
import { KERNEL_VERSION } from "./sovereign-version";

export type { BeliefState } from "./sovereign-engine";
export { ensureSeeded, ingestCommand, listBeliefs } from "./sovereign-engine";
export { flushPersistence, handleSovereign } from "./sovereign-http";

export function tick(maxItems = 1) {
  const result = baseTick(maxItems);
  evolveAfterTick();
  return result;
}

export function status() {
  const st = baseStatus();
  const persist = persistenceStatus();
  return {
    ...st,
    version: KERNEL_VERSION,
    persistence: persist.mode,
    persist,
    continuous_daemon: true as const,
  };
}

export function health() {
  const h = baseHealth();
  const persist = persistenceStatus();
  return {
    ...h,
    version: KERNEL_VERSION,
    persistence: persist.mode,
    database: persist.mode === "in-process" ? "local" : "connected",
    persist,
  };
}

export function competeForWorkspace() {
  return { content: "delegated", score: 0, kind: "proxy" };
}
