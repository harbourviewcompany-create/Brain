"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const sections = [
  ["/perception", "Perception"],
  ["/beliefs", "Beliefs"],
  ["/predictions", "Predictions"],
  ["/curiosity", "Curiosity"],
  ["/organism", "Organism"],
  ["/approvals", "Approvals"],
  ["/sources", "Sources"],
];

export function RouteFrame({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/") return <>{children}</>;

  return (
    <div className="detail-shell">
      <header className="detail-shell__header">
        <Link href="/" className="detail-shell__home">
          <span aria-hidden="true">←</span>
          <strong>BRAIN OBSERVATORY</strong>
        </Link>
        <span className="detail-shell__path">{pathname.replace(/^\//, "").replaceAll("/", " / ")}</span>
        <nav aria-label="Brain detail surfaces">
          {sections.map(([href, label]) => <Link key={href} href={href} className={pathname.startsWith(href) ? "is-active" : ""}>{label}</Link>)}
        </nav>
      </header>
      <main className="detail-shell__main">{children}</main>
    </div>
  );
}
