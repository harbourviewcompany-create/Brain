import fs from "node:fs";

const required = [
  "src/components/observatory/BrainObservatory.tsx",
  "src/components/observatory/BrainObservatory.module.css",
  "src/components/observatory/LivingCognitiveMachine.tsx",
  "src/components/observatory/LivingCognitiveMachine.module.css",
  "src/components/observatory/CognitiveField.tsx",
  "src/components/observatory/SystemPulse.tsx",
  "src/components/observatory/ThoughtInspector.tsx",
  "src/components/observatory/CognitionTimeline.tsx",
  "src/hooks/useBrainObservatory.ts",
  "src/lib/api.ts",
  "src/lib/living-brain.ts",
  "src/lib/observatory.ts",
  "src/types/living-brain.ts",
  "../../docs/observatory/BRAIN_OBSERVATORY.md",
];

for (const path of required) {
  if (!fs.existsSync(path)) throw new Error(`missing observatory artifact: ${path}`);
}

const implementation = required
  .filter((path) => path.startsWith("src/") && !path.endsWith(".css"))
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

const observatory = fs.readFileSync("src/components/observatory/BrainObservatory.tsx", "utf8");
if (!observatory.includes("LivingCognitiveMachine")) {
  throw new Error("root observatory must mount the selected living cognitive machine interface");
}
if (!observatory.includes("CognitiveField")) {
  throw new Error("existing cognitive graph inspection must remain available");
}

const apiClient = fs.readFileSync("src/lib/api.ts", "utf8");
for (const contract of [
  "submitBrainCommand",
  'request<BrainCommandReceipt>("/signals"',
  '"/evidence"',
  '"/learning-events"',
  '"/working-memory"',
]) {
  if (!apiClient.includes(contract)) throw new Error(`living Brain API contract missing: ${contract}`);
}
if (!apiClient.includes("operator_command: true") || !apiClient.includes("command_mode: mode")) {
  throw new Error("operator command history must be explicitly marked in durable signal metadata");
}

const hook = fs.readFileSync("src/hooks/useBrainObservatory.ts", "utf8");
for (const liveRead of ["listEvidence()", "listLearningEvents()", "getWorkingMemoryObservation()"]) {
  if (!hook.includes(liveRead)) throw new Error(`living Brain poll is missing ${liveRead}`);
}
if (!hook.includes("Promise.allSettled")) {
  throw new Error("partial read failures must not blank successful Observatory state");
}

const livingProjection = fs.readFileSync("src/lib/living-brain.ts", "utf8");
if (!livingProjection.includes("lexical * 0.7 + reliability * 0.3")) {
  throw new Error("evidence retrieval projection must keep its explicit transparent scoring formula");
}
if (livingProjection.includes("MultiSystemMemory.retrieve_episodes(")) {
  throw new Error("frontend must not claim unwired production MultiSystemMemory retrieval");
}

const upstream = fs.readFileSync("src/lib/brain-upstream.ts", "utf8");
if (!upstream.includes("getVercelOidcToken") || !upstream.includes("Authorization") && !upstream.includes("authorization")) {
  throw new Error("Vercel OIDC BFF authentication contract is missing");
}

const page = fs.readFileSync("src/app/page.tsx", "utf8");
if (!page.includes("BrainObservatory")) throw new Error("root route is not the Brain Observatory");

// Optional operator gate: when secrets are set, sessions are required; when unset, open.
if (!fs.existsSync("src/middleware.ts")) {
  throw new Error("src/middleware.ts is missing");
}
const middleware = fs.readFileSync("src/middleware.ts", "utf8");
if (!middleware.includes("verifySession")) {
  throw new Error("middleware must be able to verify an operator session when configured");
}
if (!/matcher/.test(middleware) || !middleware.includes("_next/static")) {
  throw new Error("middleware matcher must cover app routes except static build output");
}
if (!middleware.includes("operatorSessionConfig")) {
  throw new Error("middleware must read operatorSessionConfig to decide open vs gated");
}
if (middleware.includes("operator_auth_not_configured") && middleware.includes("return unauthorized(request, \"operator_auth_not_configured\"")) {
  throw new Error("middleware must not fail closed when operator auth is unconfigured");
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
