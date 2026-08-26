import { Panel } from "@/components/Panel";
import { MOCK_FORMULA_RUNS } from "@/lib/mock";

export default function FormulasPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Formula Audit</h1>
        <p className="text-xs text-cockpit-muted">
          Every score must be traceable to a FormulaRun (inputs, output, consequence).
        </p>
      </div>

      <Panel title="Recent runs">
        <ul className="space-y-3">
          {MOCK_FORMULA_RUNS.map((fr) => (
            <li
              key={fr.id}
              className="rounded border border-cockpit-border bg-cockpit-bg/40 p-3 text-xs"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono text-cockpit-accent">{fr.formula_id}</span>
                <span className="font-mono text-cockpit-muted">{fr.id}</span>
              </div>
              <div className="mt-1 text-cockpit-muted">
                {fr.service} → {fr.owner_object_type} {fr.owner_object_id}
              </div>
              <div className="mt-2 font-mono text-[11px]">
                output <span className="text-cockpit-text">{fr.output}</span>
                <span className="mx-2 text-cockpit-muted">·</span>
                consequence <span className="text-cockpit-text">{fr.decision_consequence}</span>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-1 sm:grid-cols-3">
                {Object.entries(fr.inputs).map(([k, v]) => (
                  <div key={k} className="font-mono text-[10px] text-cockpit-muted">
                    {k}: <span className="text-cockpit-text">{v}</span>
                  </div>
                ))}
              </div>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
