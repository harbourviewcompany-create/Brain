import { EmptyState } from "@/components/EmptyState";

export default function LearningPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Learning Console</h1>
        <p className="text-xs text-cockpit-muted">
          Outcomes · Reward / Pain · Rewire timeline. Attribution required for major learning.
        </p>
      </div>
      <EmptyState
        title="No outcomes yet"
        description="Record outcomes via POST /outcomes. Reward and pain events will appear with attribution links."
        schemaHint="Outcome · RewardEvent · PainEvent · AgencyAttribution"
        actionHref="/attribution"
        actionLabel="Attribution Inspector →"
      />
    </div>
  );
}
