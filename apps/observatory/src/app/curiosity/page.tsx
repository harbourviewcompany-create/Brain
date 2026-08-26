import { Panel } from "@/components/Panel";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState } from "@/components/EmptyState";
import { MOCK_CURIOSITY } from "@/lib/mock";
import Link from "next/link";

export default function CuriosityPage() {
  const items = [...MOCK_CURIOSITY].sort((a, b) => b.priority - a.priority);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Curiosity & Investigation Queue</h1>
        <p className="text-xs text-cockpit-muted">
          Uncertainty-reduction and contradiction follow-up tasks ranked by priority.
        </p>
      </div>

      {items.length === 0 ? (
        <EmptyState
          title="No curiosity tasks"
          description="Tasks spawn from high uncertainty, contradictions, and learning value."
          schemaHint="CuriosityTask"
        />
      ) : (
        <Panel>
          <ul className="divide-y divide-cockpit-border">
            {items.map((t) => (
              <li key={t.id} className="flex flex-wrap items-start justify-between gap-3 py-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-cockpit-muted">{t.id}</span>
                    <StatusBadge status={t.status} />
                  </div>
                  <div className="mt-1 text-sm text-cockpit-text">{t.title}</div>
                  <div className="mt-1 text-[11px] text-cockpit-muted">
                    Linked: {t.linked_object_type}{" "}
                    {t.linked_object_type === "belief" ? (
                      <Link
                        href={`/beliefs/${t.linked_object_id}`}
                        className="font-mono text-cockpit-accent hover:underline"
                      >
                        {t.linked_object_id}
                      </Link>
                    ) : (
                      <span className="font-mono">{t.linked_object_id}</span>
                    )}
                  </div>
                  {t.suggested_action && (
                    <div className="mt-1 text-[11px] text-cockpit-muted">
                      Suggested: {t.suggested_action}
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <div className="text-[10px] uppercase text-cockpit-muted">Priority</div>
                  <div className="font-mono text-sm text-cockpit-accent">
                    {t.priority.toFixed(2)}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}
