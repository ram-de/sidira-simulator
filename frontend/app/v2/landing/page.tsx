// ───────────────────────────────────────────────────────────────────────────
// /v2/landing — DESIGN SYSTEM v2 · THE CAPSTONE SHOWPIECE (flagged · unlinked)
//
// The marketing landing of the "Reading Console" rollout — a PUBLIC, NOINDEX,
// nav-suppressed (nav is globally suppressed on /v2/*), static-mock dark Console
// marketing page. Reachable ONLY by typing /v2/landing; it is a PREVIEW of the
// future landing, not the live `/` route.
//
// IMPACT BUDGET (§0.2): this is a SHOWPIECE — "no holds barred." The signature
// Population Field IS the hero (§5.5: field is the hero, not a sidebar), the ONE
// loud region (~55–70% of the first viewport, §3.2). Everything below the fold
// is WORKING-quiet: ink + hairline + negative space (the 80/20 rule). The one
// frozen DistributionPoster appears as a quiet figure in "The instrument."
//
// CONSUMES the shared v2 layer (lib/design-v2.ts, components/v2/*, v2-theme.css)
// — it does NOT re-inline tokens. The Population Field canvas is the sole place a
// color may live as a (commented, runtime) fallback (see PopulationField.tsx).
// ───────────────────────────────────────────────────────────────────────────
import type { Metadata } from "next";
import {
  ConsoleShell,
  Wrap,
  TopBar,
  Button,
  Chip,
  Designator,
  CalGlyph,
  Section,
  SectionHead,
  ScrollReveal,
  Panel,
  PopulationField,
  DistributionPoster,
  type NavItem,
  type Bar,
} from "@/components/v2";
import "@/styles/v2-theme.css";

export const metadata: Metadata = {
  title: "Sidira — read your change before you ship it",
  robots: { index: false, follow: false },
};

const NAV: NavItem[] = [
  { label: "Product", href: "#product" },
  { label: "Instrument", href: "#instrument" },
  { label: "Candor", href: "#candor" },
  { label: "About", href: "#" },
];

// Frozen poster bins — a calm two-arm separation, dodged (§5.5 / §7.1). These
// are layout coordinates on the poster's 0..360 viewBox, mirroring the precedent
// in the simulation-results mock (an honest canned baseline, not a faked run).
const CONTROL_BARS: Bar[] = [
  { x: 34, h: 14 }, { x: 66, h: 34 }, { x: 98, h: 62 }, { x: 130, h: 90 },
  { x: 162, h: 82 }, { x: 194, h: 54 }, { x: 226, h: 28 }, { x: 258, h: 12 },
];
const TREAT_BARS: Bar[] = [
  { x: 42, h: 10 }, { x: 74, h: 26 }, { x: 106, h: 50 }, { x: 138, h: 80 },
  { x: 170, h: 94 }, { x: 202, h: 70 }, { x: 234, h: 40 }, { x: 266, h: 18 },
];

export default function LandingV2Page() {
  return (
    <ConsoleShell>
      <TopBar
        nav={NAV}
        action={
          <Button as="a" href="#cta" variant="primary">
            Request access
          </Button>
        }
      />

      {/* ── HERO — the ONE loud region: Population Field as the full-bleed figure,
          headline + subhead + CTAs layered over it (§0.2, §5.5) ───────────────── */}
      <section
        style={{
          position: "relative",
          minHeight: "min(88vh, 880px)",
          display: "flex",
          alignItems: "center",
          borderBottom: "1px solid var(--console-line-50)",
          overflow: "hidden",
        }}
      >
        {/* the signature viz — full-bleed backdrop/figure of the first viewport.
            Decorative (the headline carries the meaning); the field is the loud
            accent carrier for this region (§1.9). */}
        <PopulationField
          mode="live"
          particleCount={620}
          intensity={1}
          height="100%"
          style={{ position: "absolute", inset: 0, zIndex: 0 }}
        />

        {/* a quiet vignette + left scrim so the overlaid copy stays AA-legible
            against the live field without dimming the signal (token-driven). */}
        <div
          aria-hidden
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 1,
            pointerEvents: "none",
            // token-linked scrim — color-mix keeps every stop sourced from
            // --console-900 (no raw rgb in the page; §1.x token law).
            background:
              "linear-gradient(90deg, var(--console-900) 0%, color-mix(in srgb, var(--console-900) 62%, transparent) 42%, color-mix(in srgb, var(--console-900) 12%, transparent) 72%, transparent 100%), linear-gradient(0deg, var(--console-900) 0%, transparent 26%, transparent 80%, color-mix(in srgb, var(--console-900) 50%, transparent) 100%)",
          }}
        />

        <Wrap style={{ position: "relative", zIndex: 2, paddingTop: 96, paddingBottom: 96 }}>
          <div style={{ maxWidth: 680 }}>
            <ScrollReveal>
              <div style={{ display: "inline-flex", alignItems: "center", gap: 9, marginBottom: 26 }}>
                <span
                  aria-hidden
                  style={{ width: 34, height: 1, background: "linear-gradient(90deg,var(--text-mut),transparent)" }}
                />
                <Designator>A MEASUREMENT INSTRUMENT FOR HUMAN REACTION</Designator>
              </div>
              <h1
                style={{
                  fontSize: "clamp(2.7rem, 6vw, 5rem)",
                  lineHeight: 0.99,
                  letterSpacing: "-0.035em",
                  fontWeight: 700,
                  color: "var(--text-hi)",
                  textWrap: "balance",
                  marginBottom: 26,
                }}
              >
                Read your change before you ship it.
              </h1>
              <p
                style={{
                  fontSize: "1.2rem",
                  lineHeight: 1.55,
                  color: "var(--text)",
                  maxWidth: "46ch",
                  letterSpacing: "-0.005em",
                  fontWeight: 450,
                }}
              >
                Sidira simulates a synthetic cohort of{" "}
                <b style={{ color: "var(--text-hi)", fontWeight: 550 }}>your</b> users — fit from your
                real telemetry — and runs your product change past them.{" "}
                <b style={{ color: "var(--text-hi)", fontWeight: 550 }}>
                  A candid, directional reading
                </b>{" "}
                of how people will react, days before you commit engineering to the bet.
              </p>
              <div style={{ display: "flex", gap: 12, marginTop: 36, alignItems: "center", flexWrap: "wrap" }}>
                <Button as="a" href="#cta" variant="primary" hero>
                  Request access
                </Button>
                <Button as="a" href="#instrument" variant="ghost" hero>
                  See how it reads ↓
                </Button>
              </div>
              <p
                className="v2-mono"
                style={{ marginTop: 34, fontSize: 11, letterSpacing: "0.05em", color: "var(--text-mut)" }}
              >
                SYNTHETIC COHORTS · GROUNDED IN YOUR DATA · DIRECTIONAL <CalGlyph /> UNTIL GRADED
              </p>
            </ScrollReveal>
          </div>
        </Wrap>
      </section>

      {/* ── WORKING-quiet: synthetic cohorts, grounded ─────────────────────────── */}
      <Section style={{ scrollMarginTop: 64 }}>
        <Wrap>
          <span id="product" />
          <SectionHead
            eyebrow="WHAT IT IS"
            title="Synthetic cohorts, grounded in your data."
            sub={
              <>
                Not a focus group and not a guess. Sidira fits a population of synthetic minds from your
                real user telemetry — segments, posteriors, and a sample of individuals who actually
                react — then walks your proposed change past them, one agent at a time.
              </>
            }
          />
          <ScrollReveal
            className="v2-land-grid"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3,1fr)",
              border: "1px solid var(--console-line-50)",
              borderRadius: "var(--r-panel)",
              overflow: "hidden",
              background: "var(--console-850)",
            }}
          >
            <Cell title="Fit from telemetry" chip="YOUR POPULATION" tag={<><CalGlyph graded /> GRADED</>}>
              A persona pack built from your real users — segment shares, posterior means, and a sample
              of individuals. Built once, refit as your base shifts.
            </Cell>
            <Cell title="The change under test" chip="YOUR PROPOSAL" tag="AUTHORED">
              The bet, submitted the way teams already work — a short brief plus a Figma. Sidira diffs it
              against a current snapshot of what you actually shipped.
            </Cell>
            <Cell title="One reaction per agent" chip="THE READING" tag={<><CalGlyph /> DIRECTIONAL</>} now>
              Every synthetic person reacts individually; the cohort's reactions settle into a
              distribution. The shape — not a single score — is the answer.
            </Cell>
          </ScrollReveal>
        </Wrap>
      </Section>

      {/* ── WORKING-quiet: a reading, not a guess (candor) ─────────────────────── */}
      <Section style={{ scrollMarginTop: 64 }}>
        <Wrap>
          <span id="candor" />
          <div className="v2-land-candor" style={{ display: "grid", gridTemplateColumns: "1.05fr 1fr", gap: 64, alignItems: "center" }}>
            <ScrollReveal>
              <div style={{ marginBottom: 18 }}>
                <Designator>A READING, NOT A GUESS · CANDID & DIRECTIONAL</Designator>
              </div>
              <h2
                style={{
                  fontSize: "2.05rem",
                  lineHeight: 1.1,
                  letterSpacing: "-0.028em",
                  fontWeight: 600,
                  color: "var(--text-hi)",
                  textWrap: "balance",
                }}
              >
                It tells you the direction, and tells you it&apos;s uncertain.
              </h2>
              <p style={{ marginTop: 18, fontSize: "1.075rem", lineHeight: 1.62, color: "var(--text-mut)", maxWidth: "52ch" }}>
                An ungraded reading is{" "}
                <span style={{ color: "var(--spread)" }}>raw and uncalibrated</span> — and says so, on
                every estimate it touches. You get sign and order — which way, and roughly how far — not
                a calibrated magnitude pretending to be a fact. Identifiers, seeds, and cohort counts
                print as plain fact, no false precision.
              </p>
              <p className="v2-mono" style={{ marginTop: 20, fontSize: 11, letterSpacing: "0.04em", color: "var(--text-mut)" }}>
                ± ON INFERRED READINGS ONLY · IDS &amp; SEEDS &amp; n PRINT BARE
              </p>
            </ScrollReveal>

            <ScrollReveal
              className="v2-elevated"
              style={{ background: "var(--console-850)", border: "1px solid var(--console-line-50)", borderRadius: "var(--r-panel)", padding: 26 }}
            >
              <div style={{ display: "flex", alignItems: "baseline", gap: 12, paddingBottom: 20, borderBottom: "1px solid var(--console-line-40)" }}>
                <span className="v2-mono v2-tnum" style={{ fontSize: "2.4rem", fontWeight: 500, color: "var(--text-hi)", lineHeight: 1 }}>
                  +3.6
                </span>
                <span className="v2-mono v2-tnum" style={{ fontSize: "1.05rem", color: "var(--spread)" }}>±1.4pp</span>
                <span style={{ fontSize: "1.25rem", color: "var(--spread-dim)" }}>◇</span>
                <span style={{ fontSize: 12, color: "var(--text-mut)", lineHeight: 1.45, maxWidth: "17ch", marginLeft: "auto" }}>
                  an inferred reading carries its spread and its calibration glyph — always
                </span>
              </div>
              <div style={{ marginTop: 6, display: "flex", flexDirection: "column" }}>
                <Row glyph={<span className="v2-gh">◇</span>} title="Uncalibrated">
                  No real outcome yet. The reading is directional, drifts faintly, and freezes the
                  instant you look at it — it can&apos;t lock a verdict.
                </Row>
                <Row glyph={<span className="v2-gf">◆</span>} title="Graded">
                  Validated against a real outcome. It snaps from noise to a stable reading, settles
                  once, and comes to rest.
                </Row>
                <Row glyph={<span style={{ color: "var(--text-mut)" }}>·</span>} title="Facts print bare" last>
                  Run id, seed <Fact>0x4f</Fact>, snapshot <Fact>2026-W25</Fact>, and raw{" "}
                  <Fact>n=2,500</Fact> wear no ± — they were recorded, not inferred.
                </Row>
              </div>
            </ScrollReveal>
          </div>
        </Wrap>
      </Section>

      {/* ── WORKING-quiet: the instrument (how it reads) + frozen poster figure ── */}
      <Section style={{ scrollMarginTop: 64 }}>
        <Wrap>
          <span id="instrument" />
          <SectionHead
            eyebrow="THE INSTRUMENT"
            title="One field, from the marketing promise to the real run."
            sub={
              <>
                The cloud above is the same instrument that renders a real result. At rest it drifts; on
                a bet a wavefront sweeps and the cohort re-sorts along a reaction axis into a
                distribution. Here it&apos;s frozen as a poster — the settled shape, still.
              </>
            }
          />
          <ScrollReveal>
            <Panel style={{ padding: 26 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 18 }}>
                <Designator>SETTLED DISTRIBUTION · CANNED BASELINE</Designator>
                <Chip>REVERSE ← REACTION → ADOPT</Chip>
              </div>
              <figure style={{ margin: 0 }} aria-label="Control versus treatment reaction distribution, frozen.">
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
              </figure>
              <p style={{ marginTop: 16, fontSize: 13, lineHeight: 1.55, color: "var(--text-mut)", maxWidth: "64ch" }}>
                Bar height is an agent count, printed plainly; the separation is an estimate and wears
                its ◇. On the live field this same distribution settles in motion — here it is still, so
                you can read it.
              </p>
            </Panel>
          </ScrollReveal>
        </Wrap>
      </Section>

      {/* ── CLOSING CTA ────────────────────────────────────────────────────────── */}
      <section id="cta" style={{ padding: "112px 0", textAlign: "center", scrollMarginTop: 64 }}>
        <Wrap>
          <ScrollReveal style={{ maxWidth: 640, margin: "0 auto" }}>
            <div style={{ marginBottom: 22 }}>
              <Designator>EARLY ACCESS · GROUNDED IN YOUR DATA</Designator>
            </div>
            <h2 style={{ fontSize: "2.5rem", lineHeight: 1.08, letterSpacing: "-0.03em", fontWeight: 600, color: "var(--text-hi)", textWrap: "balance" }}>
              Read the reaction before you build it.
            </h2>
            <p style={{ marginTop: 20, fontSize: "1.1rem", color: "var(--text-mut)", lineHeight: 1.6, maxWidth: "48ch", marginLeft: "auto", marginRight: "auto" }}>
              Bring a change and a sample of your users. We fit the cohort, run the bet, and hand back a
              candid, directional reading — sign and order, with its uncertainty in plain view.
            </p>
            <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 38, flexWrap: "wrap" }}>
              <Button as="a" href="#" variant="primary" hero>
                Request access
              </Button>
              <Button as="a" href="#" variant="secondary" hero>
                Talk to us
              </Button>
            </div>
            <p className="v2-mono" style={{ marginTop: 28, fontSize: 10.5, letterSpacing: "0.06em", color: "var(--text-mut)" }}>
              DIRECTIONAL <CalGlyph /> UNTIL GRADED AGAINST A REAL OUTCOME
            </p>
          </ScrollReveal>
        </Wrap>
      </section>

      {/* ── FOOTER ─────────────────────────────────────────────────────────────── */}
      <footer style={{ borderTop: "1px solid var(--console-line-50)", padding: "40px 0" }}>
        <Wrap style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
          <span style={{ fontWeight: 600, letterSpacing: "0.06em", color: "var(--text-hi)", fontSize: 14 }}>
            SIDIRA
          </span>
          <Designator>READ YOUR CHANGE BEFORE YOU SHIP IT</Designator>
          <div style={{ marginLeft: "auto", display: "flex", gap: 22 }}>
            {["Product", "Instrument", "Candor", "Privacy"].map((l) => (
              <a key={l} href="#" style={{ fontSize: 13, color: "var(--text-mut)" }}>
                {l}
              </a>
            ))}
          </div>
        </Wrap>
      </footer>

      {/* page-local responsive rules (token-driven; collapse the grids) */}
      <style>{LAND_CSS}</style>
    </ConsoleShell>
  );
}

// ── quiet three-up cell (mirrors the product/v2 InputCell convention) ─────────
function Cell({
  title,
  chip,
  tag,
  now = false,
  children,
}: {
  title: string;
  chip: string;
  tag: React.ReactNode;
  now?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className="v2-land-cell"
      style={{
        padding: "28px 26px 30px",
        borderLeft: "1px solid var(--console-line-40)",
        position: "relative",
        // token-linked highlight wash (color-mix off --text-hi; no raw rgb)
        background: now
          ? "linear-gradient(180deg, color-mix(in srgb, var(--text-hi) 3%, transparent), transparent 62%)"
          : undefined,
      }}
    >
      <h3 style={{ fontSize: "1.15rem", fontWeight: 550, letterSpacing: "-0.01em", color: "var(--text-hi)" }}>{title}</h3>
      <div style={{ marginTop: 9 }}>
        <Chip>{chip}</Chip>
      </div>
      <p style={{ marginTop: 15, fontSize: 14, lineHeight: 1.6, color: "var(--text-mut)" }}>{children}</p>
      <span className="v2-desig" style={{ position: "absolute", top: 24, right: 24, color: "var(--text-mut)" }}>
        {tag}
      </span>
    </div>
  );
}

function Row({ glyph, title, children, last = false }: { glyph: React.ReactNode; title: string; children: React.ReactNode; last?: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 14, padding: "15px 0", borderBottom: last ? "none" : "1px solid var(--console-line-30)" }}>
      <span className="v2-mono" style={{ fontSize: "1rem", flex: "0 0 auto", width: 18, textAlign: "center", lineHeight: 1.45 }}>{glyph}</span>
      <div>
        <b style={{ color: "var(--text-hi)", fontWeight: 550, display: "block", fontSize: 14 }}>{title}</b>
        <span style={{ color: "var(--text-mut)", fontSize: 13, lineHeight: 1.5 }}>{children}</span>
      </div>
    </div>
  );
}

const Fact = ({ children }: { children: React.ReactNode }) => (
  <span className="v2-mono" style={{ color: "var(--text-mut)" }}>{children}</span>
);

// ── responsive grid rules (token-driven; mirrors the product/v2 breakpoints) ──
const LAND_CSS = `
@media(max-width:1080px){
  .v2-land-candor{grid-template-columns:1fr!important;gap:40px!important;}
}
@media(max-width:760px){
  .v2-land-grid{grid-template-columns:1fr!important;}
  .v2-land-cell{border-left:none!important;border-top:1px solid var(--console-line-40);}
  .v2-land-cell:first-child{border-top:none;}
}
`;
