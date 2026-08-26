import { EmptyState } from "@/components/EmptyState";

export default function TrustPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Trust & Relationships</h1>
        <p className="text-xs text-cockpit-muted">
          Trust balances, reputation risk, relationship stage.
        </p>
      </div>
      <EmptyState
        title="Trust console staged"
        description="Trust-adjusted value already influences Approval Inbox scoring."
        schemaHint="CounterpartyProfile · trust_adjusted_value"
      />
    </div>
  );
}
