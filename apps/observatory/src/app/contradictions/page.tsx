import { Panel } from "@/components/Panel";
import { StatusBadge } from "@/components/StatusBadge";
import { BitemporalStamp } from "@/components/BitemporalStamp";
import { EmptyState } from "@/components/EmptyState";
import { MOCK_CONTRADICTIONS } from "@/lib/mock";
import Link from "next/link";

export default function ContradictionsPage() {
  const items = MOCK_CONTRADICTIONS;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Contradiction Review</h1>
        <p className="text-xs text-cockpit-muted">
          First-class conflicts. Both sides are retained. Resolution requires a human note.
        </p>
      </div>

      {items.length === 0 ? (
        <EmptyState
          title="No open contradictions"
          description="When beliefs acquire conflicting evidence, they appear here for review."
          schemaHint="Contradiction"
        />
      ) : (
        <div className="space-y-3">
          {items.map((c) => (
            <Panel key={c.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-cockpit-text">{c.id}</span>
                    <StatusBadge status={c.status} />
                  </div>
                  <div className="mt-1 text-[11px] text-cockpit-muted">
                    Beliefs:{" "}
                    {c.belief_ids.map((id) => (
                      <Link
                        key={id}
                        href={`/beliefs/${id}`}
                        className="mr-1 text-cockpit-accent hover:underline"
                      >
                        {id}
                      </Link>
                    ))}
                  </div>
                  <BitemporalStamp
                    validFrom={c.valid_from}
                    knownAt={c.known_at}
                    createdAt={c.created_at}
                  />
                </div>
                {c.investigation_pressure != null && (
                  <div className="text-right">
                    <div className="text-[10px] uppercase text-cockpit-muted">Pressure</div>
                    <div className="font-mono text-sm text-amber-300">
                      {c.investigation_pressure.toFixed(2)}
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded border border-green-500/30 bg-green-500/5 p-2">
                  <div className="text-[10px] uppercase text-green-400">Supporting</div>
                  <div className="mt-1 font-mono text-[11px] text-cockpit-text">
                    {c.supporting_evidence_ids.join(", ") || "—"}
                  </div>
                </div>
                <div className="rounded border border-red-500/30 bg-red-500/5 p-2">
                  <div className="text-[10px] uppercase text-red-400">Contradicting</div>
                  <div className="mt-1 font-mono text-[11px] text-cockpit-text">
                    {c.contradicting_evidence_ids.join(", ") || "—"}
                  </div>
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded border border-cockpit-border px-2 py-1 text-[11px] text-cockpit-muted hover:bg-cockpit-border/40"
                >
                  Mark under investigation
                </button>
                <button
                  type="button"
                  className="rounded border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-300"
                >
                  Request more evidence
                </button>
                <button
                  type="button"
                  className="rounded border border-cockpit-accent/40 bg-cockpit-accent/10 px-2 py-1 text-[11px] text-cockpit-accent"
                >
                  Resolve with note
                </button>
              </div>
            </Panel>
          ))}
        </div>
      )}
    </div>
  );
}
