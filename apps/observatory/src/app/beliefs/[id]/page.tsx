import Link from "next/link";
import { notFound } from "next/navigation";
import { Panel } from "@/components/Panel";
import { StatusBadge } from "@/components/StatusBadge";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { BitemporalStamp } from "@/components/BitemporalStamp";
import { MOCK_BELIEFS, MOCK_CONTRADICTIONS } from "@/lib/mock";

export default async function BeliefDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const belief = MOCK_BELIEFS.find((b) => b.id === id);
  if (!belief) notFound();

  const contradictions = MOCK_CONTRADICTIONS.filter((c) =>
    c.belief_ids.includes(belief.id)
  );

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link href="/beliefs" className="text-[11px] text-cockpit-accent hover:underline">
            ← Belief Ledger
          </Link>
          <h1 className="mt-1 text-lg font-semibold text-cockpit-text">{belief.statement}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={belief.state} />
            <span className="font-mono text-[10px] text-cockpit-muted">{belief.id}</span>
            <BitemporalStamp
              validFrom={belief.valid_from}
              knownAt={belief.known_at}
              createdAt={belief.created_at}
            />
          </div>
        </div>
        <div className="w-40">
          <div className="text-[10px] uppercase text-cockpit-muted">Confidence</div>
          <ConfidenceBar value={belief.confidence} />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Panel title="Supporting Evidence">
          <p className="text-xs text-cockpit-muted">
            {(belief.evidence_ids?.length || 0) === 0
              ? "No supporting evidence linked."
              : `${belief.evidence_ids!.length} evidence item(s): ${belief.evidence_ids!.join(", ")}`}
          </p>
          <p className="mt-2 text-[10px] text-cockpit-muted/70">
            Use POST /learn with supports=true to add evidence.
          </p>
        </Panel>
        <Panel title="Contradicting Evidence">
          <p className="text-xs text-cockpit-muted">
            Contradictions are never deleted or averaged away.
          </p>
          {contradictions.length === 0 ? (
            <p className="mt-2 text-xs text-cockpit-muted">No open contradictions.</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {contradictions.map((c) => (
                <li key={c.id}>
                  <Link
                    href="/contradictions"
                    className="flex items-center gap-2 text-xs text-red-300 hover:underline"
                  >
                    <StatusBadge status={c.status} />
                    <span className="font-mono">{c.id}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <Panel title="Actions">
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded border border-cockpit-border px-2 py-1 text-cockpit-muted">
            Add evidence → POST /learn
          </span>
          <Link
            href="/contradictions"
            className="rounded border border-red-500/40 bg-red-500/10 px-2 py-1 text-red-300"
          >
            Open Contradiction Review
          </Link>
        </div>
      </Panel>
    </div>
  );
}
