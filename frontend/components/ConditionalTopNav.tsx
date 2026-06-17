"use client";

import { usePathname } from "next/navigation";
import TopNav from "@/components/TopNav";

// Route-scoped chrome suppression. The design-system-v2 surfaces (/product/v2
// Console, /about/v2 Sheet) ship their OWN top bar (dark ConsoleShell TopBar /
// light SheetTopBar) and must render WITHOUT the global product TopNav — each
// mock has exactly one nav. Every other route keeps the global nav unchanged.
// This client wrapper is the least invasive way to condition the root-layout
// nav on the pathname without touching middleware or auth paths.
const SUPPRESS_NAV_PREFIXES = ["/product/v2", "/about/v2"];

export function suppressesGlobalNav(pathname: string | null): boolean {
  if (!pathname) return false;
  return SUPPRESS_NAV_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export default function ConditionalTopNav() {
  const pathname = usePathname();
  if (suppressesGlobalNav(pathname)) return null;
  return <TopNav />;
}
