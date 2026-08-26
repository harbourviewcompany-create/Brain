"use client";

import { cn } from "@/lib/cn";

export function ConfidenceBar({
  value,
  formulaRunId,
  onInspect,
  className,
}: {
  value: number;
  formulaRunId?: string | null;
  onInspect?: (formulaRunId: string) => void;
  className?: string;
}) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  const color =
    value >= 0.7 ? "bg-green-500" : value >= 0.4 ? "bg-amber-500" : "bg-red-500";

  return (
    <button
      type="button"
      disabled={!formulaRunId || !onInspect}
      onClick={() => formulaRunId && onInspect?.(formulaRunId)}
      className={cn(
        "group flex w-full min-w-[80px] items-center gap-2 text-left",
        formulaRunId && onInspect && "cursor-pointer",
        className
      )}
      title={formulaRunId ? `Formula run ${formulaRunId}` : undefined}
    >
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-cockpit-border">
        <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right font-mono text-[11px] text-cockpit-muted group-hover:text-cockpit-text">
        {pct}%
      </span>
    </button>
  );
}
