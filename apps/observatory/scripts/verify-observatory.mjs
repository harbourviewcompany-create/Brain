import fs from "node:fs";

const required = [
  "src/components/observatory/BrainObservatory.tsx",
  "src/components/observatory/CognitiveField.tsx",
  "src/components/observatory/SystemPulse.tsx",
  "src/components/observatory/ThoughtInspector.tsx",
  "src/components/observatory/CognitionTimeline.tsx",
  "src/hooks/useBrainObservatory.ts",
  "src/lib/observatory.ts",
  "../../docs/observatory/BRAIN_OBSERVATORY.md",
];

for (const path of required) {
  if (!fs.existsSync(path)) throw new Error(`missing observatory artifact: ${path}`);
}

const implementation = required
  .filter((path) => path.startsWith("src/"))
  .map((path) => fs.readFileSync(path, "utf8"))
  .join("\n");

if (implementation.includes("@/lib/mock") || implementation.includes("MOCK_")) {
  throw new Error("observatory implementation must not import mock data");
}
if (implementation.includes("Math.random(")) {
  throw new Error("observatory spatial state must be deterministic; Math.random is forbidden");
}
if (!implementation.includes("/api/brain")) {
  throw new Error("observatory must remain on the browser-safe same-origin BFF boundary");
}

const upstream = fs.readFileSync("src/lib/brain-upstream.ts", "utf8");
if (!upstream.includes("getVercelOidcToken") || !upstream.includes("Authorization") && !upstream.includes("authorization")) {
  throw new Error("Vercel OIDC BFF authentication contract is missing");
}

const page = fs.readFileSync("src/app/page.tsx", "utf8");
if (!page.includes("BrainObservatory")) throw new Error("root route is not the Brain Observatory");

// The BFF attaches the server-side Brain API key to everything it forwards, so
// an unauthenticated caller reaching it is an unauthenticated caller against the
// Brain. Middleware guarding it is a release requirement, not a nicety.
if (!fs.existsSync("src/middleware.ts")) {
  throw new Error("src/middleware.ts is missing; the Brain BFF would be an open relay");
}
const middleware = fs.readFileSync("src/middleware.ts", "utf8");
if (!middleware.includes("verifySession")) {
  throw new Error("middleware must verify an operator session before proxying to the Brain");
}
if (!/matcher/.test(middleware) || !middleware.includes("_next/static")) {
  throw new Error("middleware matcher must guard every route except static build output");
}
if (!middleware.includes("operator_auth_not_configured")) {
  throw new Error("middleware must fail closed when operator auth is unconfigured");
}

// Live views must never seed themselves with fabricated records: an operator
// cannot tell invented beliefs from real ones once they are rendered the same.
for (const route of [
  "src/app/beliefs/page.tsx",
  "src/app/predictions/page.tsx",
  "src/app/approvals/page.tsx",
  "src/app/health/page.tsx",
]) {
  const source = fs.readFileSync(route, "utf8");
  if (source.includes("MOCK_") || source.includes("@/lib/mock")) {
    throw new Error(`${route} renders mock data; live routes must show real state only`);
  }
}

console.log("Brain Observatory structural verification: PASS");
