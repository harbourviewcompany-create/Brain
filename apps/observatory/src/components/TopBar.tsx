"use client";

import { useEffect, useState } from "react";
import { apiBase, getHealth, isApiConfigured } from "@/lib/api";
import type { HealthResponse } from "@/types/brain";

export function TopBar() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [live, setLive] = useState(false);
  const [checked, setChecked] = useState(false);
  const operator = process.env.NEXT_PUBLIC_OPERATOR_ID || "tyler";

  useEffect(() => {
    if (!isApiConfigured()) {
      setLive(false);
      setChecked(true);
      return;
    }
    getHealth()
      .then((h) => {
        setHealth(h);
        setLive(true);
      })
      .catch(() => {
        setLive(false);
      })
      .finally(() => {
        setChecked(true);
      });
  }, []);

  const status = live
    ? "API live"
    : isApiConfigured()
      ? checked
        ? "API unreachable"
        : "checking API"
      : "API not configured";

  return (
    <header className="flex h-11 shrink-0 items-center justify-between border-b border-cockpit-border bg-cockpit-panel px-3">
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold tracking-wide text-cockpit-text">
          Brain Control Plane
        </span>
        <span
          className={`rounded px-1.5 py-0.5 font-mono text-[10px] ${
            live ? "bg-green-500/15 text-green-400" : "bg-amber-500/15 text-amber-400"
          }`}
        >
          {status}
        </span>
        <span className="hidden max-w-[280px] truncate font-mono text-[10px] text-cockpit-muted sm:inline">
          {apiBase()} → upstream (server)
        </span>
      </div>
      <div className="flex items-center gap-4 text-[11px] text-cockpit-muted">
        <span title="Beliefs">B {health?.beliefs ?? 0}</span>
        <span title="Events">E {health?.events ?? 0}</span>
        <span title="Predictions">P {health?.predictions ?? 0}</span>
        <span className="hidden rounded border border-cockpit-border px-2 py-0.5 font-mono sm:inline">
          op:{operator}
        </span>
      </div>
    </header>
  );
}
