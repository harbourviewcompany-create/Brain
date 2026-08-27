/**
 * Produce a Playwright storage state carrying a valid operator session.
 *
 * The Observatory requires a signed operator session on every route, so CI's
 * visual-evidence step cannot screenshot the cockpit anonymously any more — it
 * would capture the login page. This signs in through the real
 * /api/auth/login route and writes the resulting cookie in Playwright's
 * storageState format, so `playwright screenshot --load-storage` renders the
 * authenticated cockpit.
 *
 * Running it also proves the login route works end to end on every CI run.
 *
 * Usage: node scripts/ci-operator-storage-state.mjs <baseUrl> <outputFile>
 */
import { writeFileSync } from "node:fs";

const [, , baseUrl, outputFile] = process.argv;

if (!baseUrl || !outputFile) {
  console.error("usage: ci-operator-storage-state.mjs <baseUrl> <outputFile>");
  process.exit(1);
}

const accessKey = process.env.OBSERVATORY_ACCESS_KEY;
if (!accessKey) {
  console.error("OBSERVATORY_ACCESS_KEY must be set to sign in");
  process.exit(1);
}

const response = await fetch(new URL("/api/auth/login", baseUrl), {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ access_key: accessKey }),
});

if (!response.ok) {
  const detail = await response.text().catch(() => "");
  console.error(`login failed: ${response.status} ${detail}`);
  process.exit(1);
}

const setCookie = response.headers.get("set-cookie");
if (!setCookie) {
  console.error("login succeeded but returned no session cookie");
  process.exit(1);
}

// `name=value; Path=/; Max-Age=...; HttpOnly; SameSite=Lax`
const [pair] = setCookie.split(";");
const separator = pair.indexOf("=");
const name = pair.slice(0, separator).trim();
const value = pair.slice(separator + 1).trim();

const { hostname } = new URL(baseUrl);

writeFileSync(
  outputFile,
  JSON.stringify(
    {
      cookies: [
        {
          name,
          value,
          domain: hostname,
          path: "/",
          // Comfortably inside the 12-hour session TTL; Playwright wants an
          // absolute expiry in seconds.
          expires: Math.floor(Date.now() / 1000) + 60 * 60,
          httpOnly: true,
          secure: false,
          sameSite: "Lax",
        },
      ],
      origins: [],
    },
    null,
    2
  )
);

console.log(`Operator session captured for ${hostname} -> ${outputFile}`);
