"use client";

import { useCallback, useState } from "react";
import { Panel } from "@/components/Panel";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/ResourceState";
import { useBrainResource } from "@/hooks/useBrainResource";
import { approveOrganismAgencyAction, listOrganismAgencyActions } from "@/lib/api";

/**
 * The Approval Inbox is the real governance surface: it lists the organism's
 * proposed agency actions and approves them through /organism/agency/approve.
 * It previously rendered fixture rows behind buttons that did nothing, which
 * implied human control over external action that did not exist.
 */

const PENDING_STATES = new Set(["proposed", "requested", "pending", "awaiting_approval"]);

export default function ApprovalsPage() {
  const load = useCallback(() => listOrganismAgencyActions(), []);
  const { status, data, error, reload } = useBrainResource(load);

  const [approvedBy, setApprovedBy] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const pending = (data || []).filter((a) =>
    PENDING_STATES.has(String(a.status || "").toLowerCase())
  );

  async function approve(actionId: string) {
    setBusyId(actionId);
    setActionError(null);
    try {
      await approveOrganismAgencyAction(actionId, approvedBy.trim());
      reload();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Approval Inbox</h1>
        <p className="text-xs text-cockpit-muted">
          External consequence requires human decision. No auto-execute.
        </p>
      </div>

      {status === "loading" && <LoadingState label="pending actions" />}
      {status === "error" && (
        <ErrorState label="pending actions" error={error} onRetry={reload} />
      )}

      {status === "ready" && pending.length === 0 && (
        <EmptyState
          title="No pending approvals"
          description="Proposed agency actions awaiting a human decision appear here."
          schemaHint="AgencyAction · ApprovalDecision"
        />
      )}

      {status === "ready" && pending.length > 0 && (
        <>
          <Panel title="Approver identity">
            <label className="block space-y-1.5">
              <span className="text-[10px] text-cockpit-muted">
                Recorded on every decision you make below.
              </span>
              <input
                value={approvedBy}
                onChange={(e) => setApprovedBy(e.target.value)}
                placeholder="your operator id"
                className="w-full max-w-xs rounded border border-cockpit-border bg-cockpit-bg px-2.5 py-1.5 font-mono text-xs text-cockpit-text outline-none focus:border-cockpit-accent"
              />
            </label>
          </Panel>

          {actionError && (
            <p role="alert" className="text-xs text-cockpit-red">
              Approval failed: {actionError}
            </p>
          )}

          <div className="space-y-3">
            {pending.map((a) => {
              const id = String(a.id ?? "");
              return (
                <Panel key={id}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs">{id.slice(0, 8)}</span>
                        <StatusBadge status={String(a.status ?? "proposed")} />
                        {a.tier && (
                          <span className="rounded border border-cockpit-border px-1.5 py-0.5 text-[10px] text-cockpit-muted">
                            tier {String(a.tier)}
                          </span>
                        )}
                      </div>
                      {a.proposal != null && (
                        <div className="mt-1.5 text-[11px] text-cockpit-text">
                          {String(a.proposal)}
                        </div>
                      )}
                      <div className="mt-0.5 text-[11px] text-cockpit-muted">
                        Type{" "}
                        <span className="font-mono text-cockpit-text">
                          {String(a.action_type ?? "unknown")}
                        </span>
                        {typeof a.risk_score === "number" && (
                          <> · risk {a.risk_score.toFixed(2)}</>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4">
                    <button
                      type="button"
                      onClick={() => approve(id)}
                      disabled={!approvedBy.trim() || busyId === id}
                      className="rounded border border-green-500/50 bg-green-500/15 px-3 py-1.5 text-xs font-medium text-green-300 hover:bg-green-500/25 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {busyId === id ? "Approving…" : "Approve"}
                    </button>
                  </div>
                  <p className="mt-2 text-[10px] text-cockpit-muted">
                    {approvedBy.trim()
                      ? "Approval writes an audit event. Execution stays blocked until approved."
                      : "Enter an approver id above to enable approval."}
                  </p>
                </Panel>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
