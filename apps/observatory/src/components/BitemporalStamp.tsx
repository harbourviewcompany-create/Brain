export function BitemporalStamp({
  validFrom,
  knownAt,
  createdAt,
}: {
  validFrom?: string | null;
  knownAt?: string | null;
  createdAt?: string;
}) {
  const fmt = (s?: string | null) =>
    s ? new Date(s).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" }) : "—";

  return (
    <div className="flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-[10px] text-cockpit-muted">
      {validFrom && <span title="World-valid time">valid {fmt(validFrom)}</span>}
      {knownAt && <span title="Knowledge-acquisition time">known {fmt(knownAt)}</span>}
      {createdAt && !knownAt && <span>created {fmt(createdAt)}</span>}
    </div>
  );
}
