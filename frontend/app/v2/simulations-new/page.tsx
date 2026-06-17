// ───────────────────────────────────────────────────────────────────────────
// /v2/simulations-new — DESIGN SYSTEM v2 PREVIEW · new-simulation setup wizard
//
// A PUBLIC, NOINDEX, nav-suppressed, STATIC-MOCK preview under the clean
// top-level /v2/<slug> namespace. Reachable only by typing /v2/simulations-new
// — nothing links here, and it touches NO real auth-walled route. The global
// product nav is suppressed on /v2/* (components/ConditionalTopNav.tsx).
//
// ARCHETYPE — Console (dark), WORKING-class (§0.2): a setup FORM, so brutally
// quiet — ink + hairline + negative space. NO Population Field, no signal fill;
// the saturated accent is reserved for LIVE READINGS ONLY (§1.3, §1.9 signal
// budget). Here nothing is a live reading yet — it's a DRAFT — so the page
// stays entirely neutral ink; the only doubt-glyph (◇) appears next to the
// blinded-pass note, where calibration is genuinely uncertain (§7.2).
//
// The wizard is a left STEP-RAIL + numbered Panel sections; the interactive
// fields live in a small "use client" island (WizardInputs) so this page stays
// a server component. The final Panel is the SHOWPIECE read-only MANIFEST — a
// strong but STATIC summary of the whole setup before a run. The page CONSUMES
// the shared v2 layer (AppFrame + components/v2/*, v2-theme.css) and never
// re-inlines a raw hex or font name; page-local CSS is token-driven (CSS vars).
// ───────────────────────────────────────────────────────────────────────────
import type { Metadata } from "next";
import {
  AppFrame,
  Panel,
  Designator,
  Button,
  Chip,
  StatusBadge,
  CalGlyph,
} from "@/components/v2";
import { WizardInputs } from "./WizardInputs";
import "@/styles/v2-theme.css";

export const metadata: Metadata = {
  title: "New simulation — Sidira",
  robots: { index: false, follow: false },
};

// ── static mock data (consts, top of file) ─────────────────────────────────

// the five setup steps, shown both as a left step-rail and as numbered Panel
// section headers. `anchor` ties the rail link to the section's id.
type Step = { no: string; key: string; label: string; anchor: string; done: boolean };
const STEPS: Step[] = [
  { no: "1", key: "population", label: "Population", anchor: "#step-population", done: true },
  { no: "2", key: "hypothesis", label: "Hypothesis", anchor: "#step-hypothesis", done: true },
  { no: "3", key: "metric", label: "Metric", anchor: "#step-metric", done: true },
  { no: "4", key: "variants", label: "Variants", anchor: "#step-variants", done: true },
  { no: "5", key: "manifest", label: "Manifest", anchor: "#step-manifest", done: false },
];

// a section header eyebrow: numbered designator + plain-language title + a short
// instruction line. Each Panel below renders one of these.
type SectionHead = { no: string; title: string; instruction: string; anchor: string };
const SECTIONS: SectionHead[] = [
  {
    no: "1",
    title: "Population",
    instruction: "Pick the persona pack the reading runs against.",
    anchor: "step-population",
  },
  {
    no: "2",
    title: "Hypothesis",
    instruction: "State the directional claim and its mechanism.",
    anchor: "step-hypothesis",
  },
  {
    no: "3",
    title: "Metric",
    instruction: "Choose the outcome the reading reports on.",
    anchor: "step-metric",
  },
  {
    no: "4",
    title: "Variants",
    instruction: "Define control (A) against treatment (B).",
    anchor: "step-variants",
  },
];

// the read-only MANIFEST rows — the showpiece review summary. Recorded facts
// (cohort n) print bare with v2-tnum; nothing here is an inferred reading, so
// no value carries the ◇ glyph except the blinded-pass calibration note.
type ManifestRow = { k: string; v: string; mono?: boolean };
const MANIFEST: ManifestRow[] = [
  { k: "Persona pack", v: "Streamly · synthetic 6-segment" },
  { k: "Pack version", v: "v_2 · 2026-W25", mono: true },
  { k: "Cohort size", v: "2,500 agents", mono: true },
  { k: "Outcome metric", v: "Day-7 retention / pp" },
  { k: "Control (A)", v: "Gate at level 30 (current production build)" },
  { k: "Treatment (B)", v: "Gate at level 40 (deferred first paywall)" },
  { k: "Per-agent rows", v: "1 individual row each", mono: true },
  { k: "Engine", v: "Groq · default", mono: true },
];

export default function SimulationsNewV2Page() {
  return (
    <AppFrame
      activeNav="simulations"
      title="New simulation"
      workspace="Sidira"
      provenance={{ label: "DRAFT", calibrated: false, live: false }}
      actions={
        <Button as="a" href="#" variant="primary">
          Run reading
        </Button>
      }
    >
      {/* ── setup wizard body ─────────────────────────────────────────────── */}
      <div className="v2-new">
        {/* left step-rail — inert anchor links, the last step is the manifest */}
        <aside className="v2-new-rail" aria-label="Setup steps">
          <ol className="v2-new-steps">
            {STEPS.map((s, i) => (
              <li key={s.key} className="v2-new-step">
                <a
                  href={s.anchor}
                  className={
                    i === 0
                      ? "v2-new-step-link v2-new-step-link--active"
                      : "v2-new-step-link"
                  }
                  aria-current={i === 0 ? "step" : undefined}
                >
                  <span
                    className={
                      s.done
                        ? "v2-new-step-no v2-new-step-no--done v2-mono"
                        : "v2-new-step-no v2-mono"
                    }
                    aria-hidden
                  >
                    {s.done ? "✓" : s.no}
                  </span>
                  <span className="v2-new-step-label">{s.label}</span>
                </a>
              </li>
            ))}
          </ol>
          <p className="v2-new-rail-foot">
            <Designator>DRAFT</Designator>
            <span className="v2-new-rail-foot-text">
              Nothing runs until you start the reading. This is a setup form, not
              a result.
            </span>
          </p>
        </aside>

        {/* right column — the numbered sections + the manifest showpiece */}
        <div className="v2-new-main">
          {/* steps 1–4 share one quiet form (the inert client island). Each
              numbered header is a server-rendered section anchor; the matching
              fieldset inside WizardInputs carries the same id. */}
          <Panel className="v2-new-panel">
            {SECTIONS.map((sec, i) => (
              <div
                key={sec.anchor}
                className={
                  i === 0
                    ? "v2-new-sechead"
                    : "v2-new-sechead v2-new-sechead--spaced"
                }
                aria-hidden
              >
                <span className="v2-new-sechead-no v2-mono v2-tnum">
                  {sec.no}
                </span>
                <span className="v2-new-sechead-text">
                  <span className="v2-new-sechead-title">{sec.title}</span>
                  <span className="v2-new-sechead-instr">{sec.instruction}</span>
                </span>
              </div>
            ))}
            {/* the interactive, inert fields. The fieldsets inside carry the
                #step-* ids that the step-rail + section heads anchor to. */}
            <WizardInputs />
          </Panel>

          {/* ── Step 5 · MANIFEST — read-only review showpiece ─────────────── */}
          <section id="step-manifest" aria-label="Setup manifest" className="v2-new-manifest-wrap">
            <div className="v2-new-sechead v2-new-sechead--bare">
              <span className="v2-new-sechead-no v2-mono v2-tnum">5</span>
              <span className="v2-new-sechead-text">
                <span className="v2-new-sechead-title">Manifest</span>
                <span className="v2-new-sechead-instr">
                  The full setup, read-only, before the reading runs.
                </span>
              </span>
            </div>

            <Panel className="v2-new-manifest">
              {/* manifest masthead — designator + draft state badge */}
              <div className="v2-new-manifest-top">
                <Designator>SETUP MANIFEST</Designator>
                <StatusBadge kind="hold">Not yet run</StatusBadge>
              </div>

              {/* the record grid — quiet hairline-ruled key/value rows */}
              <dl className="v2-new-manifest-grid">
                {MANIFEST.map((row) => (
                  <div key={row.k} className="v2-new-manifest-row">
                    <dt className="v2-new-manifest-k v2-desig">{row.k}</dt>
                    <dd
                      className={
                        row.mono
                          ? "v2-new-manifest-v v2-mono v2-tnum"
                          : "v2-new-manifest-v"
                      }
                    >
                      {row.v}
                    </dd>
                  </div>
                ))}
              </dl>

              {/* manifest footer — calibration note + the run affordance.
                  The ◇ glyph marks where calibration is genuinely uncertain. */}
              <div className="v2-new-manifest-foot">
                <p className="v2-new-manifest-note">
                  <CalGlyph />{" "}
                  <span className="v2-new-manifest-note-text">
                    Day-7 retention reads <Chip>BLINDED-PASS</Chip> — confirmed
                    good changes separate cleanly, but read it alongside
                    sentiment, never alone, until calibration lands.
                  </span>
                </p>
                <div className="v2-new-manifest-actions">
                  <Button as="a" href="#" variant="ghost">
                    Save draft
                  </Button>
                  <Button as="a" href="#" variant="primary">
                    Run reading
                  </Button>
                </div>
              </div>
            </Panel>
          </section>
        </div>
      </div>

      {/* page-local token-driven styling (no raw hex / no raw font names) */}
      <style>{NEW_CSS}</style>
    </AppFrame>
  );
}

// ── page-local CSS — every value is a v2 CSS var or a plain unit (no hex,
//    no font names). Mirrors the SIMS_CSS precedent in simulations-list. ──────
const NEW_CSS = `
.v2-new{
  max-width:1080px;
  display:grid;
  grid-template-columns:200px minmax(0,1fr);
  gap:var(--space-section);
  align-items:start;
}
/* ── left step-rail ────────────────────────────────────────────────────── */
.v2-new-rail{
  position:sticky;
  top:84px;
  display:flex;
  flex-direction:column;
  gap:var(--space-room);
}
.v2-new-steps{
  list-style:none;
  margin:0;
  padding:0;
  display:flex;
  flex-direction:column;
  gap:2px;
}
.v2-new-step-link{
  display:flex;
  align-items:center;
  gap:var(--space-cozy);
  padding:var(--space-snug) var(--space-cozy);
  border-radius:var(--r-well);
  color:var(--text-mut);
  font-size:0.875rem;
  font-weight:450;
  transition:color .14s var(--ease-out), background .14s var(--ease-out);
}
.v2-new-step-link:hover{
  color:var(--text-hi);
  background:var(--console-800);
}
.v2-new-step-link--active{
  color:var(--text-hi);
  background:var(--console-800);
}
/* the step number is a neutral mono token in a hairline ring — never signal */
.v2-new-step-no{
  flex:0 0 auto;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  width:22px;
  height:22px;
  border-radius:var(--r-dot);
  border:1px solid var(--console-line-50);
  color:var(--text-mut);
  font-size:0.6875rem;
}
.v2-new-step-link--active .v2-new-step-no,
.v2-new-step-link:hover .v2-new-step-no{
  color:var(--text-hi);
  border-color:var(--console-line-60);
}
.v2-new-step-no--done{
  color:var(--text);
  border-color:var(--console-line-55);
}
.v2-new-step-label{white-space:nowrap;}
.v2-new-rail-foot{
  display:flex;
  flex-direction:column;
  gap:var(--space-snug);
  padding:0 var(--space-cozy);
}
.v2-new-rail-foot-text{
  font-size:0.75rem;
  line-height:1.5;
  color:var(--text-mut);
}
/* ── right column ──────────────────────────────────────────────────────── */
.v2-new-main{
  min-width:0;
  display:flex;
  flex-direction:column;
  gap:var(--space-section);
}
.v2-new-panel{
  padding:var(--space-room);
  display:flex;
  flex-direction:column;
  gap:var(--space-base);
}
/* numbered section header inside a panel — a quiet eyebrow row */
.v2-new-sechead{
  display:flex;
  align-items:baseline;
  gap:var(--space-cozy);
}
.v2-new-sechead--spaced{
  margin-top:var(--space-room);
  padding-top:var(--space-room);
  border-top:1px solid var(--console-line-40);
}
.v2-new-sechead-no{
  flex:0 0 auto;
  width:1.5rem;
  font-size:0.8125rem;
  color:var(--text-mut);
}
.v2-new-sechead-text{
  display:flex;
  flex-direction:column;
  gap:2px;
}
.v2-new-sechead-title{
  font-size:0.9375rem;
  font-weight:550;
  color:var(--text-hi);
  letter-spacing:-0.005em;
}
.v2-new-sechead-instr{
  font-size:0.8125rem;
  line-height:1.5;
  color:var(--text-mut);
}
/* the form island spaces its own fieldsets; pull its first header tight */
.v2-new-panel .v2-new-form{
  display:flex;
  flex-direction:column;
  gap:var(--space-room);
  margin:0;
  border:none;
  padding:0;
}
/* WizardInputs interleaves its fieldsets between the server section heads via
   document order; each fieldset adds its own top rule so they read as steps. */
.v2-new-field{
  margin:0;
  padding:0;
  border:none;
  min-width:0;
}
.v2-new-field + .v2-new-field{
  margin-top:var(--space-room);
  padding-top:var(--space-room);
  border-top:1px solid var(--console-line-40);
}
.v2-new-legend{
  padding:0;
  font-size:0.8125rem;
  font-weight:500;
  color:var(--text);
  margin-bottom:var(--space-cozy);
}
/* ── radio option rows (population, metric) ────────────────────────────── */
.v2-new-radios{
  display:flex;
  flex-direction:column;
  gap:var(--space-snug);
}
.v2-new-radio{
  position:relative;
  display:flex;
  align-items:flex-start;
  gap:var(--space-cozy);
  padding:var(--space-cozy) var(--space-base);
  border:1px solid var(--console-line-45);
  border-radius:var(--r-well);
  cursor:pointer;
  transition:border-color .14s var(--ease-out), background .14s var(--ease-out);
}
.v2-new-radio:hover{
  border-color:var(--console-line-60);
  background:var(--console-800);
}
/* selected = lifted INK border, never a signal fill (§1.9 budget) */
.v2-new-radio--on{
  border-color:var(--text);
  background:var(--console-800);
}
.v2-new-radio-input{
  position:absolute;
  opacity:0;
  width:1px;
  height:1px;
  pointer-events:none;
}
.v2-new-radio-mark{
  flex:0 0 auto;
  margin-top:3px;
  width:14px;
  height:14px;
  border-radius:var(--r-dot);
  border:1px solid var(--console-line-60);
  transition:border-color .14s var(--ease-out), box-shadow .14s var(--ease-out);
}
.v2-new-radio--on .v2-new-radio-mark{
  border-color:var(--text-hi);
  box-shadow:inset 0 0 0 3px var(--text-hi);
}
/* keyboard focus reads on the row, not just the hidden input */
.v2-new-radio-input:focus-visible + .v2-new-radio-mark{
  box-shadow:0 0 0 2px var(--console-900), 0 0 0 4px var(--console-line-60);
}
.v2-new-radio--on .v2-new-radio-input:focus-visible + .v2-new-radio-mark{
  box-shadow:inset 0 0 0 3px var(--text-hi), 0 0 0 2px var(--console-900), 0 0 0 4px var(--console-line-60);
}
.v2-new-radio-body{
  display:flex;
  flex-direction:column;
  gap:3px;
  min-width:0;
}
.v2-new-radio-name{
  font-size:0.875rem;
  color:var(--text-hi);
  font-weight:450;
}
.v2-new-radio-unit{
  font-size:0.75rem;
  color:var(--text-mut);
}
.v2-new-radio-meta{
  font-size:0.75rem;
  line-height:1.5;
  color:var(--text-mut);
}
/* ── textarea / variant fields ─────────────────────────────────────────── */
.v2-new-textarea{
  width:100%;
  resize:vertical;
  padding:var(--space-cozy) var(--space-base);
  background:var(--console-900);
  border:1px solid var(--console-line-50);
  border-radius:var(--r-well);
  color:var(--text-hi);
  font-family:var(--v2-font-sans);
  font-size:0.875rem;
  line-height:1.55;
  transition:border-color .14s var(--ease-out);
}
.v2-new-textarea:hover{border-color:var(--console-line-60);}
.v2-new-textarea:focus{
  outline:none;
  border-color:var(--text);
}
.v2-new-textarea--sm{font-size:0.8125rem;}
.v2-new-hint{
  display:flex;
  align-items:baseline;
  gap:var(--space-snug);
  margin:var(--space-snug) 0 0;
  max-width:72ch;
}
.v2-new-hint-mark{
  flex:0 0 auto;
  color:var(--text-mut);
  font-size:0.8125rem;
}
.v2-new-hint-text{
  font-size:0.75rem;
  line-height:1.5;
  color:var(--text-mut);
}
/* ── variants A/B ──────────────────────────────────────────────────────── */
.v2-new-variants{
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:var(--space-base);
}
.v2-new-variant{
  display:flex;
  flex-direction:column;
  gap:var(--space-snug);
  min-width:0;
}
.v2-new-variant-head{display:flex;}
/* ── manifest showpiece ────────────────────────────────────────────────── */
.v2-new-manifest-wrap{
  display:flex;
  flex-direction:column;
  gap:var(--space-base);
}
.v2-new-sechead--bare{margin:0;padding:0;border:none;}
.v2-new-manifest{
  padding:var(--space-room);
  display:flex;
  flex-direction:column;
  gap:var(--space-room);
}
.v2-new-manifest-top{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:var(--space-base);
  flex-wrap:wrap;
}
.v2-new-manifest-grid{
  margin:0;
  display:flex;
  flex-direction:column;
}
.v2-new-manifest-row{
  display:grid;
  grid-template-columns:160px minmax(0,1fr);
  gap:var(--space-base);
  align-items:baseline;
  padding:var(--space-cozy) 0;
  border-top:1px solid var(--console-line-40);
}
.v2-new-manifest-row:first-child{border-top:none;}
.v2-new-manifest-k{
  margin:0;
}
.v2-new-manifest-v{
  margin:0;
  font-size:0.875rem;
  color:var(--text-hi);
  min-width:0;
  overflow-wrap:anywhere;
}
.v2-new-manifest-foot{
  display:flex;
  align-items:flex-end;
  justify-content:space-between;
  gap:var(--space-room);
  padding-top:var(--space-base);
  border-top:1px solid var(--console-line-40);
  flex-wrap:wrap;
}
.v2-new-manifest-note{
  margin:0;
  max-width:62ch;
  font-size:0.8125rem;
  line-height:1.55;
}
.v2-new-manifest-note-text{color:var(--text-mut);}
.v2-new-manifest-actions{
  display:flex;
  align-items:center;
  gap:var(--space-snug);
  flex:0 0 auto;
}
/* ── responsive — fold the step-rail above, stack variants ─────────────── */
@media(max-width:900px){
  .v2-new{
    grid-template-columns:1fr;
    gap:var(--space-room);
  }
  .v2-new-rail{
    position:static;
    flex-direction:column;
    gap:var(--space-cozy);
  }
  .v2-new-steps{
    flex-direction:row;
    flex-wrap:wrap;
    gap:var(--space-snug);
  }
  .v2-new-rail-foot{display:none;}
}
@media(max-width:640px){
  .v2-new-variants{grid-template-columns:1fr;}
  .v2-new-manifest-row{
    grid-template-columns:1fr;
    gap:2px;
  }
  .v2-new-manifest-foot{flex-direction:column;align-items:stretch;}
  .v2-new-manifest-actions{justify-content:flex-end;}
}
`;
