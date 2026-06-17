// ───────────────────────────────────────────────────────────────────────────
// /v2/personas-new — DESIGN SYSTEM v2 PREVIEW · new persona-pack build wizard
//
// A PUBLIC, NOINDEX, nav-suppressed, STATIC-MOCK preview under the clean
// top-level /v2/<slug> namespace. Reachable only by typing /v2/personas-new —
// nothing links here, and it touches NO real auth-walled route. The global
// product nav is suppressed on /v2/* (components/ConditionalTopNav.tsx).
//
// ARCHETYPE — Console (dark), WORKING-class (§0.2): a persona-build SETUP /
// CONFIG surface, so it is brutally quiet — ink + hairline + negative space.
// Per route-law the persona-build wizard is a Console; §0.2 setup/config means
// NO Population Field, no signal fill. The saturated accent is reserved for LIVE
// READINGS ONLY (§1.3, §1.9 signal budget) — none here. The only place doubt
// shows is the ◇ uncalibrated glyph (§7.2) on the inferred stability target;
// recorded facts (column counts, row counts, k, threshold) print bare.
//
// This page CONSUMES the shared v2 layer (AppFrame + components/v2/*,
// v2-theme.css) and never re-inlines a raw hex or font name. Server component;
// the page-local body CSS is token-driven (CSS vars only), mirroring the
// SIMS_CSS precedent in app/v2/simulations-list. Every wizard control is
// intentionally INERT (no state, no handlers, no API), so the whole file stays
// a server component — no "use client" island is needed.
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
  title: "New persona pack — Sidira",
  robots: { index: false, follow: false },
};

// ── static mock data (consts, top of file) ─────────────────────────────────

// The wizard's ordered steps. `n` is the mono step index; `done` marks a step
// the mock has "completed" (resting ink check), the rest read as pending.
type Step = { n: string; key: string; title: string; hint: string; done: boolean };
const STEPS: Step[] = [
  { n: "1", key: "source", title: "Data source", hint: "Feature-store connection", done: true },
  { n: "2", key: "features", title: "Features", hint: "Columns to include", done: true },
  { n: "3", key: "segments", title: "Segmentation", hint: "k · method · stability", done: false },
  { n: "4", key: "population", title: "Population", hint: "Sample · holdout", done: false },
  { n: "5", key: "review", title: "Review", hint: "Build config", done: false },
];

// Step 1 — the chosen feature-store connection + its health note. The host /
// schema / table are recorded facts; the health badge carries the only state.
const SOURCE = {
  connection: "Snowflake · STREAMLY",
  database: "STREAMLY",
  schema: "SYNTHETIC",
  table: "USERS_FEATURE_STORE",
  rows: "2,500",
  auth: "PASSWORD",
  healthy: true,
};

// Step 2 — feature-store columns. `on` = included in the pack. Counts (selected
// / available) are recorded facts, printed bare with tnum.
type Col = { name: string; kind: string; on: boolean };
const COLUMNS: Col[] = [
  { name: "sessions_28d", kind: "numeric", on: true },
  { name: "avg_watch_min", kind: "numeric", on: true },
  { name: "ad_impressions_7d", kind: "numeric", on: true },
  { name: "tier", kind: "categorical", on: true },
  { name: "signup_cohort", kind: "categorical", on: true },
  { name: "device_class", kind: "categorical", on: true },
  { name: "region", kind: "categorical", on: false },
  { name: "last_seen_days", kind: "numeric", on: false },
  { name: "lifetime_value", kind: "numeric", on: false },
];
const COLS_ON = COLUMNS.filter((c) => c.on).length;

// Step 3 — segmentation config. k, threshold are recorded inputs (bare tnum);
// the stability TARGET is an inferred reading, so it wears the ◇ glyph (§7.2).
const SEG = {
  k: "6",
  method: "k-means (standardized)",
  threshold: "0.60",
  achieved: "0.71", // inferred → ◇ uncalibrated
};

// Step 4 — population draw. All bare recorded facts; holdout is a quiet note.
const POP = {
  fitSample: "12,000",
  populationRows: "248,000",
  holdoutPct: "20",
  seed: "20260617",
};

// Step 5 — the read-only review summary. label / value pairs only; values that
// are inferred carry the ◇ glyph, recorded facts print bare (§1.10).
type ReviewRow = { label: string; value: string; mono?: boolean; cal?: boolean };
const REVIEW: ReviewRow[] = [
  { label: "Connection", value: "STREAMLY.SYNTHETIC.USERS_FEATURE_STORE", mono: true },
  { label: "Features", value: `${COLS_ON} of ${COLUMNS.length}`, mono: true },
  { label: "Segments (k)", value: SEG.k, mono: true },
  { label: "Method", value: SEG.method },
  { label: "Stability threshold", value: SEG.threshold, mono: true },
  { label: "Stability target", value: SEG.achieved, mono: true, cal: true },
  { label: "Fit sample", value: POP.fitSample, mono: true },
  { label: "Population rows", value: POP.populationRows, mono: true },
  { label: "Holdout", value: `${POP.holdoutPct}%`, mono: true },
];

export default function PersonasNewV2Page() {
  return (
    <AppFrame
      activeNav="personas"
      title="New persona pack"
      workspace="Sidira"
      provenance={{ label: "DRAFT", calibrated: false, live: false }}
      actions={
        <Button as="a" href="#" variant="primary">
          Build pack
        </Button>
      }
    >
      {/* ── wizard body — two columns: a quiet step rail + the active steps ─── */}
      <div className="v2-pnew">
        {/* step rail — ordered designators, current/pending read in ink only */}
        <aside className="v2-pnew-rail" aria-label="Build steps">
          {STEPS.map((s) => (
            <a
              key={s.key}
              href="#"
              className={
                s.done
                  ? "v2-pnew-step v2-pnew-step--done"
                  : "v2-pnew-step"
              }
            >
              <span className="v2-pnew-step-n v2-mono v2-tnum" aria-hidden>
                {s.done ? "✓" : s.n}
              </span>
              <span className="v2-pnew-step-body">
                <span className="v2-pnew-step-title">{s.title}</span>
                <span className="v2-pnew-step-hint">{s.hint}</span>
              </span>
            </a>
          ))}
        </aside>

        {/* the steps themselves — one Panel per step, inert controls */}
        <div className="v2-pnew-steps">
          {/* ── 1 · Data source ───────────────────────────────────────────── */}
          <Panel className="v2-pnew-panel">
            <div className="v2-pnew-head">
              <Designator>STEP 1 · SOURCE</Designator>
              <h2 className="v2-pnew-h">Data source</h2>
            </div>

            <div className="v2-pnew-source">
              <div className="v2-pnew-source-main">
                <span className="v2-pnew-conn-name">{SOURCE.connection}</span>
                <span className="v2-pnew-conn-path v2-mono v2-tnum">
                  {SOURCE.database}.{SOURCE.schema}.{SOURCE.table}
                </span>
              </div>
              <div className="v2-pnew-source-health">
                <StatusDot live={SOURCE.healthy} />
                <StatusBadge kind={SOURCE.healthy ? "live" : "failed"}>
                  {SOURCE.healthy ? "Reachable" : "Unreachable"}
                </StatusBadge>
              </div>
            </div>

            <div className="v2-pnew-meta">
              <span className="v2-pnew-meta-i">
                <Designator>ROWS</Designator>
                <span className="v2-mono v2-tnum">{SOURCE.rows}</span>
              </span>
              <span className="v2-pnew-meta-i">
                <Designator>AUTH</Designator>
                <span className="v2-mono">{SOURCE.auth}</span>
              </span>
              <span className="v2-pnew-meta-i">
                <Chip>FEATURE STORE</Chip>
              </span>
            </div>
          </Panel>

          {/* ── 2 · Features ──────────────────────────────────────────────── */}
          <Panel className="v2-pnew-panel">
            <div className="v2-pnew-head">
              <Designator>STEP 2 · FEATURES</Designator>
              <h2 className="v2-pnew-h">Columns to include</h2>
              <span className="v2-pnew-count">
                <span className="v2-mono v2-tnum">{COLS_ON}</span> of{" "}
                <span className="v2-mono v2-tnum">{COLUMNS.length}</span> selected
              </span>
            </div>

            <ul className="v2-pnew-cols" aria-label="Feature-store columns">
              {COLUMNS.map((c) => (
                <li
                  key={c.name}
                  className={
                    c.on ? "v2-pnew-col v2-pnew-col--on" : "v2-pnew-col"
                  }
                >
                  <span className="v2-pnew-col-box" aria-hidden>
                    {c.on ? "✓" : ""}
                  </span>
                  <span className="v2-pnew-col-name v2-mono">{c.name}</span>
                  <span className="v2-pnew-col-kind">{c.kind}</span>
                </li>
              ))}
            </ul>
          </Panel>

          {/* ── 3 · Segmentation ──────────────────────────────────────────── */}
          <Panel className="v2-pnew-panel">
            <div className="v2-pnew-head">
              <Designator>STEP 3 · SEGMENTATION</Designator>
              <h2 className="v2-pnew-h">Segments</h2>
            </div>

            <div className="v2-pnew-fields">
              <label className="v2-pnew-field">
                <span className="v2-pnew-field-label">Number of segments (k)</span>
                <span className="v2-pnew-field-val v2-mono v2-tnum">{SEG.k}</span>
              </label>
              <label className="v2-pnew-field">
                <span className="v2-pnew-field-label">Method</span>
                <span className="v2-pnew-field-val">{SEG.method}</span>
              </label>
              <label className="v2-pnew-field">
                <span className="v2-pnew-field-label">Stability threshold</span>
                <span className="v2-pnew-field-val v2-mono v2-tnum">
                  {SEG.threshold}
                </span>
              </label>
              <label className="v2-pnew-field">
                <span className="v2-pnew-field-label">Projected stability</span>
                <span className="v2-pnew-field-val v2-pnew-field-val--cal">
                  <span className="v2-mono v2-tnum">{SEG.achieved}</span>
                  <CalGlyph />
                </span>
              </label>
            </div>

            <p className="v2-pnew-note">
              <Designator>READING</Designator>
              <span className="v2-pnew-note-text">
                Projected stability is <CalGlyph /> uncalibrated — an order-only
                estimate from the fit sample, not a graded magnitude. k and the
                threshold are recorded inputs.
              </span>
            </p>
          </Panel>

          {/* ── 4 · Population ────────────────────────────────────────────── */}
          <Panel className="v2-pnew-panel">
            <div className="v2-pnew-head">
              <Designator>STEP 4 · POPULATION</Designator>
              <h2 className="v2-pnew-h">Population draw</h2>
            </div>

            <div className="v2-pnew-fields">
              <label className="v2-pnew-field">
                <span className="v2-pnew-field-label">Fit sample (stratified)</span>
                <span className="v2-pnew-field-val v2-mono v2-tnum">
                  {POP.fitSample}
                </span>
              </label>
              <label className="v2-pnew-field">
                <span className="v2-pnew-field-label">Population rows</span>
                <span className="v2-pnew-field-val v2-mono v2-tnum">
                  {POP.populationRows}
                </span>
              </label>
              <label className="v2-pnew-field">
                <span className="v2-pnew-field-label">Holdout</span>
                <span className="v2-pnew-field-val v2-mono v2-tnum">
                  {POP.holdoutPct}%
                </span>
              </label>
              <label className="v2-pnew-field">
                <span className="v2-pnew-field-label">Seed</span>
                <span className="v2-pnew-field-val v2-mono v2-tnum">{POP.seed}</span>
              </label>
            </div>

            <p className="v2-pnew-note">
              <Designator>HOLDOUT</Designator>
              <span className="v2-pnew-note-text">
                A <span className="v2-mono v2-tnum">{POP.holdoutPct}%</span>{" "}
                holdout is reserved from the population stream for out-of-sample
                stability checks; it never enters the fit.
              </span>
            </p>
          </Panel>

          {/* ── 5 · Review ────────────────────────────────────────────────── */}
          <Panel className="v2-pnew-panel">
            <div className="v2-pnew-head">
              <Designator>STEP 5 · REVIEW</Designator>
              <h2 className="v2-pnew-h">Build config</h2>
            </div>

            <dl className="v2-pnew-review" aria-label="Build configuration summary">
              {REVIEW.map((r) => (
                <div key={r.label} className="v2-pnew-review-row">
                  <dt className="v2-pnew-review-label v2-desig">{r.label}</dt>
                  <dd
                    className={
                      r.mono
                        ? "v2-pnew-review-val v2-mono v2-tnum"
                        : "v2-pnew-review-val"
                    }
                  >
                    {r.value}
                    {r.cal ? <CalGlyph /> : null}
                  </dd>
                </div>
              ))}
            </dl>

            <div className="v2-pnew-actions">
              <Button as="a" href="#" variant="ghost">
                Save draft
              </Button>
              <Button as="a" href="#" variant="primary">
                Build pack
              </Button>
            </div>
          </Panel>
        </div>
      </div>

      {/* page-local token-driven styling (no raw hex / no raw font names) */}
      <style>{PNEW_CSS}</style>
    </AppFrame>
  );
}

// ── page-local CSS — every value is a v2 CSS var or a plain unit (no hex,
//    no font names). Mirrors the SIMS_CSS precedent in app/v2/simulations-list.
const PNEW_CSS = `
.v2-pnew{
  max-width:1120px;
  display:grid;
  grid-template-columns:232px minmax(0,1fr);
  gap:var(--space-room);
  align-items:start;
}
/* ── step rail ─────────────────────────────────────────────────────────── */
.v2-pnew-rail{
  position:sticky;
  top:calc(52px + var(--space-section));
  display:flex;
  flex-direction:column;
  gap:2px;
}
.v2-pnew-step{
  display:flex;
  align-items:flex-start;
  gap:var(--space-cozy);
  padding:var(--space-snug) var(--space-cozy);
  border-radius:var(--r-well);
  color:var(--text-mut);
  transition:color .14s var(--ease-out), background .14s var(--ease-out);
}
.v2-pnew-step:hover{
  color:var(--text-hi);
  background:var(--console-800);
}
.v2-pnew-step--done{
  color:var(--text);
}
.v2-pnew-step-n{
  flex:0 0 auto;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  width:22px;
  height:22px;
  border-radius:var(--r-dot);
  border:1px solid var(--console-line-50);
  font-size:11px;
  color:var(--text-mut);
}
.v2-pnew-step--done .v2-pnew-step-n{
  border-color:var(--console-line-60);
  color:var(--text-hi);
}
.v2-pnew-step-body{
  display:flex;
  flex-direction:column;
  gap:2px;
  min-width:0;
}
.v2-pnew-step-title{
  font-size:13.5px;
  font-weight:450;
  line-height:1.25;
  color:inherit;
}
.v2-pnew-step-hint{
  font-size:11.5px;
  color:var(--text-mut);
  line-height:1.3;
}
/* ── steps column ──────────────────────────────────────────────────────── */
.v2-pnew-steps{
  display:flex;
  flex-direction:column;
  gap:var(--space-room);
  min-width:0;
}
.v2-pnew-panel{
  padding:var(--space-room);
  display:flex;
  flex-direction:column;
  gap:var(--space-base);
}
.v2-pnew-head{
  display:flex;
  align-items:baseline;
  flex-wrap:wrap;
  gap:var(--space-snug) var(--space-cozy);
}
.v2-pnew-head .v2-desig{
  flex:0 0 100%;
}
.v2-pnew-h{
  font-size:1rem;
  line-height:1.2;
  letter-spacing:-0.01em;
  font-weight:550;
  color:var(--text-hi);
}
.v2-pnew-count{
  margin-left:auto;
  font-size:0.8125rem;
  color:var(--text-mut);
}
.v2-pnew-count .v2-mono{
  color:var(--text);
}
/* ── step 1 · source ───────────────────────────────────────────────────── */
.v2-pnew-source{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:var(--space-base);
  flex-wrap:wrap;
  padding:var(--space-cozy);
  border:1px solid var(--console-line-45);
  border-radius:var(--r-well);
  background:var(--console-800);
}
.v2-pnew-source-main{
  display:flex;
  flex-direction:column;
  gap:3px;
  min-width:0;
}
.v2-pnew-conn-name{
  color:var(--text-hi);
  font-weight:450;
  font-size:0.9375rem;
}
.v2-pnew-conn-path{
  font-size:0.8125rem;
  color:var(--text-mut);
}
.v2-pnew-source-health{
  display:inline-flex;
  align-items:center;
  gap:var(--space-snug);
}
.v2-pnew-meta{
  display:flex;
  align-items:center;
  gap:var(--space-room);
  flex-wrap:wrap;
}
.v2-pnew-meta-i{
  display:inline-flex;
  align-items:center;
  gap:var(--space-snug);
}
.v2-pnew-meta-i .v2-mono{
  color:var(--text);
  font-size:0.8125rem;
}
/* ── step 2 · features list ────────────────────────────────────────────── */
.v2-pnew-cols{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
  gap:2px var(--space-base);
}
.v2-pnew-col{
  display:flex;
  align-items:center;
  gap:var(--space-cozy);
  min-height:34px;
  padding:0 var(--space-snug);
  border-radius:var(--r-well);
  color:var(--text-mut);
  transition:background .14s var(--ease-out), color .14s var(--ease-out);
}
.v2-pnew-col:hover{
  background:var(--console-800);
}
.v2-pnew-col--on{
  color:var(--text);
}
.v2-pnew-col-box{
  flex:0 0 auto;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  width:16px;
  height:16px;
  border-radius:4px;
  border:1px solid var(--console-line-50);
  font-size:10px;
  line-height:1;
  color:var(--text-hi);
}
.v2-pnew-col--on .v2-pnew-col-box{
  border-color:var(--console-line-60);
}
.v2-pnew-col-name{
  flex:1 1 auto;
  min-width:0;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
  font-size:0.8125rem;
}
.v2-pnew-col-kind{
  flex:0 0 auto;
  font-size:11px;
  letter-spacing:0.04em;
  color:var(--text-mut);
  text-transform:lowercase;
}
/* ── steps 3 / 4 · field grids ─────────────────────────────────────────── */
.v2-pnew-fields{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:var(--space-base);
}
.v2-pnew-field{
  display:flex;
  flex-direction:column;
  gap:var(--space-tight);
  padding:var(--space-cozy);
  border:1px solid var(--console-line-45);
  border-radius:var(--r-well);
  background:var(--console-800);
}
.v2-pnew-field-label{
  font-size:11.5px;
  letter-spacing:0.02em;
  color:var(--text-mut);
}
.v2-pnew-field-val{
  font-size:0.9375rem;
  color:var(--text-hi);
}
.v2-pnew-field-val--cal{
  display:inline-flex;
  align-items:baseline;
  gap:6px;
}
/* ── reading / holdout note ────────────────────────────────────────────── */
.v2-pnew-note{
  display:flex;
  align-items:baseline;
  gap:var(--space-cozy);
  max-width:78ch;
}
.v2-pnew-note-text{
  font-size:0.8125rem;
  line-height:1.55;
  color:var(--text-mut);
}
/* ── step 5 · review ───────────────────────────────────────────────────── */
.v2-pnew-review{
  display:flex;
  flex-direction:column;
}
.v2-pnew-review-row{
  display:grid;
  grid-template-columns:200px minmax(0,1fr);
  align-items:baseline;
  gap:var(--space-base);
  min-height:40px;
  padding:var(--space-snug) 0;
  border-top:1px solid var(--console-line-40);
}
.v2-pnew-review-row:first-child{
  border-top:none;
}
.v2-pnew-review-label{
  align-self:center;
}
.v2-pnew-review-val{
  display:inline-flex;
  align-items:baseline;
  gap:6px;
  color:var(--text-hi);
  font-size:0.875rem;
  word-break:break-word;
}
.v2-pnew-actions{
  display:flex;
  align-items:center;
  justify-content:flex-end;
  gap:var(--space-snug);
  margin-top:var(--space-snug);
}
/* ── responsive — fold the step rail above the steps ───────────────────── */
@media(max-width:920px){
  .v2-pnew{
    grid-template-columns:1fr;
    gap:var(--space-base);
  }
  .v2-pnew-rail{
    position:static;
    flex-direction:row;
    gap:2px;
    overflow-x:auto;
    padding-bottom:var(--space-snug);
  }
  .v2-pnew-step{
    flex:0 0 auto;
  }
  .v2-pnew-step-hint{display:none;}
}
@media(max-width:560px){
  .v2-pnew-panel{padding:var(--space-base);}
  .v2-pnew-review-row{
    grid-template-columns:1fr;
    gap:var(--space-tight);
    align-items:start;
  }
}
`;
