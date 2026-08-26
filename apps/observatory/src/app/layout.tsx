import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./observatory-refinements.css";
import { RouteFrame } from "@/components/RouteFrame";

export const metadata: Metadata = {
  title: "Brain Observatory",
  description: "Live observatory for the Brain cognitive runtime",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#05080d",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <RouteFrame>{children}</RouteFrame>
      </body>
    </html>
  );
}
