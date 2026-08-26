"use client";

import { useCallback } from "react";
import Link from "next/link";
import { Panel } from "@/components/Panel";
import { StatusBadge } from "@/components/StatusBadge";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { EmptyState, ErrorState, LoadingState } from "@/components/ResourceState";
import { useBrainResource } from "@/hooks/useBrainResource";
import { listBeliefs } from "@/lib/api";
import type { Belief } from "@/types/brain";

function normalize(b: Partial<Belief> & { id: string; statement: string }): Belief {
  return {
    id: b.id,
    statement: b.statement,
    confidence: b.confidence ?? 0.5,
    state: (b.state as Belief["state"]) || "hypothesis",
    version: b.version ?? 1,
    valid_from: b.valid_from || new Date().toISOString(),
    created_at: b.created_at || new Date().toISOString(),
    evidence_ids: b.evidence_ids || [],
  };
}

export default function BeliefsPage() {
  const load = useCallback(async () => {
    const res = await listBeliefs();
    return {
      items: (res.items || []).map((b) => normalize(b)),
      source: res.source || "api",
    };
  }, []);

  const { status, data, error, reload } = useBrainResource(load);

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold">Belief Ledger</h1>
          <p className="text-xs text-cockpit-muted">
            Evidence-backed claims with explicit uncertainty. Contradictions are preserved.
          </p>
        </div>
        {status === "ready" && (
          <span className="font-mono text-[10px] text-cockpit-muted">
            {data.source} · {data.items.length} beliefs
          </span>
        )}
      </div>

      {status === "loading" && <LoadingState label="beliefs" />}
      {status === "error" && <ErrorState label="beliefs" error={error} onRetry={reload} />}

      {status === "ready" && data.items.length === 0 && (
        <EmptyState
          title="No beliefs yet"
          description="Beliefs appear here once evidence has been recorded against a claim."
          schemaHint="Belief · Evidence"
        />
      )}

      {status === "ready" && data.items.length > 0 && (
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-xs">
              <thead>
                <tr className="border-b border-cockpit-border text-[10px] uppercase text-cockpit-muted">
                  <th className="pb-2 pr-3 font-medium">Statement</th>
                  <th className="pb-2 pr-3 font-medium">State</th>
                  <th className="pb-2 pr-3 font-medium">Confidence</th>
                  <th className="pb-2 font-medium">Id</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((b) => (
                  <tr key={b.id} className="border-b border-cockpit-border/50">
                    <td className="py-2 pr-3">
                      <Link href={`/beliefs/${b.id}`} className="hover:text-cockpit-accent">
                        {b.statement}
                      </Link>
                    </td>
                    <td className="py-2 pr-3">
                      <StatusBadge status={b.state} />
                    </td>
                    <td className="py-2 pr-3">
                      <ConfidenceBar value={b.confidence} className="max-w-[120px]" />
                    </td>
                    <td className="py-2 font-mono text-[10px] text-cockpit-muted">
                      {b.id.slice(0, 8)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </div>
  );
}
