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

/**
 * Whether to forward Vercel deployment identity upstream.
 *
 * Only the Dockerfile.railway entrypoint verifies it: tools/live_cockpit_routes
 * wraps the app in VercelOidcAuthBridge, which checks the token's issuer,
 * audience and subject against tools/vercel_oidc.py before exchanging it for
 * the local API key. The canonical Dockerfile entrypoint
 * (apps.api.tenant_app) has no such bridge and authenticates on BRAIN_API_KEY
 * alone, so against that image the bearer token is simply ignored.
 *
 * Forwarding it is safe either way now that apps/api/main.py accepts any
 * presented credential that matches, rather than letting the bearer header mask
 * a valid X-Brain-Api-Key. Set BRAIN_UPSTREAM_ACCEPTS_OIDC=false to suppress it
 * when pointing at an upstream that should never see a deployment token.
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
        hint: "Set BRAIN_API_KEY on this deployment to the Brain runtime's BRAIN_API_KEY, then redeploy.",
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
    // Report the API key first: it is the credential the upstream actually
    // checks, so naming the deployment identity here would point debugging at
    // the wrong half of the configuration.
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
