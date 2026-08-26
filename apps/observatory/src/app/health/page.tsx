"use client";

import { useCallback } from "react";
import { Panel } from "@/components/Panel";
import { ErrorState, LoadingState } from "@/components/ResourceState";
import { useBrainResource } from "@/hooks/useBrainResource";
import { apiBase, getHealth } from "@/lib/api";

/**
 * Health must never fall back to a fixture. A green "ok" rendered from mock
 * data while the runtime is unreachable is the single most misleading thing
 * this cockpit could show.
 */

const STATUS_COLOR: Record<string, string> = {
  ok: "text-cockpit-green",
  degraded: "text-cockpit-amber",
};

export default function HealthPage() {
  const load = useCallback(() => getHealth(), []);
  const { status, data, error, reload } = useBrainResource(load);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Runtime Health</h1>
        <p className="text-xs text-cockpit-muted">GET /health · API base {apiBase()}</p>
      </div>

      {status === "loading" && <LoadingState label="runtime health" />}
      {status === "error" && <ErrorState label="runtime health" error={error} onRetry={reload} />}

      {status === "ready" && (
        <Panel>
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-[10px] uppercase text-cockpit-muted">Status</dt>
              <dd className={`font-mono ${STATUS_COLOR[data.status] || "text-cockpit-red"}`}>
                {data.status}
              </dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase text-cockpit-muted">Version</dt>
              <dd className="font-mono">{data.version}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase text-cockpit-muted">Beliefs</dt>
              <dd className="font-mono">{data.beliefs}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase text-cockpit-muted">Events</dt>
              <dd className="font-mono">{data.events}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase text-cockpit-muted">Predictions</dt>
              <dd className="font-mono">{data.predictions}</dd>
            </div>
          </dl>
        </Panel>
      )}
    </div>
  );
}
