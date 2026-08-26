import { upstreamBase, upstreamKeyConfigured } from "@/lib/brain-upstream";

export const dynamic = "force-dynamic";

/**
 * Non-secret diagnostics for operators.
 * Never returns the API key value.
 */
export async function GET() {
  const base = upstreamBase();
  const keyConfigured = upstreamKeyConfigured();

  let upstreamHealth: unknown = null;
  let upstreamHealthOk = false;
  try {
    const res = await fetch(`${base}/health`, { cache: "no-store" });
    upstreamHealthOk = res.ok;
    upstreamHealth = await res.json().catch(() => null);
  } catch (e) {
    upstreamHealth = { error: e instanceof Error ? e.message : String(e) };
  }

  let sampleAuthed: { status: number; detail?: string } | null = null;
  if (keyConfigured) {
    try {
      const res = await fetch(`${base}/beliefs`, {
        headers: {
          accept: "application/json",
          "X-Brain-Api-Key": process.env.BRAIN_API_KEY || "",
        },
        cache: "no-store",
      });
      const body = await res.text();
      let detail: string | undefined;
      try {
        detail = JSON.parse(body)?.detail;
      } catch {
        detail = body.slice(0, 120);
      }
      sampleAuthed = { status: res.status, detail };
    } catch (e) {
      sampleAuthed = {
        status: 0,
        detail: e instanceof Error ? e.message : String(e),
      };
    }
  }

  return Response.json(
    {
      bff: "ok",
      upstream_base: base,
      brain_api_key_configured: keyConfigured,
      upstream_health_ok: upstreamHealthOk,
      upstream_health: upstreamHealth,
      sample_authed_beliefs: sampleAuthed,
      fix:
        !keyConfigured
          ? "Set Vercel env BRAIN_API_KEY (server-only) to Railway BRAIN_API_KEY, then Redeploy."
          : sampleAuthed && sampleAuthed.status === 401
            ? "Key is set but Railway rejected it — values do not match. Re-copy from Railway and redeploy."
            : sampleAuthed && sampleAuthed.status === 200
              ? "Auth path OK."
              : null,
    },
    { headers: { "cache-control": "no-store" } }
  );
}
