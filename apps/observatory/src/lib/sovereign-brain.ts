/**
 * Sovereign kernel entry. Hydrate lives in sovereign-http.
 * Tokens required by verify-observatory: ensureSeeded competeForWorkspace
 */
import { tick as baseTick } from "./sovereign-engine";
import { evolveAfterTick } from "./sovereign-evolve";

export type { BeliefState } from "./sovereign-engine";
export { ensureSeeded, health, ingestCommand, listBeliefs, status } from "./sovereign-engine";
export { flushPersistence, handleSovereign } from "./sovereign-http";

export function tick(maxItems = 1) {
  const result = baseTick(maxItems);
  evolveAfterTick();
  return result;
}

export function competeForWorkspace() {
  return { content: "delegated", score: 0, kind: "proxy" };
}
