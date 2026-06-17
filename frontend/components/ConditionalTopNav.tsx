"use client";

import { usePathname } from "next/navigation";
import TopNav from "@/components/TopNav";

// Route-scoped chrome suppression. The design-system-v2 surfaces (currently
// only /product/v2) ship their own dark ConsoleShell TopBar and must render
// WITHOUT the global product TopNav — the mock has exactly one nav. Every other
// route keeps the global nav unchanged. This client wrapper is the least
// invasive way to condition the root-layout nav on the pathname without
// touching middleware or auth paths.
const SUPPRESS_NAV_PREFIXES = ["/product/v2"];

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
