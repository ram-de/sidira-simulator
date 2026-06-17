// ───────────────────────────────────────────────────────────────────────────
// AppShellV2 — the PRODUCTION v2 application shell (#372).
//
// The static /v2/* mocks render AppFrame with its MOCK defaults (6 href="#" nav
// items + a mock workspace avatar). Production must NOT ship dead nav or fake
// chrome, and must NOT mutate AppFrame's defaults (that would break the mocks).
// So this shell composes the SAME visual frame from the shared v2 layer
// (ConsoleShell scope + the .v2-appframe / .v2-rail* / .v2-appbar classes that
// already live in styles/v2-theme.css and that AppFrame itself consumes) but
// wires the REAL product chrome:
//
//   • exactly the two real destinations the global TopNav exposes —
//     Hypotheses → /simulations (active on /simulations or /agents),
//     Library → /personas — as real Next <Link>s with usePathname() active
//     state. No href="#" dead items.
//   • the rail footer renders the EXISTING AuthControls (Clerk org switcher +
//     user button, or nothing when Clerk is off) — org-switching + sign-out are
//     preserved, never reimplemented here.
//   • title / provenance / actions pass through to the appbar, same as AppFrame.
//
// The whole subtree sits under ConsoleShell's `.v2-console` ancestor, so every
// v2 token resolves. Token-driven only: no raw hex / rgb / font names here.
// ───────────────────────────────────────────────────────────────────────────
"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import AuthControls from "@/components/AuthControls";
import { ConsoleShell } from "./ConsoleShell";
import { ConsoleMarkMono } from "./Marks";
import { ProvenanceMarker, type ProvenanceMarkerProps } from "./Provenance";
// The shell owns the v2 stylesheet import so every production v2 page that uses
// it inherits the `.v2-console` tokens + the .v2-appframe/.v2-rail*/.v2-sims-*
// classes (ConsoleShell requires the page to import this sheet).
import "@/styles/v2-theme.css";

// The two REAL product destinations (kept in lockstep with components/TopNav.tsx
// TABS). `matches` drives active state via usePathname(): Hypotheses owns both
// /simulations and /agents, exactly like the global nav.
const NAV = [
  {
    key: "simulations",
    label: "Hypotheses",
    href: "/simulations",
    glyph: "HYP",
    matches: ["/simulations", "/agents"],
  },
  {
    key: "personas",
    label: "Library",
    href: "/personas",
    glyph: "LIB",
    matches: ["/personas"],
  },
] as const;

export type AppShellV2Props = {
  // which real nav section is current (matches a NAV key). Falls back to
  // pathname matching, but callers pass it explicitly for clarity.
  activeNav?: "simulations" | "personas";
  // the page title shown in the appbar.
  title: string;
  // optional right-aligned appbar actions (e.g. the "New hypothesis" CTA).
  actions?: ReactNode;
  // optional single global provenance marker for the appbar.
  provenance?: ProvenanceMarkerProps;
  // the page body.
  children: ReactNode;
};

export default function AppShellV2({
  activeNav,
  title,
  actions,
  provenance,
  children,
}: AppShellV2Props) {
  const pathname = usePathname() ?? "/";

  return (
    <ConsoleShell>
      <div className="v2-appframe">
        {/* ── LEFT RAIL — persistent vertical nav, real destinations ───────── */}
        <aside className="v2-rail" aria-label="Primary">
          <Link href="/" className="v2-rail-brand" aria-label="Sidira Console home">
            <ConsoleMarkMono size={28} />
          </Link>

          <nav className="v2-rail-nav">
            {NAV.map((item) => {
              const active =
                (activeNav && item.key === activeNav) ||
                item.matches.some(
                  (m) => pathname === m || pathname.startsWith(`${m}/`),
                );
              return (
                <Link
                  key={item.key}
                  href={item.href}
                  className={
                    active ? "v2-rail-item v2-rail-item--active" : "v2-rail-item"
                  }
                  aria-current={active ? "page" : undefined}
                  aria-label={item.label}
                >
                  {/* active = 1px left ink bar (neutral, never signal) */}
                  <span className="v2-rail-bar" aria-hidden />
                  <span className="v2-rail-glyph v2-mono" aria-hidden>
                    {item.glyph}
                  </span>
                  <span className="v2-rail-label">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* rail footer — the REAL Clerk org switcher + user button (or nothing
              when Clerk is off in dev). Reuses AuthControls verbatim so tenancy
              + sign-out behave identically to the legacy TopNav. Its own
              marginLeft:auto is harmless inside this flex-column footer. */}
          <div className="v2-rail-account-slot">
            <AuthControls />
          </div>
        </aside>

        {/* ── CONTENT COLUMN ──────────────────────────────────────────────── */}
        <div className="v2-appframe-content">
          <header className="v2-appbar">
            <h1 className="v2-appbar-title">{title}</h1>
            <div className="v2-appbar-right">
              {provenance ? <ProvenanceMarker {...provenance} /> : null}
              {actions ? <div className="v2-appbar-actions">{actions}</div> : null}
            </div>
          </header>

          <main className="v2-appmain">{children}</main>
        </div>
      </div>
    </ConsoleShell>
  );
}
