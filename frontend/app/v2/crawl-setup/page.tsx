// ───────────────────────────────────────────────────────────────────────────
// /v2/crawl-setup — DESIGN SYSTEM v2 PREVIEW · in-app crawl setup surface
//
// A PUBLIC, NOINDEX, nav-suppressed, STATIC-MOCK preview under the clean
// top-level /v2/<slug> namespace. Reachable only by typing /v2/crawl-setup —
// nothing links here, and it touches NO real auth-walled route. The global
// product nav is suppressed on /v2/* (components/ConditionalTopNav.tsx).
//
// ROUTE LAW — crawl setup = Console (dark). §0.2 config = WORKING-class:
// brutally quiet — ink + hairline + negative space. NO Population Field, no
// signal fill; the saturated accent is reserved for LIVE READINGS ONLY (§1.3,
// §1.9 signal budget). A crawl setup has no live reading, so nothing here
// breathes. The provenance marker reads DRAFT · UNCAL — this is a config the
// user is composing, not a settled artefact.
//
// This page CONSUMES the shared v2 layer (AppFrame + components/v2/*,
// v2-theme.css) and never re-inlines a raw hex or font name. It is a SERVER
// component; the one interactive affordance (the focusable config inputs) lives
// in the CrawlSetupForm "use client" island in this same directory — inert, no
// API. The summary/review Panel is static, mirroring the form's defaults.
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
import { CrawlSetupForm } from "./CrawlSetupForm";
import "@/styles/v2-theme.css";

export const metadata: Metadata = {
  title: "Crawl setup — Sidira",
  robots: { index: false, follow: false },
};

// ── static mock data (consts, top of file) ─────────────────────────────────

// The review rows mirror the form's defaults — a quiet logbook of the config
// the user is about to commit. `value` numerals print bare in tnum (§1.10:
// recorded config facts are exempt — no ◇ glyph; nothing here is an inferred
// reading). `mono` lifts a value into the data face.
type ReviewRow = { label: string; value: string; mono?: boolean };

const REVIEW: ReviewRow[] = [
  { label: "Seed", value: "https://streamly.example", mono: true },
  { label: "Scope", value: "streamly.example", mono: true },
  { label: "Robots", value: "Respected" },
  { label: "Max depth", value: "4 levels", mono: true },
  { label: "Page budget", value: "2,500 pages", mono: true },
  { label: "Parallelism", value: "4 workers", mono: true },
  { label: "Crawl delay", value: "750 ms / page", mono: true },
  { label: "Cadence", value: "One-off" },
  { label: "Snapshot", value: "streamly · 2026-W25", mono: true },
];

// the est. budget headline for the review panel — a recorded config ceiling,
// not a reading. Bare tnum, no glyph (§1.10).
const EST_PAGES = "2,500";
const EST_WORKERS = "4";

export default function CrawlSetupV2Page() {
  return (
    <AppFrame
      activeNav="crawls"
      title="Crawl setup"
      workspace="Sidira"
      provenance={{ label: "DRAFT", calibrated: false, live: false }}
      actions={
        <Button as="a" href="#" variant="primary">
          Start crawl
        </Button>
      }
    >
      {/* ── crawl setup body — config column + review rail ──────────────────── */}
      <div className="v2-cs">
        {/* a one-line intent header — quiet ink, no signal */}
        <div className="v2-cs-intro">
          <Designator>CONFIGURE</Designator>
          <p className="v2-cs-intro-text">
            Define a site crawl that feeds the product / Streamly sandbox.
            Numerals are recorded config — not a reading.
          </p>
        </div>

        {/* the two-column working layout: config form + review rail */}
        <div className="v2-cs-layout">
          {/* LEFT — the config form (interactive island, inert) */}
          <Panel className="v2-cs-config">
            <CrawlSetupForm />
          </Panel>

          {/* RIGHT — the summary / review panel, before starting */}
          <Panel className="v2-cs-review">
            <div className="v2-cs-review-head">
              <Designator>REVIEW</Designator>
              <span className="v2-cs-review-state">
                <StatusDot />
                <StatusBadge kind="hold">Draft</StatusBadge>
              </span>
            </div>

            {/* the est. ceiling — bare tnum, no glyph (recorded config) */}
            <div className="v2-cs-review-ceiling">
              <span className="v2-cs-ceiling-n v2-mono v2-tnum">{EST_PAGES}</span>
              <span className="v2-cs-ceiling-unit">pages max</span>
              <span className="v2-cs-ceiling-sep" aria-hidden>
                ·
              </span>
              <span className="v2-cs-ceiling-n v2-mono v2-tnum">
                {EST_WORKERS}
              </span>
              <span className="v2-cs-ceiling-unit">workers</span>
            </div>

            {/* the config logbook — hairline-ruled label / value rows */}
            <dl className="v2-cs-review-list">
              {REVIEW.map((r) => (
                <div key={r.label} className="v2-cs-review-row">
                  <dt className="v2-cs-review-label v2-desig">{r.label}</dt>
                  <dd
                    className={
                      r.mono
                        ? "v2-cs-review-value v2-mono v2-tnum"
                        : "v2-cs-review-value"
                    }
                  >
                    {r.value}
                  </dd>
                </div>
              ))}
            </dl>

            {/* commit affordance — primary ink, never the live accent (§1.9) */}
            <Button as="a" href="#" variant="primary" className="v2-cs-commit">
              Start crawl
            </Button>
            <p className="v2-cs-review-foot">
              The crawl runs out-of-process on the sandbox worker. Config is
              recorded with the snapshot; nothing here is a calibrated reading.
            </p>
          </Panel>
        </div>
      </div>

      {/* page-local token-driven styling (no raw hex / no raw font names) */}
      <style>{CS_CSS}</style>
    </AppFrame>
  );
}

// ── page-local CSS — every value is a v2 CSS var or a plain unit (no hex,
//    no rgb/rgba, no font names). Mirrors the SIMS_CSS precedent in
//    app/v2/simulations-list. Covers both this page AND the CrawlSetupForm
//    island's v2-cs-* classes (the island has no <style> of its own). ─────────
const CS_CSS = `
.v2-cs{
  max-width:1120px;
  display:flex;
  flex-direction:column;
  gap:var(--space-room);
}
/* ── intent header ─────────────────────────────────────────────────────────── */
.v2-cs-intro{
  display:flex;
  align-items:baseline;
  gap:var(--space-cozy);
  flex-wrap:wrap;
  max-width:78ch;
}
.v2-cs-intro-text{
  font-size:0.8125rem;
  line-height:1.55;
  color:var(--text-mut);
}
/* ── two-column working layout ─────────────────────────────────────────────── */
.v2-cs-layout{
  display:grid;
  grid-template-columns:minmax(0,1fr) 320px;
  gap:var(--space-room);
  align-items:start;
}
.v2-cs-config{
  padding:var(--space-room);
}
.v2-cs-review{
  position:sticky;
  top:76px;
  padding:var(--space-room);
  display:flex;
  flex-direction:column;
  gap:var(--space-base);
}
/* ── the config form (island) ──────────────────────────────────────────────── */
.v2-cs-form{
  display:flex;
  flex-direction:column;
  gap:var(--space-section);
}
.v2-cs-group{
  display:flex;
  flex-direction:column;
  gap:var(--space-base);
}
.v2-cs-group-head{
  display:flex;
  flex-direction:column;
  gap:var(--space-tight);
  padding-bottom:var(--space-cozy);
  border-bottom:1px solid var(--console-line-40);
}
.v2-cs-group-hint{
  font-size:0.8125rem;
  line-height:1.5;
  color:var(--text-mut);
  max-width:64ch;
}
.v2-cs-group-body{
  display:flex;
  flex-direction:column;
  gap:var(--space-base);
}
/* ── fields ────────────────────────────────────────────────────────────────── */
.v2-cs-field{
  display:flex;
  flex-direction:column;
  gap:var(--space-snug);
  min-width:0;
}
.v2-cs-label{
  font-size:0.8125rem;
  font-weight:450;
  color:var(--text);
}
.v2-cs-input{
  width:100%;
  height:38px;
  padding:0 var(--space-cozy);
  border-radius:var(--r-well);
  border:1px solid var(--console-line-50);
  background:var(--console-700);
  color:var(--text-hi);
  font-family:var(--v2-font-sans);
  font-size:0.875rem;
  transition:border-color .14s var(--ease-out), background .14s var(--ease-out);
}
.v2-cs-input::placeholder{
  color:var(--text-faint);
}
.v2-cs-input:hover{
  border-color:var(--console-line-60);
}
.v2-cs-input:focus{
  outline:none;
  border-color:var(--text-mut);
  background:var(--console-750);
}
.v2-cs-input:focus-visible{
  outline:2px solid var(--signal-dim);
  outline-offset:2px;
}
/* ── numeric field — tnum value + a quiet mono unit suffix in the well ──────── */
.v2-cs-grid{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:var(--space-base);
}
.v2-cs-numwell{
  position:relative;
  display:flex;
  align-items:center;
}
.v2-cs-input--num{
  padding-right:84px;
  text-align:left;
  letter-spacing:0.01em;
}
.v2-cs-unit{
  position:absolute;
  right:var(--space-cozy);
  font-size:0.6875rem;
  letter-spacing:0.06em;
  text-transform:uppercase;
  color:var(--text-mut);
  pointer-events:none;
}
/* ── cadence — inert Chip options; active lifts to full ink ─────────────────── */
.v2-cs-cadence{
  display:flex;
  align-items:center;
  gap:var(--space-snug);
  flex-wrap:wrap;
}
.v2-cs-cadence-opt{
  display:inline-flex;
  padding:0;
  border:none;
  background:transparent;
  cursor:pointer;
  opacity:0.55;
  transition:opacity .14s var(--ease-out);
}
.v2-cs-cadence-opt:hover{
  opacity:1;
}
.v2-cs-cadence-opt--active{
  opacity:1;
}
.v2-cs-cadence-opt:focus-visible{
  outline:2px solid var(--signal-dim);
  outline-offset:2px;
  border-radius:var(--r-well);
}
/* ── toggle row — quiet hairline switch (inert) ─────────────────────────────── */
.v2-cs-toggle{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:var(--space-room);
  cursor:pointer;
}
.v2-cs-toggle-text{
  display:flex;
  flex-direction:column;
  gap:3px;
  min-width:0;
}
.v2-cs-toggle-hint{
  font-size:0.75rem;
  line-height:1.45;
  color:var(--text-mut);
  max-width:52ch;
}
/* native checkbox styled as a Console switch — neutral ink fill, never signal */
.v2-cs-switch{
  flex:0 0 auto;
  appearance:none;
  -webkit-appearance:none;
  position:relative;
  width:38px;
  height:22px;
  border-radius:var(--r-dot);
  border:1px solid var(--console-line-55);
  background:var(--console-700);
  cursor:pointer;
  transition:background .14s var(--ease-out), border-color .14s var(--ease-out);
}
.v2-cs-switch::after{
  content:"";
  position:absolute;
  top:50%;
  left:3px;
  width:14px;
  height:14px;
  border-radius:var(--r-dot);
  background:var(--text-mut);
  transform:translateY(-50%);
  transition:transform .16s var(--ease-out), background .16s var(--ease-out);
}
.v2-cs-switch:checked{
  background:var(--console-750);
  border-color:var(--console-line-60);
}
.v2-cs-switch:checked::after{
  transform:translateY(-50%) translateX(15px);
  background:var(--text-hi);
}
.v2-cs-switch:focus-visible{
  outline:2px solid var(--signal-dim);
  outline-offset:2px;
}
/* ── review rail ──────────────────────────────────────────────────────────── */
.v2-cs-review-head{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:var(--space-base);
  padding-bottom:var(--space-cozy);
  border-bottom:1px solid var(--console-line-40);
}
.v2-cs-review-state{
  display:inline-flex;
  align-items:center;
  gap:var(--space-snug);
}
/* est. ceiling — bare tnum, no glyph (recorded config, §1.10) */
.v2-cs-review-ceiling{
  display:flex;
  align-items:baseline;
  gap:var(--space-tight);
  flex-wrap:wrap;
}
.v2-cs-ceiling-n{
  font-size:1.5rem;
  line-height:1;
  color:var(--text-hi);
  letter-spacing:-0.01em;
}
.v2-cs-ceiling-unit{
  font-size:0.75rem;
  color:var(--text-mut);
}
.v2-cs-ceiling-sep{
  color:var(--text-faint);
  padding:0 var(--space-tight);
}
/* config logbook — hairline-ruled label / value rows (§4.6) */
.v2-cs-review-list{
  display:flex;
  flex-direction:column;
}
.v2-cs-review-row{
  display:grid;
  grid-template-columns:minmax(0,96px) minmax(0,1fr);
  align-items:baseline;
  gap:var(--space-base);
  min-height:34px;
  padding:var(--space-snug) 0;
  border-top:1px solid var(--console-line-40);
}
.v2-cs-review-row:first-child{
  border-top:none;
}
.v2-cs-review-label{
  white-space:nowrap;
}
.v2-cs-review-value{
  color:var(--text);
  font-size:0.8125rem;
  text-align:right;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
}
.v2-cs-commit{
  width:100%;
  margin-top:var(--space-snug);
}
.v2-cs-review-foot{
  font-size:0.75rem;
  line-height:1.5;
  color:var(--text-mut);
}
/* ── responsive — fold the review rail under the config column ─────────────── */
@media(max-width:920px){
  .v2-cs-layout{
    grid-template-columns:1fr;
  }
  .v2-cs-review{
    position:static;
    top:auto;
  }
}
@media(max-width:560px){
  .v2-cs-config,
  .v2-cs-review{
    padding:var(--space-base);
  }
  .v2-cs-grid{
    grid-template-columns:1fr;
  }
  .v2-cs-form{
    gap:var(--space-room);
  }
}
`;
