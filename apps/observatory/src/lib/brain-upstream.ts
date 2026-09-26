import { getVercelOidcToken } from "@vercel/oidc";
import { handleSovereign } from "@/lib/sovereign-brain";

function allowedUpstreamHosts(): Set<string> {
  return new Set(
    (process.env.BRAIN_API_ALLOWED_HOSTS || "")
      .split(",")
      .map((host) => host.trim().toLowerCase())
      .filter(Boolean),
  );
}

function resolveBase(): string {
  const configured = (process.env.BRAIN_API_URL || "").trim().replace(/\/$/, "");
  if (!configured) return "";
  let parsed: URL;
  try { parsed = new URL(configured); } catch { return ""; }
  if (parsed.protocol !== "https:") return "";
  if (parsed.username || parsed.password || parsed.port) return "";
  // Railway origins are unsupported upstreams — reject and fall through to sovereign.
  if (parsed.hostname.toLowerCase().endsWith(".railway.app")) return "";
  const allowed = allowedUpstreamHosts();
  if (allowed.size > 0 && !allowed.has(parsed.hostname.toLowerCase())) return "";
  return parsed.origin + parsed.pathname.replace(/\/$/, "");
}

export function upstreamBase(): string { return resolveBase(); }
export function upstreamApiKey(): string { return (process.env.BRAIN_API_KEY || "").trim(); }
export function upstreamKeyConfigured(): boolean { return Boolean(upstreamApiKey()); }
export function upstreamConfigured(): boolean { return Boolean(upstreamBase()); }
export function sovereignMode(): boolean { return !upstreamBase(); }

function upstreamAcceptsOidc(): boolean {
  const configured = (process.env.BRAIN_UPSTREAM_ACCEPTS_OIDC || "").trim().toLowerCase();
  return configured !== "false";
}

async function upstreamVercelOidcToken(): Promise<string> {
  if (!process.env.VERCEL || !upstreamAcceptsOidc()) return "";
  try { return (await getVercelOidcToken()) || ""; } catch { return ""; }
}

const PUBLIC_UPSTREAM_PATHS = new Set(["health", "ready"]);

const ALLOWED_PREFIXES = [
  "health", "ready", "beliefs", "learn", "predictions", "signals", "evidence",
  "working-memory", "learning-events", "opportunities", "approvals", "contradictions",
  "curiosity", "sources", "outcomes", "formula-runs", "acceptance-reports", "edges",
  "tick", "runner", "money-lanes", "revenue-signals", "revenue-experiments",
  "daily-revenue-report", "organism", "explain", "snapshot",
] as const;

export function isAllowedUpstreamPath(pathSegments: string[]): boolean {
  if (pathSegments.length === 0) return false;
  return ALLOWED_PREFIXES.some((p) => p === pathSegments[0]);
}

export async function proxyToBrain(
  pathSegments: string[],
  init: { method: string; headers?: Headers; body?: string | null; search?: string },
): Promise<Response> {
  if (!isAllowedUpstreamPath(pathSegments)) {
    return Response.json({ detail: "path_not_allowed" }, { status: 404 });
  }
  const base = upstreamBase();
  if (!base) {
    const local = handleSovereign(pathSegments, init.method, init.body);
    if (local) return local;
    return Response.json({ detail: "sovereign_path_not_implemented", mode: "sovereign", path: pathSegments.join("/") }, { status: 404, headers: { "cache-control": "no-store" } });
  }
  const [oidcToken, key] = await Promise.all([upstreamVercelOidcToken(), Promise.resolve(upstreamApiKey())]);
  const isPublic = PUBLIC_UPSTREAM_PATHS.has(pathSegments[0]);
  if (!oidcToken && !key && !isPublic) {
    return Response.json({ detail: "brain_bff_upstream_identity_unavailable", hint: "Set BRAIN_API_KEY on this deployment, or clear BRAIN_API_URL for sovereign mode." }, { status: 503, headers: { "cache-control": "no-store" } });
  }
  const path = "/" + pathSegments.map(encodeURIComponent).join("/");
  const url = `${base}${path}${init.search || ""}`;
  const headers: Record<string, string> = { accept: "application/json" };
  const contentType = init.headers?.get("content-type");
  if (contentType) headers["content-type"] = contentType;
  if (oidcToken) headers.authorization = `Bearer ${oidcToken}`;
  if (key) headers["X-Brain-Api-Key"] = key;
  const upstream = await fetch(url, { method: init.method, headers, body: init.method === "GET" || init.method === "HEAD" ? undefined : init.body, cache: "no-store" });
  const text = await upstream.text();
  const outHeaders = new Headers();
  const ct = upstream.headers.get("content-type");
  if (ct) outHeaders.set("content-type", ct);
  outHeaders.set("cache-control", "no-store");
  return new Response(text, { status: upstream.status, statusText: upstream.statusText, headers: outHeaders });
}
