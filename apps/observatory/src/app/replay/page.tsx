import { EmptyState } from "@/components/EmptyState";

export default function ReplayPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Replay & Experiment Harness</h1>
        <p className="text-xs text-cockpit-muted">
          Re-run event windows under alternate policies. Determinism required.
        </p>
      </div>
      <EmptyState
        title="Replay UI ready for backend"
        description="Select a window or fixture, apply policy overrides, compare side-by-side outcomes."
        schemaHint="brain/replay.py · fixtures"
      />
    </div>
  );
}
