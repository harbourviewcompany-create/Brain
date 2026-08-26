/**
 * Operator session unit checks.
 *
 * The BFF attaches the server-side Brain API key to everything it forwards, so
 * the signed session in front of it is the only thing separating an anonymous
 * visitor from write access to the Brain. These assertions run in
 * `npm run verify` alongside lint, typecheck and build.
 *
 * The module is compiled with the project's own TypeScript rather than having
 * its types stripped by hand, so what is exercised here is what ships.
 */
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { rename } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const outDir = mkdtempSync(path.join(tmpdir(), "operator-session-"));

execFileSync(
  process.execPath,
  [
    path.join("node_modules", "typescript", "bin", "tsc"),
    "src/lib/operator-session.ts",
    "--outDir", outDir,
    "--module", "esnext",
    "--target", "es2022",
    "--moduleResolution", "bundler",
  ],
  { stdio: "inherit" }
);

// tsc emits .js; give it an .mjs extension so node loads it as an ES module
// without needing a package.json marker in the temp directory.
const emitted = path.join(outDir, "operator-session.js");
const loadable = path.join(outDir, "operator-session.mjs");
await rename(emitted, loadable);

const {
  OPERATOR_COOKIE,
  SESSION_TTL_SECONDS,
  accessKeyMatches,
  issueSession,
  operatorSessionConfig,
  verifySession,
} = await import(pathToFileURL(loadable).href);

const config = { accessKey: "correct-horse", sessionSecret: "signing-secret" };

// --- configuration must fail closed ---
delete process.env.OBSERVATORY_ACCESS_KEY;
delete process.env.OBSERVATORY_SESSION_SECRET;
assert.equal(operatorSessionConfig(), null, "missing config must return null, not a default");

process.env.OBSERVATORY_ACCESS_KEY = "k";
assert.equal(operatorSessionConfig(), null, "half-configured must still fail closed");

process.env.OBSERVATORY_SESSION_SECRET = "s";
assert.deepEqual(operatorSessionConfig(), { accessKey: "k", sessionSecret: "s" });

// --- access key ---
assert.equal(await accessKeyMatches(config, "correct-horse"), true);
assert.equal(await accessKeyMatches(config, "wrong-horse"), false);
assert.equal(await accessKeyMatches(config, ""), false);
assert.equal(await accessKeyMatches(config, "correct-horse "), false, "the submitted key is not trimmed");

// --- session round trip ---
const now = 1_800_000_000;
const session = await issueSession(config, now);
assert.equal(session.maxAge, SESSION_TTL_SECONDS);
assert.equal(await verifySession(config, session.value, now), true);

// --- expiry ---
assert.equal(
  await verifySession(config, session.value, now + SESSION_TTL_SECONDS + 1),
  false,
  "an expired session must be rejected"
);

// --- forgery ---
assert.equal(await verifySession(config, undefined, now), false);
assert.equal(await verifySession(config, "", now), false);
assert.equal(await verifySession(config, "garbage", now), false);
assert.equal(await verifySession(config, `${now + 999}.`, now), false);
assert.equal(await verifySession(config, `${now + 999}.deadbeef`, now), false, "a bad signature must be rejected");

// Extending the expiry without re-signing must not validate.
const [, signature] = session.value.split(".");
const extended = `${now + SESSION_TTL_SECONDS * 10}.${signature}`;
assert.equal(await verifySession(config, extended, now), false, "expiry is covered by the signature");

// A session signed with a different secret must not validate.
const other = await issueSession({ accessKey: "k", sessionSecret: "different-secret" }, now);
assert.equal(await verifySession(config, other.value, now), false, "sessions must not be portable across secrets");

assert.equal(OPERATOR_COOKIE, "brain_operator");

console.log("Operator session verification: PASS");
