import { getVercelOidcToken } from "@vercel/oidc";

/**
 * Server-only upstream config for the Brain Runtime API.
 * Used exclusively by /api/brain/[...path] — never import from client components.
 */

const LIVE_RAILWAY_BASE = "https://brain-api-live-production.up.railway.app";
const DEPRECATED_RAILWAY_BASES = new Set([
  "https://brain-api-docker-production.up.railway.app",
  "https://brain-api-production-f142.up.railway.app",
]);

function resolveBase(): string {
  const configured = (process.env.BRAIN_API_URL || process.env.NEXT_PUBLIC_BRAIN_API_URL || "")
    .replace(/\/$/, "");
  if (!configured || DEPRECATED_RAILWAY_BASES.has(configured)) {
    return LIVE_RAILWAY_BASE;
  }
  return configured;
}

export function upstreamBase(): string {
  return resolveBase();
}

export function upstreamApiKey(): string {
  return (process.env.BRAIN_API_KEY || "").trim();
}

export function upstreamKeyConfigured(): boolean {
  return Boolean(upstreamApiKey());
}

async function upstreamVercelOidcToken(): Promise<string> {
  if (!process.env.VERCEL) return "";
  try {
    return (await getVercelOidcToken()) || "";
  } catch {
    return "";
  }
}

const PUBLIC_UPSTREAM_PATHS = new Set(["health", "ready"]);

const ALLOWED_PREFIXES = [
  "health",
  "ready",
  "beliefs",
  "learn",
  "predictions",
  "signals",
  "opportunities",
  "approvals",
  "contradictions",
  "curiosity",
  "sources",
  "outcomes",
  "formula-runs",
  "acceptance-reports",
  "edges",
  "tick",
  "runner",
  "money-lanes",
  "revenue-signals",
  "revenue-experiments",
  "daily-revenue-report",
  "organism",
] as const;

export function isAllowedUpstreamPath(pathSegments: string[]): boolean {
  if (pathSegments.length === 0) return false;
  const head = pathSegments[0];
  return ALLOWED_PREFIXES.some((p) => p === head);
}

export async function proxyToBrain(
  pathSegments: string[],
  init: {
    method: string;
    headers?: Headers;
    body?: string | null;
    search?: string;
  }
): Promise<Response> {
  if (!isAllowedUpstreamPath(pathSegments)) {
    return Response.json({ detail: "path_not_allowed" }, { status: 404 });
  }

  const [oidcToken, key] = await Promise.all([
    upstreamVercelOidcToken(),
    Promise.resolve(upstreamApiKey()),
  ]);
  const isPublic = PUBLIC_UPSTREAM_PATHS.has(pathSegments[0]);

  if (!oidcToken && !key && !isPublic) {
    return Response.json(
      {
        detail: "brain_bff_upstream_identity_unavailable",
        hint: "The BFF has neither Vercel deployment identity nor the legacy server API-key fallback.",
      },
      { status: 503, headers: { "cache-control": "no-store" } }
    );
  }

  const base = upstreamBase();
  const path = "/" + pathSegments.map(encodeURIComponent).join("/");
  const url = `${base}${path}${init.search || ""}`;

  const headers: Record<string, string> = {
    accept: "application/json",
  };
  const contentType = init.headers?.get("content-type");
  if (contentType) headers["content-type"] = contentType;
  if (oidcToken) headers.authorization = `Bearer ${oidcToken}`;
  if (key) headers["X-Brain-Api-Key"] = key;

  const upstream = await fetch(url, {
    method: init.method,
    headers,
    body: init.method === "GET" || init.method === "HEAD" ? undefined : init.body,
    cache: "no-store",
  });

  const text = await upstream.text();
  const outHeaders = new Headers();
  const ct = upstream.headers.get("content-type");
  if (ct) outHeaders.set("content-type", ct);
  outHeaders.set("cache-control", "no-store");

  if (upstream.status === 401) {
    if (oidcToken) {
      return Response.json(
        {
          detail: "upstream_rejected_vercel_identity",
          upstream: text.slice(0, 200),
        },
        { status: 401, headers: outHeaders }
      );
    }
    if (key) {
      return Response.json(
        {
          detail: "upstream_rejected_api_key",
          upstream: text.slice(0, 200),
        },
        { status: 401, headers: outHeaders }
      );
    }
  }

  return new Response(text, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: outHeaders,
  });
}
