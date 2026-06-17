// ───────────────────────────────────────────────────────────────────────────
// /v2/agent-transcript — DESIGN SYSTEM v2 PREVIEW · single-agent transcript
//
// A PUBLIC, NOINDEX, nav-suppressed, STATIC-MOCK preview under the clean
// top-level /v2/<slug> namespace. Reachable only by typing /v2/agent-transcript
// — nothing links here, and it touches NO real auth-walled route. The global
// product nav is suppressed on /v2/* (components/ConditionalTopNav.tsx).
//
// ROUTE LAW (design-system-v2.md): an agent transcript = Console. §0.2 makes a
// transcript WORKING-class: brutally quiet — ink + hairline + negative space,
// NO Population Field, no signal fill. The saturated accent is reserved for LIVE
// READINGS ONLY (§1.3, §1.9 signal budget). The transcript records what a single
// synthetic agent was shown (BLINDED — it never saw the metric) and how it
// responded, turn by turn, ending in the blinded elicitation. The only inferred
// reading on the page — the elicited retention answer — carries the ◇
// uncalibrated glyph (§7.2); recorded facts (snapshot, model, turn count) print
// bare.
//
// This page CONSUMES the shared v2 layer (AppFrame + components/v2/*,
// v2-theme.css) and never re-inlines a raw hex or font name. Server component;
// every turn here is inert static text, so no "use client" island is needed.
// ───────────────────────────────────────────────────────────────────────────
import type { Metadata } from "next";
import {
  AppFrame,
  Panel,
  Button,
  Designator,
  StatusBadge,
  ProvenanceBar,
  type ProvSeg,
} from "@/components/v2";
import "@/styles/v2-theme.css";

export const metadata: Metadata = {
  title: "Transcript — Sidira",
  robots: { index: false, follow: false },
};

// ── static mock data (consts, top of file) ─────────────────────────────────

// Context header facts. All EXEMPT recorded facts (§1.10) — print bare.
const CTX = {
  agentId: "S1-0440",
  cohort: "Streamly S1",
  simId: "SIM-2180",
  hypothesis: "Streamly blinded-retention readout",
  model: "groq/llama-3.3-70b",
  snapshot: "2026-W25",
  turns: 7,
} as const;

// The transcript region silkscreen segments (§7.3) — all bare recorded facts.
const PROV_SEGS: ProvSeg[] = [
  { content: `SNAPSHOT ${CTX.snapshot}` },
  { content: "BLINDED", bold: true },
  { content: CTX.model },
  { content: `${CTX.turns} TURNS` },
];

// A single transcript turn. `role` drives the visual class + label:
//   stimulus    → mono, muted: the blinded prompt / variant shown to the agent.
//   agent       → sans, higher-contrast: the synthetic viewer's response.
//   elicitation → the closing blinded-metric question + answer (◇ uncalibrated).
type Role = "stimulus" | "agent" | "elicitation";
type Turn = {
  n: number;
  role: Role;
  label: string; // mono designator shown on the row
  body: string;
  // elicitation only — the blinded metric answer, rendered as a tnum value.
  answer?: { value: string; unit: string; caption: string };
};

const TURNS: Turn[] = [
  {
    n: 1,
    role: "stimulus",
    label: "SYSTEM",
    body:
      "You are a returning Streamly viewer opening the app on a weekday evening. " +
      "Browse as you normally would. You will be shown one screen at a time. " +
      "Respond honestly with what you notice and what you would do next.",
  },
  {
    n: 2,
    role: "stimulus",
    label: "STIMULUS · variant",
    body:
      "[ HOME SCREEN ] A continue-watching rail sits above the fold; a single " +
      "promoted title fills the hero. Below: three genre rails. No ad slot is " +
      "shown before the first rail. (Metric under test withheld.)",
  },
  {
    n: 3,
    role: "agent",
    label: "AGENT · S1-0440",
    body:
      "First thing I see is the show I half-finished last night, right at the top — " +
      "that pulls me in. The hero title isn't one I'd pick, so my eyes skip past it " +
      "to the continue rail. Feels calm. I'd tap back into my show.",
  },
  {
    n: 4,
    role: "stimulus",
    label: "STIMULUS · follow-up",
    body:
      "[ PLAYBACK ] Your title resumes within two seconds. A small 'Up next' card " +
      "previews the following episode as the credits approach.",
  },
  {
    n: 5,
    role: "agent",
    label: "AGENT · S1-0440",
    body:
      "Fast resume matters — if it had buffered I'd have bailed. The 'Up next' card " +
      "is doing its job; I'd let it roll into the next episode rather than close the " +
      "app. That's usually when I lose a whole evening to it.",
  },
  {
    n: 6,
    role: "agent",
    label: "AGENT · S1-0440",
    body:
      "Nothing here annoyed me — no mid-screen interruption, no upsell. If every " +
      "session opened this cleanly I'd come back tomorrow without thinking about it.",
  },
  {
    n: 7,
    role: "elicitation",
    label: "ELICITATION · blinded",
    body:
      "On a scale of 0–100, how likely are you to open Streamly again tomorrow " +
      "evening? Answer with a single number. (The agent is not told this maps to " +
      "the retention metric under test.)",
    answer: {
      value: "78",
      unit: "/ 100",
      caption: "elicited next-day return likelihood",
    },
  },
];

// role → quiet neutral badge word for the closing elicitation marker.
const ELICIT_WORD = "Blinded answer";

export default function AgentTranscriptV2Page() {
  return (
    <AppFrame
      activeNav="agents"
      title={`Transcript · ${CTX.agentId}`}
      workspace="Sidira"
      provenance={{ label: "SNAPSHOT 2026-W25", calibrated: false, live: false }}
      actions={
        <Button as="a" href="#" variant="secondary">
          Back to agent
        </Button>
      }
    >
      {/* ── transcript body ─────────────────────────────────────────────────── */}
      <div className="v2-tx">
        {/* context header — which reading this transcript is from + blinded note */}
        <header className="v2-tx-context">
          <div className="v2-tx-context-head">
            <Designator>TRANSCRIPT</Designator>
            <span className="v2-tx-context-id v2-mono v2-tnum">
              {CTX.agentId}
            </span>
            <span className="v2-tx-context-cohort">· {CTX.cohort}</span>
          </div>
          <p className="v2-tx-context-line">
            Turn-by-turn record of what synthetic agent{" "}
            <span className="v2-mono v2-tnum">{CTX.agentId}</span> was shown and
            how it responded during{" "}
            <span className="v2-tx-context-sim">{CTX.hypothesis}</span>{" "}
            (<span className="v2-mono v2-tnum">{CTX.simId}</span>). The stimulus
            was <b className="v2-tx-blind">BLINDED</b> — the agent never saw the
            metric under test.
          </p>
        </header>

        {/* region silkscreen — bare recorded facts for the transcript region */}
        <ProvenanceBar segments={PROV_SEGS} style={{ marginTop: 2 }} />

        {/* the transcript stream — stacked role-labelled turns */}
        <Panel className="v2-tx-panel">
          <ol className="v2-tx-stream" aria-label="Transcript turns">
            {TURNS.map((t) => (
              <li
                key={t.n}
                className={`v2-tx-turn v2-tx-turn--${t.role}`}
              >
                {/* turn gutter — mono turn index, hairline-aligned */}
                <span className="v2-tx-turn-n v2-mono v2-tnum" aria-hidden>
                  {String(t.n).padStart(2, "0")}
                </span>

                <div className="v2-tx-turn-main">
                  <span className="v2-tx-turn-label v2-desig">{t.label}</span>
                  <p className="v2-tx-turn-body">{t.body}</p>

                  {/* elicitation answer — the one inferred reading: ◇ uncal */}
                  {t.answer ? (
                    <div className="v2-tx-answer">
                      <span className="v2-tx-answer-state">
                        <StatusBadge kind="neutral">{ELICIT_WORD}</StatusBadge>
                      </span>
                      <span className="v2-tx-answer-fig">
                        <span className="v2-tx-answer-val v2-mono v2-tnum">
                          {t.answer.value}
                        </span>
                        <span className="v2-tx-answer-unit v2-mono">
                          {t.answer.unit}
                        </span>
                      </span>
                      <span className="v2-tx-answer-cap">
                        {t.answer.caption}
                      </span>
                    </div>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
        </Panel>

        {/* one-line provenance / calibration footnote for the transcript */}
        <p className="v2-tx-foot">
          <Designator>READING</Designator>
          <span className="v2-tx-foot-text">
            The elicited answer is <span className="v2-gh">◇</span> uncalibrated —
            a blinded self-report, not a graded metric. Stimulus copy, model, and
            turn order are recorded facts.
          </span>
        </p>
      </div>

      {/* page-local token-driven styling (no raw hex / no raw font names) */}
      <style>{TX_CSS}</style>
    </AppFrame>
  );
}

// ── page-local CSS — every value is a v2 CSS var or a plain unit (no hex, no
//    font names). Mirrors the SIMS_CSS precedent in app/v2/simulations-list. ──
const TX_CSS = `
.v2-tx{
  max-width:880px;
  display:flex;
  flex-direction:column;
  gap:var(--space-room);
}
/* ── context header ────────────────────────────────────────────────────── */
.v2-tx-context{
  display:flex;
  flex-direction:column;
  gap:var(--space-snug);
}
.v2-tx-context-head{
  display:flex;
  align-items:baseline;
  gap:var(--space-snug);
  flex-wrap:wrap;
}
.v2-tx-context-id{
  font-size:0.9375rem;
  color:var(--text-hi);
  letter-spacing:0.02em;
}
.v2-tx-context-cohort{
  font-size:0.8125rem;
  color:var(--text-mut);
}
.v2-tx-context-line{
  max-width:72ch;
  font-size:0.875rem;
  line-height:1.6;
  color:var(--text-mut);
}
.v2-tx-context-line .v2-mono{color:var(--text);}
.v2-tx-context-sim{color:var(--text);}
.v2-tx-blind{
  color:var(--text-hi);
  font-weight:550;
  letter-spacing:0.04em;
}
/* ── transcript panel + stream ─────────────────────────────────────────── */
.v2-tx-panel{
  padding:var(--space-room);
}
.v2-tx-stream{
  list-style:none;
  margin:0;
  padding:0;
  display:flex;
  flex-direction:column;
}
.v2-tx-turn{
  display:grid;
  grid-template-columns:34px minmax(0,1fr);
  gap:var(--space-cozy);
  padding:var(--space-base) 0;
  border-top:1px solid var(--console-line-40);
}
.v2-tx-turn:first-child{border-top:none;}
.v2-tx-turn-n{
  font-size:0.6875rem;
  line-height:1.7;
  color:var(--text-faint);
  text-align:right;
  padding-top:1px;
}
.v2-tx-turn-main{
  min-width:0;
  display:flex;
  flex-direction:column;
  gap:var(--space-snug);
}
.v2-tx-turn-label{
  align-self:start;
}
.v2-tx-turn-body{
  font-size:0.9375rem;
  line-height:1.62;
}
/* STIMULUS / SYSTEM turns — the machine voice: mono, muted, recessed. */
.v2-tx-turn--stimulus .v2-tx-turn-body{
  font-family:var(--v2-font-mono);
  font-size:0.8125rem;
  line-height:1.7;
  color:var(--text-mut);
}
/* AGENT turns — the synthetic viewer's voice: sans, higher contrast. */
.v2-tx-turn--agent .v2-tx-turn-body{
  color:var(--text-hi);
}
/* ELICITATION turn — the closing blinded prompt + the elicited answer. */
.v2-tx-turn--elicitation .v2-tx-turn-body{
  font-family:var(--v2-font-mono);
  font-size:0.8125rem;
  line-height:1.7;
  color:var(--text-mut);
}
/* ── elicited answer block ─────────────────────────────────────────────── */
.v2-tx-answer{
  margin-top:var(--space-snug);
  display:flex;
  align-items:baseline;
  gap:var(--space-base);
  flex-wrap:wrap;
  padding:var(--space-cozy) var(--space-base);
  border:1px solid var(--console-line-45);
  border-radius:var(--r-well);
  background:var(--console-850);
}
.v2-tx-answer-state{
  align-self:center;
}
.v2-tx-answer-fig{
  display:inline-flex;
  align-items:baseline;
  gap:6px;
}
.v2-tx-answer-val{
  font-size:1.625rem;
  line-height:1;
  letter-spacing:-0.01em;
  color:var(--text-hi);
}
.v2-tx-answer-unit{
  font-size:0.8125rem;
  color:var(--text-mut);
}
.v2-tx-answer-cap{
  font-size:0.8125rem;
  color:var(--text-mut);
}
/* ── reading footnote ──────────────────────────────────────────────────── */
.v2-tx-foot{
  display:flex;
  align-items:baseline;
  gap:var(--space-cozy);
  max-width:78ch;
}
.v2-tx-foot-text{
  font-size:0.8125rem;
  line-height:1.55;
  color:var(--text-mut);
}
.v2-tx-foot .v2-gh{color:var(--text-mut);}
/* ── responsive — collapse the turn gutter under the body ──────────────── */
@media(max-width:560px){
  .v2-tx-panel{padding:var(--space-base) var(--space-cozy);}
  .v2-tx-turn{
    grid-template-columns:1fr;
    gap:var(--space-snug);
  }
  .v2-tx-turn-n{
    text-align:left;
  }
  .v2-tx-answer{
    flex-direction:column;
    align-items:flex-start;
    gap:var(--space-snug);
  }
}
`;
