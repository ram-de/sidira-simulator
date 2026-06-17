// ───────────────────────────────────────────────────────────────────────────
// /v2/personas-list — DESIGN SYSTEM v2 PREVIEW · Personas list (dark Console)
//
// A PUBLIC, NOINDEX, nav-suppressed, STATIC-MOCK preview under the clean
// top-level /v2/<slug> namespace. Reachable only by typing /v2/personas-list —
// nothing links here, and it touches NO real auth-walled route. The global
// product nav is suppressed on /v2/* (components/ConditionalTopNav.tsx).
//
// ARCHETYPE — Console (dark), WORKING-class (§0.2): brutally quiet. Ink +
// hairline + negative space, NO Population Field, no drift. This is the in-app
// index of synthetic-cohort PERSONA PACKS, sitting inside the reusable
// <AppFrame> chrome (left rail + in-content top bar) proven by /v2/app-shell.
//
// The packs carry the ONE candor primitive this surface needs: each pack's
// calibration state is shown HONESTLY via the ◇/◆ CalGlyph (§7.2) — ◇
// UNCALIBRATED for packs graded against no held-out outcome, ◆ GRADED for packs
// scored against a real RCT. Build status carries the only StatusBadge state.
//
// This page CONSUMES the shared v2 layer (components/v2/*, lib/design-v2,
// v2-theme.css) and never re-inlines a raw hex or font name. Server component;
// page-local body CSS is token-driven (CSS vars only), mirroring the
// DASH_CSS / AUTH_CSS precedent in app/v2/app-shell and app/v2/auth.
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
  title: "Personas — Sidira",
  robots: { index: false, follow: false },
};

// ── static mock data (consts, top of file) ─────────────────────────────────

// A persona pack = a synthetic cohort fit to a real population. `segments` and
// `rows` are exempt recorded facts (print bare, tabular). `calibrated` is the
// pack's HONEST calibration state — ◆ GRADED only when scored against a real
// held-out outcome; otherwise ◇ UNCALIBRATED. `status` is the build state.
type Pack = {
  id: string;
  name: string;
  source: string;
  segments: string;
  rows: string;
  calibrated: boolean;
  status: "live" | "hold" | "failed" | "neutral";
  built: string;
};

const PACKS: Pack[] = [
  {
    id: "PER-0142",
    name: "Streamly — synthetic cohort",
    source: "Streamly · org_3F9pXz",
    segments: "6",
    rows: "2,500",
    calibrated: false,
    status: "neutral",
    built: "2026-W25",
  },
  {
    id: "PER-0138",
    name: "Cookie Cats — retention panel",
    source: "Tactile · public A/B",
    segments: "4",
    rows: "90,189",
    calibrated: true,
    status: "neutral",
    built: "2026-W24",
  },
  {
    id: "PER-0131",
    name: "Hillstrom — email RCT cohort",
    source: "MineThatData · public RCT",
    segments: "3",
    rows: "64,000",
    calibrated: true,
    status: "neutral",
    built: "2026-W23",
  },
  {
    id: "PER-0127",
    name: "Candor-law onboarding",
    source: "Sidira · internal",
    segments: "5",
    rows: "4,820",
    calibrated: false,
    status: "live",
    built: "2026-W25",
  },
  {
    id: "PER-0119",
    name: "Upworthy — headline readers",
    source: "Upworthy Archive · public",
    segments: "8",
    rows: "22,718",
    calibrated: false,
    status: "hold",
    built: "2026-W22",
  },
  {
    id: "PER-0104",
    name: "Founders — beta workspace",
    source: "Sidira · org_3Ev",
    segments: "2",
    rows: "1,200",
    calibrated: false,
    status: "failed",
    built: "2026-W20",
  },
];

// status → badge kind + word. `neutral` = a settled, idle pack (no banner).
const BADGE_KIND: Record<Pack["status"], "live" | "hold" | "failed" | "neutral"> =
  {
    live: "live",
    hold: "hold",
    failed: "failed",
    neutral: "neutral",
  };
const BADGE_WORD: Record<Pack["status"], string> = {
  live: "Building",
  hold: "Held",
  failed: "Failed",
  neutral: "Ready",
};

export default function PersonasListV2Page() {
  // exempt recorded summary facts for the index header — bare numerals (§1.10).
  const total = PACKS.length;
  const graded = PACKS.filter((p) => p.calibrated).length;

  return (
    <AppFrame
      activeNav="personas"
      title="Personas"
      workspace="Sidira"
      provenance={{ label: "SNAPSHOT 2026-W25", calibrated: false, live: false }}
      actions={
        <Button as="a" href="#" variant="primary">
          New persona pack
        </Button>
      }
    >
      {/* ── personas index body — quiet WORKING surface ──────────────────── */}
      <div className="v2-plist">
        {/* one-line orientation + bare summary facts */}
        <div className="v2-plist-head">
          <Designator>SYNTHETIC COHORTS · PERSONA PACKS</Designator>
          <h2 className="v2-plist-title">
            The cohorts your readings draw from.
          </h2>
          <p className="v2-plist-sub">
            Each pack is a synthetic population fit to a real source. A pack
            reads <span className="v2-gh">◇</span> uncalibrated until it is
            scored against a held-out outcome, then <span className="v2-gf">◆</span>{" "}
            graded.
          </p>
          <div className="v2-plist-facts">
            <span className="v2-plist-fact">
              <span className="v2-mono v2-tnum">{total}</span> packs
            </span>
            <span className="v2-plist-fact">
              <span className="v2-mono v2-tnum">{graded}</span> graded
            </span>
          </div>
        </div>

        {/* the index table — one Panel, hairline-separated rows */}
        <Panel className="v2-plist-panel">
          <div
            className="v2-plist-table"
            role="table"
            aria-label="Persona packs"
          >
            <div className="v2-plist-row v2-plist-row--head" role="row">
              <span className="v2-pc-id v2-desig" role="columnheader">
                ID
              </span>
              <span className="v2-pc-name v2-desig" role="columnheader">
                Pack
              </span>
              <span className="v2-pc-seg v2-desig" role="columnheader">
                Segments
              </span>
              <span className="v2-pc-rows v2-desig" role="columnheader">
                Rows
              </span>
              <span className="v2-pc-cal v2-desig" role="columnheader">
                Calibration
              </span>
              <span className="v2-pc-status v2-desig" role="columnheader">
                Build
              </span>
            </div>

            {PACKS.map((p) => (
              <a key={p.id} href="#" className="v2-plist-row" role="row">
                <span className="v2-pc-id v2-mono v2-tnum" role="cell">
                  {p.id}
                </span>
                <span className="v2-pc-name" role="cell">
                  <span className="v2-pc-name-main">{p.name}</span>
                  <span className="v2-pc-name-src">{p.source}</span>
                </span>
                <span className="v2-pc-seg v2-mono v2-tnum" role="cell">
                  {p.segments}
                </span>
                <span className="v2-pc-rows v2-mono v2-tnum" role="cell">
                  {p.rows}
                </span>
                <span className="v2-pc-cal" role="cell">
                  <span className="v2-pc-cal-inner">
                    <CalGlyph graded={p.calibrated} />
                    <span className="v2-pc-cal-word">
                      {p.calibrated ? "Graded" : "Uncalibrated"}
                    </span>
                  </span>
                </span>
                <span className="v2-pc-status" role="cell">
                  <span className="v2-pc-badge">
                    {p.status === "live" ? <StatusDot live /> : null}
                    <StatusBadge kind={BADGE_KIND[p.status]}>
                      {BADGE_WORD[p.status]}
                    </StatusBadge>
                  </span>
                </span>
              </a>
            ))}
          </div>
        </Panel>
      </div>

      {/* page-local token-driven styling (no raw hex / no raw font names).
          Injected via dangerouslySetInnerHTML (the same React-safe pattern as
          the root layout's focus-ring <style>): PLIST_CSS contains `"` chars
          (grid-template-areas / content), which a `<style>{string}</style>`
          text child would HTML-escape on the server (&quot;) but leave literal
          on the client — a React 18 text-content hydration mismatch. */}
      <style dangerouslySetInnerHTML={{ __html: PLIST_CSS }} />
    </AppFrame>
  );
}

// ── page-local CSS — every value is a v2 CSS var or a plain unit (no hex,
//    no font names). Mirrors the DASH_CSS / AUTH_CSS precedent. ───────────────
const PLIST_CSS = `
.v2-plist{
  max-width:1080px;
  display:flex;
  flex-direction:column;
  gap:var(--space-section);
}
.v2-plist-head{
  max-width:64ch;
}
.v2-plist-title{
  margin-top:14px;
  font-size:1.75rem;
  line-height:1.1;
  letter-spacing:-0.025em;
  font-weight:600;
  color:var(--text-hi);
  text-wrap:balance;
}
.v2-plist-sub{
  margin-top:10px;
  font-size:0.9375rem;
  line-height:1.55;
  color:var(--text-mut);
}
.v2-plist-sub .v2-gh{color:var(--spread-dim);}
.v2-plist-sub .v2-gf{color:var(--signal-dim);}
.v2-plist-facts{
  margin-top:var(--space-base);
  display:flex;
  align-items:center;
  gap:var(--space-room);
}
.v2-plist-fact{
  font-size:0.8125rem;
  color:var(--text-mut);
}
.v2-plist-fact .v2-mono{
  color:var(--text-hi);
  font-size:0.875rem;
  margin-right:4px;
}
/* index table */
.v2-plist-panel{
  padding:var(--space-room);
}
.v2-plist-table{
  display:flex;
  flex-direction:column;
}
.v2-plist-row{
  display:grid;
  grid-template-columns:96px minmax(0,1fr) 88px 96px 148px 110px;
  align-items:center;
  gap:var(--space-base);
  min-height:52px;
  padding:0 var(--space-snug);
  border-top:1px solid var(--console-line-40);
  color:var(--text);
  font-size:0.875rem;
  transition:background .14s var(--ease-out);
}
.v2-plist-row--head{
  min-height:34px;
  border-top:none;
}
a.v2-plist-row:hover{
  background:var(--console-750);
}
.v2-pc-id{
  font-size:0.8125rem;
  color:var(--text-mut);
}
.v2-pc-name{
  min-width:0;
  display:flex;
  flex-direction:column;
  gap:2px;
}
.v2-pc-name-main{
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
  color:var(--text-hi);
}
.v2-pc-name-src{
  font-size:0.75rem;
  color:var(--text-mut);
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
}
/* numeric columns are right-aligned (§4.6 logbook) */
.v2-pc-seg,
.v2-pc-rows{
  text-align:right;
  color:var(--text);
}
.v2-plist-row--head .v2-pc-seg,
.v2-plist-row--head .v2-pc-rows{
  text-align:right;
}
.v2-pc-cal-inner{
  display:inline-flex;
  align-items:center;
  gap:var(--space-tight);
}
.v2-pc-cal-word{
  font-size:0.8125rem;
  color:var(--text-mut);
}
.v2-pc-badge{
  display:inline-flex;
  align-items:center;
  gap:var(--space-snug);
}
@media(max-width:880px){
  .v2-plist-row{
    grid-template-columns:1fr auto;
    grid-template-areas:"name status" "meta cal";
    row-gap:6px;
    padding:var(--space-cozy) var(--space-snug);
    align-items:start;
    min-height:0;
  }
  .v2-pc-id{display:none;}
  .v2-pc-name{grid-area:name;}
  .v2-pc-name-main{white-space:normal;}
  .v2-pc-status{grid-area:status;justify-self:end;}
  .v2-pc-cal{grid-area:cal;justify-self:end;}
  /* fold segments + rows into one meta line on narrow widths */
  .v2-pc-seg{grid-area:meta;text-align:left;color:var(--text-mut);font-size:0.8125rem;}
  .v2-pc-seg::before{content:"seg ";letter-spacing:0.04em;}
  .v2-pc-rows{display:none;}
  .v2-plist-row--head{display:none;}
}
@media(max-width:520px){
  .v2-plist-facts{gap:var(--space-base);}
  .v2-pc-cal-word{display:none;}
}
`;
