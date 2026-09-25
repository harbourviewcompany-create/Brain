import { tick, status } from "@/lib/sovereign-brain";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

/**
 * Bounded endogenous burst for Vercel Cron (or manual GET/POST).
 * Default: 4 cognitive cycles per invocation.
 */
export async function GET(request: Request) {
  const secret = (process.env.CRON_SECRET || "").trim();
  if (secret) {
    const auth = request.headers.get("authorization") || "";
    if (auth !== `Bearer ${secret}`) {
      return Response.json({ detail: "unauthorized" }, { status: 401 });
    }
  }
  const url = new URL(request.url);
  const n = Math.min(8, Math.max(1, Number(url.searchParams.get("n") || 4)));
  const result = tick(n);
  return Response.json(
    { ok: true, ...result, status: status() },
    { headers: { "cache-control": "no-store" } },
  );
}

export async function POST(request: Request) {
  return GET(request);
}
