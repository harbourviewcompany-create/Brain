import type { CognitiveScene, SceneNode } from "@/types/observatory";

export interface FieldDiff {
  added: string[];
  removed: string[];
  updated: string[];
  /** Highest-importance cognitive change, used as attention camera hint. */
  cameraHintId: string | null;
}

function nodeFingerprint(node: SceneNode): string {
  return [
    node.state ?? "",
    node.importance.toFixed(3),
    node.size.toFixed(2),
    node.label,
    node.summary,
    node.metrics.map((metric) => `${metric.label}:${metric.value}`).join("|"),
  ].join("::");
}

/**
 * Pure scene-to-scene diff. Deterministic; safe for scrub replay.
 * Does not mutate layout — only reports identity and state change.
 */
export function diffScene(previous: CognitiveScene | null, next: CognitiveScene): FieldDiff {
  if (!previous) {
    const added = next.nodes.map((node) => node.id);
    return {
      added,
      removed: [],
      updated: [],
      cameraHintId: pickCameraHint(next, added, []),
    };
  }

  const prevById = new Map(previous.nodes.map((node) => [node.id, node]));
  const nextById = new Map(next.nodes.map((node) => [node.id, node]));

  const added: string[] = [];
  const removed: string[] = [];
  const updated: string[] = [];

  for (const node of next.nodes) {
    const prior = prevById.get(node.id);
    if (!prior) {
      added.push(node.id);
      continue;
    }
    if (nodeFingerprint(prior) !== nodeFingerprint(node)) {
      updated.push(node.id);
    }
  }

  for (const node of previous.nodes) {
    if (!nextById.has(node.id)) removed.push(node.id);
  }

  return {
    added,
    removed,
    updated,
    cameraHintId: pickCameraHint(next, added, updated),
  };
}

function pickCameraHint(scene: CognitiveScene, added: string[], updated: string[]): string | null {
  const candidates = [...added, ...updated]
    .map((id) => scene.nodes.find((node) => node.id === id))
    .filter((node): node is SceneNode => Boolean(node))
    .filter((node) => node.layer !== "diagnostic" && node.kind !== "organism");

  if (candidates.length === 0) return null;

  candidates.sort((a, b) => b.importance - a.importance);
  return candidates[0]?.id ?? null;
}
