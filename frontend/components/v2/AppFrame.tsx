// ───────────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM v2 — AppFrame (§4.5 Nav / app-shell).
//
// The standard in-app application chrome for the dark Console: a persistent
// LEFT RAIL (Console duo mark + primary nav + workspace affordance) plus an
// in-content TOP BAR (page title + optional actions + one global provenance
// marker), wrapping each page's body in the MAIN slot. Pages 3–13 of the v2
// rollout (simulations-list, personas-list, persona-detail, capability-detail,
// feature-pack, agent-detail, agent-transcript, simulation-results,
// simulations-new, personas-new, crawl-setup) all sit inside this frame.
//
// WORKING-class (§0.2): resting chrome. The active nav item reads in NEUTRAL
// INK (--text-hi), never signal — the saturated accent is reserved for LIVE
// READINGS ONLY (§1.3, §1.9 signal budget). The frame is flexible enough for a
// list page, a detail page, and a wizard page; the rail collapses to a top
// strip on narrow widths.
//
// Token-driven only: every value is a v2 CSS var (var(--console-*),
// var(--text-*), var(--signal-*), var(--r-*), var(--v2-font-*)) — NO raw hex,
// rgb/rgba, or font names. Consumers import from "@/components/v2"; this file
// re-asserts no tokens of its own (they come from .v2-console via v2-theme.css,
// which ConsoleShell scopes).
// ───────────────────────────────────────────────────────────────────────────
"use client";

import type { ReactNode } from "react";
import { ConsoleShell } from "./ConsoleShell";
import { SheetMarkDuo } from "./Marks";
import { ProvenanceMarker, type ProvenanceMarkerProps } from "./Provenance";

// A primary nav entry in the left rail. `key` is what `activeNav` matches on
// (stable across copy changes); `label` is the visible text; `glyph` is a short
// mono designator shown when the rail is collapsed / as the leading mark.
export type AppNavItem = {
  key: string;
  label: string;
  href: string;
  // a 1–2 char mono glyph (the rail's compact identifier on narrow widths).
  glyph: string;
};

// The product's in-app sections (design-system-v2.md §4 archetypes + the real
// app's surfaces). Each page sets `activeNav` to one of these keys. Exported so
// pages 3–13 reuse the exact same rail without re-declaring it.
export const APP_NAV: AppNavItem[] = [
  { key: "simulations", label: "Simulations", href: "#", glyph: "SIM" },
  { key: "personas", label: "Personas", href: "#", glyph: "PER" },
  { key: "capabilities", label: "Capabilities", href: "#", glyph: "CAP" },
  { key: "feature-packs", label: "Feature packs", href: "#", glyph: "FP" },
  { key: "agents", label: "Agents", href: "#", glyph: "AGT" },
  { key: "crawls", label: "Crawls", href: "#", glyph: "CRW" },
];

export type AppFrameProps = {
  // which primary nav section is current (matches AppNavItem.key); highlighted
  // in neutral ink, never signal.
  activeNav: string;
  // the page title shown in the in-content top bar.
  title: string;
  // optional right-aligned top-bar actions (buttons, links). Inert is fine.
  actions?: ReactNode;
  // optional single global provenance marker for the top bar (snapshot +
  // calibration + live dot). Omit on surfaces with no live reading.
  provenance?: ProvenanceMarkerProps;
  // optional override of the rail nav (defaults to APP_NAV). Lets a page add or
  // reorder sections without forking the frame.
  nav?: AppNavItem[];
  // optional workspace / account label shown in the rail footer affordance.
  workspace?: string;
  // the page body.
  children: ReactNode;
};

export function AppFrame({
  activeNav,
  title,
  actions,
  provenance,
  nav = APP_NAV,
  workspace = "Workspace",
  children,
}: AppFrameProps) {
  return (
    <ConsoleShell>
      <div className="v2-appframe">
        {/* ── LEFT RAIL — persistent vertical nav ─────────────────────────── */}
        <aside className="v2-rail" aria-label="Primary">
          <a
            href="#"
            className="v2-rail-brand"
            aria-label="Sidira Console home"
          >
            <SheetMarkDuo size={28} />
          </a>

          <nav className="v2-rail-nav">
            {nav.map((item) => {
              const active = item.key === activeNav;
              return (
                <a
                  key={item.key}
                  href={item.href}
                  className={
                    active ? "v2-rail-item v2-rail-item--active" : "v2-rail-item"
                  }
                  aria-current={active ? "page" : undefined}
                  // collapsed rail (≤1024px) hides the label and aria-hides the
                  // glyph, so name the link explicitly for screen readers.
                  aria-label={item.label}
                >
                  {/* active = 1px left ink bar (neutral, never signal) */}
                  <span className="v2-rail-bar" aria-hidden />
                  <span className="v2-rail-glyph v2-mono" aria-hidden>
                    {item.glyph}
                  </span>
                  <span className="v2-rail-label">{item.label}</span>
                </a>
              );
            })}
          </nav>

          {/* workspace / account affordance — rail footer */}
          <a href="#" className="v2-rail-account" aria-label="Workspace and account">
            <span className="v2-rail-account-avatar v2-mono" aria-hidden>
              {workspace.slice(0, 1).toUpperCase()}
            </span>
            <span className="v2-rail-account-name">{workspace}</span>
          </a>
        </aside>

        {/* ── CONTENT COLUMN ──────────────────────────────────────────────── */}
        <div className="v2-appframe-content">
          {/* in-content top bar: title + actions + one provenance marker */}
          <header className="v2-appbar">
            <h1 className="v2-appbar-title">{title}</h1>
            <div className="v2-appbar-right">
              {provenance ? <ProvenanceMarker {...provenance} /> : null}
              {actions ? <div className="v2-appbar-actions">{actions}</div> : null}
            </div>
          </header>

          {/* main body slot — each page renders its own content here */}
          <main className="v2-appmain">{children}</main>
        </div>
      </div>
      {/* AppFrame chrome CSS lives in styles/v2-theme.css (the global sheet every
          v2 page imports) — moved out of an inline <style> to avoid a React 18 /
          Next 14 multi-<style> hoist/dedupe hydration mismatch. */}
    </ConsoleShell>
  );
}
