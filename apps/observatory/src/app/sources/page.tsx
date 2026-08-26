import { Panel } from "@/components/Panel";
import { StatusBadge } from "@/components/StatusBadge";
import { MOCK_SOURCES } from "@/lib/mock";

export default function SourcesPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Sources & Sensors</h1>
        <p className="text-xs text-cockpit-muted">
          Trust, status, and cognitive-immune quarantine visibility.
        </p>
      </div>

      <Panel>
        <ul className="divide-y divide-cockpit-border">
          {MOCK_SOURCES.map((s) => (
            <li key={s.id} className="flex flex-wrap items-start justify-between gap-3 py-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-cockpit-text">{s.name}</span>
                  <StatusBadge status={s.status} />
                </div>
                <div className="mt-0.5 font-mono text-[10px] text-cockpit-muted">
                  {s.id} · {s.kind}
                </div>
                {s.quarantine_reason && (
                  <div className="mt-1 max-w-lg text-[11px] text-red-300/90">
                    {s.quarantine_reason}
                  </div>
                )}
              </div>
              <div className="text-right">
                <div className="text-[10px] uppercase text-cockpit-muted">Trust</div>
                <div className="font-mono text-sm">{s.trust_score.toFixed(2)}</div>
              </div>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
