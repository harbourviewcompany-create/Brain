import type { FieldDiff } from "@/field/diffScene";

const BIRTH_MS = 900;
const DEATH_MS = 450;

export type BirthMap = Map<string, number>;

export function createBirthMap(): BirthMap {
  return new Map();
}

/** Register first-seen timestamps for newly added scene ids. */
export function applyDiffToBirths(births: BirthMap, diff: FieldDiff, now = Date.now()): BirthMap {
  const next = new Map(births);
  for (const id of diff.added) {
    if (!next.has(id)) next.set(id, now);
  }
  for (const id of diff.removed) {
    next.delete(id);
  }
  return next;
}

function easeOutCubic(t: number): number {
  return 1 - (1 - t) ** 3;
}

/** Scale factor for morphogenesis (0.12 → 1 over BIRTH_MS). */
export function visualScale(id: string, births: BirthMap, now = Date.now()): number {
  const born = births.get(id);
  if (born === undefined) return 1;
  const t = Math.min(1, Math.max(0, (now - born) / BIRTH_MS));
  return 0.12 + 0.88 * easeOutCubic(t);
}

/** Alpha boost flash in the first moments after birth. */
export function birthFlash(id: string, births: BirthMap, now = Date.now()): number {
  const born = births.get(id);
  if (born === undefined) return 0;
  const age = now - born;
  if (age < 0 || age > BIRTH_MS * 0.55) return 0;
  return 1 - age / (BIRTH_MS * 0.55);
}

export function isStillBirthing(id: string, births: BirthMap, now = Date.now()): boolean {
  const born = births.get(id);
  if (born === undefined) return false;
  return now - born < BIRTH_MS;
}

export { BIRTH_MS, DEATH_MS };
