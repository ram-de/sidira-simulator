// ───────────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM v2 — AppFrame (§4.5 Nav / app-shell).
//
// The standard in-app application chrome for the dark Console: a persistent
// LEFT RAIL (Console mono mark + primary nav + workspace affordance) plus an
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
import { ConsoleMarkMono } from "./Marks";
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
            <ConsoleMarkMono size={28} />
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

      {/* component-local CSS — every value is a v2 CSS var or plain unit (no
          raw hex / rgb / rgba / font names). Scoped to .v2-appframe. */}
      <style>{APP_FRAME_CSS}</style>
    </ConsoleShell>
  );
}

const APP_FRAME_CSS = `
.v2-appframe{
  display:grid;
  grid-template-columns:236px minmax(0,1fr);
  min-height:100vh;
  align-items:stretch;
}
/* ── left rail ─────────────────────────────────────────────────────────── */
.v2-rail{
  position:sticky;
  top:0;
  align-self:start;
  height:100vh;
  display:flex;
  flex-direction:column;
  gap:var(--space-room);
  padding:var(--space-room) var(--space-cozy);
  background:var(--console-850);
  border-right:1px solid var(--console-line-50);
}
.v2-rail-brand{
  display:inline-flex;
  align-items:center;
  gap:var(--space-snug);
  padding:0 var(--space-snug);
  color:var(--text-hi);
}
.v2-rail-nav{
  display:flex;
  flex-direction:column;
  gap:2px;
}
.v2-rail-item{
  position:relative;
  display:flex;
  align-items:center;
  gap:var(--space-cozy);
  height:38px;
  padding:0 var(--space-cozy);
  border-radius:var(--r-well);
  color:var(--text-mut);
  font-size:13.5px;
  font-weight:450;
  transition:color .14s var(--ease-out), background .14s var(--ease-out);
}
.v2-rail-item:hover{
  color:var(--text-hi);
  background:var(--console-800);
}
.v2-rail-item--active{
  color:var(--text-hi);
  background:var(--console-800);
}
/* active marker — 1px left INK bar (neutral, never signal — §1.9 budget) */
.v2-rail-bar{
  position:absolute;
  left:0;
  top:8px;
  bottom:8px;
  width:2px;
  border-radius:2px;
  background:transparent;
}
.v2-rail-item--active .v2-rail-bar{
  background:var(--text-hi);
}
.v2-rail-glyph{
  flex:0 0 auto;
  width:30px;
  font-size:9.5px;
  letter-spacing:0.06em;
  color:var(--text-mut);
  text-align:left;
}
.v2-rail-item--active .v2-rail-glyph,
.v2-rail-item:hover .v2-rail-glyph{
  color:var(--text);
}
.v2-rail-label{
  white-space:nowrap;
}
/* workspace / account affordance — pinned to rail bottom */
.v2-rail-account{
  margin-top:auto;
  display:flex;
  align-items:center;
  gap:var(--space-snug);
  padding:var(--space-snug);
  border-radius:var(--r-well);
  border:1px solid var(--console-line-45);
  color:var(--text-mut);
  font-size:12.5px;
  transition:color .14s var(--ease-out), background .14s var(--ease-out);
}
.v2-rail-account:hover{
  color:var(--text-hi);
  background:var(--console-800);
}
.v2-rail-account-avatar{
  flex:0 0 auto;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  width:26px;
  height:26px;
  border-radius:var(--r-well);
  background:var(--console-700);
  color:var(--text-hi);
  font-size:11px;
  font-weight:500;
}
.v2-rail-account-name{
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}
/* ── content column ────────────────────────────────────────────────────── */
.v2-appframe-content{
  display:flex;
  flex-direction:column;
  min-width:0;
}
.v2-appbar{
  position:sticky;
  top:0;
  z-index:40;
  display:flex;
  align-items:center;
  gap:var(--space-room);
  min-height:52px;
  padding:var(--space-cozy) var(--space-section);
  background:var(--console-850);
  border-bottom:1px solid var(--console-line-50);
}
.v2-appbar-title{
  font-size:1.0625rem;
  line-height:1.2;
  letter-spacing:-0.01em;
  font-weight:550;
  color:var(--text-hi);
  min-width:0;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
}
.v2-appbar-right{
  margin-left:auto;
  display:flex;
  align-items:center;
  gap:var(--space-base);
}
.v2-appbar-actions{
  display:flex;
  align-items:center;
  gap:var(--space-snug);
}
.v2-appmain{
  flex:1 1 auto;
  min-width:0;
  padding:var(--space-section);
}
/* ── responsive — rail collapses to a glyph strip, then a top strip ──────── */
@media(max-width:1024px){
  .v2-appframe{grid-template-columns:64px minmax(0,1fr);}
  .v2-rail{padding:var(--space-room) var(--space-snug);align-items:center;}
  .v2-rail-label,
  .v2-rail-account-name{display:none;}
  .v2-rail-item{justify-content:center;padding:0;width:44px;}
  .v2-rail-glyph{width:auto;text-align:center;}
  .v2-rail-account{justify-content:center;padding:var(--space-snug);border:none;}
  .v2-appbar{padding:var(--space-cozy) var(--space-room);}
  .v2-appmain{padding:var(--space-room);}
}
@media(max-width:640px){
  .v2-appframe{grid-template-columns:1fr;}
  .v2-rail{
    position:sticky;
    top:0;
    height:auto;
    flex-direction:row;
    align-items:center;
    gap:var(--space-base);
    padding:var(--space-snug) var(--space-room);
    border-right:none;
    border-bottom:1px solid var(--console-line-50);
    z-index:45;
  }
  .v2-rail-nav{
    flex-direction:row;
    gap:2px;
    overflow-x:auto;
    flex:1 1 auto;
  }
  .v2-rail-item{height:36px;width:auto;padding:0 var(--space-cozy);}
  .v2-rail-bar{
    left:var(--space-snug);
    right:var(--space-snug);
    top:auto;
    bottom:0;
    width:auto;
    height:2px;
  }
  .v2-rail-account{margin-top:0;margin-left:auto;}
  .v2-rail-account-name{display:none;}
  /* rail becomes the sticky top strip on mobile; the appbar stops sticking so
     it can't slide under the rail (both were pinned at top:0). */
  .v2-appbar{position:static;padding:var(--space-cozy) var(--space-room);}
  .v2-appmain{padding:var(--space-room);}
}
`;
