// ───────────────────────────────────────────────────────────────────────────
// /v2/app-shell — DESIGN SYSTEM v2 PREVIEW · in-app shell (dark Console)
//
// A PUBLIC, NOINDEX, nav-suppressed, STATIC-MOCK preview under the clean
// top-level /v2/<slug> namespace. Reachable only by typing /v2/app-shell —
// nothing links here, and it touches NO real auth-walled route. The global
// product nav is suppressed on /v2/* (components/ConditionalTopNav.tsx).
//
// ARCHETYPE — Console (dark), WORKING-class (§0.2). This page proves the
// reusable <AppFrame> in-app chrome: the persistent left rail + in-content top
// bar that the next ~10 in-app pages (simulations-list, personas-list,
// persona-detail, capability-detail, feature-pack, agent-detail,
// agent-transcript, simulation-results, simulations-new, personas-new,
// crawl-setup) will all sit inside. The body here is a representative mock
// "home / dashboard": a recent-simulations logbook snippet, a stat row, and a
// CTA — quiet resting chrome, signal reserved for live readings only (§1.9).
//
// This page CONSUMES the shared v2 layer (components/v2/*, v2-theme.css) and
// never re-inlines a raw hex or font name. This file is a server component;
// the page-local body CSS is token-driven (CSS vars only), mirroring the
// HERO_GRID_CSS / AUTH_CSS precedent in app/product/v2 and app/v2/auth.
// ───────────────────────────────────────────────────────────────────────────
import type { Metadata } from "next";
import {
  AppFrame,
  Panel,
  Designator,
  Button,
  StatusBadge,
  StatusDot,
} from "@/components/v2";
import "@/styles/v2-theme.css";

export const metadata: Metadata = {
  title: "App shell — Sidira",
  robots: { index: false, follow: false },
};

// ── static mock data (consts, top of file) ─────────────────────────────────

// dashboard stat row — exempt recorded facts, print bare (§1.10). v2-tnum on
// every numeral.
type Stat = { label: string; value: string; unit?: string };
const STATS: Stat[] = [
  { label: "Active simulations", value: "3" },
  { label: "Persona packs", value: "12" },
  { label: "Agents this week", value: "1,840" },
  { label: "Crawls queued", value: "2" },
];

// recent-simulations logbook snippet. `n` is an exempt recorded fact (bare);
// status carries the only badge state. No inferred reading on this surface, so
// no Spread Stamp / calibration glyph.
type Run = {
  id: string;
  name: string;
  n: string;
  updated: string;
  status: "live" | "hold" | "done";
};
const RUNS: Run[] = [
  {
    id: "SIM-2207",
    name: "Candor-law onboarding copy",
    n: "2,500",
    updated: "4m ago",
    status: "live",
  },
  {
    id: "SIM-2204",
    name: "Streamly walk-speed lever",
    n: "1,200",
    updated: "1h ago",
    status: "hold",
  },
  {
    id: "SIM-2198",
    name: "Cookie-gate retention readout",
    n: "9,040",
    updated: "Yesterday",
    status: "done",
  },
  {
    id: "SIM-2191",
    name: "Hillstrom email arm comparison",
    n: "42,693",
    updated: "2d ago",
    status: "done",
  },
];

const BADGE_KIND: Record<Run["status"], "live" | "hold" | "neutral"> = {
  live: "live",
  hold: "hold",
  done: "neutral",
};
const BADGE_WORD: Record<Run["status"], string> = {
  live: "Live",
  hold: "Hold",
  done: "Settled",
};

export default function AppShellV2Page() {
  return (
    <AppFrame
      activeNav="simulations"
      title="Home"
      workspace="Sidira"
      provenance={{ label: "SNAPSHOT 2026-W25", calibrated: false, live: true }}
      actions={
        <Button as="a" href="#" variant="primary">
          New simulation
        </Button>
      }
    >
      {/* ── dashboard body — representative mock content ─────────────────── */}
      <div className="v2-dash">
        {/* one-line welcome / orientation */}
        <div className="v2-dash-head">
          <Designator>WORKSPACE · SIDIRA INSTRUMENT</Designator>
          <h2 className="v2-dash-title">Pick up where you left off.</h2>
          <p className="v2-dash-sub">
            Three readings are in flight. Open one to watch its cohort settle,
            or compose a new hypothesis.
          </p>
        </div>

        {/* stat row — bare exempt facts, tabular numerals */}
        <div className="v2-dash-stats">
          {STATS.map((s) => (
            <Panel key={s.label} className="v2-stat">
              <div className="v2-stat-val v2-mono v2-tnum">{s.value}</div>
              <div className="v2-stat-label">{s.label}</div>
            </Panel>
          ))}
        </div>

        {/* recent-simulations logbook snippet */}
        <Panel className="v2-log">
          <div className="v2-log-head">
            <Designator>RECENT SIMULATIONS</Designator>
            <a href="#" className="v2-log-all">
              View all
            </a>
          </div>

          <div className="v2-log-table" role="table" aria-label="Recent simulations">
            <div className="v2-log-row v2-log-row--head" role="row">
              <span className="v2-log-c-id v2-desig" role="columnheader">
                ID
              </span>
              <span className="v2-log-c-name v2-desig" role="columnheader">
                Hypothesis
              </span>
              <span className="v2-log-c-n v2-desig" role="columnheader">
                n
              </span>
              <span className="v2-log-c-when v2-desig" role="columnheader">
                Updated
              </span>
              <span className="v2-log-c-status v2-desig" role="columnheader">
                State
              </span>
            </div>

            {RUNS.map((r) => (
              <a key={r.id} href="#" className="v2-log-row" role="row">
                <span className="v2-log-c-id v2-mono v2-tnum" role="cell">
                  {r.id}
                </span>
                <span className="v2-log-c-name" role="cell">
                  {r.name}
                </span>
                <span className="v2-log-c-n v2-mono v2-tnum" role="cell">
                  {r.n}
                </span>
                <span className="v2-log-c-when" role="cell">
                  {r.updated}
                </span>
                <span className="v2-log-c-status" role="cell">
                  <span className="v2-log-badge">
                    {r.status === "live" ? <StatusDot live /> : null}
                    <StatusBadge kind={BADGE_KIND[r.status]}>
                      {BADGE_WORD[r.status]}
                    </StatusBadge>
                  </span>
                </span>
              </a>
            ))}
          </div>
        </Panel>

        {/* a quiet CTA panel — compose a new reading */}
        <Panel className="v2-cta">
          <div className="v2-cta-copy">
            <Designator>NEXT</Designator>
            <h3 className="v2-cta-title">Compose a hypothesis</h3>
            <p className="v2-cta-sub">
              Frame a product change as a bet, pick a synthetic cohort, and take
              a reading.
            </p>
          </div>
          <div className="v2-cta-actions">
            <Button as="a" href="#" variant="primary">
              New simulation
            </Button>
            <Button as="a" href="#" variant="secondary">
              Build a persona pack
            </Button>
          </div>
        </Panel>
      </div>

      {/* page-local token-driven styling (no raw hex / no raw font names).
          dangerouslySetInnerHTML (root-layout pattern): DASH_CSS holds `"` chars
          (grid-template-areas) that a `<style>{string}</style>` text child would
          HTML-escape server-side only → React 18 hydration text mismatch. */}
      <style dangerouslySetInnerHTML={{ __html: DASH_CSS }} />
    </AppFrame>
  );
}

// ── page-local CSS — every value is a v2 CSS var or a plain unit (no hex,
//    no font names). Mirrors the HERO_GRID_CSS / AUTH_CSS precedent. ──────────
const DASH_CSS = `
.v2-dash{
  max-width:1080px;
  display:flex;
  flex-direction:column;
  gap:var(--space-section);
}
.v2-dash-head{
  max-width:60ch;
}
.v2-dash-title{
  margin-top:14px;
  font-size:1.75rem;
  line-height:1.1;
  letter-spacing:-0.025em;
  font-weight:600;
  color:var(--text-hi);
  text-wrap:balance;
}
.v2-dash-sub{
  margin-top:10px;
  font-size:0.9375rem;
  line-height:1.55;
  color:var(--text-mut);
}
/* stat row */
.v2-dash-stats{
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:var(--space-base);
}
.v2-stat{
  padding:var(--space-room);
  display:flex;
  flex-direction:column;
  gap:var(--space-snug);
}
.v2-stat-val{
  font-size:2rem;
  line-height:1;
  font-weight:500;
  color:var(--text-hi);
}
.v2-stat-label{
  font-size:0.8125rem;
  line-height:1.4;
  color:var(--text-mut);
}
/* logbook */
.v2-log{
  padding:var(--space-room);
}
.v2-log-head{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:var(--space-base);
  margin-bottom:var(--space-base);
}
.v2-log-all{
  font-size:0.8125rem;
  color:var(--text-mut);
  transition:color .14s var(--ease-out);
}
.v2-log-all:hover{
  color:var(--text-hi);
}
.v2-log-table{
  display:flex;
  flex-direction:column;
}
.v2-log-row{
  display:grid;
  grid-template-columns:96px minmax(0,1fr) 84px 110px 110px;
  align-items:center;
  gap:var(--space-base);
  min-height:44px;
  padding:0 var(--space-snug);
  border-top:1px solid var(--console-line-40);
  color:var(--text);
  font-size:0.875rem;
  transition:background .14s var(--ease-out);
}
.v2-log-row--head{
  min-height:34px;
  border-top:none;
}
a.v2-log-row:hover{
  background:var(--console-750);
}
.v2-log-c-name{
  min-width:0;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
  color:var(--text-hi);
}
.v2-log-c-id{
  font-size:0.8125rem;
  color:var(--text-mut);
}
/* numeric columns are right-aligned (§4.6 logbook) */
.v2-log-c-n{
  text-align:right;
  color:var(--text);
}
.v2-log-row--head .v2-log-c-n{
  text-align:right;
}
.v2-log-c-when{
  color:var(--text-mut);
  font-size:0.8125rem;
}
.v2-log-badge{
  display:inline-flex;
  align-items:center;
  gap:var(--space-snug);
}
/* CTA */
.v2-cta{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:var(--space-room);
  flex-wrap:wrap;
  padding:var(--space-room) var(--space-section);
}
.v2-cta-copy{
  min-width:0;
}
.v2-cta-title{
  margin-top:10px;
  font-size:1.125rem;
  line-height:1.2;
  letter-spacing:-0.01em;
  font-weight:550;
  color:var(--text-hi);
}
.v2-cta-sub{
  margin-top:6px;
  font-size:0.875rem;
  line-height:1.5;
  color:var(--text-mut);
  max-width:46ch;
}
.v2-cta-actions{
  display:flex;
  align-items:center;
  gap:var(--space-cozy);
  flex-wrap:wrap;
}
@media(max-width:880px){
  .v2-dash-stats{grid-template-columns:repeat(2,minmax(0,1fr));}
}
@media(max-width:720px){
  .v2-log-row{
    grid-template-columns:1fr auto;
    grid-template-areas:"name status" "id when";
    row-gap:4px;
    padding:var(--space-cozy) var(--space-snug);
    align-items:start;
  }
  .v2-log-c-id{grid-area:id;}
  .v2-log-c-name{grid-area:name;white-space:normal;}
  .v2-log-c-when{grid-area:when;text-align:right;}
  .v2-log-c-status{grid-area:status;justify-self:end;}
  /* n is folded into the row on narrow widths — hidden to keep the card calm */
  .v2-log-c-n{display:none;}
  .v2-log-row--head{display:none;}
}
@media(max-width:520px){
  .v2-dash-stats{grid-template-columns:1fr;}
  .v2-cta{padding:var(--space-room);}
}
`;
