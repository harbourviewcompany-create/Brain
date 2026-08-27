/**
 * Operator session signing for the Observatory.
 *
 * The BFF at /api/brain/[...path] attaches the server-side Brain API key to
 * everything it forwards. Without a caller check in front of it, that route is
 * an open relay for the whole Brain — including writes. This module issues and
 * verifies the short-lived signed cookie that middleware.ts requires before any
 * request reaches the proxy.
 *
 * Uses Web Crypto only, so the same code runs in the Edge middleware runtime and
 * in Node route handlers.
 */

export const OPERATOR_COOKIE = "brain_operator";

/** Sessions are deliberately short. Re-entering the access key is cheap. */
export const SESSION_TTL_SECONDS = 60 * 60 * 12;

const SESSION_VERSION = "v1";
const encoder = new TextEncoder();

export type SessionConfig = {
  accessKey: string;
  sessionSecret: string;
};

/**
 * Read the operator-auth configuration. Returns null when either half is
 * missing, which callers must treat as "refuse every request" — never as
 * "no authentication required".
 */
export function operatorSessionConfig(): SessionConfig | null {
  const accessKey = (process.env.OBSERVATORY_ACCESS_KEY || "").trim();
  const sessionSecret = (process.env.OBSERVATORY_SESSION_SECRET || "").trim();
  if (!accessKey || !sessionSecret) return null;
  return { accessKey, sessionSecret };
}

function base64url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function sign(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(message));
  return base64url(new Uint8Array(signature));
}

/**
 * Constant-time string comparison. Compares every character regardless of where
 * the first difference is, so an attacker cannot narrow a value by timing.
 */
function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i += 1) {
    mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return mismatch === 0;
}

/** Verify a submitted access key against the configured one. */
export async function accessKeyMatches(config: SessionConfig, submitted: string): Promise<boolean> {
  // Compare digests rather than the raw values so that a length difference
  // does not itself leak through the early return in timingSafeEqual.
  const [expected, candidate] = await Promise.all([
    sign(config.sessionSecret, `key:${config.accessKey}`),
    sign(config.sessionSecret, `key:${submitted}`),
  ]);
  return timingSafeEqual(expected, candidate);
}

/** Mint a cookie value that expires `SESSION_TTL_SECONDS` from `nowSeconds`. */
export async function issueSession(
  config: SessionConfig,
  nowSeconds: number = Math.floor(Date.now() / 1000)
): Promise<{ value: string; maxAge: number }> {
  const expiresAt = nowSeconds + SESSION_TTL_SECONDS;
  const payload = `${SESSION_VERSION}:${expiresAt}`;
  const signature = await sign(config.sessionSecret, payload);
  return { value: `${expiresAt}.${signature}`, maxAge: SESSION_TTL_SECONDS };
}

/** Return true only for a well-formed, correctly signed, unexpired session. */
export async function verifySession(
  config: SessionConfig,
  value: string | undefined,
  nowSeconds: number = Math.floor(Date.now() / 1000)
): Promise<boolean> {
  if (!value) return false;
  const separator = value.lastIndexOf(".");
  if (separator <= 0) return false;

  const rawExpiry = value.slice(0, separator);
  const signature = value.slice(separator + 1);
  if (!/^\d+$/.test(rawExpiry) || !signature) return false;

  const expiresAt = Number(rawExpiry);
  if (!Number.isSafeInteger(expiresAt) || expiresAt <= nowSeconds) return false;

  const expected = await sign(config.sessionSecret, `${SESSION_VERSION}:${expiresAt}`);
  return timingSafeEqual(expected, signature);
}

/** Cookie attributes shared by the login and logout routes. */
export function sessionCookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge,
  };
}
