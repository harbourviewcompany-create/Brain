import { EmptyState } from "@/components/EmptyState";

/** Shown while a Brain resource is in flight. Never shows placeholder rows. */
export function LoadingState({ label }: { label: string }) {
  return (
    <div
      role="status"
      className="flex items-center justify-center rounded-lg border border-dashed border-cockpit-border bg-cockpit-panel/50 px-6 py-16 text-center"
    >
      <p className="text-xs text-cockpit-muted">Loading {label}…</p>
    </div>
  );
}

/**
 * Shown when the Brain could not be reached. Says what failed and what to do,
 * rather than falling back to data the Brain never returned.
 */
export function ErrorState({
  label,
  error,
  onRetry,
}: {
  label: string;
  error: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-cockpit-red/40 bg-cockpit-red/5 px-6 py-8 text-center"
    >
      <h3 className="text-sm font-medium text-cockpit-text">Could not load {label}</h3>
      <p className="mx-auto mt-2 max-w-md break-words font-mono text-[11px] text-cockpit-muted">
        {error}
      </p>
      <p className="mx-auto mt-2 max-w-md text-xs text-cockpit-muted">
        Nothing is shown here rather than showing data the Brain did not return.
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded border border-cockpit-border px-3 py-1.5 text-xs text-cockpit-text hover:bg-cockpit-border/40 focus-visible:ring-1 focus-visible:ring-cockpit-accent"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export { EmptyState };
