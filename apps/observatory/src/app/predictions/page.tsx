"use client";

import { useCallback } from "react";
import { Panel } from "@/components/Panel";
import { EmptyState, ErrorState, LoadingState } from "@/components/ResourceState";
import { useBrainResource } from "@/hooks/useBrainResource";
import { listPredictions } from "@/lib/api";
import type { Prediction } from "@/types/brain";

export default function PredictionsPage() {
  const load = useCallback(async () => {
    const res = await listPredictions();
    return (res.items || []) as Prediction[];
  }, []);

  const { status, data, error, reload } = useBrainResource(load);

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-lg font-semibold">Predictions</h1>
          <p className="text-xs text-cockpit-muted">
            Scored forecasts with calibration provenance.
          </p>
        </div>
        {status === "ready" && (
          <span className="font-mono text-[10px] text-cockpit-muted">
            {data.length} predictions
          </span>
        )}
      </div>

      {status === "loading" && <LoadingState label="predictions" />}
      {status === "error" && <ErrorState label="predictions" error={error} onRetry={reload} />}

      {status === "ready" && data.length === 0 && (
        <EmptyState
          title="No predictions yet"
          description="Forecasts appear here once the runtime records one against a belief or action."
          schemaHint="Prediction · Attribution"
        />
      )}

      {status === "ready" && data.length > 0 && (
        <Panel>
          <ul className="space-y-2 text-xs">
            {data.map((p) => (
              <li
                key={p.id}
                className="rounded border border-cockpit-border/80 bg-cockpit-bg/40 px-3 py-2"
              >
                <div className="text-cockpit-text">{p.statement}</div>
                <div className="mt-1 flex flex-wrap gap-3 font-mono text-[10px] text-cockpit-muted">
                  <span>id {String(p.id).slice(0, 8)}</span>
                  {"expected_value" in p && (
                    <span>ev {(p as { expected_value?: number }).expected_value}</span>
                  )}
                  {"confidence" in p && (
                    <span>conf {(p as { confidence?: number }).confidence}</span>
                  )}
                  {"status" in p && <span>{String((p as { status?: string }).status)}</span>}
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}
