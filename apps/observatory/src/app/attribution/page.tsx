import { EmptyState } from "@/components/EmptyState";

export default function AttributionPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Agency Attribution</h1>
        <p className="text-xs text-cockpit-muted">
          Credit assignment for outcomes. Low-confidence attribution should not drive major rewires.
        </p>
      </div>
      <EmptyState
        title="No attributions"
        description="Attributions are created when outcomes are recorded against predictions, edges, and sources."
        schemaHint="AgencyAttribution"
      />
    </div>
  );
}
