import { Panel } from "@/components/Panel";
import { StatusBadge } from "@/components/StatusBadge";
import { MOCK_ACCEPTANCE } from "@/lib/mock";

export default function GoHoldPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">GO / HOLD</h1>
        <p className="text-xs text-cockpit-muted">
          Acceptance reports. HOLD blocks external-action claims system-wide.
        </p>
      </div>

      <div className="space-y-3">
        {MOCK_ACCEPTANCE.map((r) => (
          <Panel key={r.id}>
            <div className="flex items-center gap-2">
              <StatusBadge status={r.verdict} />
              <span className="font-mono text-xs">{r.ticket_id}</span>
              <span className="font-mono text-[10px] text-cockpit-muted">{r.report_id}</span>
            </div>
            <div className="mt-2 text-[11px] text-cockpit-muted">
              Tests: {r.tests.join(", ") || "—"}
            </div>
            <div className="mt-1 text-[11px] text-cockpit-muted">
              Evidence: {r.evidence.join(", ") || "—"}
            </div>
            {(r.unresolved_items?.length || 0) > 0 && (
              <div className="mt-2 text-[11px] text-amber-300">
                Unresolved: {r.unresolved_items!.join(", ")}
              </div>
            )}
          </Panel>
        ))}
      </div>
    </div>
  );
}
