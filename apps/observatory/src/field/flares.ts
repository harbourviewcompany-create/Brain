export type FlareKind = "auth" | "missing_route" | "partial" | "empty";

export interface FieldFlare {
  id: string;
  kind: FlareKind;
  message: string;
  /** Normalized field position. */
  x: number;
  y: number;
}

function classify(error: string): FlareKind {
  const lower = error.toLowerCase();
  if (
    lower.includes("401") ||
    lower.includes("invalid_or_missing_api_key") ||
    lower.includes("upstream_rejected_vercel_identity") ||
    lower.includes("unauthorized")
  ) {
    return "auth";
  }
  if (lower.includes("404") || lower.includes("not deployed") || lower.includes("/organism")) {
    return "missing_route";
  }
  return "partial";
}

/**
 * Turn BFF/read errors into visible diagnostic scars on the field.
 * Never invents cognitive content — only operational truth.
 */
export function flaresFromErrors(errors: string[]): FieldFlare[] {
  if (!errors.length) return [];

  const seen = new Set<FlareKind>();
  const flares: FieldFlare[] = [];

  for (const [index, error] of errors.entries()) {
    const kind = classify(error);
    if (seen.has(kind)) continue;
    seen.add(kind);

    const angle = -Math.PI / 2 + (index / Math.max(errors.length, 1)) * Math.PI * 0.35;
    flares.push({
      id: `flare:${kind}:${index}`,
      kind,
      message: error.length > 120 ? `${error.slice(0, 117)}…` : error,
      x: 0.5 + Math.cos(angle) * 0.22,
      y: 0.49 + Math.sin(angle) * 0.16,
    });
  }

  return flares;
}

export function flareColor(kind: FlareKind): string {
  switch (kind) {
    case "auth":
      return "#ff8f5c";
    case "missing_route":
      return "#f5bd63";
    case "partial":
      return "#91a6bd";
    default:
      return "#68798e";
  }
}
