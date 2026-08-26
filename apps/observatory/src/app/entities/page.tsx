import { EmptyState } from "@/components/EmptyState";

export default function EntitiesPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Entities & Search</h1>
        <p className="text-xs text-cockpit-muted">
          Entity resolution, aliases, merge candidates, global search.
        </p>
      </div>
      <EmptyState
        title="Entity index not live"
        description="Global search across beliefs, signals, opportunities, and contradictions will land here."
        schemaHint="Entity"
      />
    </div>
  );
}
