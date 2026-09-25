import { tick, status } from "@/lib/sovereign-brain";

export const dynamic = "force-dynamic";

/**
 * Bounded endogenous tick for Vercel Cron (or manual POST).
 * Protect with CRON_SECRET when set.
 */
export async function GET(request: Request) {
  const secret = (process.env.CRON_SECRET || "").trim();
  if (secret) {
    const auth = request.headers.get("authorization") || "";
    if (auth !== `Bearer ${secret}`) {
      return Response.json({ detail: "unauthorized" }, { status: 401 });
    }
  }
  const result = tick(2);
  return Response.json(
    { ok: true, ...result, status: status() },
    { headers: { "cache-control": "no-store" } },
  );
}

export async function POST(request: Request) {
  return GET(request);
}
