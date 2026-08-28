import { getVercelOidcToken } from "@vercel/oidc";

/**
 * Server-only upstream config for the Brain Runtime API.
 * Used exclusively by /api/brain/[...path] — never import from client components.
 *
 * The zero-dollar runtime has no Railway fallback. Production must explicitly
 * point BRAIN_API_URL at the stateless Vercel-hosted Turso runtime. A missing,
 * non-HTTPS, or legacy Railway URL fails closed instead of silently restoring a
 * paid/runtime dependency that the migration is removing.
 */

const LEGACY_RAILWAY_HOSTS = new Set([
  "brain-api-live-production.up.railway.app",
  "brain-api-docker-production.up.railway.app",
  "brain-api-production-f142.up.railway.app",
]);

function resolveBase(): string {
  const configured = (process.env.BRAIN_API_URL || "").trim().replace(/\/$/, "");
  if (!configured) return "";

  let parsed: URL;
  try {
    parsed = new URL(configured);
  } catch {
    return "";
  }
  if (parsed.protocol !== "https:") return "";
  if (LEGACY_RAILWAY_HOSTS.has(parsed.hostname) || parsed.hostname.endsWith(".railway.app")) {
    return "";
  }
  return parsed.origin + parsed.pathname.replace(/\/$/, "");
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

export function upstreamConfigured(): boolean {
  return Boolean(upstreamBase());
}

/**
 * Whether to forward Vercel deployment identity upstream.
 *
 * The canonical Vercel-hosted FastAPI runtime may verify Vercel deployment
 * identity in addition to the existing server-only API key. Set
 * BRAIN_UPSTREAM_ACCEPTS_OIDC=false for a runtime that accepts only the API key.
 */
function upstreamAcceptsOidc(): boolean {
  const configured = (process.env.BRAIN_UPSTREAM_ACCEPTS_OIDC || "").trim().toLowerCase();
  return configured !== "false";
}

async function upstreamVercelOidcToken(): Promise<string> {
  if (!process.env.VERCEL || !upstreamAcceptsOidc()) return "";
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
  "evidence",
  "working-memory",
  "learning-events",
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

  const base = upstreamBase();
  if (!base) {
    return Response.json(
      {
        detail: "brain_runtime_upstream_not_configured",
        hint: "Set BRAIN_API_URL to the HTTPS origin of the Vercel-hosted Turso Brain runtime.",
      },
      { status: 503, headers: { "cache-control": "no-store" } }
    );
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
        hint: "Set BRAIN_API_KEY on this deployment to the Brain runtime's BRAIN_API_KEY, then redeploy.",
      },
      { status: 503, headers: { "cache-control": "no-store" } }
    );
  }

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
    if (key) {
      return Response.json(
        {
          detail: "upstream_rejected_api_key",
          hint: "BRAIN_API_KEY here does not match the Brain runtime's BRAIN_API_KEY.",
          upstream: text.slice(0, 200),
        },
        { status: 401, headers: outHeaders }
      );
    }
    if (oidcToken) {
      return Response.json(
        {
          detail: "upstream_rejected_vercel_identity",
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
