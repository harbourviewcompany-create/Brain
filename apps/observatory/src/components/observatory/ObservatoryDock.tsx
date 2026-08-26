"use client";

import Link from "next/link";

const primary = [
  { href: "/perception", label: "Perception", short: "Perception" },
  { href: "/beliefs", label: "Beliefs", short: "Beliefs" },
  { href: "/predictions", label: "Predictions", short: "Forecast" },
  { href: "/organism", label: "Organism", short: "Organism" },
];

const more = [
  { href: "/curiosity", label: "Curiosity" },
  { href: "/contradictions", label: "Contradictions" },
  { href: "/approvals", label: "Approvals" },
  { href: "/sources", label: "Sources" },
  { href: "/opportunities", label: "Opportunities" },
  { href: "/health", label: "Runtime health" },
];

export function ObservatoryDock() {
  return (
    <>
      <nav className="observatory-dock observatory-dock--desktop" aria-label="Operator surfaces">
        <div className="observatory-dock__mark"><span>OBSERVE</span><strong>BO</strong></div>
        {primary.map((item) => (
          <Link key={item.href} href={item.href} title={item.label}>
            <span>{item.short}</span>
          </Link>
        ))}
        <details>
          <summary><span>More</span></summary>
          <div className="observatory-dock__menu">
            {more.map((item) => <Link key={item.href} href={item.href}>{item.label}</Link>)}
          </div>
        </details>
      </nav>

      <nav className="observatory-dock observatory-dock--mobile" aria-label="Operator surfaces">
        {primary.map((item) => (
          <Link key={item.href} href={item.href}>
            <span>{item.short}</span>
          </Link>
        ))}
        <details>
          <summary><span>More</span></summary>
          <div className="observatory-dock__menu">
            {more.map((item) => <Link key={item.href} href={item.href}>{item.label}</Link>)}
          </div>
        </details>
      </nav>
    </>
  );
}
