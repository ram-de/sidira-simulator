// ───────────────────────────────────────────────────────────────────────────
// /v2/agent-detail — DESIGN SYSTEM v2 PREVIEW · in-app single-agent detail
//
// A PUBLIC, NOINDEX, nav-suppressed, STATIC-MOCK preview under the clean
// top-level /v2/<slug> namespace. Reachable only by typing /v2/agent-detail —
// nothing links here, and it touches NO real auth-walled route. The global
// product nav is suppressed on /v2/* (components/ConditionalTopNav.tsx).
//
// ARCHETYPE — Console (dark), WORKING-class (§0.2): brutally quiet — ink +
// hairline + negative space. This is ONE synthetic viewer (a single agent drawn
// from a persona pack), so there is NO Population Field and NO signal fill; the
// page carries at most ONE tiny isolated agent-dot motif — a single resting
// StatusDot beside the identity line, never a field. The saturated accent is
// reserved for LIVE READINGS ONLY (§1.3, §1.9 signal budget). The only doubt
// shown is the ◇ uncalibrated glyph (§7.2) next to each inferred directional
// outcome — recorded facts (standardised features, dates) print bare.
//
// This page CONSUMES the shared v2 layer (AppFrame + components/v2/*,
// v2-theme.css) and never re-inlines a raw hex or font name. Server component;
// every control here is intentionally inert, so the whole file stays a server
// component — no "use client" island is needed.
// ───────────────────────────────────────────────────────────────────────────
import type { Metadata } from "next";
import {
  AppFrame,
  Panel,
  Designator,
  Button,
  StatusBadge,
  StatusDot,
  CalGlyph,
} from "@/components/v2";
import "@/styles/v2-theme.css";

export const metadata: Metadata = {
  title: "Agent — Sidira",
  robots: { index: false, follow: false },
};

// ── static mock data (consts, top of file) ─────────────────────────────────
// ONE synthetic agent record: a single simulated viewer drawn from the Streamly
// persona pack (S1 · Binge loyalists). All values are synthetic — drawn around
// the segment centroid — and no cell maps to a real Streamly account.

const AGENT = {
  id: "S1-0440",
  pack: "Streamly · v2",
  segment: "S1 · Binge loyalists",
  org: "org_3F9pXz",
  drawn: "2026-06-14",
  snapshot: "2026-W25",
  tenure: "412", // days — recorded fact, bare tnum
  read: "Daily long-session viewer; deep catalogue reach, low ad-tolerance.",
};

// ── identity facts — recorded, bare tnum (§1.10 exempt) ──────────────────────
type Fact = { k: string; v: string };
const IDENTITY: Fact[] = [
  { k: "Pack", v: AGENT.pack },
  { k: "Segment", v: AGENT.segment },
  { k: "Source", v: AGENT.org },
  { k: "Drawn", v: AGENT.drawn },
  { k: "Tenure (days)", v: AGENT.tenure },
];

// ── feature vector — the agent's standardised features (z-scores), drawn
//    around the S1 centroid. `z` is a recorded synthetic coordinate, not an
//    inferred reading — it prints bare (no ◇). `dir` is a neutral sign-mark
//    for the deviation from the population mean (§1.6: a verdict is not a
//    color — the mark reads from shape, never valence hue).
type Feature = { name: string; z: string; dir: "up" | "down" | "flat" };
const FEATURES: Feature[] = [
  { name: "watch_hours_z", z: "+1.84", dir: "up" },
  { name: "sessions_per_wk_z", z: "+1.52", dir: "up" },
  { name: "catalogue_reach_z", z: "+1.21", dir: "up" },
  { name: "completion_rate_z", z: "+0.74", dir: "up" },
  { name: "ad_tolerance_z", z: "−1.36", dir: "down" },
  { name: "weekend_skew_z", z: "−0.42", dir: "down" },
  { name: "recency_gap_z", z: "−0.88", dir: "down" },
  { name: "churn_risk_z", z: "−0.05", dir: "flat" },
];

// ── participation history — recent simulations this agent was drawn into.
//    `outcome` is the agent's elicited directional response — an INFERRED
//    reading, so it carries the ◇ uncalibrated glyph (§7.2); `dir` is its
//    sign for the leading sign-mark. `date` is a recorded fact, bare tnum.
type Part = {
  sim: string;
  name: string;
  outcome: string;
  dir: "up" | "down" | "flat";
  date: string;
};
const HISTORY: Part[] = [
  {
    sim: "SIM-2207",
    name: "Candor-law onboarding copy",
    outcome: "Stayed",
    dir: "up",
    date: "2026-06-17",
  },
  {
    sim: "SIM-2198",
    name: "Streamly ad-density A/B (sentiment)",
    outcome: "Soured",
    dir: "down",
    date: "2026-06-16",
  },
  {
    sim: "SIM-2204",
    name: "Streamly walk-speed lever (2→4)",
    outcome: "Stayed",
    dir: "up",
    date: "2026-06-17",
  },
  {
    sim: "SIM-2180",
    name: "Streamly blinded-retention readout",
    outcome: "Retained",
    dir: "up",
    date: "2026-06-13",
  },
  {
    sim: "SIM-2169",
    name: "Capability shrinkage interface seam",
    outcome: "No change",
    dir: "flat",
    date: "2026-06-11",
  },
];

// leading sign-mark — a neutral mono caret, NOT a valence color (§1.6). The
// deviation/direction reads from the caret shape alone; magnitude stays bare.
const DIR_MARK: Record<"up" | "down" | "flat", string> = {
  up: "▲",
  down: "▼",
  flat: "—",
};

export default function AgentDetailV2Page() {
  return (
    <AppFrame
      activeNav="agents"
      title={`Agent · ${AGENT.id}`}
      workspace="Sidira"
      provenance={{ label: "SNAPSHOT 2026-W25", calibrated: false, live: false }}
      actions={
        <Button as="a" href="#" variant="secondary">
          View transcript
        </Button>
      }
    >
      {/* ── agent detail body ─────────────────────────────────────────────── */}
      <div className="v2-agt">
        {/* ── (1) identity panel ──────────────────────────────────────────── */}
        <Panel className="v2-agt-id">
          <div className="v2-agt-id-head">
            <div className="v2-agt-id-mark">
              {/* the ONE isolated agent-dot motif — a single resting dot, no
                  field, no signal (it is not live) */}
              <StatusDot />
              <span className="v2-agt-id-code v2-mono v2-tnum">{AGENT.id}</span>
            </div>
            <StatusBadge kind="neutral">Synthetic viewer</StatusBadge>
          </div>

          <p className="v2-agt-id-read">{AGENT.read}</p>

          <dl className="v2-agt-facts">
            {IDENTITY.map((f) => (
              <div key={f.k} className="v2-agt-fact">
                <dt className="v2-desig">{f.k}</dt>
                <dd className="v2-agt-fact-v v2-mono v2-tnum">{f.v}</dd>
              </div>
            ))}
          </dl>
        </Panel>

        {/* ── (2) feature vector panel ────────────────────────────────────── */}
        <Panel className="v2-agt-panel">
          <div className="v2-agt-panel-head">
            <Designator>Feature vector</Designator>
            <span className="v2-agt-panel-note">
              standardised · drawn around the S1 centroid
            </span>
          </div>

          <div className="v2-agt-feat" role="table" aria-label="Feature vector">
            <div className="v2-agt-feat-row v2-agt-feat-row--head" role="row">
              <span className="v2-agt-feat-name v2-desig" role="columnheader">
                Feature
              </span>
              <span className="v2-agt-feat-z v2-desig" role="columnheader">
                Standardised value
              </span>
            </div>
            {FEATURES.map((f) => (
              <div key={f.name} className="v2-agt-feat-row" role="row">
                <span
                  className="v2-agt-feat-name v2-mono"
                  role="cell"
                >
                  {f.name}
                </span>
                <span className="v2-agt-feat-z" role="cell">
                  <span
                    className={`v2-agt-dir v2-agt-dir--${f.dir} v2-mono`}
                    aria-hidden
                  >
                    {DIR_MARK[f.dir]}
                  </span>
                  <span className="v2-agt-feat-zval v2-mono v2-tnum">{f.z}</span>
                </span>
              </div>
            ))}
          </div>

          <p className="v2-agt-panel-foot">
            <Designator>RECORDED</Designator>
            <span className="v2-agt-panel-foot-text">
              Standardised coordinates are synthetic, drawn around the segment
              centre — printed bare, no ± and no glyph. They are a description of
              one viewer, not a reading of one.
            </span>
          </p>
        </Panel>

        {/* ── (3) participation history panel ─────────────────────────────── */}
        <Panel className="v2-agt-panel">
          <div className="v2-agt-panel-head">
            <Designator>Participation history</Designator>
            <span className="v2-agt-panel-note">
              <span className="v2-mono v2-tnum">{HISTORY.length}</span> recent
              simulations
            </span>
          </div>

          <div
            className="v2-agt-hist"
            role="table"
            aria-label="Participation history"
          >
            <div className="v2-agt-hist-row v2-agt-hist-row--head" role="row">
              <span className="v2-agt-hist-name v2-desig" role="columnheader">
                Hypothesis
              </span>
              <span className="v2-agt-hist-out v2-desig" role="columnheader">
                Elicited outcome
              </span>
              <span className="v2-agt-hist-when v2-desig" role="columnheader">
                Date
              </span>
            </div>
            {HISTORY.map((h) => (
              <a key={h.sim} href="#" className="v2-agt-hist-row" role="row">
                <span className="v2-agt-hist-name" role="cell">
                  <span className="v2-agt-hist-hyp">{h.name}</span>
                  <span className="v2-agt-hist-sim v2-mono v2-tnum">
                    {h.sim}
                  </span>
                </span>
                <span className="v2-agt-hist-out" role="cell">
                  <span
                    className={`v2-agt-dir v2-agt-dir--${h.dir} v2-mono`}
                    aria-hidden
                  >
                    {DIR_MARK[h.dir]}
                  </span>
                  <span className="v2-agt-hist-label">{h.outcome}</span>
                  <CalGlyph />
                </span>
                <span
                  className="v2-agt-hist-when v2-mono v2-tnum"
                  role="cell"
                >
                  {h.date}
                </span>
              </a>
            ))}
          </div>

          <p className="v2-agt-panel-foot">
            <Designator>READING</Designator>
            <span className="v2-agt-panel-foot-text">
              Elicited outcomes are <CalGlyph /> uncalibrated — the agent&rsquo;s
              directional response only, no calibrated magnitude. Simulation ids
              and dates are recorded facts.
            </span>
          </p>
        </Panel>
      </div>

      {/* page-local token-driven styling (no raw hex / no raw font names).
          dangerouslySetInnerHTML (root-layout pattern): AGT_CSS holds `"` chars
          (grid-template-areas) that a `<style>{string}</style>` text child would
          HTML-escape server-side only → React 18 hydration text mismatch. */}
      <style dangerouslySetInnerHTML={{ __html: AGT_CSS }} />
    </AppFrame>
  );
}

// ── page-local CSS — every value is a v2 CSS var or a plain unit (no hex,
//    no font names). Mirrors the SIMS_CSS precedent in simulations-list. ──────
const AGT_CSS = `
.v2-agt{
  max-width:880px;
  display:flex;
  flex-direction:column;
  gap:var(--space-room);
}
/* ── (1) identity panel ────────────────────────────────────────────────── */
.v2-agt-id{
  padding:var(--space-room);
  display:flex;
  flex-direction:column;
  gap:var(--space-base);
}
.v2-agt-id-head{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:var(--space-base);
  flex-wrap:wrap;
}
.v2-agt-id-mark{
  display:inline-flex;
  align-items:center;
  gap:var(--space-cozy);
}
.v2-agt-id-code{
  font-size:1.375rem;
  letter-spacing:0.01em;
  color:var(--text-hi);
}
.v2-agt-id-read{
  margin:0;
  max-width:62ch;
  font-size:0.9375rem;
  line-height:1.55;
  color:var(--text);
}
/* identity facts — a quiet hairline-free key/value strip */
.v2-agt-facts{
  margin:0;
  display:flex;
  flex-wrap:wrap;
  gap:var(--space-room);
}
.v2-agt-fact{
  display:flex;
  flex-direction:column;
  gap:var(--space-tight);
  min-width:0;
}
.v2-agt-fact-v{
  font-size:0.875rem;
  color:var(--text);
}
/* ── shared panel head / foot (feature + history) ──────────────────────── */
.v2-agt-panel{
  padding:var(--space-snug) var(--space-room) var(--space-room);
  display:flex;
  flex-direction:column;
}
.v2-agt-panel-head{
  display:flex;
  align-items:baseline;
  justify-content:space-between;
  gap:var(--space-base);
  flex-wrap:wrap;
  min-height:40px;
}
.v2-agt-panel-note{
  font-size:0.8125rem;
  color:var(--text-mut);
}
.v2-agt-panel-note .v2-mono{
  color:var(--text);
}
.v2-agt-panel-foot{
  display:flex;
  align-items:baseline;
  gap:var(--space-cozy);
  max-width:78ch;
  margin:var(--space-base) 0 0;
}
.v2-agt-panel-foot-text{
  font-size:0.8125rem;
  line-height:1.55;
  color:var(--text-mut);
}
/* ── (2) feature vector table ──────────────────────────────────────────── */
.v2-agt-feat{
  display:flex;
  flex-direction:column;
}
.v2-agt-feat-row{
  display:grid;
  grid-template-columns:minmax(0,1fr) 200px;
  align-items:center;
  gap:var(--space-base);
  min-height:44px;
  padding:var(--space-snug) 0;
  border-top:1px solid var(--console-line-40);
  font-size:0.875rem;
}
.v2-agt-feat-row--head{
  min-height:34px;
  border-top:none;
  align-items:end;
}
.v2-agt-feat-name{
  min-width:0;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
  color:var(--text);
}
.v2-agt-feat-row--head .v2-agt-feat-z{
  text-align:right;
}
.v2-agt-feat-z{
  display:inline-flex;
  align-items:baseline;
  justify-content:flex-end;
  gap:var(--space-snug);
  white-space:nowrap;
}
.v2-agt-feat-zval{
  color:var(--text);
}
/* ── (3) participation history table ───────────────────────────────────── */
.v2-agt-hist{
  display:flex;
  flex-direction:column;
}
.v2-agt-hist-row{
  display:grid;
  grid-template-columns:minmax(0,1fr) 168px 116px;
  align-items:center;
  gap:var(--space-base);
  min-height:52px;
  padding:var(--space-snug);
  border-top:1px solid var(--console-line-40);
  color:var(--text);
  font-size:0.875rem;
  transition:background .14s var(--ease-out);
}
.v2-agt-hist-row--head{
  min-height:34px;
  border-top:none;
  align-items:end;
}
a.v2-agt-hist-row:hover{
  background:var(--console-750);
}
.v2-agt-hist-name{
  min-width:0;
  display:flex;
  flex-direction:column;
  gap:3px;
}
.v2-agt-hist-hyp{
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
  color:var(--text-hi);
  font-weight:450;
}
.v2-agt-hist-sim{
  font-size:0.75rem;
  color:var(--text-mut);
}
.v2-agt-hist-row--head .v2-agt-hist-out,
.v2-agt-hist-row--head .v2-agt-hist-when{
  text-align:right;
}
.v2-agt-hist-out{
  display:inline-flex;
  align-items:baseline;
  justify-content:flex-end;
  gap:var(--space-tight);
  white-space:nowrap;
}
.v2-agt-hist-label{
  color:var(--text);
}
.v2-agt-hist-when{
  text-align:right;
  color:var(--text-mut);
  font-size:0.8125rem;
}
/* ── sign-marks — NEUTRAL ink, never valence color (§1.6). Direction reads
   from the caret shape alone; magnitude / label stays bare. ─────────────── */
.v2-agt-dir{
  font-size:0.6875rem;
  color:var(--text-mut);
  transform:translateY(-1px);
}
.v2-agt-dir--up,
.v2-agt-dir--down,
.v2-agt-dir--flat{
  color:var(--text-mut);
}
/* ── responsive — fold the right columns under the name ────────────────── */
@media(max-width:720px){
  .v2-agt-feat-row{
    grid-template-columns:minmax(0,1fr) auto;
  }
  .v2-agt-hist-row{
    grid-template-columns:minmax(0,1fr) auto;
    grid-template-areas:
      "name out"
      "when out";
    row-gap:var(--space-tight);
    align-items:start;
  }
  .v2-agt-hist-name{grid-area:name;}
  .v2-agt-hist-out{grid-area:out;justify-self:end;align-self:center;}
  .v2-agt-hist-when{grid-area:when;text-align:left;}
  .v2-agt-hist-row--head{display:none;}
}
@media(max-width:480px){
  .v2-agt-id,
  .v2-agt-panel{padding:var(--space-snug) var(--space-cozy) var(--space-cozy);}
  .v2-agt-facts{gap:var(--space-base);}
}
`;
