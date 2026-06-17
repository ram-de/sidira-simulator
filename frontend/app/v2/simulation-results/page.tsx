// ───────────────────────────────────────────────────────────────────────────
// /v2/simulation-results — DESIGN SYSTEM v2 PREVIEW · simulation RESULTS (the
// reading the simulation produced — the "money screen").
//
// A PUBLIC, NOINDEX, nav-suppressed, STATIC-MOCK preview under the clean
// top-level /v2/<slug> namespace. Reachable only by typing /v2/simulation-results
// — nothing links here, and it touches NO real auth-walled route. The global
// product nav is suppressed on /v2/* (components/ConditionalTopNav.tsx).
//
// ARCHETYPE — Console (dark), and the ONE §0.2 SHOWPIECE on the rollout: a
// simulation result earns the page's single focal figure. The live WebGL
// Population Field ships later with /v2/landing; until then this page uses the
// FROZEN DistributionPoster (static SVG, §5.5/§7.1) as the centerpiece — a
// legitimate "frozen poster of the settled shape." NO WebGL field is built here.
// Per the §0.2 80/20 rule everything OUTSIDE that one figure stays WORKING-quiet:
// ink + hairline + negative space, no signal fill.
//
// CANDOR LAW: this reading is UNCALIBRATED. It has not been graded against a
// held-out outcome, so the result stays DIRECTIONAL — control vs treatment, sign
// and order only, no calibrated magnitude. Doubt lives in the ◇ glyph and the
// spread/±, NEVER in red/green valence (§1.6: a verdict is not a color). The
// marks are neutral ink; the only saturated accent is the arm tints inside the
// poster figure itself.
//
// This page CONSUMES the shared v2 layer (AppFrame + components/v2/*,
// v2-theme.css) and never re-inlines a raw hex or font name. Server component;
// every control here is inert static markup, so no "use client" island is needed.
// ───────────────────────────────────────────────────────────────────────────
import type { Metadata } from "next";
import {
  AppFrame,
  Panel,
  Designator,
  Button,
  CalGlyph,
  ProvenanceBar,
  DistributionPoster,
  type ProvSeg,
  type Bar,
} from "@/components/v2";
import "@/styles/v2-theme.css";

export const metadata: Metadata = {
  title: "Results — Sidira",
  robots: { index: false, follow: false },
};

// ── static mock data (consts, top of file) ─────────────────────────────────

// The reading, as a candor-honest record. `hypothesis` is the question asked;
// `result` is the DIRECTIONAL verdict (sign + order only). `lift` carries the ◇
// glyph (inferred → uncalibrated, §7.2); `spread` is the ± that holds the doubt.
// `arms`, `model`, `n`, `snapshot` are EXEMPT recorded facts (§1.10) — print bare.
const READING = {
  hypothesis:
    "Does a softer downgrade nudge keep more Streamly viewers from cancelling?",
  // directional verdict — neutral words, no valence color
  result: "Treatment separates above control",
  dir: "up" as const,
  lift: "+3.6 pp",
  spread: "± 1.9",
  // recorded facts
  snapshot: "2026-W25",
  arms: "control · treatment",
  model: "groq/llama-3.3-70b",
} as const;

// directional sign-mark — a NEUTRAL mono caret, never a valence color (§1.6).
const DIR_MARK: Record<"up" | "down" | "flat", string> = {
  up: "▲",
  down: "▼",
  flat: "—",
};

// the figure's region silkscreen (§7.3): snapshot · arms · model · n. All bare
// recorded facts; the region's calibration state is carried ONCE by the bar's ◇.
const PROV_SEGS: ProvSeg[] = [
  { content: `SNAPSHOT ${READING.snapshot}` },
  { content: "2 ARMS", bold: true },
  { content: READING.model },
  { content: <span className="v2-tnum">n=2,500</span> },
];

// the small stats panel — control n, treatment n, separation (pp), sentiment.
// n values are bare recorded facts; separation is the inferred directional
// reading (so it wears ◇, attached in the row below); sentiment is a recorded
// pooled score, printed plainly.
type Stat = { k: string; v: string; glyph?: boolean };
const STATS: Stat[] = [
  { k: "Control n", v: "1,250" },
  { k: "Treatment n", v: "1,250" },
  { k: "Separation", v: "3.6 pp", glyph: true },
  { k: "Sentiment", v: "0.41" },
];

// ── the frozen poster bins ──────────────────────────────────────────────────
// Per-arm dodged bin counts over the reaction axis (rejects ← reaction → adopts).
// Bar height = agents in bin (a recorded count). The treatment arm sits slightly
// right of control — the directional separation, frozen. Mirrors the prop shape
// the persona-detail record feeds DistributionPoster (type Bar = {x,h}).
const CONTROL_BARS: Bar[] = [
  { x: 34, h: 14 }, { x: 66, h: 34 }, { x: 98, h: 62 }, { x: 130, h: 90 },
  { x: 162, h: 84 }, { x: 194, h: 56 }, { x: 226, h: 28 }, { x: 258, h: 12 },
];
const TREAT_BARS: Bar[] = [
  { x: 42, h: 10 }, { x: 74, h: 26 }, { x: 106, h: 52 }, { x: 138, h: 80 },
  { x: 170, h: 94 }, { x: 202, h: 70 }, { x: 234, h: 40 }, { x: 266, h: 18 },
];

export default function SimulationResultsV2Page() {
  return (
    <AppFrame
      activeNav="simulations"
      title="Results · Streamly downgrade nudge"
      workspace="Sidira"
      provenance={{ label: "SNAPSHOT 2026-W25", calibrated: false, live: false }}
      actions={
        <Button as="a" href="#" variant="secondary">
          Open setup
        </Button>
      }
    >
      {/* ── results body ────────────────────────────────────────────────────── */}
      <div className="v2-res">
        {/* ── (1) the headline reading block — the candor-honest verdict ──────── */}
        <Panel className="v2-res-head">
          <p className="v2-res-hyp">
            <Designator>Hypothesis</Designator>
            <span className="v2-res-hyp-text">{READING.hypothesis}</span>
          </p>

          {/* the directional reading: neutral words, then the bare lift + ◇ + ± */}
          <div className="v2-res-verdict">
            <span className="v2-res-verdict-line">{READING.result}</span>
            <span className="v2-res-lift">
              <span
                className={`v2-res-dir v2-res-dir--${READING.dir} v2-mono`}
                aria-hidden
              >
                {DIR_MARK[READING.dir]}
              </span>
              <span className="v2-res-lift-mag v2-mono v2-tnum">
                {READING.lift}
              </span>
              <CalGlyph />
              <span className="v2-res-spread v2-mono v2-tnum">
                {READING.spread}
              </span>
            </span>
          </div>

          <p className="v2-res-verdict-sub">
            Directional only — sign and order, not a calibrated magnitude.
          </p>
        </Panel>

        {/* ── (2) the centerpiece — frozen DistributionPoster (§5.5/§7.1) ─────── */}
        <Panel className="v2-res-figure">
          {/* region silkscreen strip ABOVE the figure: snapshot · arms · model · n */}
          <div className="v2-res-figure-top">
            <span className="v2-desig">Settled distribution</span>
            <ProvenanceBar calibrated={false} segments={PROV_SEGS} align="end" />
          </div>

          <figure className="v2-res-poster" aria-label="Control versus treatment reaction distribution, frozen.">
            <DistributionPoster
              controlBars={CONTROL_BARS}
              treatBars={TREAT_BARS}
              pooledMeanX={166}
              controlMeanX={150}
              treatMeanX={184}
              pooledMeanLabel="MEAN +3.6 pp"
              calibrated={false}
              ci={{ x: 150, width: 52 }}
              footerNote="2,500 AGENTS · BINNED · BAR HEIGHT = AGENT COUNT"
              ariaLabel="Binned reaction histogram, dodged by arm: control left-shifted, treatment right-shifted, over rejects ← reaction → adopts. Separation +3.6 pp, uncalibrated."
            />

            {/* arm legend — the only saturated tints on the page (the figure) */}
            <figcaption className="v2-res-legend">
              <span className="v2-res-leg">
                <ArmDot kind="ctl" />
                CONTROL · <span className="v2-tnum">1,250</span>
              </span>
              <span className="v2-res-leg">
                TREATMENT · <span className="v2-tnum">1,250</span>
                <ArmDot kind="trt" />
              </span>
            </figcaption>
          </figure>

          <p className="v2-res-poster-note">
            A frozen poster of the settled shape — bar height is an agent count,
            printed plainly; the separation is an estimate and wears its ◇. On the
            live field this same distribution settles in motion; here it is still.
          </p>
        </Panel>

        {/* ── (3) the small stats panel — recorded facts, tabular numerals ────── */}
        <Panel className="v2-res-stats">
          <div className="v2-res-stats-grid">
            {STATS.map((s) => (
              <div key={s.k} className="v2-res-stat">
                <span className="v2-res-stat-k v2-desig">{s.k}</span>
                <span className="v2-res-stat-v v2-mono v2-tnum">
                  {s.v}
                  {s.glyph ? <CalGlyph /> : null}
                </span>
              </div>
            ))}
          </div>
        </Panel>

        {/* ── (4) candor footnote — the law, stated plainly ───────────────────── */}
        <p className="v2-res-foot">
          <Designator>Reading</Designator>
          <span className="v2-res-foot-text">
            This reading is <CalGlyph /> uncalibrated. It stays directional —
            control versus treatment, sign and order only — until it is graded
            against a held-out outcome. No calibrated magnitude is claimed; the
            doubt lives in the glyph and the spread, not in a verdict color.
          </span>
        </p>
      </div>

      {/* page-local token-driven styling (no raw hex / no raw font names) */}
      <style>{RES_CSS}</style>
    </AppFrame>
  );
}

// arm-tinted legend dot — the figure's own saturated accent (§1.9 budget; the
// arm tints are the one place saturation is allowed on this WORKING-quiet page).
function ArmDot({ kind }: { kind: "ctl" | "trt" }) {
  return (
    <span
      aria-hidden
      className={`v2-res-armdot v2-res-armdot--${kind}`}
    />
  );
}

// ── page-local CSS — every value is a v2 CSS var or a plain unit (no hex,
//    no rgb/rgba, no font names). Scoped to .v2-res. ───────────────────────────
const RES_CSS = `
.v2-res{
  max-width:920px;
  display:flex;
  flex-direction:column;
  gap:var(--space-room);
}
/* ── (1) headline reading block ────────────────────────────────────────────── */
.v2-res-head{
  padding:var(--space-room) var(--space-room) var(--space-base);
  display:flex;
  flex-direction:column;
  gap:var(--space-base);
}
.v2-res-hyp{
  display:flex;
  flex-direction:column;
  gap:var(--space-snug);
}
.v2-res-hyp-text{
  font-size:1.0625rem;
  line-height:1.45;
  letter-spacing:-0.01em;
  color:var(--text-hi);
  max-width:54ch;
}
/* the directional verdict — words (hi ink) + the bare lift cluster, baseline-set */
.v2-res-verdict{
  display:flex;
  align-items:baseline;
  justify-content:space-between;
  gap:var(--space-room);
  flex-wrap:wrap;
  padding-top:var(--space-snug);
  border-top:1px solid var(--console-line-40);
}
.v2-res-verdict-line{
  font-size:1rem;
  color:var(--text);
  font-weight:450;
}
.v2-res-lift{
  display:inline-flex;
  align-items:baseline;
  gap:var(--space-snug);
  white-space:nowrap;
}
/* sign-mark — NEUTRAL ink, never valence color (§1.6) */
.v2-res-dir{
  font-size:0.9rem;
  color:var(--text-mut);
  transform:translateY(-1px);
}
.v2-res-dir--up,
.v2-res-dir--down,
.v2-res-dir--flat{
  color:var(--text-mut);
}
.v2-res-lift-mag{
  font-size:1.75rem;
  line-height:1;
  letter-spacing:-0.02em;
  color:var(--text-hi);
}
.v2-res-spread{
  font-size:0.9375rem;
  color:var(--spread);
}
.v2-res-verdict-sub{
  font-size:0.8125rem;
  line-height:1.5;
  color:var(--text-mut);
}
/* ── (2) the centerpiece figure ────────────────────────────────────────────── */
.v2-res-figure{
  padding:var(--space-base) var(--space-room) var(--space-room);
  display:flex;
  flex-direction:column;
  gap:var(--space-base);
}
.v2-res-figure-top{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:var(--space-base);
  flex-wrap:wrap;
  padding-bottom:var(--space-snug);
  border-bottom:1px solid var(--console-line-40);
}
.v2-res-poster{
  margin:0;
  display:flex;
  flex-direction:column;
  gap:var(--space-cozy);
}
.v2-res-legend{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:var(--space-base);
  font-family:var(--v2-font-mono);
  font-size:10.5px;
  letter-spacing:0.04em;
  color:var(--text-mut);
}
.v2-res-leg{
  display:inline-flex;
  align-items:center;
}
.v2-res-armdot{
  width:7px;
  height:7px;
  border-radius:var(--r-dot);
  display:inline-block;
  vertical-align:middle;
  margin:0 var(--space-snug);
}
.v2-res-armdot--ctl{ background:var(--arm-control); }
.v2-res-armdot--trt{ background:var(--arm-treat); }
.v2-res-poster-note{
  font-size:0.8125rem;
  line-height:1.55;
  color:var(--text-mut);
  max-width:64ch;
}
/* ── (3) small stats panel ─────────────────────────────────────────────────── */
.v2-res-stats{
  padding:var(--space-base) var(--space-room);
}
.v2-res-stats-grid{
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:var(--space-base);
}
.v2-res-stat{
  display:flex;
  flex-direction:column;
  gap:var(--space-snug);
  min-width:0;
}
.v2-res-stat-k{
  color:var(--text-mut);
}
.v2-res-stat-v{
  display:inline-flex;
  align-items:baseline;
  gap:var(--space-snug);
  font-size:1.25rem;
  line-height:1;
  letter-spacing:-0.01em;
  color:var(--text-hi);
}
/* ── (4) candor footnote ───────────────────────────────────────────────────── */
.v2-res-foot{
  display:flex;
  align-items:baseline;
  gap:var(--space-cozy);
  max-width:80ch;
}
.v2-res-foot-text{
  font-size:0.8125rem;
  line-height:1.6;
  color:var(--text-mut);
}
/* ── responsive ────────────────────────────────────────────────────────────── */
@media(max-width:720px){
  .v2-res-stats-grid{grid-template-columns:repeat(2,minmax(0,1fr));row-gap:var(--space-room);}
  .v2-res-verdict{flex-direction:column;align-items:flex-start;gap:var(--space-base);}
}
@media(max-width:440px){
  .v2-res-stats-grid{grid-template-columns:1fr;}
  .v2-res-legend{flex-direction:column;align-items:flex-start;gap:var(--space-snug);}
}
`;
