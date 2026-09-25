import { sovereignMode, upstreamBase, upstreamKeyConfigured } from "@/lib/brain-upstream";
import { health, listBeliefs, status, tick } from "@/lib/sovereign-brain";

export const dynamic = "force-dynamic";

/**
 * Non-secret diagnostics for operators.
 * Never returns the API key value.
 * Sovereign mode: reports in-process cognition when no upstream is configured.
 */
export async function GET() {
  if (sovereignMode()) {
    // Advance one endogenous cycle on each status poll so the cockpit lives.
    tick(1);
    const st = status();
    const beliefs = listBeliefs();
    return Response.json(
      {
        bff: "ok",
        mode: "sovereign",
        upstream_base: "",
        brain_api_key_configured: upstreamKeyConfigured(),
        upstream_health_ok: true,
        upstream_health: health(),
        sample_authed_beliefs: { status: 200, detail: `${beliefs.length} beliefs` },
        sovereign: st,
        fix: null,
      },
      { headers: { "cache-control": "no-store" } },
    );
  }

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
      mode: "upstream",
      upstream_base: base,
      brain_api_key_configured: keyConfigured,
      upstream_health_ok: upstreamHealthOk,
      upstream_health: upstreamHealth,
      sample_authed_beliefs: sampleAuthed,
      fix:
        !keyConfigured
          ? "Set BRAIN_API_KEY, or clear BRAIN_API_URL to use sovereign in-process mode."
          : sampleAuthed && sampleAuthed.status === 401
            ? "Key is set but upstream rejected it."
            : sampleAuthed && sampleAuthed.status === 200
              ? "Auth path OK."
              : null,
    },
    { headers: { "cache-control": "no-store" } },
  );
}
