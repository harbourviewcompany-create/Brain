import Link from "next/link";

export function EmptyState({
  title,
  description,
  schemaHint,
  actionHref,
  actionLabel,
}: {
  title: string;
  description: string;
  schemaHint?: string;
  actionHref?: string;
  actionLabel?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-cockpit-border bg-cockpit-panel/50 px-6 py-16 text-center">
      <h3 className="text-sm font-medium text-cockpit-text">{title}</h3>
      <p className="mt-2 max-w-md text-xs text-cockpit-muted">{description}</p>
      {schemaHint && (
        <p className="mt-3 font-mono text-[10px] text-cockpit-muted/80">
          Schema: {schemaHint}
        </p>
      )}
      {actionHref && actionLabel && (
        <Link
          href={actionHref}
          className="mt-4 rounded border border-cockpit-accent/40 bg-cockpit-accent/10 px-3 py-1.5 text-xs text-cockpit-accent hover:bg-cockpit-accent/20"
        >
          {actionLabel}
        </Link>
      )}
    </div>
  );
}
