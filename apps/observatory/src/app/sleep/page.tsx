import { EmptyState } from "@/components/EmptyState";

export default function SleepPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Sleep & Recovery</h1>
        <p className="text-xs text-cockpit-muted">
          Offline recombination / dreaming. Dreams create hypotheses only — never facts.
        </p>
      </div>
      <EmptyState
        title="Consolidation loop not exposed"
        description="Dream hypotheses require new evidence before promotion to belief."
        schemaHint="ConsolidationService · dreaming"
      />
    </div>
  );
}
