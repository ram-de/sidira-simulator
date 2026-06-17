"use client";

import { usePathname } from "next/navigation";
import TopNav from "@/components/TopNav";

// Route-scoped chrome suppression. The design-system-v2 surfaces (/product/v2
// Console, /about/v2 Sheet) ship their OWN top bar (dark ConsoleShell TopBar /
// light SheetTopBar) and must render WITHOUT the global product TopNav — each
// mock has exactly one nav. Every other route keeps the global nav unchanged.
// This client wrapper is the least invasive way to condition the root-layout
// nav on the pathname without touching middleware or auth paths.
//
// "/v2" suppresses the whole clean top-level /v2/<slug> preview namespace (e.g.
// /v2/auth): each page there ships its own self-contained ConsoleShell/Sheet top
// bar, so the global product TopNav must never render on top of it.
const SUPPRESS_NAV_PREFIXES = ["/product/v2", "/about/v2", "/v2"];

export function suppressesGlobalNav(pathname: string | null): boolean {
  if (!pathname) return false;
  return SUPPRESS_NAV_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

// The LIVE list routes that ship their own v2 shell (AppShellV2) when the v2
// flag is on must suppress the global TopNav there to avoid a double nav — but
// ONLY when the flag is on. The flag value is evaluated on the SERVER (root
// layout reads the cookie/env via v2Enabled) and passed in as `v2On`, so this
// stays deterministic across SSR + hydration (no flash, no hydration mismatch).
// With the flag off, these routes keep the normal nav.
//
// Membership set, one EXACT list path per migrated route (#372 /simulations,
// then /personas). Only the LIST route renders the v2 shell — nested routes
// (/simulations/[id], /personas/new, …) still render legacy and keep the
// global TopNav. Add a route by appending one entry (e.g. "/agents").
const V2_MIGRATED_ROUTES = new Set(["/simulations", "/personas"]);

function suppressesForV2Route(pathname: string | null, v2On: boolean): boolean {
  if (!v2On || !pathname) return false;
  return V2_MIGRATED_ROUTES.has(pathname);
}

export default function ConditionalTopNav({ v2On = false }: { v2On?: boolean }) {
  const pathname = usePathname();
  if (suppressesGlobalNav(pathname)) return null;
  if (suppressesForV2Route(pathname, v2On)) return null;
  return <TopNav />;
}
