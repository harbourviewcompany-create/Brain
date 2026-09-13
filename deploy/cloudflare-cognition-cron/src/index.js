/**
 * Free-tier Cloudflare Worker: cron → Brain API lease-aware cognition tick.
 *
 * Does not run Python. Invokes POST {BRAIN_API_URL}{path} with X-Brain-Api-Key.
 * Safe when inline cognition or a worker already holds the lease (API returns
 * lease_held_elsewhere without double-writing).
 */

const DEFAULT_PATH = "/internal/cognition/tick";

async function triggerTick(env) {
  const base = (env.BRAIN_API_URL || "").replace(/\/$/, "");
  const key = env.BRAIN_API_KEY || "";
  const path = env.BRAIN_TICK_PATH || DEFAULT_PATH;

  if (!base || !key) {
    console.error("BRAIN_API_URL and BRAIN_API_KEY secrets are required");
    return { ok: false, error: "missing_secrets" };
  }

  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Brain-Api-Key": key,
    },
    body: JSON.stringify({ max_items: 1, max_ticks: 1 }),
  });

  const text = await response.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    body = { raw: text.slice(0, 500) };
  }

  console.log(
    JSON.stringify({
      status: response.status,
      ok: response.ok,
      brain: body,
    }),
  );

  return { ok: response.ok, status: response.status, brain: body };
}

export default {
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(triggerTick(env));
  },

  // Manual probe: GET / or POST / on the Worker URL runs one tick (still needs secrets).
  async fetch(_request, env, ctx) {
    const result = await triggerTick(env);
    return new Response(JSON.stringify(result, null, 2), {
      status: result.ok ? 200 : 502,
      headers: { "Content-Type": "application/json" },
    });
  },
};
