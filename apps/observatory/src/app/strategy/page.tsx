import { EmptyState } from "@/components/EmptyState";

export default function StrategyPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Strategy & Capital</h1>
        <p className="text-xs text-cockpit-muted">
          CapitalState, risk-adjusted metrics, money-path performance.
        </p>
      </div>
      <EmptyState
        title="Money-spine projections staged"
        description="Capital and strategy surfaces activate with V1 economic objects."
        schemaHint="CapitalState · MoneyPath · RevenueAttribution"
      />
    </div>
  );
}
