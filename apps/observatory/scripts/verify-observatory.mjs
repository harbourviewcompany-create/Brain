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

console.log("Brain Observatory structural verification: PASS");
