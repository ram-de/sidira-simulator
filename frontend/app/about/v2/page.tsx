// ───────────────────────────────────────────────────────────────────────────
// /about/v2 — DESIGN SYSTEM v2 PREVIEW · SHEET (light) RECORD page (flagged · unlinked)
//
// Phase-2 port of the "Reading Console" v2 system. /about is a RECORD-class
// Sheet page (§4 archetype): still, ink-on-paper, serif prose, a Provenance
// Spine binder-margin, and exactly ONE §6.4 Console well (a frozen reading
// specimen) embedded without inverting the route. Reachable ONLY by typing
// /about/v2 — nothing links here; the live /about page is untouched.
//
// This page CONSUMES the shared v2 Sheet layer (SheetShell, SheetTopBar,
// RecordGrid, ProvenanceSpine, Prose, SheetSection from @/components/v2) — it
// does NOT re-inline tokens. The Sheet primitives were added to the shared
// layer here so the next Sheet pages (landing, capability/PRD detail) reuse them.
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
  type SheetNavItem,
  type SpineFact,
} from "@/components/v2";
import { SpecimenWell } from "./SpecimenWell";
import "@/styles/v2-theme.css";

export const metadata: Metadata = {
  title: "About — Sidira",
  robots: { index: false, follow: false },
};

const NAV: SheetNavItem[] = [
  { label: "Product", href: "#" },
  { label: "About", href: "#", active: true },
  { label: "Capabilities", href: "#" },
];

const SPINE_FACTS: SpineFact[] = [
  { k: "Document", v: "ABOUT · v1.0" },
  { k: "Filed", v: "2026-06-16" },
  { k: "Snapshot", v: "2026-W25" },
  { k: "Seed", v: "0x4f" },
  { k: "Model", v: "groq/llama-3.3" },
  { k: "Cohort n", v: "1,200" },
];

export default function AboutV2Page() {
  return (
    <SheetShell>
      <SheetTopBar
        nav={NAV}
        actions={
          <>
            <Button as="a" href="#" variant="ghost">
              Sign in
            </Button>
            <Button as="a" href="mailto:founders@sidira.ai?subject=Sidira%20access" variant="secondary">
              Request access
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
          {/* HERO — above the fold; NOT behind ScrollReveal (must be visible on load) */}
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
            About Sidira
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
            We read the population before you pay to find out.
          </h1>
          <p
            style={{
              fontFamily: "var(--v2-font-serif)",
              fontSize: "1.3rem",
              lineHeight: 1.52,
              color: "var(--sheet-ink)",
              letterSpacing: "-0.005em",
              marginTop: 30,
              maxWidth: "42ch",
            }}
          >
            Product teams aren&rsquo;t short on hypotheses. They&rsquo;re short on answers that arrive
            before the build commitment.
          </p>

          <Prose lead style={{ marginTop: 40 }}>
            <p>
              Every roadmap is a stack of bets the team can&rsquo;t price. A pricing change, a new
              onboarding, a removed feature: each one is a guess that resolves only after weeks of
              engineering, a launch, and a quarter of waiting on a dashboard. By the time the number
              comes back, the cost is sunk and the next bet is already queued.
            </p>
            <p>
              Sidira closes that gap. We fit a <strong>customer-grounded population</strong>, synthetic
              agents built from real product analytics and research, then pressure-test a proposed
              change against it. What comes back is a directional read: how this specific population
              reacts, split by experiment arm, traceable down to the individual agent that adopted,
              hesitated, or churned.
            </p>
            <p>
              The specimen below is one such reading. It is a record of an estimate, so it sits still,
              and the figures speak for the method that produced them.
            </p>
          </Prose>

          {/* THE ONE §6.4 Console well — a frozen reading specimen, also above
              the deeper fold; rendered eagerly, not behind a scroll reveal. */}
          <SpecimenWell />

          {/* ── The four laws ─────────────────────────────────────────────── */}
          <ScrollReveal>
            <SheetSection kicker="What we hold to" title="Four laws make a reading trustworthy.">
              <div style={{ borderTop: "0.75px solid var(--sheet-line)", marginTop: 8 }}>
                {LAWS.map((law) => (
                  <Law key={law.pt} mk={law.mk} pt={law.pt}>
                    {law.pd}
                  </Law>
                ))}
              </div>
            </SheetSection>
          </ScrollReveal>

          {/* ── The reading, in numbers — Sheet ledger ────────────────────── */}
          <ScrollReveal>
            <SheetSection kicker="The reading, in numbers" title="What one Sidira pass produces.">
              <Ledger />
            </SheetSection>
          </ScrollReveal>

          {/* ── The build log ─────────────────────────────────────────────── */}
          <ScrollReveal>
            <SheetSection kicker="The build log" title="How the instrument came to be.">
              <Timeline />
            </SheetSection>
          </ScrollReveal>

          {/* ── Founders ──────────────────────────────────────────────────── */}
          <ScrollReveal>
            <SheetSection
              kicker="Built by"
              title="A small team that won't ship a number it can't defend."
            >
              <Founders />
            </SheetSection>
          </ScrollReveal>
        </article>
      </RecordGrid>

      {/* ── CLOSING — stays on the Sheet (no print-back-to-console) ────────── */}
      <section className="v2-close" style={{ marginTop: 112, borderTop: "0.75px solid var(--sheet-line)" }}>
        <RecordGrid
          spine={
            <aside
              className="v2-spine v2-close-spine"
              aria-label="End of record"
              style={{
                position: "relative",
                borderRight: "0.75px solid var(--sheet-line)",
                padding: "80px 28px 96px 0",
              }}
            >
              <div className="v2-close-stamp" style={{ position: "sticky", top: 96, display: "flex", flexDirection: "column" }}>
                <span style={{ fontFamily: "var(--v2-font-mono)", fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--sheet-mut)" }}>
                  — END OF RECORD —
                </span>
                <span style={{ height: "0.75px", background: "var(--sheet-line)", margin: "14px 0 16px" }} />
                <Colophon k="Filed" v="2026-W25" />
                <Colophon k="Pages" v="1 of 1" />
                <Colophon k="State" v={<><span className="v2-gh" style={{ marginRight: 4 }}>◇</span>uncalibrated</>} mut />
              </div>
            </aside>
          }
        >
          <div className="v2-doc v2-close-inner" style={{ padding: "80px 0 96px 56px", maxWidth: 760 }}>
            <ScrollReveal>
              <h2
                style={{
                  fontWeight: 600,
                  fontSize: "clamp(1.8rem,3vw,2.4rem)",
                  lineHeight: 1.06,
                  letterSpacing: "-0.025em",
                  color: "var(--sheet-ink)",
                  textWrap: "balance",
                  maxWidth: "20ch",
                }}
              >
                Stop guessing where a bet lands.
              </h2>
              <p
                style={{
                  fontFamily: "var(--v2-font-serif)",
                  fontSize: "1.0625rem",
                  lineHeight: 1.62,
                  color: "var(--sheet-mut)",
                  maxWidth: "54ch",
                  marginTop: 20,
                }}
              >
                Take a reading on your next change against a population grounded in your own customers.
                Every inferred number arrives with its uncertainty attached, exactly as it should.
              </p>
              <div style={{ marginTop: 30, display: "flex", gap: 12, flexWrap: "wrap" }}>
                <Button as="a" href="mailto:founders@sidira.ai?subject=Sidira%20access" variant="primary">
                  Request access &rarr;
                </Button>
                <Button as="a" href="#" variant="secondary">
                  Read the method
                </Button>
              </div>
            </ScrollReveal>
          </div>
        </RecordGrid>
      </section>

      {/* ── FOOTER ────────────────────────────────────────────────────────── */}
      <footer style={{ borderTop: "0.75px solid var(--sheet-line)", background: "var(--sheet-raised)" }}>
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
            about · v1.0 · n=1,200 · seed 0x4f · groq/llama-3.3 · 2026-W25 ·{" "}
            <span style={{ color: "var(--sheet-mut)" }}>
              <span className="v2-gh" style={{ marginRight: 4 }}>◇</span>uncalibrated
            </span>
          </span>
          <span>
            <a href="mailto:founders@sidira.ai" style={{ color: "var(--sheet-mut)" }}>
              founders@sidira.ai
            </a>
          </span>
        </div>
      </footer>

      <style>{ABOUT_CSS}</style>
    </SheetShell>
  );
}

// ── the four laws ────────────────────────────────────────────────────────────
const LAWS = [
  {
    mk: "◇",
    pt: "The visualization is the computation.",
    pd: "When the product renders a population reacting, that figure is the actual run: one mark per simulated agent, not decoration added afterward. If an effect can't be read as taking a reading, it doesn't ship.",
  },
  {
    mk: "±",
    pt: "Inferred numbers carry their uncertainty.",
    pd: "A value the model estimated about people prints with its confidence interval and a calibration glyph. Recorded facts — ids, seeds, counts, dates — print plainly. The scope is mechanical, applied the same way every time.",
  },
  {
    mk: "●",
    pt: "Color carries meaning, never mood.",
    pd: "One accent marks a live reading and nothing else. Arm tints name which experiment arm: identity, not valence. A negative reaction renders in plain ink with a down-glyph rather than alarm-red, because harm is information.",
  },
  {
    mk: "◆",
    pt: "An ungraded reading stays hedged.",
    pd: "A graded reading locks and comes to rest. An ungraded one keeps its ◇ glyph and directional wording, so it never reads as ground truth. The verdict it carries is a band, stated as such.",
  },
];

function Law({ mk, pt, children }: { mk: string; pt: string; children: React.ReactNode }) {
  return (
    <div
      className="v2-law"
      style={{
        padding: "24px 0",
        borderBottom: "0.75px solid var(--sheet-line)",
        display: "grid",
        gridTemplateColumns: "34px 1fr",
        gap: "0 20px",
        alignItems: "start",
      }}
    >
      <div style={{ fontFamily: "var(--v2-font-mono)", fontSize: 11, color: "var(--sheet-mut)", paddingTop: 3, letterSpacing: "0.04em" }}>
        {mk}
      </div>
      <div>
        <div style={{ fontWeight: 600, fontSize: "1.0625rem", letterSpacing: "-0.01em", color: "var(--sheet-ink)", marginBottom: 7 }}>
          {pt}
        </div>
        <div style={{ fontFamily: "var(--v2-font-serif)", fontSize: "1rem", lineHeight: 1.62, color: "var(--sheet-mut)", maxWidth: "62ch" }}>
          {children}
        </div>
      </div>
    </div>
  );
}

// ── the ledger ───────────────────────────────────────────────────────────────
function Ledger() {
  return (
    <>
      <div style={{ border: "0.75px solid var(--sheet-line)", borderRadius: "var(--r-panel)", background: "var(--sheet-raised)", overflow: "hidden" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr auto",
            gap: 16,
            padding: "12px 18px",
            borderBottom: "0.75px solid var(--sheet-line)",
            fontFamily: "var(--v2-font-mono)",
            fontSize: 10,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--sheet-mut)",
          }}
        >
          <span>METRIC</span>
          <span>VALUE</span>
        </div>
        <LedgerRow label="Population simulated" sub="one agent per synthetic person · a recorded count" val="1,200" />
        <LedgerRow label="Agreement score" sub="how tightly the cohort converges" infer val={<>0.62 <CI>±0.08</CI><Gl /></>} />
        <LedgerRow label="Net adoption lift" sub="treatment vs. control arm" infer val={<>+0.041 <CI>±0.012</CI><Gl /></>} />
        <LedgerRow label="Mean sentiment" sub="−1 reject → +1 adopt" infer val={<>+0.18 <CI>±0.06</CI><Gl /></>} />
        <LedgerRow label="Time to reading" sub="setup to settled distribution · a duration" val="~4 min" />
        <LedgerRow
          label="Verdict"
          sub="uncalibrated · read alongside sentiment"
          val={<span style={{ color: "var(--sheet-mut)" }}>DIRECTIONAL <Gl /></span>}
          last
        />
      </div>
      <div
        style={{
          border: "0.75px solid var(--sheet-line)",
          borderTop: 0,
          borderRadius: "0 0 var(--r-panel) var(--r-panel)",
          marginTop: -1,
          padding: "12px 18px",
          fontFamily: "var(--v2-font-sans)",
          fontSize: 12.5,
          color: "var(--sheet-mut)",
          lineHeight: 1.5,
        }}
      >
        The three tinted rows carry a <strong style={{ fontWeight: 600, color: "var(--sheet-ink)" }}>±</strong> and a ◇:
        estimates the model inferred about people. The count and the duration are facts of the run,
        printed plainly. That distinction is the whole discipline.
      </div>
    </>
  );
}

function LedgerRow({
  label,
  sub,
  val,
  infer = false,
  last = false,
}: {
  label: string;
  sub: string;
  val: React.ReactNode;
  infer?: boolean;
  last?: boolean;
}) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr auto",
        gap: 16,
        alignItems: "baseline",
        padding: "14px 18px",
        borderBottom: last ? "none" : "0.75px solid var(--sheet-line)",
        background: infer ? "linear-gradient(90deg,rgba(111,94,51,.045),transparent 64%)" : undefined,
      }}
    >
      <span style={{ fontSize: 14, color: "var(--sheet-ink)", fontWeight: 500 }}>
        {label}
        <small style={{ display: "block", fontFamily: "var(--v2-font-serif)", fontSize: 13, color: "var(--sheet-mut)", marginTop: 3, fontWeight: 400, fontStyle: "italic" }}>
          {sub}
        </small>
      </span>
      <span className="v2-tnum" style={{ fontFamily: "var(--v2-font-mono)", fontSize: 14, color: "var(--sheet-ink)", textAlign: "right", whiteSpace: "nowrap" }}>
        {val}
      </span>
    </div>
  );
}

const CI = ({ children }: { children: React.ReactNode }) => (
  <span style={{ color: "var(--sheet-spread)" }}>{children}</span>
);
const Gl = () => <span style={{ color: "var(--sheet-spread)", marginLeft: 7 }}>◇</span>;

// ── the build log ────────────────────────────────────────────────────────────
const TIMELINE = [
  { date: "2025 · Q3", title: "The premise", body: "Two founders, tired of shipping bets that resolved a quarter too late, ask a plain question: what if you could read the population before you built for it?", live: false },
  { date: "2025 · Q4", title: "First grounded population", body: "Synthetic agents fit from real product analytics. The first cohort reacts to a known pricing change, and the distribution lands within the band of the recorded result.", live: false },
  { date: "2026 · W18", title: "The candor architecture", body: "The spread stamp, the provenance bar, and the provenance spine ship together, making “this is an uncalibrated estimate” structurally unavoidable wherever an inferred number appears.", live: false },
  { date: "2026 · W25 · NOW", title: "Self-serve readings", body: "A founder crawls their own product, builds a persona pack, and runs a population field in one session. The marketing promise and the product are provably the same instrument.", live: true },
];

function Timeline() {
  return (
    <div className="v2-timeline" style={{ position: "relative", paddingLeft: 28 }}>
      {TIMELINE.map((t, i) => (
        <div
          key={t.title}
          className={t.live ? "v2-tl-item v2-tl-live" : "v2-tl-item"}
          style={{ position: "relative", padding: i === TIMELINE.length - 1 ? "0" : "0 0 30px" }}
        >
          <div style={{ fontFamily: "var(--v2-font-mono)", fontSize: 11, letterSpacing: "0.06em", color: "var(--sheet-mut)", marginBottom: 6 }}>
            {t.live ? <span style={{ color: "var(--sheet-ink)", fontWeight: 500 }}>{t.date}</span> : t.date}
          </div>
          <div style={{ fontWeight: 600, fontSize: 15, color: "var(--sheet-ink)", marginBottom: 5 }}>{t.title}</div>
          <div style={{ fontFamily: "var(--v2-font-serif)", fontSize: 14.5, lineHeight: 1.58, color: "var(--sheet-mut)", maxWidth: "56ch" }}>
            {t.body}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── founders ─────────────────────────────────────────────────────────────────
function Founders() {
  return (
    <div
      className="v2-founders"
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        border: "0.75px solid var(--sheet-line)",
        borderRadius: "var(--r-panel)",
        overflow: "hidden",
        background: "var(--sheet-raised)",
      }}
    >
      <Founder
        pole="ctl"
        initials="RD"
        role="CO-FOUNDER · PRODUCT"
        name="Ram Desai"
        sig="— builds the instrument"
        bio="Spent a decade watching teams pour quarters into bets that data could have settled in an afternoon. Reads the field before the build, not after the launch."
        first
      />
      <Founder
        pole="trt"
        initials="MN"
        role="CO-FOUNDER · SCIENCE"
        name="Mara Nilsson"
        sig="— keeps it honest"
        bio="Comes from experimentation rigor. Insists every reading carries its calibration state, on the principle that an instrument should never hide its limits."
      />
    </div>
  );
}

function Founder({
  pole,
  initials,
  role,
  name,
  sig,
  bio,
  first = false,
}: {
  pole: "ctl" | "trt";
  initials: string;
  role: string;
  name: string;
  sig: string;
  bio: string;
  first?: boolean;
}) {
  const tint = pole === "ctl" ? "var(--arm-control)" : "var(--arm-treat)";
  return (
    <div
      className="v2-founder"
      style={{
        padding: "28px 28px 26px",
        display: "grid",
        gridTemplateColumns: "64px 1fr",
        gap: 20,
        alignItems: "start",
        borderRight: first ? "0.75px solid var(--sheet-line)" : undefined,
      }}
    >
      <svg viewBox="0 0 64 64" fill="none" aria-hidden style={{ width: 64, height: 64, display: "block" }}>
        <circle cx="32" cy="32" r="30.5" stroke="var(--sheet-line)" strokeWidth="1" />
        <circle cx="32" cy="32" r="20" stroke="var(--sheet-mut)" strokeWidth="1.1" />
        <path
          d="M14,40 C22,40 25,33 30,23 C32,19 33,17 35,17 C37,17 38,19 40,23 C45,33 48,40 50,40"
          fill="none"
          stroke={tint}
          strokeWidth="1.2"
        />
        <line x1="35" y1="17" x2="35" y2="40" stroke={tint} strokeWidth="1" strokeDasharray="2 2.5" opacity=".7" />
        <text x="32" y="56" fill="var(--sheet-mut)" fontFamily="'Geist Mono',monospace" fontSize="6.5" letterSpacing="1" textAnchor="middle">
          {initials}
        </text>
      </svg>
      <div>
        <div style={{ fontFamily: "var(--v2-font-mono)", fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--sheet-mut)", marginBottom: 11 }}>
          {role}
        </div>
        <div style={{ fontWeight: 600, fontSize: "1.125rem", color: "var(--sheet-ink)", letterSpacing: "-0.01em" }}>
          {name}
          <span style={{ display: "block", fontFamily: "var(--v2-font-serif)", fontStyle: "italic", fontWeight: 400, fontSize: "1.05rem", color: "var(--sheet-mut)", letterSpacing: 0, marginTop: 3 }}>
            {sig}
          </span>
        </div>
        <div style={{ fontFamily: "var(--v2-font-serif)", fontSize: 14.5, lineHeight: 1.6, color: "var(--sheet-mut)", marginTop: 11, maxWidth: "40ch" }}>
          {bio}
        </div>
      </div>
    </div>
  );
}

function Colophon({ k, v, mut = false }: { k: string; v: React.ReactNode; mut?: boolean }) {
  return (
    <span style={{ display: "flex", justifyContent: "space-between", gap: 10, marginBottom: 9, fontFamily: "var(--v2-font-mono)", fontSize: 11 }}>
      <span style={{ color: "var(--sheet-mut)", letterSpacing: "0.05em", textTransform: "uppercase", fontSize: 9.5, alignSelf: "center" }}>{k}</span>
      <span style={{ color: mut ? "var(--sheet-mut)" : "var(--sheet-ink)", letterSpacing: "0.01em" }}>{v}</span>
    </span>
  );
}

// ── page-local CSS — /about-SPECIFIC ONLY ────────────────────────────────────
// Generic Sheet layout (the SheetTopBar collapse, the RecordGrid/ProvenanceSpine
// responsive collapse, and the §6.4 ConsoleWell `.v2-console-scope` token block)
// now lives in the SHARED stylesheet (styles/v2-theme.css under `.v2-sheet`) so
// the next Sheet page inherits correct layout without copy-paste. Everything
// below is content unique to THIS /about record — the specimen well body sizing,
// the build-log timeline rail, and the collapse of /about's own composite
// blocks (close-stamp, founders grid, the four-laws grid).
const ABOUT_CSS = `
.v2-well-body{padding:22px;display:grid;grid-template-columns:1fr 250px;gap:24px;align-items:center;}
.v2-tl-item::before{content:"";position:absolute;left:-28px;top:5px;width:9px;height:9px;border-radius:9999px;background:var(--sheet-raised);border:1.5px solid var(--sheet-mut);}
.v2-tl-item.v2-tl-live::before{background:var(--sheet-ink);border-color:var(--sheet-ink);}
.v2-timeline::before{content:"";position:absolute;left:4px;top:7px;bottom:7px;width:1px;background:var(--sheet-line);}
@media(max-width:1024px){
  .v2-close-stamp{position:static!important;}
  .v2-doc{padding:48px 0 0!important;}
  /* .v2-sheet prefix keeps these at equal specificity to the shared
     .v2-sheet .v2-spine collapse rule so /about's own padding still wins */
  .v2-sheet .v2-close-spine{padding:40px 0 22px!important;}
  .v2-close-inner{padding:72px 0 80px!important;}
}
@media(max-width:720px){
  .v2-founders{grid-template-columns:1fr!important;}
  .v2-founder{border-right:0!important;}
  .v2-founder:first-child{border-bottom:.75px solid var(--sheet-line);}
  .v2-well-body{grid-template-columns:1fr!important;}
  .v2-law{grid-template-columns:1fr!important;}
}
`;
