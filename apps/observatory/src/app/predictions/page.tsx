"use client";

import { useEffect, useState } from "react";
import { Panel } from "@/components/Panel";
import { MOCK_PREDICTIONS } from "@/lib/mock";
import { isApiConfigured, listPredictions } from "@/lib/api";
import type { Prediction } from "@/types/brain";

export default function PredictionsPage() {
  const [items, setItems] = useState<Prediction[]>(MOCK_PREDICTIONS as Prediction[]);
  const [source, setSource] = useState("mock");

  useEffect(() => {
    if (!isApiConfigured()) return;
    listPredictions()
      .then((res) => {
        if (res.items) {
          setItems(res.items as Prediction[]);
          setSource("api");
        }
      })
      .catch(() => setSource("mock"));
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-lg font-semibold">Predictions</h1>
          <p className="text-xs text-cockpit-muted">Scored forecasts with calibration provenance.</p>
        </div>
        <span className="font-mono text-[10px] text-cockpit-muted">{source}</span>
      </div>
      <Panel>
        <ul className="space-y-2 text-xs">
          {items.length === 0 && (
            <li className="text-cockpit-muted">No predictions yet.</li>
          )}
          {items.map((p) => (
            <li
              key={p.id}
              className="rounded border border-cockpit-border/80 bg-cockpit-bg/40 px-3 py-2"
            >
              <div className="text-cockpit-text">{p.statement}</div>
              <div className="mt-1 flex flex-wrap gap-3 font-mono text-[10px] text-cockpit-muted">
                <span>id {String(p.id).slice(0, 8)}</span>
                {"expected_value" in p && <span>ev {(p as { expected_value?: number }).expected_value}</span>}
                {"confidence" in p && <span>conf {(p as { confidence?: number }).confidence}</span>}
                {"status" in p && <span>{String((p as { status?: string }).status)}</span>}
              </div>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
