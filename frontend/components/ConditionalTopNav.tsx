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
//
// The live auth routes (/sign-in, /sign-up, /sso-callback) now render the v2
// dark Console auth stage, which owns the full viewport and carries its own
// mark in its head (design-rethink/mocks/auth.html). The light paper TopNav
// must never sit on top of that dark stage, so suppress it across all three.
//
// The public marketing pages (/about, /product) ship their OWN dark Console
// top bar (PublicConsoleTopBar). On the public host the global nav is already
// off (layout's showProductNav=false); but /product is redirected to the APP
// host (site-hosts PRODUCT_PATH_PREFIXES) where showProductNav=true, so the
// global TopNav would double up on the page's own bar. Suppress both so each
// page keeps exactly one nav, on either host. ("/about"/"/product" subsume the
// "/about/v2"/"/product/v2" prefixes, kept above for the Sheet/Console mocks.)
// Two groups of prefixes suppress the global product TopNav, for the same
// reason — the route already ships its OWN single top bar:
//   1. Marketing / auth surfaces ship their own bar (dark Console / Sheet /
//      auth stage): /product, /about (and their /v2 mocks), the /v2/<slug>
//      preview namespace, and the live auth routes (/sign-in, /sign-up,
//      /sso-callback). "/about"/"/product" subsume their "/v2" variants.
//   2. The app subtrees /simulations, /personas, /agents wrap the v2 Reading-
//      Console shell (AppShellV2) on every page, which carries its own rail +
//      app bar — so the global TopNav would double up.
// (Until the global v2 rollout these app prefixes were gated on a runtime flag;
// v2 is now permanent, so they are unconditional.)
const SUPPRESS_NAV_PREFIXES = [
  "/product/v2",
  "/about/v2",
  "/v2",
  "/sign-in",
  "/sign-up",
  "/sso-callback",
  "/about",
  "/product",
  "/simulations",
  "/personas",
  "/agents",
];

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
