/**
 * Sovereign Brain — self-hosted cognition inside the Observatory process.
 *
 * No Railway. No Fly. No external API host.
 * When BRAIN_API_URL is unset, the BFF serves this kernel so the machine
 * thinks on Vercel alone (Path B clean-start / zero external host).
 *
 * State is process-local (survives warm serverless instances; re-seeds on cold start).
 * Vercel Cron can POST /api/brain/tick to advance cycles.
 */

export type SovereignBelief = {
  id: string;
  statement: string;
  confidence: number;
  state: string;
  created_at: string;
  updated_at: string;
  version: number;
  evidence_ids: string[];
  unknowns?: string[];
};

export type SovereignStatus = {
  status: "ok" | "degraded";
  mode: "sovereign";
  version: string;
  ticks: number;
  total_processed: number;
  belief_count: number;
  working_memory_size: number;
  circadian_phase: string;
  focus: string | null;
  open_curiosity: number;
  self_model_phase: string;
  persistence: "in-process";
  continuous_daemon: false;
  bounded_cognition: true;
};

type Store = {
  beliefs: Map<string, SovereignBelief>;
  wm: string[];
  ticks: number;
  processed: number;
  focus: string | null;
  curiosity: string[];
  selfPhase: string;
  phase: "wake" | "focus" | "reflect" | "rest";
  seeded: boolean;
};

const FOUNDATIONAL: Array<{ statement: string; confidence: number; unknowns: string[] }> = [
  {
    statement: "I am a cognitive machine that maintains beliefs under uncertainty",
    confidence: 0.92,
    unknowns: ["What is my durable identity across deploys?"],
  },
  {
    statement: "Attention is a scarce resource; novelty and contradiction raise priority",
    confidence: 0.88,
    unknowns: ["Which external signals are still unavailable?"],
  },
  {
    statement: "Endogenous thought can proceed without an external host",
    confidence: 0.85,
    unknowns: ["When should persistence be upgraded to Turso?"],
  },
  {
    statement: "Observatory and runtime are one sovereign surface on Vercel",
    confidence: 0.9,
    unknowns: ["Operator goals not yet stated"],
  },
];

const g = globalThis as unknown as { __sovereignBrain?: Store };

function store(): Store {
  if (!g.__sovereignBrain) {
    g.__sovereignBrain = {
      beliefs: new Map(),
      wm: [],
      ticks: 0,
      processed: 0,
      focus: null,
      curiosity: [],
      selfPhase: "observing",
      phase: "wake",
      seeded: false,
    };
  }
  return g.__sovereignBrain;
}

function nowIso(): string {
  return new Date().toISOString();
}

function uid(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

export function ensureSeeded(): number {
  const s = store();
  if (s.seeded) return 0;
  const t = nowIso();
  for (const f of FOUNDATIONAL) {
    const id = uid("sb");
    s.beliefs.set(id, {
      id,
      statement: f.statement,
      confidence: f.confidence,
      state: "established",
      created_at: t,
      updated_at: t,
      version: 1,
      evidence_ids: [],
      unknowns: f.unknowns,
    });
    for (const u of f.unknowns) s.curiosity.push(u);
  }
  s.seeded = true;
  s.focus = FOUNDATIONAL[0].statement;
  s.wm = FOUNDATIONAL.map((f) => f.statement).slice(0, 4);
  s.selfPhase = "revised";
  return FOUNDATIONAL.length;
}

export function tick(maxItems = 1): Record<string, unknown> {
  ensureSeeded();
  const s = store();
  const n = Math.max(1, Math.min(5, maxItems));
  let processed = 0;

  for (let i = 0; i < n; i++) {
    s.ticks += 1;
    processed += 1;
    s.processed += 1;

    // Endogenous cycle: raise or invent a belief from open curiosity
    const q = s.curiosity[s.ticks % Math.max(1, s.curiosity.length)] ?? "What should I attend to next?";
    const id = uid("sb");
    const t = nowIso();
    const statement = `Hypothesis: ${q.replace(/\?$/, "")} is actionable under current constraints`;
    s.beliefs.set(id, {
      id,
      statement,
      confidence: 0.35 + (s.ticks % 40) / 100,
      state: "hypothesis",
      created_at: t,
      updated_at: t,
      version: 1,
      evidence_ids: [],
      unknowns: [q],
    });
    s.focus = statement;
    s.wm = [statement, ...s.wm].slice(0, 7);
    s.phase = (["wake", "focus", "reflect", "rest"] as const)[s.ticks % 4];
    if (s.ticks % 5 === 0) s.selfPhase = "revised";
  }

  return {
    processed_this_call: processed,
    ticks: s.ticks,
    total_processed: s.processed,
    endogenous: true,
    cycles: [
      {
        attention_score: 0.5 + (s.ticks % 50) / 100,
        working_memory_size: s.wm.length,
      },
    ],
  };
}

export function listBeliefs(): SovereignBelief[] {
  ensureSeeded();
  return [...store().beliefs.values()].sort((a, b) => b.confidence - a.confidence);
}

export function status(): SovereignStatus {
  ensureSeeded();
  const s = store();
  return {
    status: "ok",
    mode: "sovereign",
    version: "0.9.0-sovereign",
    ticks: s.ticks,
    total_processed: s.processed,
    belief_count: s.beliefs.size,
    working_memory_size: s.wm.length,
    circadian_phase: s.phase,
    focus: s.focus,
    open_curiosity: s.curiosity.length,
    self_model_phase: s.selfPhase,
    persistence: "in-process",
    continuous_daemon: false,
    bounded_cognition: true,
  };
}

export function health(): Record<string, unknown> {
  const st = status();
  return {
    status: "ok",
    version: st.version,
    database: "in-process",
    persistence: "sovereign",
    bounded_cognition: true,
    continuous_daemon: false,
    heartbeat: {
      ticks: st.ticks,
      total_processed: st.total_processed,
      working_memory_size: st.working_memory_size,
    },
  };
}

/** Route sovereign paths without an external upstream. */
export function handleSovereign(
  pathSegments: string[],
  method: string,
  bodyText?: string | null,
): Response | null {
  const head = pathSegments[0] || "";
  ensureSeeded();

  if (head === "health" || head === "ready") {
    return Response.json(health(), { headers: { "cache-control": "no-store" } });
  }

  if (head === "beliefs" && method === "GET") {
    return Response.json(listBeliefs(), { headers: { "cache-control": "no-store" } });
  }

  if ((head === "tick" || (head === "runner" && pathSegments[1] === "tick")) && method === "POST") {
    let maxItems = 1;
    try {
      if (bodyText) {
        const parsed = JSON.parse(bodyText) as { max_items?: number };
        if (parsed.max_items) maxItems = parsed.max_items;
      }
    } catch {
      /* ignore */
    }
    return Response.json(tick(maxItems), { headers: { "cache-control": "no-store" } });
  }

  if (head === "organism" && method === "GET") {
    const st = status();
    return Response.json(
      {
        self_model_phase: st.self_model_phase,
        open_curiosity: st.open_curiosity,
        last_focus: st.focus,
        workspace: { items: store().wm, workspace_items: store().wm },
        goals: ["Maintain coherent beliefs", "Reduce open curiosity", "Stay sovereign on Vercel"],
      },
      { headers: { "cache-control": "no-store" } },
    );
  }

  if (head === "working-memory" && method === "GET") {
    return Response.json(
      { size: store().wm.length, capacity: 12, items: store().wm },
      { headers: { "cache-control": "no-store" } },
    );
  }

  if (head === "curiosity" && method === "GET") {
    return Response.json(
      store().curiosity.map((title, i) => ({
        id: `cu-sov-${i}`,
        title,
        status: "open",
        priority: 0.5 + (i % 5) / 10,
        created_at: nowIso(),
      })),
      { headers: { "cache-control": "no-store" } },
    );
  }

  // Empty collections for surfaces we do not synthesize yet
  if (
    ["predictions", "signals", "evidence", "contradictions", "opportunities", "approvals", "sources", "outcomes", "learning-events"].includes(
      head,
    ) &&
    method === "GET"
  ) {
    return Response.json([], { headers: { "cache-control": "no-store" } });
  }

  return null;
}
