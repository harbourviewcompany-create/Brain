import { Panel } from "@/components/Panel";
import { StatusBadge } from "@/components/StatusBadge";
import { MOCK_OPPORTUNITIES } from "@/lib/mock";

export default function OpportunitiesPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Opportunity Board</h1>
        <p className="text-xs text-cockpit-muted">
          Scored opportunities with money-spine fields (net, time-to-cash, fee protection, disposition).
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {MOCK_OPPORTUNITIES.map((o) => (
          <Panel key={o.id}>
            <div className="flex items-start justify-between gap-2">
              <StatusBadge status={o.status} />
              <span className="font-mono text-[10px] text-cockpit-muted">{o.id}</span>
            </div>
            <h3 className="mt-2 text-sm font-medium text-cockpit-text">{o.title}</h3>
            <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
              <dt className="text-cockpit-muted">Expected</dt>
              <dd className="font-mono text-right">{o.expected_value}</dd>
              <dt className="text-cockpit-muted">Net</dt>
              <dd className="font-mono text-right">{o.expected_net_value ?? "—"}</dd>
              <dt className="text-cockpit-muted">Time to cash</dt>
              <dd className="font-mono text-right">
                {o.time_to_cash_days != null ? `${o.time_to_cash_days}d` : "—"}
              </dd>
              <dt className="text-cockpit-muted">Conversion</dt>
              <dd className="font-mono text-right">
                {o.conversion_probability != null
                  ? `${(o.conversion_probability * 100).toFixed(0)}%`
                  : "—"}
              </dd>
              <dt className="text-cockpit-muted">Fee protected</dt>
              <dd className="font-mono text-right">{o.fee_protected ? "yes" : "—"}</dd>
              <dt className="text-cockpit-muted">Disposition</dt>
              <dd className="font-mono text-right">{o.disposition ?? "—"}</dd>
            </dl>
          </Panel>
        ))}
      </div>
    </div>
  );
}
