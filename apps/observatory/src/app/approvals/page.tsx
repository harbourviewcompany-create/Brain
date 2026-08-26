import { Panel } from "@/components/Panel";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState } from "@/components/EmptyState";
import { MOCK_APPROVALS } from "@/lib/mock";

export default function ApprovalsPage() {
  const items = MOCK_APPROVALS.filter((a) => a.state === "requested");

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Approval Inbox</h1>
        <p className="text-xs text-cockpit-muted">
          External consequence requires human decision. No auto-execute.
        </p>
      </div>

      {items.length === 0 ? (
        <EmptyState
          title="No pending approvals"
          description="Candidate actions with external_consequence=true appear here."
          schemaHint="ApprovalRequest · CandidateAction"
        />
      ) : (
        <div className="space-y-3">
          {items.map((a) => (
            <Panel key={a.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs">{a.id}</span>
                    <StatusBadge status={a.state} />
                    {a.external_consequence && (
                      <span className="rounded border border-red-500/40 px-1.5 py-0.5 text-[10px] text-red-300">
                        external
                      </span>
                    )}
                  </div>
                  <div className="mt-1 text-[11px] text-cockpit-muted">
                    Action <span className="font-mono text-cockpit-text">{a.action_id}</span>
                  </div>
                  <div className="mt-0.5 text-[11px] text-cockpit-muted">
                    Required approver:{" "}
                    <span className="font-mono text-cockpit-text">{a.required_approver}</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded border border-green-500/50 bg-green-500/15 px-3 py-1.5 text-xs font-medium text-green-300 hover:bg-green-500/25"
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="rounded border border-red-500/50 bg-red-500/15 px-3 py-1.5 text-xs font-medium text-red-300 hover:bg-red-500/25"
                >
                  Reject
                </button>
                <button
                  type="button"
                  className="rounded border border-cockpit-border px-3 py-1.5 text-xs text-cockpit-muted hover:bg-cockpit-border/40"
                >
                  Request more evidence
                </button>
              </div>
              <p className="mt-2 text-[10px] text-cockpit-muted">
                Decision writes ApprovalDecision + AuditEvent. Execution is blocked until approved.
              </p>
            </Panel>
          ))}
        </div>
      )}
    </div>
  );
}
