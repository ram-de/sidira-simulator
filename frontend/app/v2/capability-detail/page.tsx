// ───────────────────────────────────────────────────────────────────────────
// /v2/capability-detail — DESIGN SYSTEM v2 PREVIEW · SHEET (light) RECORD page
// (flagged · NOINDEX · unlinked).
//
// A capability PRD, filed as a printed spec of record: the candor law that keeps
// uncalibrated readings directional and wearing the ◇ glyph. Per design-system-v2.md
// §0.1/§0.2 this is a RECORD-class, light Sheet route — STILL: serif prose, a
// Provenance Spine in the left binder margin, airy chapter rhythm, NO canvas, NO
// drift, NO motion beyond the once-only page reveal. A frozen DistributionPoster
// (static SVG, §5.5/§7.1) is permitted as a figure; a live field is NOT. NO
// AppFrame, NO dark masthead — no mode inversion.
//
// This page CONSUMES the shared v2 Sheet layer (SheetShell, SheetTopBar,
// RecordGrid, ProvenanceSpine, Prose, SheetSection + the §6.4 ConsoleWell /
// DistributionPoster figure from @/components/v2). It re-inlines no tokens — only
// the scoped `var(--sheet-*)` / `var(--console-*)` / `var(--v2-font-*)` /
// `var(--space-*)` / `var(--r-*)` CSS vars and the design-v2 token constants.
// Reachable ONLY by typing /v2/capability-detail.
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
  title: "Capability — Sidira",
  robots: { index: false, follow: false },
};

const NAV: SheetNavItem[] = [
  { label: "Product", href: "#" },
  { label: "Capabilities", href: "#", active: true },
  { label: "Method", href: "#" },
];

const SPINE_FACTS: SpineFact[] = [
  { k: "Capability", v: "CAP-0007" },
  { k: "Owner", v: "Science" },
  { k: "Status", v: "Shipped" },
  { k: "Filed", v: "2026-06-16" },
  { k: "Snapshot", v: "2026-W25" },
  { k: "Acceptance", v: <span className="v2-tnum">6 of 6</span> },
];

export default function CapabilityDetailV2Page() {
  return (
    <SheetShell>
      <SheetTopBar
        nav={NAV}
        actions={
          <Button
            as="a"
            href="mailto:founders@sidira.ai?subject=Sidira%20capability%20CAP-0007"
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
            Capability &middot; PRD of record
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
            Candor law &mdash; directional-only readings.
          </h1>
          <p
            style={{
              fontFamily: "var(--v2-font-serif)",
              fontSize: "1.3rem",
              lineHeight: 1.52,
              color: "var(--sheet-ink)",
              letterSpacing: "-0.005em",
              marginTop: 30,
              maxWidth: "46ch",
            }}
          >
            An uncalibrated reading must stay <em>directional</em> &mdash; hedged in
            wording, banded in its verdict, and wearing the ◇ glyph &mdash; until a
            held-out experiment earns it the right to speak plainly.
          </p>

          <Prose lead style={{ marginTop: 40 }}>
            <p>
              This capability encodes a single discipline into the product surface:
              a figure the model <strong>inferred about people</strong> may never be
              presented as a settled fact. Until a reading is graded against a
              held-out experiment, every inferred number it carries prints with its
              calibration glyph, every verdict it states is a band rather than a
              point, and every sentence that summarises it is worded as a direction,
              not a measurement.
            </p>
            <p>
              The hypothesis it encodes is a trust hypothesis, not a modelling one:
              that a customer shown an honest <em>directional</em> read &mdash; one
              that visibly refuses to overclaim &mdash; will trust the instrument
              more, and act on it sooner, than a customer handed a falsely precise
              number that a later experiment contradicts. The candor law makes the
              honest framing structural, so no individual screen can quietly opt out
              of it.
            </p>
            <p>
              The record below is the spec, filed. It sits still: a printed
              description of a rule the product now obeys, not a live reading of one.
              The single figure is a frozen poster of what a directional reading
              looks like on the Sheet &mdash; the ◇ on its mean, the band on its
              spread, the plain ink on its counts.
            </p>
          </Prose>

          {/* ── (a) Behaviour spec ───────────────────────────────────────────── */}
          <ScrollReveal>
            <SheetSection
              kicker="Behaviour spec"
              title="What the law does, wherever an inferred number appears."
              intro="The rule is mechanical and global: it applies to every reading the same way, in marketing surfaces and in the product alike, with no per-screen exception. Concretely, an uncalibrated reading is held to the following."
            >
              <SpecList />
            </SheetSection>
          </ScrollReveal>

          {/* ── (b) Acceptance criteria ──────────────────────────────────────── */}
          <ScrollReveal>
            <SheetSection
              kicker="Acceptance criteria"
              title="Testable conditions the law must satisfy."
              intro="Each condition is a check a reviewer or a test can apply to a rendered reading. All six pass on the current snapshot; a failure on any one blocks the reading from shipping as anything but directional."
            >
              <CriteriaList />
            </SheetSection>
          </ScrollReveal>

          {/* ── (c) Expected impact — the frozen poster figure ───────────────── */}
          <ScrollReveal>
            <SheetSection
              kicker="Expected impact"
              title="What a directional reading looks like, frozen."
              intro="One reading under the law: a treatment-vs-control distribution with the pooled mean wearing its ◇ and a band on its spread. A frozen poster of the settled shape, permitted on a record; on the live field this same figure runs in motion."
            >
              <ImpactFigure />
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
            cap-0007 · shipped · acceptance 6/6 · owner science · 2026-W25 ·{" "}
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

// ── (a) the behaviour spec — what the law does ───────────────────────────────
type SpecItem = { mk: string; pt: string; pd: string };

const SPEC: SpecItem[] = [
  {
    mk: "◇",
    pt: "Every inferred number wears the glyph.",
    pd: "A value the model estimated about people renders with the ◇ calibration glyph beside it. Recorded facts — ids, seeds, counts, dates, durations — render plainly, with no glyph and no band.",
  },
  {
    mk: "±",
    pt: "A verdict is a band, never a point.",
    pd: "The summary verdict an uncalibrated reading carries is stated as a range with its spread attached. It reads DIRECTIONAL, never a single locked figure dressed as ground truth.",
  },
  {
    mk: "—",
    pt: "Wording stays hedged.",
    pd: "The prose around a reading uses directional language — leans, shifts, points toward — rather than measurement language. Harm renders in plain ink with a down-glyph, not alarm color, because a negative reaction is information.",
  },
  {
    mk: "●",
    pt: "Grading is the only path to plain speech.",
    pd: "The only way a reading drops the ◇ and speaks plainly is to be graded against a held-out experiment. Until that grade exists, the law holds with no manual override available on any surface.",
  },
];

function SpecList() {
  return (
    <div style={{ borderTop: "0.75px solid var(--sheet-line)" }}>
      {SPEC.map((s) => (
        <div
          key={s.pt}
          className="v2-spec"
          style={{
            padding: "24px 0",
            borderBottom: "0.75px solid var(--sheet-line)",
            display: "grid",
            gridTemplateColumns: "34px 1fr",
            gap: "0 20px",
            alignItems: "start",
          }}
        >
          <div
            style={{
              fontFamily: "var(--v2-font-mono)",
              fontSize: 11,
              color: "var(--sheet-mut)",
              paddingTop: 3,
              letterSpacing: "0.04em",
            }}
          >
            {s.mk}
          </div>
          <div>
            <div
              style={{
                fontWeight: 600,
                fontSize: "1.0625rem",
                letterSpacing: "-0.01em",
                color: "var(--sheet-ink)",
                marginBottom: 7,
              }}
            >
              {s.pt}
            </div>
            <div
              style={{
                fontFamily: "var(--v2-font-serif)",
                fontSize: "1rem",
                lineHeight: 1.62,
                color: "var(--sheet-mut)",
                maxWidth: "62ch",
              }}
            >
              {s.pd}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── (b) acceptance criteria — testable checklist ─────────────────────────────
type Criterion = { id: string; text: string; pass: boolean };

const CRITERIA: Criterion[] = [
  { id: "AC-1", text: "Every inferred figure in a rendered reading carries a ◇ glyph.", pass: true },
  { id: "AC-2", text: "Recorded facts (ids, seeds, counts, dates) render with no glyph or band.", pass: true },
  { id: "AC-3", text: "An uncalibrated verdict prints as a band labelled DIRECTIONAL, never a point.", pass: true },
  { id: "AC-4", text: "Reading copy uses directional wording; harm renders in plain ink, not alarm color.", pass: true },
  { id: "AC-5", text: "No surface exposes a manual override to drop the ◇ before grading.", pass: true },
  { id: "AC-6", text: "A graded reading, and only a graded reading, may lock and speak plainly.", pass: true },
];

function CriteriaList() {
  const passed = CRITERIA.filter((c) => c.pass).length;
  return (
    <div
      style={{
        border: "0.75px solid var(--sheet-line)",
        borderRadius: "var(--r-panel)",
        background: "var(--sheet-raised)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "12px 18px",
          borderBottom: "0.75px solid var(--sheet-line)",
          fontFamily: "var(--v2-font-mono)",
          fontSize: 10,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "var(--sheet-mut)",
          display: "flex",
          justifyContent: "space-between",
          gap: 16,
        }}
      >
        <span>Criterion</span>
        <span>Status</span>
      </div>
      {CRITERIA.map((c, i) => (
        <div
          key={c.id}
          className="v2-crit-row"
          style={{
            padding: "14px 18px",
            borderBottom: i === CRITERIA.length - 1 ? "none" : "0.75px solid var(--sheet-line)",
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
              {c.id}
            </span>
            <span
              style={{
                fontSize: 14,
                color: "var(--sheet-ink)",
                letterSpacing: "-0.005em",
                lineHeight: 1.5,
              }}
            >
              {c.text}
            </span>
          </span>
          <span
            aria-label={c.pass ? "Pass" : "Fail"}
            style={{
              fontFamily: "var(--v2-font-mono)",
              fontSize: 11,
              letterSpacing: "0.06em",
              color: "var(--sheet-mut)",
              whiteSpace: "nowrap",
              textAlign: "right",
              alignSelf: "center",
            }}
          >
            <span aria-hidden style={{ marginRight: 6, color: "var(--sheet-ink)" }}>
              ✓
            </span>
            PASS
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
          {passed} of {CRITERIA.length} passing
        </span>
      </div>
    </div>
  );
}

// ── (c) the frozen impact figure — DistributionPoster in a §6.4 well ─────────
// One reading under the law: adoption-shift across the cohort, dodged by arm
// (control vs. treatment). Bar heights are agent counts; the pooled mean carries
// ◇ (uncalibrated). All color comes from the dark Console scope the ConsoleWell
// re-asserts — no literal is inlined.
const CONTROL_BARS: Bar[] = [
  { x: 34, h: 10 }, { x: 66, h: 26 }, { x: 98, h: 52 }, { x: 130, h: 84 },
  { x: 162, h: 90 }, { x: 194, h: 62 }, { x: 226, h: 32 }, { x: 258, h: 14 },
];
const TREAT_BARS: Bar[] = [
  { x: 42, h: 18 }, { x: 74, h: 40 }, { x: 106, h: 70 }, { x: 138, h: 94 },
  { x: 170, h: 80 }, { x: 202, h: 48 }, { x: 234, h: 22 }, { x: 266, h: 9 },
];

function ImpactFigure() {
  return (
    <figure style={{ margin: 0 }}>
      <ConsoleWell
        role="figure"
        aria-label="Adoption shift across the cohort, dodged by experiment arm: control in blue (left-shifted) and treatment in magenta (right-shifted), over an axis from reject to adopt. Pooled mean +0.04, uncalibrated, with a directional band."
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
            Adoption shift · directional
          </span>
          <ProvenanceBar
            calibrated={false}
            segments={[
              { content: "reading · adoption_lift" },
              { content: <span className="v2-tnum">n=1,200</span> },
              { content: "2026-W25" },
            ]}
          />
        </div>

        <DistributionPoster
          controlBars={CONTROL_BARS}
          treatBars={TREAT_BARS}
          pooledMeanX={150}
          controlMeanX={132}
          treatMeanX={166}
          pooledMeanLabel="MEAN +0.04"
          calibrated={false}
          ci={{ x: 124, width: 52 }}
          footerNote="1,200 AGENTS · BINNED · BAR HEIGHT = AGENT COUNT"
          ariaLabel="Binned adoption-shift histogram, dodged by experiment arm."
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
            CONTROL · 600
          </span>
          <span>
            TREATMENT · 600
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
        Figure 1 &mdash; a directional reading under the candor law, frozen. Bar
        height is an agent count, printed plainly; the pooled adoption lift is an
        estimate and wears its ◇, with a band on its spread. On the live field this
        distribution settles in motion &mdash; here it is a printed poster, still.
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

// ── page-local CSS — /v2/capability-detail-SPECIFIC ONLY ─────────────────────
// Generic Sheet layout (SheetTopBar collapse, the RecordGrid/ProvenanceSpine
// responsive collapse, the §6.4 ConsoleWell `.v2-console-scope` token block) all
// live in the SHARED stylesheet (styles/v2-theme.css, `.v2-sheet`). Below is only
// what is unique to THIS record: the doc-column padding collapse and the
// acceptance-criteria row grid.
const PAGE_CSS = `
.v2-doc{}
.v2-crit-row{display:grid;grid-template-columns:1fr auto;gap:16px;align-items:baseline;}
@media(max-width:1024px){
  .v2-doc{padding:48px 0 0!important;}
}
@media(max-width:720px){
  .v2-spec{grid-template-columns:1fr!important;}
}
`;
