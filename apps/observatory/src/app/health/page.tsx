"use client";

import { useEffect, useState } from "react";
import { Panel } from "@/components/Panel";
import { apiBase, getHealth } from "@/lib/api";
import type { HealthResponse } from "@/types/brain";
import { MOCK_HEALTH } from "@/lib/mock";

export default function HealthPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e) => {
        setError(String(e.message || e));
        setHealth(MOCK_HEALTH);
      });
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Runtime Health</h1>
        <p className="text-xs text-cockpit-muted">GET /health · API base {apiBase()}</p>
      </div>

      <Panel>
        {error && (
          <div className="mb-3 rounded border border-amber-500/40 bg-amber-500/10 px-2 py-1.5 text-[11px] text-amber-300">
            Live API unreachable — showing mock. {error}
          </div>
        )}
        {health ? (
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-[10px] uppercase text-cockpit-muted">Status</dt>
              <dd className="font-mono text-green-400">{health.status}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase text-cockpit-muted">Version</dt>
              <dd className="font-mono">{health.version}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase text-cockpit-muted">Beliefs</dt>
              <dd className="font-mono">{health.beliefs}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase text-cockpit-muted">Events</dt>
              <dd className="font-mono">{health.events}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase text-cockpit-muted">Predictions</dt>
              <dd className="font-mono">{health.predictions}</dd>
            </div>
          </dl>
        ) : (
          <p className="text-xs text-cockpit-muted">Loading…</p>
        )}
      </Panel>
    </div>
  );
}
