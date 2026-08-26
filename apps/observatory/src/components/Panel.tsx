import { cn } from "@/lib/cn";

export function Panel({
  title,
  children,
  className,
  action,
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
  action?: React.ReactNode;
}) {
  return (
    <section
      className={cn(
        "rounded-lg border border-cockpit-border bg-cockpit-panel",
        className
      )}
    >
      {title && (
        <header className="flex items-center justify-between border-b border-cockpit-border px-3 py-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-cockpit-muted">
            {title}
          </h2>
          {action}
        </header>
      )}
      <div className="p-3">{children}</div>
    </section>
  );
}
