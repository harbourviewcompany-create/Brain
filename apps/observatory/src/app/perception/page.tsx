import { Panel } from "@/components/Panel";
import { MOCK_SIGNALS } from "@/lib/mock";
import Link from "next/link";

export default function PerceptionPage() {
  const signals = [...MOCK_SIGNALS].sort((a, b) => b.attention_score - a.attention_score);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Perception Inbox</h1>
        <p className="text-xs text-cockpit-muted">
          Signals ranked by attention_score (F-003). Click score for formula trace when live.
        </p>
      </div>

      <Panel>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-left text-xs">
            <thead>
              <tr className="border-b border-cockpit-border text-[10px] uppercase text-cockpit-muted">
                <th className="pb-2 pr-3">ID</th>
                <th className="pb-2 pr-3">Attention</th>
                <th className="pb-2 pr-3">Novelty</th>
                <th className="pb-2 pr-3">Urgency</th>
                <th className="pb-2 pr-3">Upside</th>
                <th className="pb-2 pr-3">Source</th>
                <th className="pb-2">Formula</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((s) => (
                <tr key={s.id} className="border-b border-cockpit-border/50">
                  <td className="py-2 pr-3 font-mono text-cockpit-text">{s.id}</td>
                  <td className="py-2 pr-3 font-mono text-cockpit-accent">
                    {s.attention_score.toFixed(2)}
                  </td>
                  <td className="py-2 pr-3 font-mono">{s.novelty.toFixed(2)}</td>
                  <td className="py-2 pr-3 font-mono">{s.urgency.toFixed(2)}</td>
                  <td className="py-2 pr-3 font-mono">{s.commercial_upside}</td>
                  <td className="py-2 pr-3 font-mono text-cockpit-muted">{s.source_id}</td>
                  <td className="py-2 font-mono text-[10px] text-cockpit-muted">
                    {s.formula_run_id || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 text-[11px] text-cockpit-muted">
          Promote to evidence or spawn curiosity from a live signal once write endpoints are wired.{" "}
          <Link href="/curiosity" className="text-cockpit-accent hover:underline">
            Curiosity queue →
          </Link>
        </div>
      </Panel>
    </div>
  );
}
