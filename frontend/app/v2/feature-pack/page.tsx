// ───────────────────────────────────────────────────────────────────────────
// /v2/feature-pack — DESIGN SYSTEM v2 PREVIEW · in-app Feature pack config
//
// A PUBLIC, NOINDEX, nav-suppressed, STATIC-MOCK preview under the clean
// top-level /v2/<slug> namespace. Reachable only by typing /v2/feature-pack —
// nothing links here, and it touches NO real auth-walled route. The global
// product nav is suppressed on /v2/* (components/ConditionalTopNav.tsx).
//
// ARCHETYPE — Console (dark), WORKING-class (§0.2): combobox-heavy config, so
// brutally quiet — ink + hairline + negative space. NO Population Field, no
// signal fill; the saturated accent is reserved for LIVE READINGS ONLY (§1.3,
// §1.9 signal budget). This is the feature-store column selection/config for
// building a persona pack: pick which columns the synthetic cohort is fit on.
//
// The "combobox config" feel is conveyed STATICALLY — included vs available
// columns, grouped by domain, each row a recorded fact (type, coverage). The
// only candor primitive: the pack is ◇ UNCALIBRATED until graded (§7.2), shown
// once on the summary panel; everything else here is config, not a reading.
//
// This page CONSUMES the shared v2 layer (AppFrame + components/v2/*,
// v2-theme.css) and never re-inlines a raw hex or font name. Server component;
// the page-local body CSS is token-driven (CSS vars only), mirroring the
// SIMS_CSS / PLIST_CSS precedent. Every control here is intentionally inert, so
// the whole file stays a server component — no "use client" island is needed.
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
  title: "Feature pack — Sidira",
  robots: { index: false, follow: false },
};

// ── static mock data (consts, top of file) ─────────────────────────────────

// A feature-store column the pack can be fit on. `type` is numeric/categorical;
// `coverage` is the % of the population with a non-null value — an exempt
// recorded fact (print bare, tnum). `included` is the include/exclude state:
// selected columns feed the persona fit, available ones sit unselected.
type FeatType = "numeric" | "categorical";
type Feature = {
  key: string; // the feature-store column key (mono)
  label: string; // human label
  type: FeatType;
  coverage: string; // "%" — bare tnum recorded fact
  included: boolean;
};

// Feature-store columns grouped by domain (§4.6 logbook grouping). Streamly-
// flavored: a 6-segment synthetic-cohort source. 14 columns across 4 groups.
type Group = { name: string; features: Feature[] };

const GROUPS: Group[] = [
  {
    name: "Engagement",
    features: [
      { key: "sessions_28d", label: "Sessions (28d)", type: "numeric", coverage: "99.4", included: true },
      { key: "watch_minutes_28d", label: "Watch minutes (28d)", type: "numeric", coverage: "98.1", included: true },
      { key: "active_days_28d", label: "Active days (28d)", type: "numeric", coverage: "99.4", included: true },
      { key: "last_session_recency", label: "Days since last session", type: "numeric", coverage: "99.4", included: false },
    ],
  },
  {
    name: "Tenure",
    features: [
      { key: "account_age_days", label: "Account age (days)", type: "numeric", coverage: "100.0", included: true },
      { key: "signup_cohort", label: "Signup cohort", type: "categorical", coverage: "100.0", included: true },
      { key: "acquisition_channel", label: "Acquisition channel", type: "categorical", coverage: "94.7", included: false },
    ],
  },
  {
    name: "Monetization",
    features: [
      { key: "plan_tier", label: "Plan tier", type: "categorical", coverage: "100.0", included: true },
      { key: "ltv_to_date", label: "LTV to date", type: "numeric", coverage: "96.3", included: true },
      { key: "trial_converted", label: "Trial converted", type: "categorical", coverage: "88.5", included: false },
      { key: "billing_failures_90d", label: "Billing failures (90d)", type: "numeric", coverage: "100.0", included: false },
    ],
  },
  {
    name: "Content",
    features: [
      { key: "top_genre", label: "Top genre", type: "categorical", coverage: "97.2", included: true },
      { key: "genre_entropy", label: "Genre diversity", type: "numeric", coverage: "97.2", included: true },
      { key: "device_class", label: "Primary device class", type: "categorical", coverage: "91.8", included: false },
    ],
  },
];

// type → short mono designator shown in the row (recorded schema fact).
const TYPE_MARK: Record<FeatType, string> = {
  numeric: "NUM",
  categorical: "CAT",
};

// inert toolbar filters (§4.8 chips) — resting designators, no signal.
const FILTERS = ["ALL", "INCLUDED", "AVAILABLE"] as const;

export default function FeaturePackV2Page() {
  // exempt recorded summary facts for the header — bare numerals (§1.10).
  const allFeatures = GROUPS.flatMap((g) => g.features);
  const selected = allFeatures.filter((f) => f.included).length;
  const total = allFeatures.length;

  return (
    <AppFrame
      activeNav="feature-packs"
      title="Feature pack"
      workspace="Sidira"
      provenance={{ label: "SNAPSHOT 2026-W25", calibrated: false, live: false }}
      actions={
        <Button as="a" href="#" variant="primary">
          Build pack
        </Button>
      }
    >
      {/* ── feature-pack config body — quiet WORKING surface ─────────────────── */}
      <div className="v2-fp">
        {/* summary panel — pack identity + the few config facts that matter */}
        <Panel className="v2-fp-summary">
          <div className="v2-fp-summary-head">
            <Designator>FEATURE PACK · COLUMN SELECTION</Designator>
            <h2 className="v2-fp-name">Streamly — synthetic cohort</h2>
            <p className="v2-fp-src">Streamly · org_3F9pXz · feature store</p>
          </div>

          {/* config facts — bare tnum recorded values, hairline-ruled */}
          <dl className="v2-fp-stats">
            <div className="v2-fp-stat">
              <dt className="v2-desig">Features selected</dt>
              <dd className="v2-mono">
                <span className="v2-tnum">{selected}</span>
                <span className="v2-fp-stat-of"> / </span>
                <span className="v2-tnum">{total}</span>
              </dd>
            </div>
            <div className="v2-fp-stat">
              <dt className="v2-desig">Population coverage</dt>
              <dd className="v2-mono v2-tnum">96.4%</dd>
            </div>
            <div className="v2-fp-stat">
              <dt className="v2-desig">Stability threshold</dt>
              <dd className="v2-mono v2-tnum">0.60</dd>
            </div>
            <div className="v2-fp-stat">
              <dt className="v2-desig">Build status</dt>
              <dd className="v2-fp-stat-badge">
                <StatusBadge kind="neutral">Draft</StatusBadge>
              </dd>
            </div>
          </dl>

          {/* one-line calibration honesty note (§7.2) — the only ◇ on the page */}
          <p className="v2-fp-cal">
            <CalGlyph />
            <span className="v2-fp-cal-text">
              This pack is uncalibrated — it has not been scored against a
              held-out outcome. Coverage and column types are recorded schema
              facts.
            </span>
          </p>
        </Panel>

        {/* toolbar — inert filter chips + a bare selected count */}
        <div className="v2-fp-toolbar">
          <div
            className="v2-fp-filters"
            role="group"
            aria-label="Filter feature columns"
          >
            {FILTERS.map((f, i) => (
              <a
                key={f}
                href="#"
                className={
                  i === 0
                    ? "v2-fp-filter v2-fp-filter--active"
                    : "v2-fp-filter"
                }
                aria-current={i === 0 ? "true" : undefined}
              >
                <Chip>{f}</Chip>
              </a>
            ))}
          </div>
          <div className="v2-fp-count">
            <span className="v2-mono v2-tnum">{selected}</span> included of{" "}
            <span className="v2-mono v2-tnum">{total}</span> columns
          </div>
        </div>

        {/* the column selection — one Panel per group, hairline-ruled rows */}
        {GROUPS.map((group) => {
          const groupSel = group.features.filter((f) => f.included).length;
          return (
            <Panel key={group.name} className="v2-fp-group">
              {/* group header — domain name + bare included/total fact */}
              <div className="v2-fp-group-head">
                <Designator>{group.name}</Designator>
                <span className="v2-fp-group-count">
                  <span className="v2-mono v2-tnum">{groupSel}</span>
                  <span className="v2-fp-group-of"> / </span>
                  <span className="v2-mono v2-tnum">
                    {group.features.length}
                  </span>{" "}
                  included
                </span>
              </div>

              <div
                className="v2-fp-table"
                role="table"
                aria-label={`${group.name} feature columns`}
              >
                {/* column header row */}
                <div className="v2-fp-row v2-fp-row--head" role="row">
                  <span className="v2-fp-c-sel v2-desig" role="columnheader">
                    Use
                  </span>
                  <span className="v2-fp-c-name v2-desig" role="columnheader">
                    Column
                  </span>
                  <span className="v2-fp-c-type v2-desig" role="columnheader">
                    Type
                  </span>
                  <span className="v2-fp-c-cov v2-desig" role="columnheader">
                    Coverage
                  </span>
                  <span className="v2-fp-c-state v2-desig" role="columnheader">
                    State
                  </span>
                </div>

                {group.features.map((f) => (
                  <div
                    key={f.key}
                    className={
                      f.included
                        ? "v2-fp-row v2-fp-row--on"
                        : "v2-fp-row v2-fp-row--off"
                    }
                    role="row"
                  >
                    {/* include state — a quiet check dot (no signal fill) */}
                    <span className="v2-fp-c-sel" role="cell">
                      {f.included ? (
                        <StatusDot />
                      ) : (
                        <span className="v2-fp-sel-empty" aria-hidden />
                      )}
                    </span>

                    {/* column — human label over the mono store key */}
                    <span className="v2-fp-c-name" role="cell">
                      <span className="v2-fp-name-main">{f.label}</span>
                      <span className="v2-fp-name-key v2-mono">{f.key}</span>
                    </span>

                    {/* schema type — recorded fact, mono designator */}
                    <span className="v2-fp-c-type" role="cell">
                      <span className="v2-fp-type-mark v2-mono">
                        {TYPE_MARK[f.type]}
                      </span>
                    </span>

                    {/* coverage — bare tnum recorded fact, right-aligned */}
                    <span
                      className="v2-fp-c-cov v2-mono v2-tnum"
                      role="cell"
                    >
                      {f.coverage}%
                    </span>

                    {/* include/exclude — quiet word badge; included reads ink */}
                    <span className="v2-fp-c-state" role="cell">
                      <StatusBadge kind="neutral">
                        {f.included ? "Included" : "Available"}
                      </StatusBadge>
                    </span>
                  </div>
                ))}
              </div>
            </Panel>
          );
        })}

        {/* one-line config footnote for the whole surface */}
        <p className="v2-fp-foot">
          <Designator>CONFIG</Designator>
          <span className="v2-fp-foot-text">
            Included columns feed the persona fit; available columns are present
            in the store but excluded from this pack. Coverage is the share of
            the population with a non-null value — a recorded schema fact.
          </span>
        </p>
      </div>

      {/* page-local token-driven styling (no raw hex / no raw font names).
          dangerouslySetInnerHTML (root-layout pattern): FP_CSS holds `"` chars
          (grid-template-areas) that a `<style>{string}</style>` text child would
          HTML-escape server-side only → React 18 hydration text mismatch. */}
      <style dangerouslySetInnerHTML={{ __html: FP_CSS }} />
    </AppFrame>
  );
}

// ── page-local CSS — every value is a v2 CSS var or a plain unit (no hex,
//    no font names). Mirrors the SIMS_CSS / PLIST_CSS precedent. ──────────────
const FP_CSS = `
.v2-fp{
  max-width:1080px;
  display:flex;
  flex-direction:column;
  gap:var(--space-room);
}
/* ── summary panel ─────────────────────────────────────────────────────── */
.v2-fp-summary{
  padding:var(--space-room);
  display:flex;
  flex-direction:column;
  gap:var(--space-base);
}
.v2-fp-summary-head{
  max-width:64ch;
}
.v2-fp-name{
  margin-top:10px;
  font-size:1.375rem;
  line-height:1.15;
  letter-spacing:-0.02em;
  font-weight:600;
  color:var(--text-hi);
}
.v2-fp-src{
  margin-top:6px;
  font-size:0.8125rem;
  color:var(--text-mut);
}
/* config facts — a quiet hairline-topped row of bare numerals */
.v2-fp-stats{
  margin:0;
  display:flex;
  flex-wrap:wrap;
  gap:var(--space-vast);
  padding-top:var(--space-base);
  border-top:1px solid var(--console-line-40);
}
.v2-fp-stat{
  display:flex;
  flex-direction:column;
  gap:6px;
}
.v2-fp-stat dd{
  margin:0;
  font-size:1.0625rem;
  color:var(--text-hi);
}
.v2-fp-stat-of{
  color:var(--text-mut);
}
.v2-fp-stat-badge{
  margin:0;
  display:flex;
  align-items:center;
  min-height:24px;
}
/* calibration honesty note */
.v2-fp-cal{
  display:flex;
  align-items:baseline;
  gap:var(--space-snug);
  max-width:72ch;
  padding-top:var(--space-snug);
}
.v2-fp-cal-text{
  font-size:0.8125rem;
  line-height:1.55;
  color:var(--text-mut);
}
/* ── toolbar ───────────────────────────────────────────────────────────── */
.v2-fp-toolbar{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:var(--space-base);
  flex-wrap:wrap;
}
.v2-fp-filters{
  display:flex;
  align-items:center;
  gap:var(--space-snug);
  flex-wrap:wrap;
}
.v2-fp-filter{
  display:inline-flex;
  opacity:0.62;
  transition:opacity .14s var(--ease-out);
}
.v2-fp-filter:hover{
  opacity:1;
}
.v2-fp-filter--active{
  opacity:1;
}
.v2-fp-count{
  font-size:0.8125rem;
  color:var(--text-mut);
  white-space:nowrap;
}
.v2-fp-count .v2-mono{
  color:var(--text);
}
/* ── group panel + table ───────────────────────────────────────────────── */
.v2-fp-group{
  padding:var(--space-snug) var(--space-room) var(--space-room);
}
.v2-fp-group-head{
  display:flex;
  align-items:baseline;
  justify-content:space-between;
  gap:var(--space-base);
  padding:var(--space-base) 0 var(--space-snug);
}
.v2-fp-group-count{
  font-size:0.75rem;
  color:var(--text-mut);
  white-space:nowrap;
}
.v2-fp-group-count .v2-mono{
  color:var(--text);
}
.v2-fp-group-of{
  color:var(--text-mut);
}
.v2-fp-table{
  display:flex;
  flex-direction:column;
}
.v2-fp-row{
  display:grid;
  grid-template-columns:44px minmax(0,1fr) 88px 104px 132px;
  align-items:center;
  gap:var(--space-base);
  min-height:50px;
  padding:var(--space-snug);
  border-top:1px solid var(--console-line-40);
  color:var(--text);
  font-size:0.875rem;
}
.v2-fp-row--head{
  min-height:36px;
  border-top:none;
  align-items:end;
}
/* excluded rows recede — quieter ink, never a separate color (§1.6) */
.v2-fp-row--off{
  color:var(--text-mut);
}
.v2-fp-row--off .v2-fp-name-main{
  color:var(--text-mut);
}
/* use / include-state cell — a quiet check dot, or a hollow placeholder */
.v2-fp-c-sel{
  display:inline-flex;
  align-items:center;
  justify-content:flex-start;
}
.v2-fp-sel-empty{
  display:inline-block;
  width:7px;
  height:7px;
  border-radius:var(--r-dot);
  border:1px solid var(--console-line-55);
}
/* column cell — label (hi) over mono store key (mut) */
.v2-fp-c-name{
  min-width:0;
  display:flex;
  flex-direction:column;
  gap:2px;
}
.v2-fp-name-main{
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
  color:var(--text-hi);
  font-weight:450;
}
.v2-fp-name-key{
  font-size:0.75rem;
  color:var(--text-mut);
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
}
/* schema type — small mono designator */
.v2-fp-type-mark{
  font-size:0.6875rem;
  letter-spacing:0.06em;
  color:var(--text-mut);
}
/* coverage — right-aligned recorded fact (§4.6 logbook) */
.v2-fp-c-cov{
  text-align:right;
  color:var(--text);
}
.v2-fp-row--head .v2-fp-c-cov{
  text-align:right;
}
.v2-fp-row--off .v2-fp-c-cov{
  color:var(--text-mut);
}
.v2-fp-c-state{
  display:inline-flex;
  align-items:center;
  justify-content:flex-start;
}
/* ── config footnote ───────────────────────────────────────────────────── */
.v2-fp-foot{
  display:flex;
  align-items:baseline;
  gap:var(--space-cozy);
  max-width:80ch;
}
.v2-fp-foot-text{
  font-size:0.8125rem;
  line-height:1.55;
  color:var(--text-mut);
}
/* ── responsive — fold secondary columns under the column name ───────────── */
@media(max-width:880px){
  .v2-fp-stats{gap:var(--space-room);}
  .v2-fp-row{
    grid-template-columns:28px minmax(0,1fr) auto;
    grid-template-areas:
      "sel name state"
      "sel meta state";
    row-gap:4px;
    align-items:center;
  }
  .v2-fp-c-sel{grid-area:sel;align-self:center;}
  .v2-fp-c-name{grid-area:name;}
  .v2-fp-c-state{grid-area:state;justify-self:end;align-self:center;}
  /* type + coverage collapse into one quiet meta line under the name */
  .v2-fp-c-type{
    grid-area:meta;
    display:inline-flex;
  }
  .v2-fp-c-cov{
    grid-area:meta;
    justify-self:start;
    text-align:left;
    margin-left:54px;
    color:var(--text-mut);
  }
  .v2-fp-row--head{display:none;}
}
@media(max-width:560px){
  .v2-fp-toolbar{align-items:flex-start;flex-direction:column;}
  .v2-fp-summary,
  .v2-fp-group{
    padding:var(--space-snug) var(--space-cozy) var(--space-cozy);
  }
  .v2-fp-stats{gap:var(--space-base) var(--space-room);}
}
`;
