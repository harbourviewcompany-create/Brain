/**
 * Optional Postgres snapshot for the sovereign kernel.
 * No-ops when DATABASE_URL is unset or the driver/query fails.
 */
export type SnapshotPayload = {
  version: string;
  ticks: number;
  processed: number;
  identityDigest: string;
  phase: string;
  focus: string | null;
  goals: string[];
  goalLock: { content: string; untilTick: number } | null;
  lastDelta: string;
  lastCycle: Record<string, unknown> | null;
  selfPhase: string;
  sleepPressure: number;
  stress: number;
  wm: string[];
  beliefs: unknown[];
  evidence: unknown[];
  predictions: unknown[];
  outcomes: unknown[];
  signals: unknown[];
  contradictions: unknown[];
  curiosity: unknown[];
  learning: unknown[];
  edges: unknown[];
};

type PersistState = {
  ready: boolean;
  mode: "in-process" | "postgres";
  lastError: string | null;
  lastSavedAt: string | null;
};

const persist: PersistState = {
  ready: false,
  mode: "in-process",
  lastError: null,
  lastSavedAt: null,
};

function databaseUrl(): string {
  return (process.env.DATABASE_URL || process.env.BRAIN_WORKER_DATABASE_URL || "").trim();
}

export function persistenceStatus(): PersistState {
  return { ...persist, ready: persist.ready || persist.mode === "postgres" };
}

type Sql = ((strings: TemplateStringsArray, ...values: unknown[]) => Promise<Record<string, unknown>[]>) & {
  query: (text: string, params?: unknown[]) => Promise<Record<string, unknown>[]>;
};

async function client(): Promise<Sql | null> {
  const url = databaseUrl();
  if (!url) return null;
  try {
    const mod = await import("@neondatabase/serverless");
    return mod.neon(url) as unknown as Sql;
  } catch (err) {
    persist.lastError = err instanceof Error ? err.message : "driver_unavailable";
    return null;
  }
}

async function ensureSchema(sql: Sql): Promise<void> {
  await sql`
    CREATE TABLE IF NOT EXISTS sovereign_snapshot (
      id text PRIMARY KEY,
      version text NOT NULL,
      ticks integer NOT NULL,
      identity_digest text,
      payload jsonb NOT NULL,
      updated_at timestamptz NOT NULL DEFAULT now()
    )
  `;
  await sql`
    CREATE TABLE IF NOT EXISTS sovereign_event (
      id bigserial PRIMARY KEY,
      tick integer NOT NULL,
      event_type text NOT NULL,
      payload jsonb NOT NULL,
      occurred_at timestamptz NOT NULL DEFAULT now()
    )
  `;
}

export async function loadSnapshot(): Promise<SnapshotPayload | null> {
  const sql = await client();
  if (!sql) return null;
  try {
    await ensureSchema(sql);
    const rows = await sql`SELECT payload, ticks FROM sovereign_snapshot WHERE id = 'live' LIMIT 1`;
    const row = rows[0];
    if (!row || !row.payload) {
      persist.mode = "postgres";
      persist.ready = true;
      persist.lastError = null;
      return null;
    }
    persist.mode = "postgres";
    persist.ready = true;
    persist.lastError = null;
    return row.payload as SnapshotPayload;
  } catch (err) {
    persist.lastError = err instanceof Error ? err.message : "load_failed";
    persist.mode = "in-process";
    return null;
  }
}

export async function saveSnapshot(payload: SnapshotPayload): Promise<boolean> {
  const sql = await client();
  if (!sql) return false;
  try {
    await ensureSchema(sql);
    await sql.query(
      `INSERT INTO sovereign_snapshot (id, version, ticks, identity_digest, payload, updated_at)
       VALUES ('live', $1, $2, $3, $4::jsonb, now())
       ON CONFLICT (id) DO UPDATE SET
         version = EXCLUDED.version,
         ticks = EXCLUDED.ticks,
         identity_digest = EXCLUDED.identity_digest,
         payload = EXCLUDED.payload,
         updated_at = now()
       WHERE sovereign_snapshot.ticks <= EXCLUDED.ticks`,
      [payload.version, payload.ticks, payload.identityDigest, JSON.stringify(payload)],
    );
    persist.mode = "postgres";
    persist.ready = true;
    persist.lastError = null;
    persist.lastSavedAt = new Date().toISOString();
    return true;
  } catch (err) {
    persist.lastError = err instanceof Error ? err.message : "save_failed";
    return false;
  }
}

export async function appendEvent(tick: number, eventType: string, payload: Record<string, unknown>): Promise<void> {
  const sql = await client();
  if (!sql) return;
  try {
    await sql.query(
      `INSERT INTO sovereign_event (tick, event_type, payload) VALUES ($1, $2, $3::jsonb)`,
      [tick, eventType, JSON.stringify(payload)],
    );
  } catch {
    /* snapshot is the source of truth */
  }
}
