// ───────────────────────────────────────────────────────────────────────────
// /v2/simulations-list — DESIGN SYSTEM v2 PREVIEW · in-app Simulations list
//
// A PUBLIC, NOINDEX, nav-suppressed, STATIC-MOCK preview under the clean
// top-level /v2/<slug> namespace. Reachable only by typing /v2/simulations-list
// — nothing links here, and it touches NO real auth-walled route. The global
// product nav is suppressed on /v2/* (components/ConditionalTopNav.tsx).
//
// ARCHETYPE — Console (dark), WORKING-class (§0.2): brutally quiet — ink +
// hairline + negative space. No Population Field, no signal fill; the saturated
// accent is reserved for LIVE READINGS ONLY (§1.3, §1.9 signal budget). The
// only place doubt shows is the ◇ uncalibrated glyph (§7.2) next to each
// inferred directional reading — recorded facts (cohort n, dates) print bare.
//
// This page CONSUMES the shared v2 layer (AppFrame + components/v2/*,
// v2-theme.css) and never re-inlines a raw hex or font name. Server component;
// the page-local body CSS is token-driven (CSS vars only), mirroring the
// DASH_CSS precedent in app/v2/app-shell. The one interactive affordance (the
// filter chips) is intentionally inert here, so this whole file stays a server
// component — no "use client" island is needed.
// ───────────────────────────────────────────────────────────────────────────
import type { Metadata } from "next";
import {
  AppFrame,
  Panel,
  Designator,
  Button,
  Chip,
  StatusBadge,
  StatusDot,
  CalGlyph,
} from "@/components/v2";
import "@/styles/v2-theme.css";

export const metadata: Metadata = {
  title: "Simulations — Sidira",
  robots: { index: false, follow: false },
};

// ── static mock data (consts, top of file) ─────────────────────────────────

// A single simulation index row. `n` (cohort size) and `updated` (date) are
// EXEMPT recorded facts — print bare (§1.10). `lift` is an INFERRED directional
// reading, so it carries the ◇ uncalibrated glyph (§7.2); `dir` is its sign for
// the leading sign-mark. `status` carries the only badge state.
type Status = "live" | "hold" | "failed" | "settled";
type Sim = {
  id: string;
  name: string;
  n: string;
  lift: string; // signed, e.g. "+3.6 pp" — bare numeral, glyph carries doubt
  dir: "up" | "down" | "flat";
  updated: string;
  status: Status;
};

const SIMS: Sim[] = [
  {
    id: "SIM-2207",
    name: "Candor-law onboarding copy",
    n: "2,500",
    lift: "+3.6 pp",
    dir: "up",
    updated: "2026-06-17",
    status: "live",
  },
  {
    id: "SIM-2204",
    name: "Streamly walk-speed lever (2→4)",
    n: "1,200",
    lift: "+1.2 pp",
    dir: "up",
    updated: "2026-06-17",
    status: "live",
  },
  {
    id: "SIM-2201",
    name: "Cookie-gate at level 30 vs 40",
    n: "9,040",
    lift: "−2.1 pp",
    dir: "down",
    updated: "2026-06-16",
    status: "hold",
  },
  {
    id: "SIM-2198",
    name: "Streamly ad-density A/B (sentiment)",
    n: "4,800",
    lift: "−0.4 pp",
    dir: "down",
    updated: "2026-06-16",
    status: "hold",
  },
  {
    id: "SIM-2191",
    name: "Hillstrom email arm comparison",
    n: "42,693",
    lift: "0.0 pp",
    dir: "flat",
    updated: "2026-06-15",
    status: "failed",
  },
  {
    id: "SIM-2186",
    name: "Upworthy headline CTR ceiling",
    n: "1,000",
    lift: "−0.11 ρ",
    dir: "flat",
    updated: "2026-06-14",
    status: "failed",
  },
  {
    id: "SIM-2180",
    name: "Streamly blinded-retention readout",
    n: "2,500",
    lift: "+3.6 pp",
    dir: "up",
    updated: "2026-06-13",
    status: "settled",
  },
  {
    id: "SIM-2174",
    name: "Founder onboarding affordance fix #1",
    n: "1,840",
    lift: "0.0 pp",
    dir: "flat",
    updated: "2026-06-12",
    status: "settled",
  },
  {
    id: "SIM-2169",
    name: "Capability shrinkage interface seam",
    n: "3,200",
    lift: "+0.8 pp",
    dir: "up",
    updated: "2026-06-11",
    status: "settled",
  },
];

// status → badge kind + visible word. `settled` reads as quiet neutral ink.
const BADGE_KIND: Record<Status, "live" | "hold" | "failed" | "neutral"> = {
  live: "live",
  hold: "hold",
  failed: "failed",
  settled: "neutral",
};
const BADGE_WORD: Record<Status, string> = {
  live: "Live",
  hold: "On hold",
  failed: "Refuted",
  settled: "Settled",
};

// inert toolbar filters (§4.8 chips). The active read is carried by ink, not by
// a saturated fill — these are resting designators, no signal.
const FILTERS = ["ALL", "LIVE", "ON HOLD", "REFUTED", "SETTLED"] as const;

// leading sign-mark for the directional reading — a neutral mono caret, NOT a
// valence color (§1.6: a verdict is not a color). Doubt lives in the ◇ glyph.
const DIR_MARK: Record<Sim["dir"], string> = {
  up: "▲",
  down: "▼",
  flat: "—",
};

export default function SimulationsListV2Page() {
  return (
    <AppFrame
      activeNav="simulations"
      title="Simulations"
      workspace="Sidira"
      provenance={{ label: "SNAPSHOT 2026-W25", calibrated: false, live: false }}
      actions={
        <Button as="a" href="#" variant="primary">
          New simulation
        </Button>
      }
    >
      {/* ── simulations index body ──────────────────────────────────────────── */}
      <div className="v2-sims">
        {/* toolbar — inert filter chips + a bare result count */}
        <div className="v2-sims-toolbar">
          <div className="v2-sims-filters" role="group" aria-label="Filter simulations">
            {FILTERS.map((f, i) => (
              <a
                key={f}
                href="#"
                className={
                  i === 0
                    ? "v2-sims-filter v2-sims-filter--active"
                    : "v2-sims-filter"
                }
                aria-current={i === 0 ? "true" : undefined}
              >
                <Chip>{f}</Chip>
              </a>
            ))}
          </div>
          <div className="v2-sims-count">
            <span className="v2-mono v2-tnum">{SIMS.length}</span> simulations
          </div>
        </div>

        {/* the index — one panel, a quiet hairline-ruled table */}
        <Panel className="v2-sims-panel">
          <div
            className="v2-sims-table"
            role="table"
            aria-label="Simulations index"
          >
            {/* column header row */}
            <div className="v2-sims-row v2-sims-row--head" role="row">
              <span className="v2-sims-c-name v2-desig" role="columnheader">
                Hypothesis
              </span>
              <span className="v2-sims-c-status v2-desig" role="columnheader">
                State
              </span>
              <span className="v2-sims-c-n v2-desig" role="columnheader">
                Cohort
              </span>
              <span className="v2-sims-c-lift v2-desig" role="columnheader">
                Directional reading
              </span>
              <span className="v2-sims-c-when v2-desig" role="columnheader">
                Updated
              </span>
            </div>

            {SIMS.map((s) => (
              <a key={s.id} href="#" className="v2-sims-row" role="row">
                {/* hypothesis name + machine id */}
                <span className="v2-sims-c-name" role="cell">
                  <span className="v2-sims-name">{s.name}</span>
                  <span className="v2-sims-id v2-mono v2-tnum">{s.id}</span>
                </span>

                {/* state — badge (+ breathing dot only when live) */}
                <span className="v2-sims-c-status" role="cell">
                  <span className="v2-sims-state">
                    {s.status === "live" ? <StatusDot live /> : null}
                    <StatusBadge kind={BADGE_KIND[s.status]}>
                      {BADGE_WORD[s.status]}
                    </StatusBadge>
                  </span>
                </span>

                {/* cohort size — exempt recorded fact, bare tnum */}
                <span className="v2-sims-c-n v2-mono v2-tnum" role="cell">
                  {s.n}
                </span>

                {/* directional reading — inferred, so ◇ uncalibrated (§7.2) */}
                <span className="v2-sims-c-lift" role="cell">
                  <span
                    className={`v2-sims-dir v2-sims-dir--${s.dir} v2-mono`}
                    aria-hidden
                  >
                    {DIR_MARK[s.dir]}
                  </span>
                  <span className="v2-sims-lift v2-mono v2-tnum">{s.lift}</span>
                  <CalGlyph />
                </span>

                {/* updated — exempt recorded fact, bare tnum */}
                <span className="v2-sims-c-when v2-mono v2-tnum" role="cell">
                  {s.updated}
                </span>
              </a>
            ))}
          </div>
        </Panel>

        {/* one-line provenance / calibration footnote for the whole index */}
        <p className="v2-sims-foot">
          <Designator>READING</Designator>
          <span className="v2-sims-foot-text">
            Directional readings are <CalGlyph /> uncalibrated — sign and order
            only, no calibrated magnitude. Cohort sizes and dates are recorded
            facts.
          </span>
        </p>
      </div>

      {/* page-local token-driven styling (no raw hex / no raw font names) */}
      <style>{SIMS_CSS}</style>
    </AppFrame>
  );
}

// ── page-local CSS — every value is a v2 CSS var or a plain unit (no hex,
//    no font names). Mirrors the DASH_CSS precedent in app/v2/app-shell. ──────
const SIMS_CSS = `
.v2-sims{
  max-width:1120px;
  display:flex;
  flex-direction:column;
  gap:var(--space-room);
}
/* ── toolbar ───────────────────────────────────────────────────────────── */
.v2-sims-toolbar{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:var(--space-base);
  flex-wrap:wrap;
}
.v2-sims-filters{
  display:flex;
  align-items:center;
  gap:var(--space-snug);
  flex-wrap:wrap;
}
/* a filter is an inert link wrapping a Chip; the active one lifts to full ink */
.v2-sims-filter{
  display:inline-flex;
  opacity:0.62;
  transition:opacity .14s var(--ease-out);
}
.v2-sims-filter:hover{
  opacity:1;
}
.v2-sims-filter--active{
  opacity:1;
}
.v2-sims-count{
  font-size:0.8125rem;
  color:var(--text-mut);
  white-space:nowrap;
}
.v2-sims-count .v2-mono{
  color:var(--text);
}
/* ── index panel + table ───────────────────────────────────────────────── */
.v2-sims-panel{
  padding:var(--space-snug) var(--space-room) var(--space-room);
}
.v2-sims-table{
  display:flex;
  flex-direction:column;
}
.v2-sims-row{
  display:grid;
  grid-template-columns:minmax(0,1fr) 120px 96px 168px 116px;
  align-items:center;
  gap:var(--space-base);
  min-height:52px;
  padding:var(--space-snug);
  border-top:1px solid var(--console-line-40);
  color:var(--text);
  font-size:0.875rem;
  transition:background .14s var(--ease-out);
}
.v2-sims-row--head{
  min-height:40px;
  border-top:none;
  align-items:end;
}
a.v2-sims-row:hover{
  background:var(--console-750);
}
/* hypothesis cell — name (hi) over machine id (mut) */
.v2-sims-c-name{
  min-width:0;
  display:flex;
  flex-direction:column;
  gap:3px;
}
.v2-sims-name{
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
  color:var(--text-hi);
  font-weight:450;
}
.v2-sims-id{
  font-size:0.75rem;
  color:var(--text-mut);
}
/* state cell */
.v2-sims-state{
  display:inline-flex;
  align-items:center;
  gap:var(--space-snug);
}
/* cohort — right-aligned recorded fact (§4.6 logbook) */
.v2-sims-c-n{
  text-align:right;
  color:var(--text);
}
.v2-sims-row--head .v2-sims-c-n,
.v2-sims-row--head .v2-sims-c-lift,
.v2-sims-row--head .v2-sims-c-when{
  text-align:right;
}
/* directional reading — sign-mark + bare magnitude + ◇ glyph, right-aligned */
.v2-sims-c-lift{
  display:inline-flex;
  align-items:baseline;
  justify-content:flex-end;
  gap:4px;
  white-space:nowrap;
}
.v2-sims-dir{
  font-size:0.6875rem;
  color:var(--text-mut);
  transform:translateY(-1px);
}
/* sign-marks are NEUTRAL ink, never valence color (§1.6). Direction reads from
   the caret shape alone; magnitude stays bare. */
.v2-sims-dir--up,
.v2-sims-dir--down,
.v2-sims-dir--flat{
  color:var(--text-mut);
}
.v2-sims-lift{
  color:var(--text);
}
.v2-sims-c-when{
  text-align:right;
  color:var(--text-mut);
  font-size:0.8125rem;
}
/* ── reading footnote ──────────────────────────────────────────────────── */
.v2-sims-foot{
  display:flex;
  align-items:baseline;
  gap:var(--space-cozy);
  max-width:78ch;
}
.v2-sims-foot-text{
  font-size:0.8125rem;
  line-height:1.55;
  color:var(--text-mut);
}
/* ── responsive — fold the secondary columns under the name ──────────────── */
@media(max-width:920px){
  .v2-sims-row{
    grid-template-columns:minmax(0,1fr) auto;
    grid-template-areas:
      "name status"
      "meta lift";
    row-gap:var(--space-snug);
    align-items:start;
  }
  .v2-sims-c-name{grid-area:name;}
  .v2-sims-c-status{grid-area:status;justify-self:end;}
  .v2-sims-c-lift{grid-area:lift;justify-self:end;}
  /* cohort + updated collapse into one quiet meta line under the name */
  .v2-sims-c-n{
    grid-area:meta;
    text-align:left;
    color:var(--text-mut);
    font-size:0.75rem;
  }
  .v2-sims-c-when{display:none;}
  .v2-sims-row--head{display:none;}
}
@media(max-width:560px){
  .v2-sims-toolbar{align-items:flex-start;flex-direction:column;}
  .v2-sims-panel{padding:var(--space-snug) var(--space-cozy) var(--space-cozy);}
  .v2-sims-row{
    grid-template-columns:1fr;
    grid-template-areas:
      "name"
      "status"
      "meta"
      "lift";
    row-gap:4px;
  }
  .v2-sims-c-status,
  .v2-sims-c-lift{justify-self:start;}
}
`;
