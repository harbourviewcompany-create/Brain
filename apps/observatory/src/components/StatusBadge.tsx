import { cn } from "@/lib/cn";

const STYLES: Record<string, string> = {
  hypothesis: "bg-blue-500/20 text-blue-300 border-blue-500/40",
  provisional: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  established: "bg-green-500/20 text-green-300 border-green-500/40",
  contested: "bg-red-500/20 text-red-300 border-red-500/40",
  rejected: "bg-zinc-500/20 text-zinc-400 border-zinc-500/40",
  dormant: "bg-zinc-600/20 text-zinc-500 border-zinc-600/40",
  requested: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  approved: "bg-green-500/20 text-green-300 border-green-500/40",
  open: "bg-blue-500/20 text-blue-300 border-blue-500/40",
  under_investigation: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  user_decision_required: "bg-red-500/20 text-red-300 border-red-500/40",
  resolved_with_note: "bg-zinc-500/20 text-zinc-400 border-zinc-500/40",
  active: "bg-green-500/20 text-green-300 border-green-500/40",
  quarantined: "bg-red-500/20 text-red-300 border-red-500/40",
  blocked: "bg-red-500/20 text-red-300 border-red-500/40",
  GO: "bg-green-500/20 text-green-300 border-green-500/40",
  HOLD: "bg-red-500/20 text-red-300 border-red-500/40",
  candidate: "bg-blue-500/20 text-blue-300 border-blue-500/40",
  research: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  recommendation: "bg-purple-500/20 text-purple-300 border-purple-500/40",
  in_progress: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  completed: "bg-green-500/20 text-green-300 border-green-500/40",
  dismissed: "bg-zinc-500/20 text-zinc-400 border-zinc-500/40",
};

export function StatusBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide",
        STYLES[status] || "bg-zinc-500/20 text-zinc-400 border-zinc-500/40",
        className
      )}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
