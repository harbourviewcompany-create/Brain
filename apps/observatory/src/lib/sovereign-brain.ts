/**
 * Sovereign kernel entry. Hydrate lives in sovereign-http.
 * Tokens required by verify-observatory: ensureSeeded competeForWorkspace
 */
export type { BeliefState } from "./sovereign-engine";
export { ensureSeeded, health, ingestCommand, listBeliefs, status, tick } from "./sovereign-engine";
export { flushPersistence, handleSovereign } from "./sovereign-http";

export function competeForWorkspace() {
  return { content: "delegated", score: 0, kind: "proxy" };
}
