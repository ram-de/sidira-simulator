// ───────────────────────────────────────────────────────────────────────────
// /product/v2 — DESIGN SYSTEM v2 PREVIEW (flagged · unlinked)
//
// Phase-1 port of the finalized "Reading Console" design system (v2) to the
// product page. Reachable ONLY by typing /product/v2 — nothing links here; the
// live /product page (app/product/page.tsx) is untouched. Mirrors the
// console-results preview precedent.
//
// IMPACT BUDGET (§0.2): this page is WORKING-class. The crawler is
// infrastructure, not the computation — so NO full-bleed Population Field (P9).
// The hero showpiece is a quiet, inspectable ARTIFACT BROWSER; a single static
// distribution poster (SVG) appears once. ~80% of the page is brutally quiet.
//
// This page CONSUMES the shared v2 layer (lib/design-v2.ts, components/v2/*,
// v2-theme.css) — it does NOT re-inline tokens. That is the test that the layer
// is real and the next 14 pages can reuse it.
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
  type NavItem,
} from "@/components/v2";
import { ArtifactBrowser } from "./ArtifactBrowser";
import "@/styles/v2-theme.css";

export const metadata: Metadata = {
  title: "Product · Grounded simulations — Sidira",
  robots: { index: false, follow: false },
};

const NAV: NavItem[] = [
  { label: "Personas", href: "#" },
  { label: "Product", href: "#", active: true },
  { label: "Simulations", href: "#" },
  { label: "About", href: "#" },
];

export default function ProductV2Page() {
  return (
    <ConsoleShell>
      <TopBar
        nav={NAV}
        provenance={{ label: "SNAPSHOT 2026-W25", calibrated: false, live: false }}
        action={
          <Button as="a" href="#" variant="secondary">
            Sign in
          </Button>
        }
      />

      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      <section style={{ position: "relative", borderBottom: "1px solid var(--console-line-50)", overflow: "hidden" }}>
        <div
          aria-hidden
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 0,
            pointerEvents: "none",
            background:
              "radial-gradient(80% 70% at 78% 16%, rgba(79,168,224,.05), transparent 60%), linear-gradient(180deg, var(--console-850) 0%, var(--console-900) 100%)",
          }}
        />
        <Wrap style={{ position: "relative", zIndex: 2, paddingTop: 104, paddingBottom: 104 }}>
          <div className="v2-hero-grid">
            <div>
              {/* the page's one decorative eyebrow (§2.3) — neutral ink (P2) */}
              <div style={{ display: "inline-flex", alignItems: "center", gap: 9, marginBottom: 28 }}>
                <span aria-hidden style={{ width: 34, height: 1, background: "linear-gradient(90deg,var(--text-mut),transparent)" }} />
                <Designator>PRODUCT CONTEXT · AUTO-CAPTURED</Designator>
              </div>
              <h1
                style={{
                  fontSize: "clamp(2.6rem,5vw,4.2rem)",
                  lineHeight: 1.0,
                  letterSpacing: "-0.035em",
                  fontWeight: 700,
                  color: "var(--text-hi)",
                  textWrap: "balance",
                  marginBottom: 26,
                }}
              >
                A simulation is only as honest as its picture of the product today.
              </h1>
              <p style={{ fontSize: "1.18rem", lineHeight: 1.55, color: "var(--text)", maxWidth: "40ch", letterSpacing: "-0.005em", fontWeight: 450 }}>
                Sidira keeps a current, structured snapshot of what you actually shipped — so a
                synthetic cohort reacts to the{" "}
                <b style={{ color: "var(--text-hi)", fontWeight: 550 }}>real</b> product, not one the
                model invented.{" "}
                <b style={{ color: "var(--text-hi)", fontWeight: 550 }}>
                  Fewer hallucinated reads. Grounded answers by Monday.
                </b>
              </p>
              <div style={{ display: "flex", gap: 12, marginTop: 36, alignItems: "center", flexWrap: "wrap" }}>
                <Button as="a" href="#" variant="primary" hero>
                  Connect a sandbox
                </Button>
                <Button as="a" href="#" variant="ghost" hero>
                  Read the spec ↗
                </Button>
              </div>
              <div style={{ marginTop: 44, display: "flex", gap: 40, flexWrap: "wrap" }}>
                <HeroStat v="8" unit="capabilities" k="walked per snapshot" />
                <HeroStat v="~40" unit="min" k="weekly capture, in CI" />
                <HeroStat v="3" unit="roles" k="re-walked, role-gated" />
              </div>
            </div>
            <ArtifactBrowser />
          </div>
        </Wrap>
      </section>

      {/* ── WHY: THE THREE INPUTS ────────────────────────────────────────── */}
      <Section>
        <Wrap>
          <SectionHead
            eyebrow="WHY IT EXISTS"
            title="Three inputs make a grounded read. Two are yours. We keep the third current."
            sub={
              <>
                Without a current-product representation, a simulation is{" "}
                <b style={{ color: "var(--text)", fontWeight: 500 }}>ungrounded</b> — the model invents
                the context and the resulting score is fiction. Sidira closes that gap on a schedule,
                so no one hand-writes “how our product works today” before testing a change.
              </>
            }
          />
          <ScrollReveal
            className="v2-inputs"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3,1fr)",
              border: "1px solid var(--console-line-50)",
              borderRadius: "var(--r-panel)",
              overflow: "hidden",
              background: "var(--console-850)",
            }}
          >
            <InputCell
              title="The persona pack"
              chip="YOUR POPULATION"
              tag={<><CalGlyph graded /> GRADED</>}
            >
              Synthetic minds fit from your real user telemetry — segments, posteriors, and a sample
              of individuals who react. Built once, refit as your base shifts.
            </InputCell>
            <InputCell
              title="The proposed change"
              chip="YOUR PROPOSAL"
              tag="AUTHORED"
            >
              The bet under test, submitted the way teams already work — a PRD plus a Figma. “Move
              saved-card selection above the address step in checkout.”
            </InputCell>
            <InputCell
              title="The current product"
              chip="WE KEEP THIS CURRENT"
              tag={<><CalGlyph /> SNAPSHOT</>}
              now
            >
              A weekly snapshot of what you actually shipped, shaped exactly like a proposal — a
              reverse-PRD plus a reverse-Figma per capability. Generated, never authored.
            </InputCell>
          </ScrollReveal>
        </Wrap>
      </Section>

      {/* ── THE SYMMETRY PRINCIPLE ───────────────────────────────────────── */}
      <Section>
        <Wrap>
          <SectionHead
            eyebrow="THE LOAD-BEARING IDEA · SYMMETRY"
            title="Compare like-shape to like-shape."
            sub={
              <>
                A team submits a change as a PRD plus a Figma. Sidira produces the current state as a{" "}
                <b style={{ color: "var(--text)", fontWeight: 500 }}>reverse-PRD plus a reverse-Figma</b>{" "}
                per capability. The simulation diffs one against the other — apples to apples. This
                symmetry is the entire reason the snapshot is shaped the way it is.
              </>
            }
          />
          <SymmetryCompare />
        </Wrap>
      </Section>

      {/* ── HOW IT WALKS — a flow, no 01/02 numerals; arrows carry order ─── */}
      <Section>
        <Wrap>
          <SectionHead
            eyebrow="HOW THE CAPTURE RUNS"
            title="A Playwright walker, authenticated per role, four passes to a snapshot."
            sub={
              <>
                You name 5–10 priority capabilities, 1–3 entry URLs each, and one test login per role
                into a <b style={{ color: "var(--text)", fontWeight: 500 }}>sandbox tenant</b> — never
                production. The walker does the rest, every Monday at 04:00 UTC, in roughly 40 minutes
                of CI.
              </>
            }
          />
          <Pipeline />
          <p
            className="v2-mono"
            style={{ marginTop: 18, fontSize: 11, letterSpacing: "0.04em", color: "var(--text-mut)" }}
          >
            SANDBOX TENANT ONLY · MON 04:00 UTC · ~40 MIN CI · PROMOTE → GATED ON REVIEW
          </p>
        </Wrap>
      </Section>

      {/* ── WHAT A CAPABILITY CAPTURES ───────────────────────────────────── */}
      <Section>
        <Wrap>
          <SectionHead
            eyebrow="INSIDE A CAPABILITY"
            title="Two files per capability. Nothing more, nothing less."
            sub={
              <>
                Screenshots and pixel data are <b style={{ color: "var(--text)", fontWeight: 500 }}>out</b>{" "}
                — a team doesn’t submit pixels for the proposed change, so symmetry says we don’t
                capture them either. Copy lives inline in the component nodes. The value is{" "}
                <b style={{ color: "var(--text)", fontWeight: 500 }}>this</b> product’s specifics, never
                generic UX advice.
              </>
            }
          />
          <Manifest />
        </Wrap>
      </Section>

      {/* ── CANDOR — one stamp specimen, scoped to inferred readings ──────── */}
      <Section>
        <Wrap>
          <CandorBand />
        </Wrap>
      </Section>

      {/* ── CTA ──────────────────────────────────────────────────────────── */}
      <section style={{ padding: "112px 0", textAlign: "center" }}>
        <Wrap>
          <ScrollReveal style={{ maxWidth: 640, margin: "0 auto" }}>
            <div style={{ marginBottom: 22 }}>
              <Designator>MVP · SIDIRA INFRA · YOUR SANDBOX</Designator>
            </div>
            <h2 style={{ fontSize: "2.5rem", lineHeight: 1.08, letterSpacing: "-0.03em", fontWeight: 600, color: "var(--text-hi)", textWrap: "balance" }}>
              Connect your sandbox. Get a grounded read by Monday.
            </h2>
            <p style={{ marginTop: 20, fontSize: "1.1rem", color: "var(--text-mut)", lineHeight: 1.6, maxWidth: "48ch", marginLeft: "auto", marginRight: "auto" }}>
              Name your capabilities, drop in entry URLs and one test login per role. The capture runs
              in CI and publishes on its own — closing the tab changes nothing.
            </p>
            <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 38, flexWrap: "wrap" }}>
              <Button as="a" href="#" variant="primary" hero>
                Connect a sandbox
              </Button>
              <Button as="a" href="#" variant="secondary" hero>
                Talk to us
              </Button>
            </div>
            <p
              className="v2-mono"
              style={{ marginTop: 28, fontSize: 10.5, letterSpacing: "0.06em", color: "var(--text-mut)" }}
            >
              NO PRODUCTION ACCESS · SANDBOX TENANT ONLY · <CalGlyph /> UNCALIBRATED UNTIL GRADED
            </p>
          </ScrollReveal>
        </Wrap>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────────────────── */}
      <footer style={{ borderTop: "1px solid var(--console-line-50)", padding: "40px 0" }}>
        <Wrap style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
          <span style={{ fontWeight: 600, letterSpacing: "0.06em", color: "var(--text-hi)", fontSize: 14 }}>
            SIDIRA
          </span>
          <Designator>A MEASUREMENT INSTRUMENT FOR HUMAN REACTION</Designator>
          <div style={{ marginLeft: "auto", display: "flex", gap: 22 }}>
            {["Spec", "Personas", "Simulations", "Privacy"].map((l) => (
              <a key={l} href="#" style={{ fontSize: 13, color: "var(--text-mut)" }}>
                {l}
              </a>
            ))}
          </div>
        </Wrap>
      </footer>

      {/* page-local responsive rules for the grid sections (still token-driven) */}
      <style>{HERO_GRID_CSS}</style>
    </ConsoleShell>
  );
}

// ── hero stat ───────────────────────────────────────────────────────────────
function HeroStat({ v, unit, k }: { v: string; unit: string; k: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <span className="v2-mono v2-tnum" style={{ fontSize: "1.5rem", fontWeight: 500, color: "var(--text-hi)", lineHeight: 1 }}>
        {v}
        <span style={{ fontSize: "0.78rem", color: "var(--text-mut)", marginLeft: 5 }}>{unit}</span>
      </span>
      <span className="v2-mono" style={{ fontSize: 10, letterSpacing: "0.09em", textTransform: "uppercase", color: "var(--text-mut)" }}>
        {k}
      </span>
    </div>
  );
}

// ── three-inputs cell ───────────────────────────────────────────────────────
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
        padding: "28px 26px 30px",
        borderLeft: "1px solid var(--console-line-40)",
        position: "relative",
        background: now ? "linear-gradient(180deg,rgba(255,255,255,.025),transparent 62%)" : undefined,
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

// ── symmetry compare — proposed vs as-built, the as-built reads as a diff ───
function SymmetryCompare() {
  return (
    <ScrollReveal
      className="v2-sym"
      style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", alignItems: "stretch" }}
    >
      <SymCol title="Proposed — what the team submits" chip="PRD + FIGMA">
        <Ln h># checkout · saved-card-first</Ln>
        <Ln><K>user_goal:</K> "Pay faster with a saved card"</Ln>
        <Ln><K>roles:</K>      [guest, member, pro]</Ln>
        <Ln><K>flow:</K>       cart → pay → address → confirm</Ln>
        <Ln><K>success:</K>    fewer steps to a placed order</Ln>
        <Ln><K>figma:</K>      {"{screens:4, components:13,"}</Ln>
        <Ln>             states:[default,error,empty]{"}"}</Ln>
      </SymCol>

      <div className="v2-sym-mid" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "0 28px", gap: 14 }}>
        <span className="v2-sym-vline" style={{ flex: 1, width: 1, background: "linear-gradient(180deg,transparent,var(--console-line) 24%,var(--console-line) 76%,transparent)" }} />
        <span className="v2-mono v2-sym-lbl" style={{ fontSize: 9.5, letterSpacing: "0.1em", color: "var(--text-mut)", writingMode: "vertical-rl", textOrientation: "mixed" }}>DIFFED IN-SIM</span>
        <span className="v2-mono" style={{ fontSize: 22, color: "var(--text-mut)" }}>⇄</span>
        <span className="v2-mono v2-sym-lbl" style={{ fontSize: 9.5, letterSpacing: "0.1em", color: "var(--text-mut)", writingMode: "vertical-rl", textOrientation: "mixed" }}>SAME SHAPE</span>
        <span className="v2-sym-vline" style={{ flex: 1, width: 1, background: "linear-gradient(180deg,transparent,var(--console-line) 24%,var(--console-line) 76%,transparent)" }} />
      </div>

      <SymCol title="As-built — what Sidira captured" chip="REVERSE">
        <Ln h># checkout · current</Ln>
        <Ln chg><K>user_goal:</K> "Complete a purchase"</Ln>
        <Ln><K>roles:</K>      [guest, member, pro]</Ln>
        <Ln chg><K>flow:</K>       cart → <D>address → pay</D> → confirm</Ln>
        <Ln><K>implicit:</K>   optimized for completion</Ln>
        <Ln chg><K>figma:</K>      {"{screens:4, components:"}<D>14</D>,</Ln>
        <Ln>             states:[default,error,empty]{"}"}</Ln>
      </SymCol>
    </ScrollReveal>
  );
}

function SymCol({ title, chip, children }: { title: string; chip: string; children: React.ReactNode }) {
  return (
    <div
      className="v2-elevated"
      style={{ background: "var(--console-850)", border: "1px solid var(--console-line-50)", borderRadius: "var(--r-panel)", overflow: "hidden" }}
    >
      <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--console-line-50)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, background: "rgba(11,18,32,.35)" }}>
        <span style={{ fontSize: 14, fontWeight: 550, color: "var(--text-hi)" }}>{title}</span>
        <Chip>{chip}</Chip>
      </div>
      <div className="v2-mono" style={{ padding: 20, fontSize: 12, lineHeight: 1.75, color: "var(--text)" }}>
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
        color: h ? "var(--text-hi)" : undefined,
        fontWeight: h ? 500 : undefined,
        ...(chg ? { background: "rgba(200,182,138,.07)", boxShadow: "inset 2px 0 0 var(--spread)" } : null),
      }}
    >
      {children}
    </span>
  );
}
const K = ({ children }: { children: React.ReactNode }) => <span style={{ color: "var(--text-mut)" }}>{children}</span>;
const D = ({ children }: { children: React.ReactNode }) => <span style={{ color: "var(--spread)" }}>{children}</span>;

// ── pipeline — a quiet flow; arrows carry order, no 01/02 numerals ──────────
const STEPS = [
  { glyph: "→", h: "Walk, per role", p: "Logs in as each declared role into the sandbox, then walks each flow ~3 hops deep — screens, components, states, copy, transitions." },
  { glyph: "→", h: "Synthesize reverse-PRD", p: "Goal, roles, flow-per-role, success criteria, edge cases, and the implicit metric the surface optimizes for." },
  { glyph: "→", h: "Emit reverse-Figma", p: "Structured screens, components with semantic roles, per-state copy, and prototype transitions — Figma-level abstraction, no pixels." },
  { glyph: "▪", h: "Tag & diff", p: "Versions the snapshot and diffs it against last week. Promotion to “latest” is gated on a human reviewing the diff." },
];

function Pipeline() {
  return (
    <ScrollReveal
      className="v2-pipe"
      style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", border: "1px solid var(--console-line-50)", borderRadius: "var(--r-panel)", overflow: "hidden", background: "var(--console-850)" }}
    >
      {STEPS.map((s, i) => (
        <div key={s.h} className="v2-step" style={{ padding: "24px 22px 26px", borderLeft: i === 0 ? "none" : "1px solid var(--console-line-40)", position: "relative" }}>
          <span className="v2-mono" style={{ fontSize: 13, color: "var(--text-mut)" }}>{s.glyph}</span>
          <h4 style={{ marginTop: 14, fontSize: 14.5, fontWeight: 550, color: "var(--text-hi)", lineHeight: 1.3 }}>{s.h}</h4>
          <p style={{ marginTop: 9, fontSize: 13, lineHeight: 1.55, color: "var(--text-mut)" }}>{s.p}</p>
          {i < STEPS.length - 1 ? (
            <svg className="v2-step-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} style={{ position: "absolute", right: -7, top: 30, width: 13, height: 13, color: "var(--text-mut)", zIndex: 2 }}>
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          ) : null}
        </div>
      ))}
    </ScrollReveal>
  );
}

// ── manifest — a tiny two-file directory (breaks the grid cadence) ──────────
function Manifest() {
  return (
    <ScrollReveal
      className="v2-elevated"
      style={{ border: "1px solid var(--console-line-50)", borderRadius: "var(--r-panel)", overflow: "hidden", background: "var(--console-850)" }}
    >
      <div className="v2-mf-head" style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 18, alignItems: "baseline", padding: "13px 24px", background: "rgba(11,18,32,.35)" }}>
        <span className="v2-mono" style={{ fontSize: 12.5, color: "var(--text-hi)", fontWeight: 500, letterSpacing: "0.01em" }}>capability/checkout/</span>
        <span style={{ fontSize: 12.5, color: "var(--text-mut)", lineHeight: 1.5, textAlign: "right" }}>2 files · no screenshots, no pixels — by symmetry with a submitted change</span>
      </div>
      <MfRow file="reverse-prd.md" fmt="MARKDOWN" fields="goal · roles & flow-per-role · success criteria · edge cases · dependencies · implicit metric" />
      <MfRow file="reverse-figma.json" fmt="JSON" fields="screens scoped per role · components w/ semantic role · states (default · error · empty) · inline copy · click→screen transitions · role-gating" />
      <div className="v2-mf-foot" style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 18, alignItems: "baseline", padding: "18px 24px", borderTop: "1px solid var(--console-line-40)", background: "rgba(11,18,32,.2)" }}>
        <span className="v2-mono" style={{ fontSize: 11, letterSpacing: "0.05em", color: "var(--spread)", textTransform: "uppercase" }}>Δ DIFF vs prior</span>
        <span style={{ fontSize: 13, color: "var(--text-mut)", lineHeight: 1.55 }}>
          A by-product, not a third file: added / removed capabilities, copy &amp; component deltas, and
          flow-shape changes — computed on tag, and the gate on promoting a snapshot to{" "}
          <span className="v2-mono" style={{ color: "var(--text-mut)", fontSize: 12 }}>latest</span>.
        </span>
      </div>
    </ScrollReveal>
  );
}

function MfRow({ file, fmt, fields }: { file: string; fmt: string; fields: string }) {
  return (
    <div className="v2-mf-row" style={{ display: "grid", gridTemplateColumns: "200px 88px 1fr", gap: 18, alignItems: "baseline", padding: "18px 24px", borderTop: "1px solid var(--console-line-40)" }}>
      <span className="v2-mono" style={{ fontSize: 13, color: "var(--text-hi)", fontWeight: 500 }}>{file}</span>
      <span className="v2-mono" style={{ fontSize: 9.5, letterSpacing: "0.08em", color: "var(--text-mut)", border: "1px solid var(--console-line-55)", borderRadius: 2, padding: "2px 6px", justifySelf: "start" }}>{fmt}</span>
      <span className="v2-mono" style={{ fontSize: 11.5, color: "var(--text)", lineHeight: 1.65, letterSpacing: "0.01em" }}>{fields}</span>
    </div>
  );
}

// ── candor band — one stamp specimen, scoped to inferred readings ───────────
function CandorBand() {
  return (
    <div className="v2-candor" style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 64, alignItems: "center" }}>
      <ScrollReveal>
        <div style={{ marginBottom: 18 }}>
          <Designator>CANDOR, SCOPED</Designator>
        </div>
        <p style={{ fontSize: "1.35rem", lineHeight: 1.5, color: "var(--text-hi)", letterSpacing: "-0.015em", fontWeight: 450, textWrap: "balance" }}>
          The snapshot is a <span style={{ color: "var(--spread)" }}>raw, uncalibrated</span> reading
          of your product — and it says so, on every reading it touches. Identifiers, seeds, and dates
          print as plain fact.
        </p>
        <p className="v2-mono" style={{ marginTop: 20, fontSize: 11, letterSpacing: "0.04em", color: "var(--text-mut)" }}>
          SPREAD ON INFERRED READINGS ONLY · IDS &amp; SEEDS PRINT BARE
        </p>
      </ScrollReveal>

      <ScrollReveal
        className="v2-elevated"
        style={{ background: "var(--console-850)", border: "1px solid var(--console-line-50)", borderRadius: "var(--r-panel)", padding: 26 }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, paddingBottom: 20, borderBottom: "1px solid var(--console-line-40)" }}>
          <span className="v2-mono v2-tnum" style={{ fontSize: "2.4rem", fontWeight: 500, color: "var(--text-hi)", lineHeight: 1 }}>0.62</span>
          <span className="v2-mono v2-tnum" style={{ fontSize: "1.05rem", color: "var(--spread)" }}>±0.08</span>
          <span style={{ fontSize: "1.25rem", color: "var(--spread-dim)" }}>◇</span>
          <span style={{ fontSize: 12, color: "var(--text-mut)", lineHeight: 1.45, maxWidth: "17ch", marginLeft: "auto" }}>
            an inferred reading carries its spread and its calibration glyph — always
          </span>
        </div>
        <div style={{ marginTop: 6, display: "flex", flexDirection: "column" }}>
          <CRow glyph={<span className="v2-gh">◇</span>} title="Uncalibrated">
            No real outcome yet. The reading is directional, drifts faintly, and freezes the instant
            you look at it — it can’t lock a verdict.
          </CRow>
          <CRow glyph={<span className="v2-gf">◆</span>} title="Graded">
            Validated against a real outcome. It snaps from noise to a stable reading, settles once,
            and comes to rest.
          </CRow>
          <CRow glyph={<span style={{ color: "var(--text-mut)" }}>·</span>} title="Facts print bare" last>
            Persona id, seed <Fact>0x4f</Fact>, snapshot <Fact>2026-W25</Fact>, and raw <Fact>n=240</Fact>{" "}
            wear no ± — they were recorded, not inferred.
          </CRow>
        </div>
      </ScrollReveal>
    </div>
  );
}

function CRow({ glyph, title, children, last = false }: { glyph: React.ReactNode; title: string; children: React.ReactNode; last?: boolean }) {
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

// ── responsive grid rules (token-driven; mirrors the mock breakpoints) ──────
const HERO_GRID_CSS = `
.v2-hero-grid{display:grid;grid-template-columns:minmax(0,1fr) 512px;gap:72px;align-items:center;}
@media(max-width:1080px){
  .v2-hero-grid{grid-template-columns:1fr;gap:52px;}
  .v2-candor{grid-template-columns:1fr!important;gap:40px!important;}
  .v2-pipe{grid-template-columns:repeat(2,1fr)!important;}
  .v2-step-arrow{display:none!important;}
  .v2-mf-row{grid-template-columns:160px 72px 1fr!important;gap:12px!important;}
}
@media(max-width:760px){
  .v2-inputs{grid-template-columns:1fr!important;}
  .v2-input-cell{border-left:none!important;border-top:1px solid var(--console-line-40);}
  .v2-input-cell:first-child{border-top:none;}
  .v2-mf-row,.v2-mf-foot,.v2-mf-head{grid-template-columns:1fr!important;gap:8px!important;}
  .v2-sym{grid-template-columns:1fr!important;gap:16px!important;}
  .v2-sym-mid{flex-direction:row!important;padding:0!important;}
  .v2-sym-vline{display:none!important;}
  .v2-sym-lbl{writing-mode:horizontal-tb!important;}
  .v2-pipe{grid-template-columns:1fr!important;}
  .v2-step{border-left:none!important;border-top:1px solid var(--console-line-40);}
  .v2-step:first-child{border-top:none;}
}
`;
