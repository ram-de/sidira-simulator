// ───────────────────────────────────────────────────────────────────────────
// /v2/persona-detail — DESIGN SYSTEM v2 PREVIEW · SHEET (light) RECORD page
// (flagged · NOINDEX · unlinked).
//
// A persona-pack archival record: the Streamly synthetic cohort (v2), filed as a
// printed fact. Per design-system-v2.md §0.1/§0.2 this is a RECORD-class, light
// Sheet route — STILL: serif prose, a Provenance Spine in the left binder margin,
// airy chapter rhythm, NO canvas, NO drift, NO motion beyond the once-only page
// reveal. A frozen DistributionPoster (static SVG, §5.5/§7.1) is permitted as a
// figure; a live field is NOT. NO AppFrame, NO dark masthead — no mode inversion.
//
// This page CONSUMES the shared v2 Sheet layer (SheetShell, SheetTopBar,
// RecordGrid, ProvenanceSpine, Prose, SheetSection + the §6.4 ConsoleWell /
// DistributionPoster figure from @/components/v2). It re-inlines no tokens — only
// the scoped `var(--sheet-*)` / `var(--v2-font-*)` CSS vars and the design-v2
// token constants. Reachable ONLY by typing /v2/persona-detail.
// ───────────────────────────────────────────────────────────────────────────
import type { Metadata } from "next";
import {
  SheetShell,
  SheetTopBar,
  RecordGrid,
  ProvenanceSpine,
  Prose,
  SheetSection,
  ScrollReveal,
  Button,
  ConsoleWell,
  ProvenanceBar,
  DistributionPoster,
  type SheetNavItem,
  type SpineFact,
  type Bar,
} from "@/components/v2";
import "@/styles/v2-theme.css";

export const metadata: Metadata = {
  title: "Persona pack — Sidira",
  robots: { index: false, follow: false },
};

const NAV: SheetNavItem[] = [
  { label: "Product", href: "#" },
  { label: "Persona packs", href: "#", active: true },
  { label: "Method", href: "#" },
];

const SPINE_FACTS: SpineFact[] = [
  { k: "Pack", v: "STREAMLY · v2" },
  { k: "Source", v: "org_3F9pXz" },
  { k: "Built", v: "2026-06-14" },
  { k: "Snapshot", v: "2026-W25" },
  { k: "Population n", v: <span className="v2-tnum">2,500</span> },
  { k: "Segments", v: <span className="v2-tnum">6</span> },
];

export default function PersonaDetailV2Page() {
  return (
    <SheetShell>
      <SheetTopBar
        nav={NAV}
        actions={
          <Button
            as="a"
            href="mailto:founders@sidira.ai?subject=Sidira%20persona-pack%20access"
            variant="secondary"
          >
            Request access
          </Button>
        }
      />

      {/* ── THE RECORD — Sheet, still, archival ─────────────────────────────── */}
      <RecordGrid
        spine={
          <ProvenanceSpine heading="Record" facts={SPINE_FACTS} calibrated={false} />
        }
      >
        <article className="v2-doc" style={{ padding: "128px 0 0 56px", maxWidth: 760 }}>
          {/* HERO — above the fold; rendered eagerly, NOT behind a reveal. */}
          <div
            style={{
              fontFamily: "var(--v2-font-mono)",
              fontSize: 11,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--sheet-mut)",
              marginBottom: 24,
            }}
          >
            Persona pack · record
          </div>
          <h1
            style={{
              fontWeight: 600,
              fontSize: "clamp(2.4rem,4.4vw,3.25rem)",
              lineHeight: 1.02,
              letterSpacing: "-0.03em",
              color: "var(--sheet-ink)",
              textWrap: "balance",
              maxWidth: "18ch",
            }}
          >
            Streamly &mdash; synthetic cohort, v2.
          </h1>
          <p
            style={{
              fontFamily: "var(--v2-font-serif)",
              fontSize: "1.3rem",
              lineHeight: 1.52,
              color: "var(--sheet-ink)",
              letterSpacing: "-0.005em",
              marginTop: 30,
              maxWidth: "44ch",
            }}
          >
            A grounded population of{" "}
            <span className="v2-tnum">2,500</span> synthetic viewers, fit from
            Streamly&rsquo;s own feature store and frozen as a reusable record.
          </p>

          <Prose lead style={{ marginTop: 40 }}>
            <p>
              A persona pack is a population, not a profile. This one is fit from
              Streamly&rsquo;s synthetic feature store &mdash; a{" "}
              <span className="v2-tnum">2,500</span>-row, six-segment fixture keyed
              to real viewing behaviour &mdash; and stored so any number of readings
              can draw the same cohort instead of re-sampling people each time.
            </p>
            <p>
              The build is the on-brand recipe: each segment is summarised by a{" "}
              <strong>centroid</strong> over its standardised features, a{" "}
              <strong>feature scale</strong> that records how much each dimension was
              stretched to fit, and a <strong>posterior mean</strong> that pulls thin
              segments back toward the population before they speak. Individual
              synthetic rows are then drawn around those centres, so a reading can
              address one agent at a time without ever touching a real viewer.
            </p>
            <p>
              The pack is <strong>uncalibrated</strong>. It has not yet been graded
              against a held-out experiment, so every inferred figure it produces
              stays directional and wears the ◇ glyph. The record below sits still:
              a filed description of a population, not a live reading of one.
            </p>
          </Prose>

          {/* ── (a) Segments ─────────────────────────────────────────────────── */}
          <ScrollReveal>
            <SheetSection
              kicker="The cohort"
              title="Six segments, one population."
              intro="Each segment carries a share of the population and a one-line read of who it captures. Shares are recorded counts over the fixture — printed plainly, no ± and no glyph."
            >
              <SegmentTable />
            </SheetSection>
          </ScrollReveal>

          {/* ── (b) Feature distributions — the frozen poster figure ─────────── */}
          <ScrollReveal>
            <SheetSection
              kicker="Feature distributions"
              title="What the population looks like, frozen."
              intro="One feature — weekly watch hours, standardised — binned across the whole cohort and dodged by the segment poles. A frozen poster of the settled shape, permitted on a record; on the live field this same figure runs in motion."
            >
              <DistributionFigure />
            </SheetSection>
          </ScrollReveal>

          {/* ── (c) Sample rows ──────────────────────────────────────────────── */}
          <ScrollReveal>
            <SheetSection
              kicker="Sample rows"
              title="Six synthetic viewers, drawn from the pack."
              intro="Example rows the simulator addresses individually. Every value is synthetic — drawn around a segment centre — and no cell maps to a real Streamly account."
            >
              <SampleRows />
            </SheetSection>
          </ScrollReveal>
        </article>
      </RecordGrid>

      {/* ── FOOTER ────────────────────────────────────────────────────────── */}
      <footer
        style={{
          borderTop: "0.75px solid var(--sheet-line)",
          background: "var(--sheet-raised)",
          marginTop: 112,
        }}
      >
        <div
          style={{
            maxWidth: 1180,
            margin: "0 auto",
            padding: "30px 32px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 20,
            flexWrap: "wrap",
            fontFamily: "var(--v2-font-mono)",
            fontSize: 11.5,
            letterSpacing: "0.02em",
            color: "var(--sheet-mut)",
          }}
        >
          <span>© 2026 SIDIRA</span>
          <span className="v2-tnum">
            streamly · v2 · n=2,500 · 6 segments · org_3F9pXz · 2026-W25 ·{" "}
            <span style={{ color: "var(--sheet-mut)" }}>
              <span className="v2-gh" style={{ marginRight: 4 }}>
                ◇
              </span>
              uncalibrated
            </span>
          </span>
          <span>
            <a href="mailto:founders@sidira.ai" style={{ color: "var(--sheet-mut)" }}>
              founders@sidira.ai
            </a>
          </span>
        </div>
      </footer>

      <style>{PAGE_CSS}</style>
    </SheetShell>
  );
}

// ── (a) the segment ledger ───────────────────────────────────────────────────
type Segment = { code: string; name: string; share: string; n: string; read: string };

const SEGMENTS: Segment[] = [
  { code: "S1", name: "Binge loyalists", share: "26.4", n: "660", read: "Daily long-session viewers; deep catalogue reach." },
  { code: "S2", name: "Weekend catch-up", share: "22.0", n: "550", read: "Concentrated Fri–Sun watching; few weekday sessions." },
  { code: "S3", name: "Casual samplers", share: "18.8", n: "470", read: "Short, exploratory sessions across many titles." },
  { code: "S4", name: "Family / shared", share: "14.4", n: "360", read: "Multi-profile household; mixed-genre, kids-heavy." },
  { code: "S5", name: "Lapsing", share: "11.2", n: "280", read: "Declining frequency; long gaps between sessions." },
  { code: "S6", name: "New & unscored", share: "7.2", n: "180", read: "Under 30 days tenure; sparse, high-variance signal." },
];

function SegmentTable() {
  return (
    <div
      className="v2-seg-card"
      style={{
        border: "0.75px solid var(--sheet-line)",
        borderRadius: "var(--r-panel)",
        background: "var(--sheet-raised)",
        overflow: "hidden",
      }}
    >
      <div
        className="v2-seg-head"
        style={{
          padding: "12px 18px",
          borderBottom: "0.75px solid var(--sheet-line)",
          fontFamily: "var(--v2-font-mono)",
          fontSize: 10,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "var(--sheet-mut)",
        }}
      >
        <span>Segment</span>
        <span style={{ textAlign: "right" }}>Share</span>
        <span style={{ textAlign: "right" }}>n</span>
      </div>
      {SEGMENTS.map((s, i) => (
        <div
          key={s.code}
          className="v2-seg-row"
          style={{
            padding: "14px 18px",
            borderBottom: i === SEGMENTS.length - 1 ? "none" : "0.75px solid var(--sheet-line)",
          }}
        >
          <span style={{ minWidth: 0 }}>
            <span
              style={{
                fontFamily: "var(--v2-font-mono)",
                fontSize: 11,
                color: "var(--sheet-mut)",
                marginRight: 10,
                letterSpacing: "0.04em",
              }}
            >
              {s.code}
            </span>
            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--sheet-ink)", letterSpacing: "-0.01em" }}>
              {s.name}
            </span>
            <small
              style={{
                display: "block",
                fontFamily: "var(--v2-font-serif)",
                fontStyle: "italic",
                fontSize: 13,
                color: "var(--sheet-mut)",
                marginTop: 3,
              }}
            >
              {s.read}
            </small>
          </span>
          <span
            className="v2-tnum"
            style={{
              fontFamily: "var(--v2-font-mono)",
              fontSize: 14,
              color: "var(--sheet-ink)",
              textAlign: "right",
              whiteSpace: "nowrap",
            }}
          >
            {s.share}%
          </span>
          <span
            className="v2-tnum"
            style={{
              fontFamily: "var(--v2-font-mono)",
              fontSize: 14,
              color: "var(--sheet-mut)",
              textAlign: "right",
              whiteSpace: "nowrap",
            }}
          >
            {s.n}
          </span>
        </div>
      ))}
      <div
        style={{
          padding: "12px 18px",
          borderTop: "0.75px solid var(--sheet-line)",
          background: "var(--sheet-sunk)",
          fontFamily: "var(--v2-font-mono)",
          fontSize: 12,
          letterSpacing: "0.02em",
          color: "var(--sheet-mut)",
          display: "flex",
          justifyContent: "space-between",
          gap: 16,
        }}
      >
        <span>TOTAL</span>
        <span className="v2-tnum">
          100.0% · 2,500 rows
        </span>
      </div>
    </div>
  );
}

// ── (b) the frozen distribution figure — DistributionPoster in a §6.4 well ──
// Binned counts for "weekly watch hours (standardised)" across the cohort,
// dodged by the two segment poles (loyalists vs. lapsing). Bar heights are agent
// counts; means carry ◇ (uncalibrated). All color comes from the dark Console
// scope the ConsoleWell re-asserts — no literal is inlined.
const CONTROL_BARS: Bar[] = [
  { x: 34, h: 8 }, { x: 66, h: 20 }, { x: 98, h: 44 }, { x: 130, h: 76 },
  { x: 162, h: 92 }, { x: 194, h: 70 }, { x: 226, h: 40 }, { x: 258, h: 18 },
];
const TREAT_BARS: Bar[] = [
  { x: 42, h: 24 }, { x: 74, h: 52 }, { x: 106, h: 84 }, { x: 138, h: 96 },
  { x: 170, h: 64 }, { x: 202, h: 34 }, { x: 234, h: 16 }, { x: 266, h: 7 },
];

function DistributionFigure() {
  return (
    <figure style={{ margin: 0 }}>
      <ConsoleWell
        role="figure"
        aria-label="Weekly watch hours, standardised, binned across the Streamly cohort and dodged by segment pole: binge loyalists in blue (right-shifted) and lapsing viewers in magenta (left-shifted), over an axis from low to high. Pooled mean −0.02, uncalibrated."
        style={{ padding: "20px 18px 4px" }}
      >
        <div
          style={{
            padding: "0 4px 12px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              fontFamily: "var(--v2-font-mono)",
              fontSize: 10,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--text-mut)",
            }}
          >
            Weekly watch hours · standardised
          </span>
          <ProvenanceBar
            calibrated={false}
            segments={[
              { content: "feature · watch_hours_z" },
              { content: <span className="v2-tnum">n=2,500</span> },
              { content: "2026-W25" },
            ]}
          />
        </div>

        <DistributionPoster
          controlBars={CONTROL_BARS}
          treatBars={TREAT_BARS}
          pooledMeanX={172}
          controlMeanX={186}
          treatMeanX={120}
          pooledMeanLabel="MEAN −0.02"
          calibrated={false}
          ci={{ x: 138, width: 60 }}
          footerNote="2,500 AGENTS · BINNED · BAR HEIGHT = AGENT COUNT"
          ariaLabel="Binned weekly-watch-hours histogram, dodged by segment pole."
        />

        <div
          style={{
            padding: "10px 4px 14px",
            display: "flex",
            justifyContent: "space-between",
            fontFamily: "var(--v2-font-mono)",
            fontSize: 10.5,
            letterSpacing: "0.02em",
            color: "var(--text-mut)",
          }}
        >
          <span>
            <ArmDot kind="ctl" />
            BINGE LOYALISTS · 660
          </span>
          <span>
            LAPSING · 280
            <ArmDot kind="trt" />
          </span>
        </div>
      </ConsoleWell>

      <figcaption
        style={{
          marginTop: 10,
          fontSize: 12,
          color: "var(--sheet-mut)",
          fontFamily: "var(--v2-font-sans)",
          maxWidth: "62ch",
          lineHeight: 1.5,
        }}
      >
        Figure 1 &mdash; the population&rsquo;s standardised watch-hours shape, frozen.
        Bar height is an agent count, printed plainly; the pooled mean is an
        estimate and wears its ◇. On the live field this distribution settles in
        motion &mdash; here it is a printed poster, still.
      </figcaption>
    </figure>
  );
}

function ArmDot({ kind }: { kind: "ctl" | "trt" }) {
  return (
    <span
      aria-hidden
      style={{
        width: 7,
        height: 7,
        borderRadius: "var(--r-dot)",
        display: "inline-block",
        verticalAlign: "middle",
        margin: "0 5px",
        background: kind === "ctl" ? "var(--arm-control)" : "var(--arm-treat)",
      }}
    />
  );
}

// ── (c) sample synthetic rows ────────────────────────────────────────────────
type Row = { id: string; seg: string; hrs: string; sess: string; tenure: string };

const ROWS: Row[] = [
  { id: "u_0001", seg: "S1", hrs: "18.4", sess: "11", tenure: "412" },
  { id: "u_0002", seg: "S2", hrs: "9.7", sess: "4", tenure: "286" },
  { id: "u_0003", seg: "S3", hrs: "3.2", sess: "6", tenure: "158" },
  { id: "u_0004", seg: "S4", hrs: "12.1", sess: "8", tenure: "523" },
  { id: "u_0005", seg: "S5", hrs: "1.6", sess: "1", tenure: "377" },
  { id: "u_0006", seg: "S6", hrs: "4.9", sess: "3", tenure: "21" },
];

function SampleRows() {
  return (
    <div
      className="v2-rows-scroll"
      style={{
        border: "0.75px solid var(--sheet-line)",
        borderRadius: "var(--r-panel)",
        background: "var(--sheet-raised)",
        overflow: "hidden",
      }}
    >
      <table
        className="v2-rows-table v2-tnum"
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontFamily: "var(--v2-font-mono)",
          fontSize: 13,
        }}
      >
        <thead>
          <tr>
            {["agent", "seg", "watch hrs / wk", "sessions / wk", "tenure (days)"].map((h, i) => (
              <th
                key={h}
                scope="col"
                style={{
                  textAlign: i <= 1 ? "left" : "right",
                  padding: "11px 18px",
                  borderBottom: "0.75px solid var(--sheet-line)",
                  fontSize: 10,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  fontWeight: 400,
                  color: "var(--sheet-mut)",
                  whiteSpace: "nowrap",
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map((r, i) => (
            <tr key={r.id}>
              <td style={cell(i, "left", "ink")}>{r.id}</td>
              <td style={cell(i, "left", "mut")}>{r.seg}</td>
              <td style={cell(i, "right", "ink")}>{r.hrs}</td>
              <td style={cell(i, "right", "ink")}>{r.sess}</td>
              <td style={cell(i, "right", "ink")}>{r.tenure}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function cell(i: number, align: "left" | "right", tone: "ink" | "mut") {
  return {
    textAlign: align,
    padding: "11px 18px",
    borderBottom: i === ROWS.length - 1 ? "none" : "0.75px solid var(--sheet-line)",
    color: tone === "ink" ? "var(--sheet-ink)" : "var(--sheet-mut)",
    whiteSpace: "nowrap" as const,
  };
}

// ── page-local CSS — /v2/persona-detail-SPECIFIC ONLY ────────────────────────
// Generic Sheet layout (SheetTopBar collapse, the RecordGrid/ProvenanceSpine
// responsive collapse, the §6.4 ConsoleWell `.v2-console-scope` token block) all
// live in the SHARED stylesheet (styles/v2-theme.css, `.v2-sheet`). Below is only
// what is unique to THIS record: the doc-column padding collapse and the two
// composite tables' (segment ledger + sample rows) own grid/scroll behaviour.
const PAGE_CSS = `
.v2-doc{}
.v2-seg-head,
.v2-seg-row{display:grid;grid-template-columns:1fr 84px 64px;gap:16px;align-items:baseline;}
.v2-rows-scroll{overflow-x:auto;}
.v2-rows-table th:first-child,.v2-rows-table td:first-child{padding-left:18px;}
@media(max-width:1024px){
  .v2-doc{padding:48px 0 0!important;}
}
`;
