import type { CognitiveScene, SceneNode } from "@/types/observatory";

export interface FieldCamera {
  /** World focus in normalized scene coords (0–1). */
  x: number;
  y: number;
  /** 1 = default; slightly above 1 pulls in on focus. */
  zoom: number;
}

export const DEFAULT_CAMERA: FieldCamera = {
  x: 0.5,
  y: 0.49,
  zoom: 1,
};

export function createCamera(): FieldCamera {
  return { ...DEFAULT_CAMERA };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function nodeTarget(node: SceneNode | undefined, fallback: FieldCamera): { x: number; y: number; zoom: number } {
  if (!node) return { x: fallback.x, y: fallback.y, zoom: 1 };
  const zoom = node.kind === "organism" ? 1 : clamp(1.02 + node.importance * 0.12, 1, 1.18);
  return { x: node.x, y: node.y, zoom };
}

/**
 * Resolve the attention target from selection, diff hint, or organism core.
 */
export function resolveCameraTarget(
  scene: CognitiveScene,
  selectedId: string | null,
  cameraHintId: string | null,
): { x: number; y: number; zoom: number } {
  const selected = selectedId ? scene.nodes.find((node) => node.id === selectedId) : undefined;
  if (selected) return nodeTarget(selected, DEFAULT_CAMERA);

  const hinted = cameraHintId ? scene.nodes.find((node) => node.id === cameraHintId) : undefined;
  if (hinted && hinted.layer !== "diagnostic") return nodeTarget(hinted, DEFAULT_CAMERA);

  const organism = scene.nodes.find((node) => node.kind === "organism");
  return nodeTarget(organism, DEFAULT_CAMERA);
}

/**
 * Frame-step toward target. Mutates and returns the same camera object.
 */
export function stepCamera(camera: FieldCamera, target: { x: number; y: number; zoom: number }, dtMs: number): FieldCamera {
  // Normalize to ~60fps easing strength.
  const t = 1 - Math.exp(-(dtMs / 1000) * 4.2);
  camera.x += (target.x - camera.x) * t;
  camera.y += (target.y - camera.y) * t;
  camera.zoom += (target.zoom - camera.zoom) * t;
  return camera;
}

/**
 * Map normalized node position through camera into canvas pixels.
 * Zoom is centered on the camera focus point.
 */
export function projectPoint(
  nx: number,
  ny: number,
  width: number,
  height: number,
  camera: FieldCamera,
): { x: number; y: number } {
  const cx = camera.x * width;
  const cy = camera.y * height;
  const z = camera.zoom;
  return {
    x: cx + (nx * width - cx) * z,
    y: cy + (ny * height - cy) * z,
  };
}
