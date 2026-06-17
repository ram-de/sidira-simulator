// ───────────────────────────────────────────────────────────────────────────
// /product/v2 — DESIGN SYSTEM v2 PREVIEW · SHEET (light · brand-mode) (flagged · unlinked)
//
// /product is a PUBLIC marketing page, so per DESIGN.md §1.3 it is LIGHT
// brand-mode — paper, ink, the dual-color aperture mark — consistent with
// /about/v2, NOT the dark Console. This is the unified marketing surface: the
// SAME product messaging (current-product snapshot · the artifact browser
// showpiece · three inputs · symmetry · capture pipeline · manifest · candor ·
// CTA) recomposed on the Sheet RECORD layer.
//
// The hero showpiece — the ArtifactBrowser cohort-reaction instrument — becomes
// a §6.4 ConsoleWell: a dark instrument well sitting INSIDE the light page,
// exactly like /about's SpecimenWell. The tabbed browser is an instrument view,
// so it stays dark inside the well; everything else is ink-on-paper record.
//
// Reachable ONLY by typing /product/v2 — nothing links here; the live /product
// page (app/product/page.tsx) is untouched, and this route is robots:noindex +
// in ConditionalTopNav's suppress list (it ships its own SheetTopBar).
//
// This page CONSUMES the shared v2 Sheet layer (components/v2/*, v2-theme.css) —
// it does NOT re-inline tokens.
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
  Chip,
  CalGlyph,
  type SheetNavItem,
  type SpineFact,
} from "@/components/v2";
import { ArtifactBrowser } from "./ArtifactBrowser";
import "@/styles/v2-theme.css";

export const metadata: Metadata = {
  title: "Product · Grounded simulations — Sidira",
  robots: { index: false, follow: false },
};

const NAV: SheetNavItem[] = [
  { label: "Product", href: "#", active: true },
  { label: "About", href: "#" },
  { label: "Capabilities", href: "#" },
];

const SPINE_FACTS: SpineFact[] = [
  { k: "Document", v: "PRODUCT · v1.0" },
  { k: "Filed", v: "2026-06-16" },
  { k: "Snapshot", v: "2026-W25" },
  { k: "Capture", v: "MON 04:00 UTC" },
  { k: "Walker", v: "playwright · 4-pass" },
  { k: "Tenant", v: "sandbox only" },
];

export default function ProductV2Page() {
  return (
    <SheetShell>
      <SheetTopBar
        nav={NAV}
        actions={
          <>
            <Button as="a" href="#" variant="ghost">
              Sign in
            </Button>
            <Button as="a" href="mailto:founders@sidira.ai?subject=Sidira%20sandbox" variant="secondary">
              Connect a sandbox
            </Button>
          </>
        }
      />

      {/* ── THE RECORD — Sheet, still, archival ─────────────────────────────── */}
      <RecordGrid
        spine={
          <ProvenanceSpine heading="Record" facts={SPINE_FACTS} calibrated={false} />
        }
      >
        <article className="v2-doc" style={{ padding: "128px 0 0 56px", maxWidth: 760 }}>
          {/* HERO — above the fold; NOT behind ScrollReveal (visible on load) */}
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
            Product context · auto-captured
          </div>
          <h1
            style={{
              fontWeight: 600,
              fontSize: "clamp(2.4rem,4.4vw,3.25rem)",
              lineHeight: 1.02,
              letterSpacing: "-0.03em",
              color: "var(--sheet-ink)",
              textWrap: "balance",
              maxWidth: "20ch",
            }}
          >
            A simulation is only as honest as its picture of the product today.
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
            Sidira keeps a current, structured snapshot of what you actually shipped &mdash; so a
            synthetic cohort reacts to the <strong>real</strong> product, not one the model invented.
            Fewer hallucinated reads. Grounded answers by Monday.
          </p>

          <div style={{ marginTop: 30, display: "flex", gap: 12, flexWrap: "wrap" }}>
            <Button as="a" href="mailto:founders@sidira.ai?subject=Sidira%20sandbox" variant="primary">
              Connect a sandbox
            </Button>
            <Button as="a" href="#" variant="secondary">
              Read the spec &rarr;
            </Button>
          </div>

          <div style={{ marginTop: 36, display: "flex", gap: 40, flexWrap: "wrap" }}>
            <HeroStat v="8" unit="capabilities" k="walked per snapshot" />
            <HeroStat v="~40" unit="min" k="weekly capture, in CI" />
            <HeroStat v="3" unit="roles" k="re-walked, role-gated" />
          </div>

          {/* THE SHOWPIECE — a §6.4 dark instrument well inside the light page.
              An inspectable ARTIFACT BROWSER: cohort-reaction poster + reverse-PRD
              + reverse-Figma. Rendered eagerly (above the deeper fold). */}
          <div style={{ marginTop: 44 }}>
            <div
              style={{
                fontFamily: "var(--v2-font-mono)",
                fontSize: 10,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--sheet-mut)",
                marginBottom: 10,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span>Specimen · one captured capability</span>
              <span style={{ flex: 1, height: "0.75px", background: "var(--sheet-line)" }} />
            </div>
            <ArtifactBrowser />
            <p
              style={{
                marginTop: 10,
                fontSize: 12,
                color: "var(--sheet-mut)",
                fontFamily: "var(--v2-font-sans)",
                maxWidth: "60ch",
              }}
            >
              The dark well is a live-instrument view, the kind the product renders in motion. On this
              record it sits still: a frozen reading and the two files behind it.
            </p>
          </div>

          {/* ── WHY: THE THREE INPUTS ──────────────────────────────────────── */}
          <ScrollReveal>
            <SheetSection
              kicker="Why it exists"
              title="Three inputs make a grounded read. Two are yours. We keep the third current."
              intro={
                <>
                  Without a current-product representation, a simulation is <strong>ungrounded</strong>{" "}
                  &mdash; the model invents the context and the resulting score is fiction. Sidira closes
                  that gap on a schedule, so no one hand-writes &ldquo;how our product works today&rdquo;
                  before testing a change.
                </>
              }
            >
              <Inputs />
            </SheetSection>
          </ScrollReveal>

          {/* ── THE SYMMETRY PRINCIPLE ──────────────────────────────────────── */}
          <ScrollReveal>
            <SheetSection
              kicker="The load-bearing idea · symmetry"
              title="Compare like-shape to like-shape."
              intro={
                <>
                  A team submits a change as a PRD plus a Figma. Sidira produces the current state as a{" "}
                  <strong>reverse-PRD plus a reverse-Figma</strong> per capability. The simulation diffs
                  one against the other &mdash; apples to apples. This symmetry is the entire reason the
                  snapshot is shaped the way it is.
                </>
              }
            >
              <SymmetryCompare />
            </SheetSection>
          </ScrollReveal>

          {/* ── HOW THE CAPTURE RUNS ────────────────────────────────────────── */}
          <ScrollReveal>
            <SheetSection
              kicker="How the capture runs"
              title="A Playwright walker, authenticated per role, four passes to a snapshot."
              intro={
                <>
                  You name 5&ndash;10 priority capabilities, 1&ndash;3 entry URLs each, and one test login
                  per role into a <strong>sandbox tenant</strong> &mdash; never production. The walker does
                  the rest, every Monday at 04:00 UTC, in roughly 40 minutes of CI.
                </>
              }
            >
              <Pipeline />
              <p
                className="v2-mono"
                style={{ marginTop: 16, fontSize: 11, letterSpacing: "0.04em", color: "var(--sheet-mut)" }}
              >
                SANDBOX TENANT ONLY · MON 04:00 UTC · ~40 MIN CI · PROMOTE → GATED ON REVIEW
              </p>
            </SheetSection>
          </ScrollReveal>

          {/* ── WHAT A CAPABILITY CAPTURES ──────────────────────────────────── */}
          <ScrollReveal>
            <SheetSection
              kicker="Inside a capability"
              title="Two files per capability. Nothing more, nothing less."
              intro={
                <>
                  Screenshots and pixel data are <strong>out</strong> &mdash; a team doesn&rsquo;t submit
                  pixels for the proposed change, so symmetry says we don&rsquo;t capture them either. Copy
                  lives inline in the component nodes. The value is <strong>this</strong> product&rsquo;s
                  specifics, never generic UX advice.
                </>
              }
            >
              <Manifest />
            </SheetSection>
          </ScrollReveal>

          {/* ── CANDOR, SCOPED ──────────────────────────────────────────────── */}
          <ScrollReveal>
            <SheetSection kicker="Candor, scoped" title="The snapshot says what it is.">
              <CandorBand />
            </SheetSection>
          </ScrollReveal>

          {/* ── CTA ─────────────────────────────────────────────────────────── */}
          <ScrollReveal>
            <SheetSection kicker="MVP · Sidira infra · your sandbox" title="Connect your sandbox. Get a grounded read by Monday.">
              <p
                style={{
                  fontFamily: "var(--v2-font-serif)",
                  fontSize: "1.0625rem",
                  lineHeight: 1.62,
                  color: "var(--sheet-mut)",
                  maxWidth: "56ch",
                  marginTop: -8,
                }}
              >
                Name your capabilities, drop in entry URLs and one test login per role. The capture runs
                in CI and publishes on its own &mdash; closing the tab changes nothing.
              </p>
              <div style={{ marginTop: 26, display: "flex", gap: 12, flexWrap: "wrap" }}>
                <Button as="a" href="mailto:founders@sidira.ai?subject=Sidira%20sandbox" variant="primary">
                  Connect a sandbox &rarr;
                </Button>
                <Button as="a" href="#" variant="secondary">
                  Talk to us
                </Button>
              </div>
              <p
                className="v2-mono"
                style={{ marginTop: 24, fontSize: 10.5, letterSpacing: "0.05em", color: "var(--sheet-mut)" }}
              >
                NO PRODUCTION ACCESS · SANDBOX TENANT ONLY · <CalGlyph /> UNCALIBRATED UNTIL GRADED
              </p>
            </SheetSection>
          </ScrollReveal>
        </article>
      </RecordGrid>

      {/* ── FOOTER ────────────────────────────────────────────────────────── */}
      <footer style={{ borderTop: "0.75px solid var(--sheet-line)", background: "var(--sheet-raised)", marginTop: 112 }}>
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
          <span>
            product · v1.0 · snapshot 2026-W25 · sandbox tenant ·{" "}
            <span style={{ color: "var(--sheet-mut)" }}>
              <span className="v2-gh" style={{ marginRight: 4 }}>◇</span>uncalibrated until graded
            </span>
          </span>
          <span>
            <a href="mailto:founders@sidira.ai" style={{ color: "var(--sheet-mut)" }}>
              founders@sidira.ai
            </a>
          </span>
        </div>
      </footer>

      <style>{PRODUCT_CSS}</style>
    </SheetShell>
  );
}

// ── hero stat ───────────────────────────────────────────────────────────────
function HeroStat({ v, unit, k }: { v: string; unit: string; k: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <span className="v2-mono v2-tnum" style={{ fontSize: "1.5rem", fontWeight: 500, color: "var(--sheet-ink)", lineHeight: 1 }}>
        {v}
        <span style={{ fontSize: "0.78rem", color: "var(--sheet-mut)", marginLeft: 5 }}>{unit}</span>
      </span>
      <span className="v2-mono" style={{ fontSize: 10, letterSpacing: "0.09em", textTransform: "uppercase", color: "var(--sheet-mut)" }}>
        {k}
      </span>
    </div>
  );
}

// ── three inputs — a light record ledger of cells ──────────────────────────
function Inputs() {
  return (
    <div
      className="v2-inputs"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3,1fr)",
        border: "0.75px solid var(--sheet-line)",
        borderRadius: "var(--r-panel)",
        overflow: "hidden",
        background: "var(--sheet-raised)",
      }}
    >
      <InputCell
        title="The persona pack"
        chip="YOUR POPULATION"
        tag={<><CalGlyph graded /> GRADED</>}
      >
        Synthetic minds fit from your real user telemetry &mdash; segments, posteriors, and a sample
        of individuals who react. Built once, refit as your base shifts.
      </InputCell>
      <InputCell
        title="The proposed change"
        chip="YOUR PROPOSAL"
        tag="AUTHORED"
      >
        The bet under test, submitted the way teams already work &mdash; a PRD plus a Figma. &ldquo;Move
        saved-card selection above the address step in checkout.&rdquo;
      </InputCell>
      <InputCell
        title="The current product"
        chip="WE KEEP THIS CURRENT"
        tag={<><CalGlyph /> SNAPSHOT</>}
        now
      >
        A weekly snapshot of what you actually shipped, shaped exactly like a proposal &mdash; a
        reverse-PRD plus a reverse-Figma per capability. Generated, never authored.
      </InputCell>
    </div>
  );
}

function InputCell({
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
      className="v2-input-cell"
      style={{
        padding: "26px 24px 28px",
        borderLeft: "0.75px solid var(--sheet-line)",
        position: "relative",
        background: now ? "linear-gradient(180deg,rgba(111,94,51,.045),transparent 62%)" : undefined,
      }}
    >
      <h3 style={{ fontSize: "1.1rem", fontWeight: 600, letterSpacing: "-0.01em", color: "var(--sheet-ink)" }}>{title}</h3>
      <div style={{ marginTop: 9 }}>
        <Chip>{chip}</Chip>
      </div>
      <p style={{ marginTop: 14, fontSize: 13.5, lineHeight: 1.58, color: "var(--sheet-mut)" }}>{children}</p>
      <span className="v2-desig" style={{ position: "absolute", top: 22, right: 22 }}>
        {tag}
      </span>
    </div>
  );
}

// ── symmetry compare — proposed vs as-built; the as-built reads as a diff ───
function SymmetryCompare() {
  return (
    <div
      className="v2-sym"
      style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", alignItems: "stretch" }}
    >
      <SymCol title="Proposed — what the team submits" chip="PRD + FIGMA">
        <Ln h># checkout · saved-card-first</Ln>
        <Ln><K>user_goal:</K> &ldquo;Pay faster with a saved card&rdquo;</Ln>
        <Ln><K>roles:</K>      [guest, member, pro]</Ln>
        <Ln><K>flow:</K>       cart → pay → address → confirm</Ln>
        <Ln><K>success:</K>    fewer steps to a placed order</Ln>
        <Ln><K>figma:</K>      {"{screens:4, components:13,"}</Ln>
        <Ln>             states:[default,error,empty]{"}"}</Ln>
      </SymCol>

      <div className="v2-sym-mid" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "0 26px", gap: 14 }}>
        <span className="v2-sym-vline" style={{ flex: 1, width: "0.75px", background: "linear-gradient(180deg,transparent,var(--sheet-line) 24%,var(--sheet-line) 76%,transparent)" }} />
        <span className="v2-mono v2-sym-lbl" style={{ fontSize: 9.5, letterSpacing: "0.1em", color: "var(--sheet-mut)", writingMode: "vertical-rl", textOrientation: "mixed" }}>DIFFED IN-SIM</span>
        <span className="v2-mono" style={{ fontSize: 22, color: "var(--sheet-mut)" }}>⇄</span>
        <span className="v2-mono v2-sym-lbl" style={{ fontSize: 9.5, letterSpacing: "0.1em", color: "var(--sheet-mut)", writingMode: "vertical-rl", textOrientation: "mixed" }}>SAME SHAPE</span>
        <span className="v2-sym-vline" style={{ flex: 1, width: "0.75px", background: "linear-gradient(180deg,transparent,var(--sheet-line) 24%,var(--sheet-line) 76%,transparent)" }} />
      </div>

      <SymCol title="As-built — what Sidira captured" chip="REVERSE">
        <Ln h># checkout · current</Ln>
        <Ln chg><K>user_goal:</K> &ldquo;Complete a purchase&rdquo;</Ln>
        <Ln><K>roles:</K>      [guest, member, pro]</Ln>
        <Ln chg><K>flow:</K>       cart → <D>address → pay</D> → confirm</Ln>
        <Ln><K>implicit:</K>   optimized for completion</Ln>
        <Ln chg><K>figma:</K>      {"{screens:4, components:"}<D>14</D>,</Ln>
        <Ln>             states:[default,error,empty]{"}"}</Ln>
      </SymCol>
    </div>
  );
}

function SymCol({ title, chip, children }: { title: string; chip: string; children: React.ReactNode }) {
  return (
    <div
      style={{ background: "var(--sheet-raised)", border: "0.75px solid var(--sheet-line)", borderRadius: "var(--r-panel)", overflow: "hidden" }}
    >
      <div style={{ padding: "13px 18px", borderBottom: "0.75px solid var(--sheet-line)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, background: "var(--sheet-sunk)" }}>
        <span style={{ fontSize: 13.5, fontWeight: 600, color: "var(--sheet-ink)" }}>{title}</span>
        <Chip>{chip}</Chip>
      </div>
      <div className="v2-mono" style={{ padding: 20, fontSize: 12, lineHeight: 1.75, color: "var(--sheet-ink)" }}>
        {children}
      </div>
    </div>
  );
}

function Ln({ children, h = false, chg = false }: { children: React.ReactNode; h?: boolean; chg?: boolean }) {
  return (
    <span
      style={{
        display: "block",
        whiteSpace: "pre-wrap",
        padding: "0 8px",
        margin: "0 -8px",
        borderRadius: 2,
        color: h ? "var(--sheet-ink)" : undefined,
        fontWeight: h ? 600 : undefined,
        ...(chg ? { background: "rgba(111,94,51,.07)", boxShadow: "inset 2px 0 0 var(--sheet-spread)" } : null),
      }}
    >
      {children}
    </span>
  );
}
const K = ({ children }: { children: React.ReactNode }) => <span style={{ color: "var(--sheet-mut)" }}>{children}</span>;
const D = ({ children }: { children: React.ReactNode }) => <span style={{ color: "var(--sheet-spread)" }}>{children}</span>;

// ── pipeline — a quiet flow; arrows carry order, no 01/02 numerals ──────────
const STEPS = [
  { glyph: "→", h: "Walk, per role", p: "Logs in as each declared role into the sandbox, then walks each flow ~3 hops deep — screens, components, states, copy, transitions." },
  { glyph: "→", h: "Synthesize reverse-PRD", p: "Goal, roles, flow-per-role, success criteria, edge cases, and the implicit metric the surface optimizes for." },
  { glyph: "→", h: "Emit reverse-Figma", p: "Structured screens, components with semantic roles, per-state copy, and prototype transitions — Figma-level abstraction, no pixels." },
  { glyph: "▪", h: "Tag & diff", p: "Versions the snapshot and diffs it against last week. Promotion to “latest” is gated on a human reviewing the diff." },
];

function Pipeline() {
  return (
    <div
      className="v2-pipe"
      style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", border: "0.75px solid var(--sheet-line)", borderRadius: "var(--r-panel)", overflow: "hidden", background: "var(--sheet-raised)" }}
    >
      {STEPS.map((s, i) => (
        <div key={s.h} className="v2-step" style={{ padding: "22px 20px 24px", borderLeft: i === 0 ? "none" : "0.75px solid var(--sheet-line)", position: "relative" }}>
          <span className="v2-mono" style={{ fontSize: 13, color: "var(--sheet-mut)" }}>{s.glyph}</span>
          <h4 style={{ marginTop: 13, fontSize: 14, fontWeight: 600, color: "var(--sheet-ink)", lineHeight: 1.3 }}>{s.h}</h4>
          <p style={{ marginTop: 9, fontSize: 12.5, lineHeight: 1.55, color: "var(--sheet-mut)" }}>{s.p}</p>
          {i < STEPS.length - 1 ? (
            <svg className="v2-step-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} style={{ position: "absolute", right: -7, top: 28, width: 13, height: 13, color: "var(--sheet-mut)", zIndex: 2 }}>
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          ) : null}
        </div>
      ))}
    </div>
  );
}

// ── manifest — a tiny two-file directory (light record) ─────────────────────
function Manifest() {
  return (
    <div
      style={{ border: "0.75px solid var(--sheet-line)", borderRadius: "var(--r-panel)", overflow: "hidden", background: "var(--sheet-raised)" }}
    >
      <div className="v2-mf-head" style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 18, alignItems: "baseline", padding: "13px 22px", background: "var(--sheet-sunk)" }}>
        <span className="v2-mono" style={{ fontSize: 12.5, color: "var(--sheet-ink)", fontWeight: 500, letterSpacing: "0.01em" }}>capability/checkout/</span>
        <span style={{ fontSize: 12.5, color: "var(--sheet-mut)", lineHeight: 1.5, textAlign: "right" }}>2 files · no screenshots, no pixels — by symmetry with a submitted change</span>
      </div>
      <MfRow file="reverse-prd.md" fmt="MARKDOWN" fields="goal · roles & flow-per-role · success criteria · edge cases · dependencies · implicit metric" />
      <MfRow file="reverse-figma.json" fmt="JSON" fields="screens scoped per role · components w/ semantic role · states (default · error · empty) · inline copy · click→screen transitions · role-gating" />
      <div className="v2-mf-foot" style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 18, alignItems: "baseline", padding: "18px 22px", borderTop: "0.75px solid var(--sheet-line)", background: "var(--sheet-sunk)" }}>
        <span className="v2-mono" style={{ fontSize: 11, letterSpacing: "0.05em", color: "var(--sheet-spread)", textTransform: "uppercase" }}>Δ DIFF vs prior</span>
        <span style={{ fontSize: 13, color: "var(--sheet-mut)", lineHeight: 1.55 }}>
          A by-product, not a third file: added / removed capabilities, copy &amp; component deltas, and
          flow-shape changes &mdash; computed on tag, and the gate on promoting a snapshot to{" "}
          <span className="v2-mono" style={{ color: "var(--sheet-mut)", fontSize: 12 }}>latest</span>.
        </span>
      </div>
    </div>
  );
}

function MfRow({ file, fmt, fields }: { file: string; fmt: string; fields: string }) {
  return (
    <div className="v2-mf-row" style={{ display: "grid", gridTemplateColumns: "200px 88px 1fr", gap: 18, alignItems: "baseline", padding: "18px 22px", borderTop: "0.75px solid var(--sheet-line)" }}>
      <span className="v2-mono" style={{ fontSize: 13, color: "var(--sheet-ink)", fontWeight: 500 }}>{file}</span>
      <span className="v2-mono" style={{ fontSize: 9.5, letterSpacing: "0.08em", color: "var(--sheet-mut)", border: "0.75px solid var(--sheet-line)", borderRadius: 2, padding: "2px 6px", justifySelf: "start" }}>{fmt}</span>
      <span className="v2-mono" style={{ fontSize: 11.5, color: "var(--sheet-ink)", lineHeight: 1.65, letterSpacing: "0.01em" }}>{fields}</span>
    </div>
  );
}

// ── candor band — the snapshot prints its own calibration state ─────────────
function CandorBand() {
  return (
    <div className="v2-candor" style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 48, alignItems: "start" }}>
      <div>
        <p style={{ fontFamily: "var(--v2-font-serif)", fontSize: "1.2rem", lineHeight: 1.5, color: "var(--sheet-ink)", letterSpacing: "-0.005em", textWrap: "balance" }}>
          The snapshot is a <span style={{ color: "var(--sheet-spread)" }}>raw, uncalibrated</span> reading
          of your product &mdash; and it says so, on every reading it touches. Identifiers, seeds, and
          dates print as plain fact.
        </p>
        <p className="v2-mono" style={{ marginTop: 18, fontSize: 11, letterSpacing: "0.04em", color: "var(--sheet-mut)" }}>
          SPREAD ON INFERRED READINGS ONLY · IDS &amp; SEEDS PRINT BARE
        </p>
      </div>

      <div
        style={{ background: "var(--sheet-raised)", border: "0.75px solid var(--sheet-line)", borderRadius: "var(--r-panel)", padding: 24 }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, paddingBottom: 18, borderBottom: "0.75px solid var(--sheet-line)" }}>
          <span className="v2-mono v2-tnum" style={{ fontSize: "2.2rem", fontWeight: 500, color: "var(--sheet-ink)", lineHeight: 1 }}>0.62</span>
          <span className="v2-mono v2-tnum" style={{ fontSize: "1.05rem", color: "var(--sheet-spread)" }}>±0.08</span>
          <span className="v2-gh" style={{ fontSize: "1.25rem" }}>◇</span>
          <span style={{ fontSize: 12, color: "var(--sheet-mut)", lineHeight: 1.45, maxWidth: "17ch", marginLeft: "auto" }}>
            an inferred reading carries its spread and its calibration glyph &mdash; always
          </span>
        </div>
        <div style={{ marginTop: 4, display: "flex", flexDirection: "column" }}>
          <CRow glyph={<span className="v2-gh">◇</span>} title="Uncalibrated">
            No real outcome yet. The reading is directional, drifts faintly, and freezes the instant
            you look at it &mdash; it can&rsquo;t lock a verdict.
          </CRow>
          <CRow glyph={<span className="v2-gf">◆</span>} title="Graded">
            Validated against a real outcome. It snaps from noise to a stable reading, settles once,
            and comes to rest.
          </CRow>
          <CRow glyph={<span style={{ color: "var(--sheet-mut)" }}>·</span>} title="Facts print bare" last>
            Persona id, seed <Fact>0x4f</Fact>, snapshot <Fact>2026-W25</Fact>, and raw <Fact>n=240</Fact>{" "}
            wear no ± &mdash; they were recorded, not inferred.
          </CRow>
        </div>
      </div>
    </div>
  );
}

function CRow({ glyph, title, children, last = false }: { glyph: React.ReactNode; title: string; children: React.ReactNode; last?: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 14, padding: "14px 0", borderBottom: last ? "none" : "0.75px solid var(--sheet-line)" }}>
      <span className="v2-mono" style={{ fontSize: "1rem", flex: "0 0 auto", width: 18, textAlign: "center", lineHeight: 1.45 }}>{glyph}</span>
      <div>
        <b style={{ color: "var(--sheet-ink)", fontWeight: 600, display: "block", fontSize: 14 }}>{title}</b>
        <span style={{ color: "var(--sheet-mut)", fontSize: 13, lineHeight: 1.5 }}>{children}</span>
      </div>
    </div>
  );
}
const Fact = ({ children }: { children: React.ReactNode }) => (
  <span className="v2-mono" style={{ color: "var(--sheet-mut)" }}>{children}</span>
);

// ── page-local responsive rules (token-driven; mirrors the mock breakpoints) ──
const PRODUCT_CSS = `
@media(max-width:1024px){
  .v2-doc{padding:48px 0 0!important;}
}
@media(max-width:900px){
  .v2-candor{grid-template-columns:1fr!important;gap:28px!important;}
  .v2-pipe{grid-template-columns:repeat(2,1fr)!important;}
  .v2-step-arrow{display:none!important;}
  .v2-mf-row{grid-template-columns:160px 72px 1fr!important;gap:12px!important;}
}
@media(max-width:720px){
  .v2-inputs{grid-template-columns:1fr!important;}
  .v2-input-cell{border-left:none!important;border-top:0.75px solid var(--sheet-line);}
  .v2-input-cell:first-child{border-top:none;}
  .v2-mf-row,.v2-mf-foot,.v2-mf-head{grid-template-columns:1fr!important;gap:8px!important;}
  .v2-sym{grid-template-columns:1fr!important;gap:16px!important;}
  .v2-sym-mid{flex-direction:row!important;padding:0!important;}
  .v2-sym-vline{display:none!important;}
  .v2-sym-lbl{writing-mode:horizontal-tb!important;}
  .v2-pipe{grid-template-columns:1fr!important;}
  .v2-step{border-left:none!important;border-top:0.75px solid var(--sheet-line);}
  .v2-step:first-child{border-top:none;}
}
`;
