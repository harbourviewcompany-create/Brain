/**
 * Durable snapshot: Postgres when a URL is present, else Vercel Blob.
 * Never throws into the request path.
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

type PersistMode = "in-process" | "postgres" | "blob";

type PersistState = {
  ready: boolean;
  mode: PersistMode;
  lastError: string | null;
  lastSavedAt: string | null;
  urlConfigured: boolean;
  blobConfigured: boolean;
};

const persist: PersistState = {
  ready: false,
  mode: "in-process",
  lastError: null,
  lastSavedAt: null,
  urlConfigured: false,
  blobConfigured: false,
};

const BLOB_KEY = "sovereign/snapshot-live.json";

function databaseUrl(): string {
  const keys = [
    "DATABASE_URL",
    "BRAIN_WORKER_DATABASE_URL",
    "POSTGRES_URL",
    "POSTGRES_PRISMA_URL",
    "POSTGRES_URL_NON_POOLING",
    "NEON_DATABASE_URL",
  ];
  for (const key of keys) {
    const value = (process.env[key] || "").trim();
    if (value) return value;
  }
  return "";
}

function blobToken(): string {
  return (process.env.BLOB_READ_WRITE_TOKEN || process.env.brain_READ_WRITE_TOKEN || "").trim();
}

export function persistenceStatus(): PersistState {
  persist.urlConfigured = Boolean(databaseUrl());
  persist.blobConfigured = Boolean(blobToken());
  return { ...persist };
}

type Sql = ((strings: TemplateStringsArray, ...values: unknown[]) => Promise<Record<string, unknown>[]>) & {
  query: (text: string, params?: unknown[]) => Promise<Record<string, unknown>[]>;
};

async function pg(): Promise<Sql | null> {
  const url = databaseUrl();
  persist.urlConfigured = Boolean(url);
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

async function loadBlob(): Promise<SnapshotPayload | null> {
  const token = blobToken();
  persist.blobConfigured = Boolean(token);
  if (!token) return null;
  try {
    const { list } = await import("@vercel/blob");
    const listed = await list({ prefix: BLOB_KEY, limit: 1, token });
    const hit = listed.blobs[0];
    if (!hit) {
      persist.mode = "blob";
      persist.ready = true;
      persist.lastError = null;
      return null;
    }
    const res = await fetch(hit.url);
    if (!res.ok) throw new Error(`blob_http_${res.status}`);
    persist.mode = "blob";
    persist.ready = true;
    persist.lastError = null;
    return (await res.json()) as SnapshotPayload;
  } catch (err) {
    persist.lastError = err instanceof Error ? err.message : "blob_load_failed";
    return null;
  }
}

async function saveBlob(payload: SnapshotPayload): Promise<boolean> {
  const token = blobToken();
  if (!token) return false;
  try {
    const { put } = await import("@vercel/blob");
    await put(BLOB_KEY, JSON.stringify(payload), {
      access: "public",
      addRandomSuffix: false,
      allowOverwrite: true,
      contentType: "application/json",
      token,
    });
    persist.mode = "blob";
    persist.ready = true;
    persist.lastError = null;
    persist.lastSavedAt = new Date().toISOString();
    return true;
  } catch (err) {
    persist.lastError = err instanceof Error ? err.message : "blob_save_failed";
    return false;
  }
}

export async function loadSnapshot(): Promise<SnapshotPayload | null> {
  const sql = await pg();
  if (sql) {
    try {
      await ensureSchema(sql);
      const rows = await sql`SELECT payload, ticks FROM sovereign_snapshot WHERE id = 'live' LIMIT 1`;
      persist.mode = "postgres";
      persist.ready = true;
      persist.lastError = null;
      const row = rows[0];
      if (!row || !row.payload) return null;
      return row.payload as SnapshotPayload;
    } catch (err) {
      persist.lastError = err instanceof Error ? err.message : "load_failed";
    }
  }
  return loadBlob();
}

export async function saveSnapshot(payload: SnapshotPayload): Promise<boolean> {
  const sql = await pg();
  if (sql) {
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
    }
  }
  return saveBlob(payload);
}

export async function appendEvent(tick: number, eventType: string, payload: Record<string, unknown>): Promise<void> {
  const sql = await pg();
  if (!sql) return;
  try {
    await sql.query(`INSERT INTO sovereign_event (tick, event_type, payload) VALUES ($1, $2, $3::jsonb)`, [
      tick,
      eventType,
      JSON.stringify(payload),
    ]);
  } catch {
    /* best-effort */
  }
}
