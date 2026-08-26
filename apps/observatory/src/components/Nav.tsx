"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";

const NAV = [
  { href: "/", label: "Cockpit" },
  { href: "/organism", label: "Organism" },
  { href: "/perception", label: "Perception" },
  { href: "/curiosity", label: "Curiosity" },
  { href: "/contradictions", label: "Contradictions" },
  { href: "/beliefs", label: "Beliefs" },
  { href: "/predictions", label: "Predictions" },
  { href: "/opportunities", label: "Opportunities" },
  { href: "/approvals", label: "Approvals" },
  { href: "/learning", label: "Learning" },
  { href: "/attribution", label: "Attribution" },
  { href: "/memory", label: "Memory" },
  { href: "/graph", label: "Graph" },
  { href: "/formulas", label: "Formulas" },
  { href: "/replay", label: "Replay" },
  { href: "/strategy", label: "Strategy" },
  { href: "/trust", label: "Trust" },
  { href: "/sleep", label: "Sleep" },
  { href: "/sources", label: "Sources" },
  { href: "/entities", label: "Entities" },
  { href: "/audit", label: "Audit" },
  { href: "/go-hold", label: "GO/HOLD" },
  { href: "/health", label: "Health" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <nav className="flex h-full flex-col gap-0.5 overflow-y-auto p-2">
      <div className="mb-3 px-2 pt-2">
        <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-cockpit-text">
          Brain
        </div>
        <div className="text-[10px] text-cockpit-muted">Control Plane</div>
      </div>
      {NAV.map((item) => {
        const active =
          item.href === "/"
            ? pathname === "/"
            : pathname === item.href || pathname.startsWith(item.href + "/");
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "rounded px-2 py-1.5 text-xs transition-colors",
              active
                ? "bg-cockpit-accent/15 text-cockpit-accent"
                : "text-cockpit-muted hover:bg-cockpit-border/60 hover:text-cockpit-text"
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
