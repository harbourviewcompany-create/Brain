import { EmptyState } from "@/components/EmptyState";

export default function AuditPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Audit / Event Log</h1>
        <p className="text-xs text-cockpit-muted">
          Filterable BrainEvent and AuditEvent stream. Actor · action · object · time.
        </p>
      </div>
      <EmptyState
        title="Audit stream not connected"
        description="Every state transition should emit audit evidence. Wire to event ledger read API."
        schemaHint="AuditEvent · BrainEvent"
      />
    </div>
  );
}
