"use client";

import { useEffect, useState } from "react";
import { Panel } from "@/components/Panel";
import {
  apiBase,
  getOrganismCockpit,
  getOrganismPersistenceStatus,
  getOrganismSelfState,
  listOrganismAgencyActions,
  listOrganismCuriosity,
  listOrganismQuarantine,
} from "@/lib/api";
import type {
  OrganismAgencyAction,
  OrganismCockpit,
  OrganismCuriosityTask,
  OrganismPersistenceStatus,
  OrganismQuarantineItem,
  OrganismSelfState,
} from "@/types/brain";

export default function OrganismPage() {
  const [cockpit, setCockpit] = useState<OrganismCockpit | null>(null);
  const [selfState, setSelfState] = useState<OrganismSelfState | null>(null);
  const [curiosity, setCuriosity] = useState<OrganismCuriosityTask[]>([]);
  const [agency, setAgency] = useState<OrganismAgencyAction[]>([]);
  const [quarantine, setQuarantine] = useState<OrganismQuarantineItem[]>([]);
  const [persistence, setPersistence] = useState<OrganismPersistenceStatus | null>(null);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [c, s, cur, ag, q, p] = await Promise.all([
          getOrganismCockpit(),
          getOrganismSelfState(),
          listOrganismCuriosity(),
          listOrganismAgencyActions(),
          listOrganismQuarantine(),
          getOrganismPersistenceStatus(),
        ]);
        if (cancelled) return;
        const hasAny = Boolean(c || s || p || cur.length || ag.length || q.length);
        setAvailable(hasAny);
        setCockpit(c);
        setSelfState(s);
        setCuriosity(cur);
        setAgency(ag);
        setQuarantine(q);
        setPersistence(p);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
          setAvailable(false);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-cockpit-text">Cognitive Organism</h1>
        <p className="text-xs text-cockpit-muted">
          Self-model · workspace · curiosity · agency · immune quarantine · {apiBase()}
        </p>
      </div>

      {loading && (
        <Panel>
          <p className="text-xs text-cockpit-muted">Loading organism layer…</p>
        </Panel>
      )}

      {!loading && available === false && (
        <Panel title="Organism layer not deployed">
          <p className="text-xs text-cockpit-muted">
            Routes under <span className="font-mono text-cockpit-accent">/organism/*</span> returned
            404. Promote the Brain Runtime on Railway to current <span className="font-mono">main</span>{" "}
            (v0.8+) so the control plane can surface self-state, workspace, and agency.
          </p>
          {error && (
            <p className="mt-2 font-mono text-[11px] text-amber-300">{error}</p>
          )}
        </Panel>
      )}

      {!loading && available && (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Self state">
              {selfState ? (
                <dl className="grid grid-cols-2 gap-2 text-xs">
                  {selfState.current_focus_summary && (
                    <div className="col-span-2">
                      <dt className="text-[10px] uppercase text-cockpit-muted">Focus</dt>
                      <dd className="text-cockpit-text">{String(selfState.current_focus_summary)}</dd>
                    </div>
                  )}
                  {[
                    ["Beliefs", selfState.belief_count],
                    ["Events", selfState.event_count],
                    ["Predictions", selfState.prediction_count],
                    ["Opportunities", selfState.opportunity_count],
                    ["Uncertainty", selfState.uncertainty_load],
                    ["Contradiction", selfState.contradiction_load],
                    ["Curiosity pressure", selfState.curiosity_pressure],
                    ["Revenue pressure", selfState.revenue_pressure],
                    ["Risk", selfState.risk_pressure],
                    ["Memory", selfState.memory_pressure],
                    ["Action backlog", selfState.action_backlog_pressure],
                  ].map(([label, value]) =>
                    value !== undefined && value !== null ? (
                      <div key={String(label)}>
                        <dt className="text-[10px] uppercase text-cockpit-muted">{label}</dt>
                        <dd className="font-mono text-cockpit-text">{String(value)}</dd>
                      </div>
                    ) : null
                  )}
                </dl>
              ) : (
                <p className="text-xs text-cockpit-muted">No self-state payload.</p>
              )}
            </Panel>

            <Panel title="Persistence">
              {persistence ? (
                <dl className="space-y-2 text-xs">
                  <div>
                    <dt className="text-[10px] uppercase text-cockpit-muted">Store</dt>
                    <dd className="font-mono">{persistence.store ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-[10px] uppercase text-cockpit-muted">Checkpoint</dt>
                    <dd className="font-mono">{persistence.checkpoint_name ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-[10px] uppercase text-cockpit-muted">Startup checkpoint</dt>
                    <dd className="font-mono">
                      {persistence.has_startup_checkpoint ? "yes" : "no"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[10px] uppercase text-cockpit-muted">Autonomy boundary</dt>
                    <dd className="font-mono text-[11px]">
                      {persistence.autonomy_boundary ?? "—"}
                    </dd>
                  </div>
                </dl>
              ) : (
                <p className="text-xs text-cockpit-muted">No persistence status.</p>
              )}
            </Panel>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Panel title={`Curiosity (${curiosity.length})`}>
              {curiosity.length === 0 ? (
                <p className="text-xs text-cockpit-muted">No organism curiosity tasks.</p>
              ) : (
                <ul className="space-y-2 text-xs">
                  {curiosity.slice(0, 8).map((t, i) => (
                    <li
                      key={String(t.id ?? i)}
                      className="rounded border border-cockpit-border/80 bg-cockpit-bg/50 px-2 py-2"
                    >
                      <div className="text-cockpit-text">{t.question || t.trigger_type || "task"}</div>
                      <div className="mt-1 flex gap-2 font-mono text-[10px] text-cockpit-muted">
                        {t.expected_value != null && <span>ev {Number(t.expected_value).toFixed(2)}</span>}
                        {t.uncertainty != null && <span>unc {Number(t.uncertainty).toFixed(2)}</span>}
                        {t.status && <span>{t.status}</span>}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel title={`Agency (${agency.length})`}>
              {agency.length === 0 ? (
                <p className="text-xs text-cockpit-muted">No agency actions.</p>
              ) : (
                <ul className="space-y-2 text-xs">
                  {agency.slice(0, 8).map((a, i) => (
                    <li
                      key={String(a.id ?? i)}
                      className="rounded border border-cockpit-border/80 bg-cockpit-bg/50 px-2 py-2"
                    >
                      <div className="text-cockpit-text">{a.proposal || a.action_type || "action"}</div>
                      <div className="mt-1 flex gap-2 font-mono text-[10px] text-cockpit-muted">
                        {a.tier && <span>{a.tier}</span>}
                        {a.state && <span>{a.state}</span>}
                        {a.approval_status && <span>{a.approval_status}</span>}
                        {a.risk_score != null && <span>risk {Number(a.risk_score).toFixed(2)}</span>}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel title={`Quarantine (${quarantine.length})`}>
              {quarantine.length === 0 ? (
                <p className="text-xs text-cockpit-muted">Immune quarantine empty.</p>
              ) : (
                <ul className="space-y-2 text-xs">
                  {quarantine.slice(0, 8).map((q, i) => (
                    <li
                      key={String(q.id ?? i)}
                      className="rounded border border-amber-500/30 bg-amber-500/5 px-2 py-2"
                    >
                      <div className="font-mono text-[10px] text-cockpit-muted">
                        {q.item_type} · {q.item_ref}
                      </div>
                      {q.reason && <div className="mt-1 text-cockpit-text">{q.reason}</div>}
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>

          {cockpit && (
            <Panel title="Raw cockpit snapshot">
              <pre className="max-h-64 overflow-auto rounded bg-cockpit-bg/60 p-2 font-mono text-[10px] text-cockpit-muted">
                {JSON.stringify(cockpit, null, 2)}
              </pre>
            </Panel>
          )}
        </>
      )}
    </div>
  );
}
