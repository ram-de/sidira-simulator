"use client";

// ───────────────────────────────────────────────────────────────────────────
// /simulations/[id] — the v2 dark "Reading Console" reskin.
//
// FORK-AND-RESTYLE of SimulationDetailLegacy.tsx (the FROZEN source of truth for
// ALL behaviour). This file reproduces every data load, poll, state branch,
// honesty/disclosure branch, conditional, Link and button the legacy reader has
// — byte-for-byte in LOGIC — and changes ONLY the presentation (markup + CSS
// classes + layout) into the dark Console language of
// design-rethink/mocks/simulation-results.html + console/ReadingConsoleResults.
//
// It renders INSIDE AppShellV2 surface="console" (the shell owns the dark rail +
// appbar). The body is scoped under a single `.rconsole` wrapper so the copied
// RCONSOLE_CSS applies; we do NOT emit the console's own .shell/.rail/.topbar
// (the shell owns that chrome). The PopulationField hero breaks full-bleed out
// of the `.v2-appmain` section padding; the rest sits in a centered column.
//
// Honesty law (DESIGN.md §8.1 / §9.7): verdict is a hollow glyph + word +
// qualifier, never a ship-green / hold-red fill. Raw uncalibrated framing and
// every "UNGRADED / NO PERSISTED POLICY / LEDGER EMPTY" disclosure survive
// verbatim. The legacy's §8.1 honesty branches (out_of_scope, input_flags,
// metric lift, A/B degradation, live trace) are preserved exactly.
// ───────────────────────────────────────────────────────────────────────────

import Link from "next/link";
import { useParams } from "next/navigation";
import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ApiError,
  getSimulation,
  getSimulationState,
  isTerminalStatus,
  listSimulationAgents,
  type Hypothesis,
  type RunEvent,
  type Simulation,
  type EvidenceEdge,
  type SimulationResult,
  type SimulationRunState,
  type SimulationStatus,
  type Weakness,
} from "@/lib/api";
import AppShellV2 from "@/components/v2/AppShellV2";

// ── model labels — mirrors the legacy MODEL_LABELS convention ────────────────
const MODEL_LABELS: Record<string, { label: string; provider: string }> = {
  "llama-3.3-70b-versatile": { label: "Llama 3.3 70B", provider: "Groq" },
  "openai/gpt-oss-120b": { label: "GPT-OSS 120B", provider: "Groq" },
  "openai/gpt-oss-20b": { label: "GPT-OSS 20B", provider: "Groq" },
  "qwen/qwen3-32b": { label: "Qwen3 32B", provider: "Groq" },
  "meta-llama/llama-4-scout-17b-16e-instruct": {
    label: "Llama 4 Scout 17B",
    provider: "Groq",
  },
  "llama-3.1-8b-instant": { label: "Llama 3.1 8B Instant", provider: "Groq" },
  "claude-opus-4-7": { label: "Claude Opus 4.7", provider: "Anthropic" },
  "claude-sonnet-4-6": { label: "Claude Sonnet 4.6", provider: "Anthropic" },
  "claude-haiku-4-5": { label: "Claude Haiku 4.5", provider: "Anthropic" },
  "gpt-5.5": { label: "GPT-5.5", provider: "OpenAI" },
  "gpt-5.4-mini": { label: "GPT-5.4 Mini", provider: "OpenAI" },
};

function modelDisplay(
  modelId: string | null | undefined,
): { label: string; provider: string } | null {
  if (!modelId) return null;
  return MODEL_LABELS[modelId] ?? { label: modelId, provider: "selected provider" };
}

function formatCategory(cat: string): string {
  return cat
    .split("_")
    .map((w) => (w.length > 0 ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour12: false });
  } catch {
    return iso;
  }
}

function formatDateTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString([], { hour12: false });
  } catch {
    return iso;
  }
}

function describeEvent(ev: RunEvent): string {
  const payload = (ev.payload ?? {}) as Record<string, unknown>;
  const persona =
    typeof payload.persona === "string" ? (payload.persona as string) : null;
  const agentId =
    typeof payload.agent_id === "string" ? (payload.agent_id as string) : null;
  const score =
    typeof payload.score === "number" ? (payload.score as number) : null;
  const err =
    typeof payload.error === "string" ? (payload.error as string) : null;

  let suffix = "";
  if (persona) suffix = ` — ${persona}`;
  else if (agentId) suffix = ` — ${agentId.slice(0, 8)}`;
  else if (score !== null) suffix = ` — ${score}`;
  else if (err) suffix = ` — ${err}`;

  return `[${formatTime(ev.at)}] ${ev.type}${suffix}`;
}

// The backend does not return a decision policy or threshold — this constant
// is the page's DISPLAY RUBRIC, codifying the shipped "≥80 = validated" copy
// as an explicit decision rule (DESIGN.md §8.1: a verdict never appears
// without the policy that produced it). Disclosed as a display rubric in the
// method card and the provenance rail; flagged as a data gap in #166.
const DECISION_POLICY = {
  id: "DR-1",
  threshold: 80,
  rule: "SHIP CANDIDATE IF AGREEMENT ≥ 80 / 100",
} as const;

// Same base the API client uses (lib/api.ts keeps it private) — only for the
// provenance rail's raw-artifact links. Not a new API call: these are the
// exact endpoints this page already reads, exposed as inspectable JSON.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

const METRIC_DISPLAY_LABELS: Record<string, string> = {
  conversion: "Conversion",
  retention: "Retention",
  ctr: "CTR",
};

function metricDisplayLabel(name: string): string {
  return METRIC_DISPLAY_LABELS[name] ?? name.toUpperCase();
}

// One accumulated point per poll tick — DESIGN.md §9.7: the trace IS the
// progress indicator; points are event-driven (no per-point tween).
type TracePoint = { x: number; y: number };

// Verdict lexicon — MVP states only (DESIGN.md §8.1). "DECISIVE" is reserved
// for calibrated readings and MUST NOT appear while the ledger is empty.
//
// In the dark Console, verdict NEVER carries a ship-green / hold-red fill — it
// is a hollow glyph + word + qualifier. The `tone` field is consumed only by
// the verdict CHIP border accent (a hairline rule, never a tinted background or
// coloured word). Logic (the label text + every branch) is byte-identical to
// the legacy verdictFor.
function verdictFor(
  status: SimulationStatus,
  result: SimulationResult | null,
): { label: string } {
  if (status === "failed") return { label: "RUN FAILED — NO VERDICT" };
  if (status !== "complete" || !result)
    return { label: "READING IN PROGRESS" };
  // #311 / T2 — instrument-fit abstention takes precedence over the numeric
  // ship/directional verdict (DESIGN.md §8.2): when the OEC is unresolvable by a
  // first-exposure single-session panel, the score is still computed but the
  // ship/no-ship verdict is categorically WITHHELD. This composes with the
  // `underpowered_design` flip below — abstention is the outermost branch.
  if (result.instrument_scope === "out_of_scope")
    return { label: "NOT ANSWERABLE BY THIS INSTRUMENT" };
  const underpowered = (result.weaknesses ?? []).some(
    (w) => w.category === "underpowered_design",
  );
  if (underpowered)
    return { label: "UNDERPOWERED — TREAT AS DIRECTIONAL" };
  const s = result.confidence_score;
  if (s >= DECISION_POLICY.threshold)
    return { label: "HIGH SIM AGREEMENT · SHIP CANDIDATE" };
  if (s >= 60) return { label: "DIRECTIONAL — BELOW SHIP THRESHOLD" };
  // Codex P3 (#166): a sub-60 score IS low agreement — say so.
  return { label: "LOW SIM AGREEMENT · DO NOT SHIP" };
}

// ── number helpers (from ReadingConsoleResults) ──────────────────────────────
function fmt1(n: number): string {
  return n.toFixed(1);
}
function fmtSigned1(n: number): string {
  return `${n >= 0 ? "+" : ""}${n.toFixed(1)}`;
}
function ciHalf(ci: [number, number] | null | undefined): number | null {
  if (!ci || ci.length !== 2) return null;
  const [lo, hi] = ci;
  if (typeof lo !== "number" || typeof hi !== "number") return null;
  return Math.abs(hi - lo) / 2;
}
function shortId(id: string): string {
  const tail = id.replace(/^sim[_-]?/i, "").slice(-8);
  return tail.toUpperCase();
}
function seedHex(seed: number | null | undefined): string | null {
  if (seed == null || !Number.isFinite(seed)) return null;
  try {
    const b = BigInt(Math.trunc(seed));
    return b < 0n ? `-0x${(-b).toString(16)}` : `0x${b.toString(16)}`;
  } catch {
    return String(seed);
  }
}

// ── scoped console tokens (verbatim from ReadingConsoleResults RCONSOLE_CSS,
//    plus a small `.fullbleed` helper to break the field out of .v2-appmain's
//    section padding, and a `.bodywrap` centered content column). The unused
//    .shell/.rail/.topbar/.preview-ribbon rules are kept but never emitted —
//    AppShellV2 owns that chrome. ──────────────────────────────────────────
const RCONSOLE_CSS = `
.rconsole{
  --console:#0B1220; --console-900:#0B1220; --console-850:#10192A;
  --console-800:#161F32; --console-750:#1D2740; --console-700:#26314C;
  --line:rgba(231,236,245,.10); --console-line:#33405C;
  --text-hi:#E7ECF5; --text:#C6CCD8; --text-mut:#929BAE; --text-faint:#646E84;
  --signal:#48EFCA; --signal-dim:#39B894;
  --spread:#C9B47A; --spread-dim:#90815F; --spread-wash:rgba(200,182,138,.14);
  --arm-control:#4FA8E0; --arm-treat:#E08BC4;
  --edge-warn:#C9A227; --alert:#F0683C;
  --r-well:4px; --r-panel:8px; --r-frame:10px;
  --font-mono:var(--v2-font-mono,var(--font-mono,ui-monospace,"JetBrains Mono",SFMono-Regular,monospace));
  color:var(--text);
  font-family:var(--font-mono); font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased;
  font-variant-numeric:tabular-nums; overflow-x:hidden;
}
.rconsole *{box-sizing:border-box; font-variant-numeric:tabular-nums;}
.rconsole a{color:inherit; text-decoration:none;}
.rconsole ::selection{background:rgba(72,239,202,.12); color:var(--text-hi);}
.rconsole .mono{font-family:var(--font-mono);}
.rconsole .desig{font-size:11px; font-weight:500; letter-spacing:.08em;
  text-transform:uppercase; color:var(--text-mut);}
.rconsole .desig-sm{font-size:10px;}
.rconsole .glyph-hollow{color:var(--spread-dim);}
.rconsole .unc{color:var(--text-mut);}

/* Contained field hero (matches the mock's centered 1320px column). It used to
   be full-bleed (edge-to-edge negative margins), which bled the agreement
   readout past the viewport edges — clipping "82.2" and the reaction split — and
   spread the reaction clusters into unreadable edge-sticks. Now the canvas, the
   axis caption, and the verdict band live in one framed panel; nothing clips. */
.rconsole .fieldhero{max-width:1320px; margin:0 auto;
  border:1px solid var(--console-line); border-radius:var(--r-frame);
  overflow:hidden; box-shadow:inset 0 1px 0 rgba(255,255,255,.05);}
/* x-axis caption under the field: names the poles + explains the green mean line.
   Mono, muted; the pole words pick up the arm colors. No own border — it sits
   between the canvas's border-bottom and the verdict band's border-top. */
.rconsole .field-axis{display:flex; align-items:center; justify-content:space-between;
  gap:16px; padding:9px 24px; font-family:var(--font-mono); font-size:10.5px;
  letter-spacing:.06em; text-transform:uppercase; color:var(--text-mut);
  background:rgba(11,18,32,.4);}
.rconsole .field-axis .rej{color:var(--arm-control);}
.rconsole .field-axis .adt{color:var(--arm-treat);}
.rconsole .field-axis .mid{letter-spacing:.03em;}
.rconsole .field-axis .mid .gl{color:var(--signal);}
/* the green mean line's floating caption, positioned at the mean x over the field */
.rconsole .mean-label{position:absolute; top:13%; transform:translateX(-50%);
  pointer-events:none; z-index:2; font-family:var(--font-mono); font-size:9.5px;
  font-weight:500; letter-spacing:.14em; color:var(--signal); white-space:nowrap;}
.rconsole .bodywrap{max-width:1320px; margin:0 auto; padding:48px 0 96px;}

/* population field */
.rconsole .fieldwrap{position:relative; width:100%;
  background:
    radial-gradient(120% 90% at 78% 12%, rgba(72,239,202,.05), transparent 60%),
    radial-gradient(140% 120% at 20% 0%, var(--console-800), var(--console-900) 70%);
  border-bottom:1px solid var(--console-line); overflow:hidden;}
.rconsole #rc-field{display:block; width:100%; height:440px;}
.rconsole .field-vignette{position:absolute; inset:0; pointer-events:none;
  background:linear-gradient(180deg, rgba(11,18,32,.35) 0%, transparent 22%,
    transparent 68%, rgba(11,18,32,.86) 100%);}
.rconsole .field-legend{position:absolute; left:24px; top:18px; right:24px;
  display:flex; gap:10px; align-items:center; pointer-events:none;
  font-size:11px; letter-spacing:.06em; color:var(--text-mut); flex-wrap:wrap;}
.rconsole .field-legend .hi{color:var(--text);}
.rconsole .field-legend .sep{color:var(--console-line);}
.rconsole .field-verdict{position:absolute; left:24px; bottom:24px; right:24px;
  display:flex; align-items:flex-end; justify-content:space-between; gap:40px;
  pointer-events:none; flex-wrap:wrap;}
.rconsole .verdict-figure .lab{font-size:11px; letter-spacing:.07em;
  text-transform:uppercase; color:var(--text-mut); margin-bottom:10px;
  display:flex; align-items:center; gap:8px;}
.rconsole .verdict-figure .num{font-weight:500; font-size:104px; line-height:.9;
  letter-spacing:-.02em; color:var(--text-hi); display:flex;
  align-items:baseline; gap:16px; flex-wrap:wrap;}
.rconsole .verdict-figure .num .ci{font-size:24px; font-weight:400;
  color:var(--spread); letter-spacing:0;}
.rconsole .verdict-figure .num .of{font-size:24px; color:var(--text-mut);
  font-weight:400;}
.rconsole .verdict-figure .num .stamp{font-size:28px; color:var(--spread-dim);
  align-self:center;}
.rconsole .verdict-tag{display:inline-flex; align-items:center; gap:9px;
  margin-top:16px; font-size:12.5px; letter-spacing:.05em; text-transform:uppercase;
  color:var(--text-hi); border:1px solid var(--console-line);
  border-radius:var(--r-well); padding:6px 12px; flex-wrap:wrap;}
.rconsole .verdict-tag .vg{color:var(--spread-dim); font-size:13px;}

.rconsole .field-readout{max-width:300px; align-self:flex-end; padding-bottom:6px;}
.rconsole .field-readout .rlab{font-size:10px; letter-spacing:.07em;
  text-transform:uppercase; color:var(--text-mut); margin-bottom:9px;
  display:flex; justify-content:space-between; align-items:baseline;}
.rconsole .field-readout .rlab .rej{color:var(--arm-control);}
.rconsole .field-readout .rlab .adt{color:var(--arm-treat);}
.rconsole .split-strip{display:flex; align-items:flex-end; gap:3px;}
.rconsole .split-strip .seg{flex:1; min-width:0; display:flex;
  flex-direction:column; justify-content:flex-end; height:48px;}
.rconsole .split-strip .seg .bar{width:100%; min-height:2px;
  border-radius:1px 1px 0 0; opacity:.85;}
.rconsole .split-strip .seg .pc{font-size:11px; color:var(--text-hi);
  text-align:center; margin-bottom:4px;}
.rconsole .split-strip .seg .nm{margin-top:5px; font-size:9.5px;
  letter-spacing:.04em; text-transform:uppercase; color:var(--text-mut);
  text-align:center;}
.rconsole .field-readout .rfoot{font-size:10px; letter-spacing:.04em;
  color:var(--text-mut); margin-top:8px; text-align:right;}

/* page scaffold */
.rconsole .grid{display:grid; grid-template-columns:minmax(0,1fr) 348px; gap:48px;
  align-items:start; padding:48px 24px 0;}
.rconsole .col-main{min-width:0; display:flex; flex-direction:column; gap:48px;}

/* panels */
.rconsole .panel{background:var(--console-800);
  border:1px solid var(--console-line); border-radius:var(--r-panel);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04);}
.rconsole .panel-pad{padding:24px;}
.rconsole .panel.alert{border-color:rgba(240,104,60,.55);}
.rconsole .glass{background:var(--console-900);
  border:1px solid var(--console-line); border-radius:var(--r-frame);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05); overflow:hidden;}
.rconsole .chan-legend{display:flex; flex-wrap:wrap; align-items:center; gap:9px;
  padding:9px 16px; border-bottom:1px solid var(--console-line);
  font-size:11px; letter-spacing:.05em; color:var(--text-mut);
  background:rgba(11,18,32,.4);}
.rconsole .chan-legend .ch{color:var(--text);}
.rconsole .chan-legend .sep{color:var(--console-line);}

/* hypothesis header */
.rconsole .hcrumb{margin-bottom:14px; font-size:11px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--text-mut);}
.rconsole .hcrumb a{color:var(--text-mut);}
.rconsole .hcrumb a:hover{color:var(--text-hi);}
.rconsole .hcrumb b{color:var(--text); font-weight:500;}
.rconsole .lineage{display:flex; align-items:center; gap:9px; margin-bottom:18px;
  flex-wrap:wrap; font-size:11px; letter-spacing:.08em; text-transform:uppercase;}
.rconsole .lineage .node{display:inline-flex; align-items:center; gap:7px;}
.rconsole .lineage .sq{width:6px; height:6px; display:inline-block;}
.rconsole .lineage .sq.fill{background:var(--text);}
.rconsole .lineage .sq.alert{background:var(--alert);}
.rconsole .lineage .sq.open{border:1px solid var(--text-mut); background:transparent;}
.rconsole .lineage .rule{width:30px; height:1px; background:var(--console-line);}
.rconsole .lineage .on{color:var(--text);}
.rconsole .lineage .off{color:var(--text-mut);}
.rconsole h1.htitle{font-family:var(--font-sans); font-weight:600; font-size:32px;
  line-height:1.08; letter-spacing:-.025em; color:var(--text-hi); margin:0 0 12px;
  text-wrap:balance; max-width:36ch;}
/* Unparseable prose that's long: render as a readable statement, not a poster
   wall (a 32px headline of 60+ words is unreadable). Wider measure, smaller. */
.rconsole h1.htitle.htitle-long{font-size:20px; line-height:1.4;
  letter-spacing:-.01em; max-width:70ch;}
/* Parsed hypothesis claim — a sans headline + labeled Treatment/Control/Predict
   rows (the raw prose is one long run-on; the console base font is mono, which
   turned it into an unreadable wall). Sans for the prose, mono only for labels. */
.rconsole .hclaim{margin:0 0 14px;}
.rconsole .hclaim-lead{font-family:var(--font-sans); font-weight:600; font-size:27px;
  line-height:1.16; letter-spacing:-.02em; color:var(--text-hi);
  text-wrap:balance; max-width:46ch; margin-bottom:16px;}
/* predicted outcome folded into the headline — muted arrow, the outcome itself
   in normal weight so it reads as the *consequence* of the change, not part of
   the change's name. Not colored: the direction is a hypothesis, not a result. */
.rconsole .hclaim-lead .hclaim-arrow{color:var(--text-mut); font-weight:400;}
.rconsole .hclaim-lead .hclaim-out{font-weight:400; color:var(--text);}
.rconsole .hclaim-row{display:grid; grid-template-columns:104px 1fr; gap:16px;
  padding:11px 0; border-top:1px solid var(--console-line); align-items:baseline;}
.rconsole .hclaim-row .hk{font-family:var(--font-mono); font-size:10px; font-weight:500;
  letter-spacing:.12em; color:var(--text-mut); padding-top:3px;}
.rconsole .hclaim-row .hv{font-family:var(--font-sans); font-size:15px;
  line-height:1.55; color:var(--text); max-width:72ch;}
.rconsole .verdicttag-row{display:flex; align-items:center; gap:10px;
  flex-wrap:wrap; margin-bottom:12px;}
.rconsole .vchip{font-size:11px; letter-spacing:.05em; text-transform:uppercase;
  padding:4px 10px; border-radius:var(--r-well);
  border:1px solid var(--console-line); color:var(--text-hi);
  display:inline-flex; align-items:center; gap:8px;}
.rconsole .vchip .vg{color:var(--spread-dim);}
.rconsole .whyline{font-size:12px; letter-spacing:.02em; line-height:1.7;
  color:var(--text-mut); max-width:78ch;}
.rconsole .whyline .em{color:var(--text);}

/* disclosure note (out_of_scope / input-lint / degraded A/B) — a data
   condition, NOT an alarm: hairline rule border, message in ink, no tint. */
.rconsole .note{margin-top:12px; border:1px solid var(--console-line);
  border-radius:var(--r-well); padding:10px 12px; background:rgba(11,18,32,.4);}
.rconsole .note.warn{border-color:rgba(201,162,39,.5);}
.rconsole .note.alert{border-color:rgba(240,104,60,.5);}
.rconsole .note .nh{font-size:10px; font-weight:500; letter-spacing:.06em;
  text-transform:uppercase; color:var(--text-mut); margin-bottom:6px;}
.rconsole .note ul{margin:0; padding-left:18px; color:var(--text);
  font-size:13px; line-height:1.5;}
.rconsole .note li{margin-bottom:4px;}
.rconsole .note p{margin:0; color:var(--text); font-size:13px; line-height:1.5;}
.rconsole .note b, .rconsole .note strong{color:var(--text-hi); font-weight:550;}

.rconsole .tele{display:grid; grid-template-columns:repeat(6,minmax(0,1fr));
  gap:14px; margin-top:22px; padding-top:16px;
  border-top:1px solid var(--console-line);}
.rconsole .tele .cell .k{margin-bottom:5px;}
.rconsole .tele .cell .v{font-size:13.5px; color:var(--text-hi);
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.rconsole .tele .cell .carrier{display:block; height:2px;
  background:var(--signal); margin-top:3px; animation:rc-pulse 3.4s ease-in-out infinite;}
@keyframes rc-pulse{0%,100%{opacity:.45;}50%{opacity:1;}}

/* glass instrument grid */
.rconsole .glassgrid{display:grid; grid-template-columns:1.42fr 1fr;}
.rconsole .glass-cell{padding:24px; min-width:0;}
.rconsole .glass-cell.left{border-right:1px solid var(--console-line);}
.rconsole .glass-cell.full{grid-column:1 / -1; border-right:none;}
.rconsole .glass-lab{font-size:12.5px; font-weight:450; color:var(--text);}
.rconsole .glass-lab .sub{color:var(--text-mut);}
.rconsole .reading-row{display:flex; align-items:baseline; gap:14px;
  margin-top:20px; flex-wrap:wrap;}
.rconsole .reading-num{font-weight:500; font-size:64px; line-height:1;
  color:var(--text-hi); letter-spacing:-.01em;}
.rconsole .reading-num.muted{color:var(--text-mut);}
.rconsole .reading-ci{font-size:18px; color:var(--spread);}
.rconsole .reading-unit{font-size:11px; letter-spacing:.05em; color:var(--text-mut);
  align-self:flex-end; padding-bottom:8px;}
.rconsole .stamp{font-size:15px; vertical-align:middle;}
.rconsole .stamp.hollow{color:var(--spread-dim);}
.rconsole .kvrow{display:flex; gap:26px; flex-wrap:wrap; margin:18px 0;}
.rconsole .kv .k{font-size:10px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--text-mut); margin-bottom:3px;}
.rconsole .kv .v{font-size:14px; color:var(--text-hi);}
.rconsole .kv .v .ci{color:var(--spread); font-size:12px;}
.rconsole .kv .v .g{color:var(--spread-dim); font-size:12px;}
.rconsole .axisnote{font-size:11px; letter-spacing:.03em; line-height:1.7;
  color:var(--text-mut); margin-top:10px;}
.rconsole .axisnote .clears{color:var(--text-hi);}

/* paired-arm comparison */
.rconsole .armcompare{margin-top:18px;}
.rconsole .arm-track{position:relative; height:30px; margin:0 0 2px;}
.rconsole .arm-track .lab{position:absolute; left:0; top:50%;
  transform:translateY(-50%); font-size:10.5px; letter-spacing:.05em;
  text-transform:uppercase; color:var(--text-mut); width:62px;}
.rconsole .arm-track .lab .dot{display:inline-block; width:7px; height:7px;
  border-radius:9999px; margin-right:6px; vertical-align:middle;}
.rconsole .arm-track .lab .dot.c{background:var(--arm-control);}
.rconsole .arm-track .lab .dot.t{background:var(--arm-treat);}
.rconsole .arm-plot{position:absolute; left:70px; right:14px; top:0; bottom:0;}
.rconsole .arm-plot .strip{position:absolute; left:0; right:0; top:50%; height:1px;
  background:var(--console-line); transform:translateY(-50%);}
.rconsole .arm-plot .mean{position:absolute; top:18%; bottom:18%; width:2px;
  transform:translateX(-50%);}
.rconsole .arm-plot .mean.c{background:var(--arm-control);}
.rconsole .arm-plot .mean.t{background:var(--arm-treat);}
.rconsole .arm-plot .mean .v{position:absolute; top:-15px; left:50%;
  transform:translateX(-50%); font-size:11px; color:var(--text-hi);
  white-space:nowrap;}
.rconsole .arm-gap{position:relative; margin:2px 14px 0 70px; height:26px;}
.rconsole .arm-gap .bracket{position:absolute; top:6px; height:7px;
  border-left:1px solid var(--spread); border-right:1px solid var(--spread);
  border-bottom:1px solid var(--spread);}
.rconsole .arm-gap .glab{position:absolute; top:13px; transform:translateX(-50%);
  font-size:11px; color:var(--text-hi); white-space:nowrap;}
.rconsole .arm-gap .glab .ci{color:var(--spread); font-size:10px;}
.rconsole .arm-gap .glab .g{color:var(--spread-dim);}
.rconsole .arm-scale{margin:4px 14px 0 70px; display:flex;
  justify-content:space-between;}

.rconsole .glass-foot{display:flex; justify-content:space-between; gap:16px;
  flex-wrap:wrap; padding:11px 24px; border-top:1px solid var(--console-line);
  font-size:10.5px; letter-spacing:.04em; color:var(--text-mut);
  background:rgba(11,18,32,.35);}

.rconsole .sechead{font-size:11px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--text-mut); margin:0 0 16px;}
.rconsole .sechead.tight{margin-bottom:8px;}

/* metric lift / per-arm tiles */
.rconsole .bignum{font-weight:500; font-size:40px; line-height:1;
  color:var(--text-hi); letter-spacing:-.01em;}
.rconsole .bignum.muted{color:var(--text-mut);}
.rconsole .armtiles{display:grid;
  grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:18px;}
.rconsole .armtile .num{font-weight:500; font-size:28px; line-height:1;
  color:var(--text-hi);}
.rconsole .armtile .num.muted{color:var(--text-mut);}
.rconsole .bodytext{font-size:13px; color:var(--text-mut); line-height:1.55;
  max-width:74ch;}
.rconsole .bodytext.hi{color:var(--text);}

/* weakness register */
.rconsole .wk-headrow, .rconsole .wk-row{display:grid;
  grid-template-columns:minmax(0,1fr) 230px; gap:18px;}
.rconsole .wk-headrow{padding-bottom:10px;
  border-bottom:1px solid var(--console-line);}
.rconsole .wk-headrow span{font-size:11px; letter-spacing:.05em;
  text-transform:uppercase; color:var(--text-mut);}
.rconsole .wk-row{padding:14px 0; border-top:1px solid var(--console-line);}
.rconsole .wk-row:first-of-type{border-top:none;}
.rconsole .wk-name{font-size:15px; font-weight:550; color:var(--text-hi);
  margin-bottom:4px; display:flex; align-items:center; gap:7px;
  position:relative;}
.rconsole .wk-info{font-size:10px; color:var(--text-mut);
  border:1px solid var(--console-line); border-radius:9999px; width:16px;
  height:16px; display:inline-flex; align-items:center; justify-content:center;
  cursor:pointer; background:transparent; padding:0; line-height:1;}
.rconsole .wk-info[aria-expanded="true"]{background:var(--text-hi);
  color:var(--console-900); border-color:var(--text-hi);}
.rconsole .wk-pop{position:absolute; top:calc(100% + 8px); left:0; z-index:20;
  width:320px; max-width:85vw; background:var(--console-800);
  border:1px solid var(--console-line); border-radius:var(--r-panel);
  box-shadow:0 10px 28px rgba(0,0,0,.45); padding:14px;}
.rconsole .wk-pop .pt{font-size:13px; font-weight:600; color:var(--text-hi);
  margin-bottom:6px;}
.rconsole .wk-pop .pd{font-size:13px; color:var(--text-mut); line-height:1.55;
  font-weight:400;}
.rconsole .wk-pop .pclose{position:absolute; top:6px; right:6px;
  background:transparent; border:none; color:var(--text-mut); font-size:16px;
  line-height:1; cursor:pointer; padding:4px 6px;}
.rconsole .wk-sum{font-size:13.5px; color:var(--text); line-height:1.5;}
.rconsole .wk-sum b{color:var(--text-hi); font-weight:500;}
.rconsole .freqbar{position:relative; height:9px;}
.rconsole .freqbar .base{position:absolute; left:0; right:0; bottom:0; height:1px;
  background:var(--console-line);}
.rconsole .freqbar .ci{position:absolute; bottom:1px; height:6px;
  background:var(--spread-wash); border-left:1px solid var(--spread);
  border-right:1px solid var(--spread);}
.rconsole .freqbar .val{position:absolute; left:0; bottom:0; height:2px;
  background:var(--text-hi);}
.rconsole .freqlabel{font-size:11px; color:var(--text); margin-top:7px;}
.rconsole .freqlabel .ci{color:var(--spread);}

/* method card */
.rconsole .method-row{display:grid; grid-template-columns:140px minmax(0,1fr);
  gap:18px; padding:12px 0; border-top:1px solid var(--console-line);}
.rconsole .method-row:first-of-type{border-top:none;}
.rconsole .method-row .k{font-size:11px; letter-spacing:.05em;
  text-transform:uppercase; color:var(--text-mut); padding-top:2px;}
.rconsole .method-row .v{font-size:13.5px; color:var(--text); line-height:1.6;}

/* cohort register (persona-grouped, interactive) */
.rconsole .prow{padding:14px 0; border-top:1px solid var(--console-line);}
.rconsole .prow:first-of-type{border-top:none;}
.rconsole .prow-head{display:flex; align-items:baseline; gap:12px; width:100%;
  min-width:0;}
.rconsole .prow-toggle{display:flex; align-items:baseline; gap:12px; flex:1;
  min-width:0; text-align:left; background:transparent; border:none; padding:0;
  cursor:pointer; color:inherit;}
.rconsole .prow-caret{font-size:12px; color:var(--text-mut); width:12px;
  flex:0 0 auto;}
.rconsole .prow-name{font-size:15px; font-weight:600; color:var(--text-hi);
  flex:0 1 auto; min-width:0; overflow:hidden; text-overflow:ellipsis;
  white-space:nowrap;}
.rconsole .prow-count{font-size:13px; color:var(--text-mut); flex:0 0 auto;}
.rconsole .prow-pid{font-size:11px; color:var(--text-mut); margin-left:auto;
  min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
  font-family:var(--font-mono);}
.rconsole .chiplink{font-size:10px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--text-hi); border:1px solid var(--console-line);
  border-radius:var(--r-well); padding:4px 8px; white-space:nowrap;
  flex:0 0 auto; display:inline-block;}
.rconsole .chiplink:hover{border-color:var(--text-mut);}
.rconsole .chiplink.disabled{color:var(--text-faint); cursor:not-allowed;}
.rconsole .schip{font-size:11px; padding:2px 8px; border-radius:9999px;
  border:1px solid var(--console-line); color:var(--text); display:inline-flex;
  align-items:center; gap:4px; white-space:nowrap; flex:0 0 auto;}
.rconsole .schip .g{font-weight:600; color:var(--text-mut);}
.rconsole .armletter{font-size:11px; color:var(--text-mut); font-weight:600;}
.rconsole .quote{display:block; width:100%; text-align:left; background:transparent;
  border:none; padding:4px 0 0 24px; margin:0; cursor:pointer; font-size:13px;
  color:var(--text-mut); line-height:1.5; overflow:hidden; text-overflow:ellipsis;}
.rconsole .quote.clamp{white-space:nowrap;}
.rconsole .quote.open{white-space:normal;}
.rconsole .quote .qtag{font-size:10px; letter-spacing:.05em; text-transform:uppercase;
  color:var(--text-mut); margin-right:8px; padding:1px 6px;
  border:1px solid var(--console-line); border-radius:var(--r-well);}
.rconsole .subgroup{padding:8px 0 0 24px;}
.rconsole .subhead{display:flex; align-items:center; gap:8px; font-size:11px;
  letter-spacing:.05em; text-transform:uppercase; color:var(--text-mut);
  font-weight:600; padding:4px 0; border-bottom:1px solid var(--console-line);}
.rconsole .subhead .n{color:var(--text-mut); font-weight:400;}
.rconsole .alirow{padding:8px 0; border-top:1px dashed var(--console-line);}
.rconsole .alihead{display:flex; align-items:baseline; gap:12px; font-size:13px;}
.rconsole .aliid{color:var(--text-hi); font-family:var(--font-mono);
  flex:0 0 auto;}

/* refinement queue */
.rconsole .refrow{display:grid; grid-template-columns:minmax(0,1fr) auto;
  gap:18px; align-items:center; padding:13px 0;
  border-top:1px solid var(--console-line);}
.rconsole .refrow:first-of-type{border-top:none;}
.rconsole .refrow .txt{font-size:14px; color:var(--text); line-height:1.5;}

/* run log */
.rconsole .runlog{list-style:none; padding:12px; margin:0;
  background:var(--console-900); border:1px solid var(--console-line);
  border-radius:var(--r-well); font-size:12px; color:var(--text);}
.rconsole .runlog li{padding:2px 0;}

/* cohort agents fallback list */
.rconsole .cohort-fallback{list-style:none; padding:0; margin:0;}
.rconsole .cohort-fallback li{padding:8px 0; border-top:1px solid var(--console-line);
  font-size:14px;}
.rconsole .cohort-fallback li:first-child{border-top:none;}
.rconsole .cohort-fallback .aid{color:var(--text-hi);
  text-decoration:underline; text-decoration-color:var(--console-line);}
.rconsole .cohort-fallback .afull{color:var(--text-mut); margin-left:8px;
  font-size:12px;}

/* inspector rail */
.rconsole .inspector{position:sticky; top:24px; align-self:start;
  background:var(--console-800); border:1px solid var(--console-line);
  border-radius:var(--r-panel); box-shadow:inset 0 1px 0 rgba(255,255,255,.04);
  padding:20px; min-width:0;}
.rconsole .pbtn{display:flex; align-items:baseline; gap:8px; width:100%;
  text-align:left; background:transparent; border:none;
  border-top:1px solid var(--console-line); padding:8px 6px; cursor:pointer;
  color:inherit;}
.rconsole .pbtn[aria-pressed="true"]{background:var(--console-750);}
.rconsole .pbtn .pn{font-size:13px; color:var(--text-hi); flex:1; min-width:0;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.rconsole .pbtn[aria-pressed="true"] .pn{font-weight:600;}
.rconsole .pbtn .pc{font-size:11px; color:var(--text-mut); white-space:nowrap;}
.rconsole .quotewell{background:var(--console-900);
  border:1px solid var(--console-line); border-radius:var(--r-well); padding:13px;
  margin:6px 0 20px;}
.rconsole .quotewell .ql{font-size:10px; letter-spacing:.05em;
  text-transform:uppercase; color:var(--text-mut); margin-bottom:8px;}
.rconsole .quotewell .qt{font-size:13.5px; color:var(--text-hi); line-height:1.55;}
.rconsole .quotewell .qm{font-size:11px; color:var(--text-mut);}
.rconsole .prov{margin:0 0 18px;}
.rconsole .provrow{display:grid; grid-template-columns:118px minmax(0,1fr);
  gap:8px; padding:6px 0; border-top:1px solid var(--console-line);}
.rconsole .provrow:first-child{border-top:none;}
.rconsole .provrow dt{font-size:10px; letter-spacing:.04em; text-transform:uppercase;
  color:var(--text-mut); padding-top:1px;}
.rconsole .provrow dd{margin:0; font-size:11.5px; color:var(--text-hi);
  overflow-wrap:anywhere;}
.rconsole .artlink{font-size:11.5px; letter-spacing:.04em; color:var(--text);}
.rconsole .artlink:hover{color:var(--text-hi);}

/* quiet states (pending / running / failed) */
.rconsole .quiet-state{max-width:1320px; margin:0 auto; padding:64px 24px 96px;}
.rconsole .quiet-card{background:var(--console-800);
  border:1px solid var(--console-line); border-radius:var(--r-panel);
  padding:32px; box-shadow:inset 0 1px 0 rgba(255,255,255,.04);}
.rconsole .quiet-card.failed{border-color:rgba(240,104,60,.55);}
.rconsole .quiet-head{font-size:12px; letter-spacing:.06em; text-transform:uppercase;
  display:flex; align-items:center; gap:9px; margin-bottom:14px;}
.rconsole .quiet-head.running{color:var(--text-hi);}
.rconsole .quiet-head.pending{color:var(--text-mut);}
.rconsole .quiet-head.failed{color:var(--alert);}
.rconsole .quiet-body{font-size:13.5px; color:var(--text-mut); line-height:1.6;
  max-width:64ch;}
.rconsole .live-dot{width:7px; height:7px; border-radius:9999px;
  background:var(--signal); display:inline-block;
  animation:rc-breath 2s ease-in-out infinite;}
@keyframes rc-breath{0%,100%{opacity:.5;}50%{opacity:1;}}

/* top error banner */
.rconsole .errbanner{border:1px solid rgba(240,104,60,.55);
  background:rgba(240,104,60,.08); color:var(--text-hi); border-radius:var(--r-well);
  padding:10px 14px; margin:0 24px 16px; font-size:13px;}

/* focus rings */
.rconsole a:focus-visible, .rconsole button:focus-visible{
  outline:2px solid var(--signal-dim); outline-offset:2px; border-radius:var(--r-well);}

@media (max-width:1040px){
  .rconsole .grid{grid-template-columns:minmax(0,1fr); gap:48px;}
  .rconsole .inspector{position:static;}
  .rconsole .glassgrid{grid-template-columns:1fr;}
  .rconsole .glass-cell.left{border-right:none;
    border-bottom:1px solid var(--console-line);}
  .rconsole .tele{grid-template-columns:repeat(3,1fr);}
  .rconsole .verdict-figure .num{font-size:72px;}
  .rconsole .field-verdict{position:static; padding:24px;}
  .rconsole #rc-field{height:320px;}
}
@media (prefers-reduced-motion:reduce){
  .rconsole *{animation:none!important;}
}
`;

// ── the showpiece canvas (verbatim from ReadingConsoleResults) ───────────────
type FieldAgent = {
  arm: 0 | 1;
  score: number;
  rx: number;
  ry: number;
  delay: number;
  bin: number;
  stack: number;
  tx: number;
  ty: number;
  sx: number;
  sy: number;
};

type FieldModel = {
  agents: FieldAgent[];
  mean: number;
  ciHalf: number | null;
  armKnown: boolean;
};

function mulberry(seed: number): () => number {
  let a = seed | 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function buildFieldModel(sim: Simulation, result: SimulationResult): FieldModel {
  const rnd = mulberry((sim.run_seed ?? 0x4f17) >>> 0);
  const agents: FieldAgent[] = [];
  const treatFrac = sim.arm_split?.treatment_fraction ?? null;
  const isAB = treatFrac != null;

  const per = result.per_agent_analyses ?? [];
  const blank = (): Omit<FieldAgent, "arm" | "score"> => ({
    rx: rnd(),
    ry: rnd(),
    delay: rnd(),
    bin: 0,
    stack: 0,
    tx: 0,
    ty: 0,
    sx: 0,
    sy: 0,
  });

  let armKnown = false;

  if (per.length > 0) {
    per.forEach((a) => {
      const dir = a.sentiment === "positive" ? 1 : a.sentiment === "negative" ? -1 : 0;
      const conf = Math.max(0, Math.min(1, a.sentiment_confidence));
      const signed = dir === 0 ? (rnd() - 0.5) * 0.18 : dir * (0.18 + conf * 0.42);
      const score = Math.max(0.02, Math.min(0.98, 0.5 + signed));
      agents.push({ arm: 0, score, ...blank() });
    });
  } else {
    const n = sim.sampled_agent_count ?? 120;
    const tScore = result.treatment_score;
    const cScore = result.control_score;
    const haveArms =
      isAB && typeof tScore === "number" && typeof cScore === "number";
    armKnown = haveArms;
    const centerC = haveArms ? (cScore as number) / 100 : result.confidence_score / 100;
    const centerT = haveArms ? (tScore as number) / 100 : centerC;
    const spread = 0.16;
    for (let i = 0; i < n; i++) {
      const arm: 0 | 1 = haveArms ? (i % 2 === 1 ? 1 : 0) : 0;
      const base = arm === 1 ? centerT : centerC;
      const u1 = rnd();
      const u2 = rnd();
      const g = Math.sqrt(-2 * Math.log(u1 + 1e-6)) * Math.cos(6.2831853 * u2);
      const score = Math.max(0.02, Math.min(0.98, base + g * spread));
      agents.push({ arm, score, ...blank() });
    }
  }

  const mean =
    agents.length > 0
      ? agents.reduce((s, a) => s + a.score, 0) / agents.length
      : result.confidence_score / 100;

  const ch = ciHalf(result.confidence_score_ci);
  return { agents, mean, ciHalf: ch != null ? ch / 100 : null, armKnown };
}

// Parse the composed hypothesis prose into labeled blocks. Authored prose comes
// in several shapes — there is no single rigid template, so each marker is
// handled independently rather than as one fixed regex:
//   • an optional leading "If "
//   • an optional "Treatment: … Control: …" framing (with or without a "|")
//   • an optional trailing ", then <outcome>"
// We extract whatever markers are present. If NONE are found we return null so
// the caller renders the prose verbatim (never lose or mangle the author's
// words). Both of these parse correctly:
//   "If The change "X". | Treatment: … Control: …, then engagement increases."
//   "The change "X". Treatment: … Control: … partially finished."
type ClaimParts = {
  lead: string;
  treatment: string | null;
  control: string | null;
  outcome: string | null;
};
function parseClaim(proseRaw: string): ClaimParts | null {
  let s = (proseRaw ?? "").trim();
  if (!s) return null;
  // Strip an optional leading "If " wrapper.
  s = s.replace(/^if\s+/i, "");
  // Pull a trailing ", then <outcome>" if present (optional — many runs omit it).
  // Greedy prefix so we split on the LAST ", then" — a change can legitimately
  // contain "…, then…" mid-sentence; only the final clause is the outcome.
  let outcome: string | null = null;
  const thenM = s.match(/^([\s\S]*),\s*then\s+([\s\S]+?)\.?\s*$/i);
  if (thenM) {
    s = thenM[1].trim();
    outcome = thenM[2].trim().replace(/\.+$/, "");
  }
  // Split "Treatment: … Control: …" framing, leading "|" optional, wrapper or no.
  let treatment: string | null = null;
  let control: string | null = null;
  let change = s;
  const tc = s.match(
    /^([\s\S]*?)\|?\s*treatment:\s*([\s\S]+?)\s*control:\s*([\s\S]+)$/i,
  );
  if (tc) {
    change = tc[1].replace(/[.\s|]+$/, "").trim();
    treatment = tc[2].replace(/[.\s]+$/, "").trim();
    control = tc[3].replace(/[.\s]+$/, "").trim();
  }
  // No structured markers at all → let the caller render the raw prose verbatim
  // rather than dumping a half-parsed string into the headline.
  if (treatment == null && control == null && outcome == null) return null;
  return { lead: cleanLead(change), treatment, control, outcome };
}

// Tidy the headline so it reads as a claim, not a cut-off label. Two safe,
// targeted strips: a leading "The change <quoted name>" / "Change: " label-in
// (only when it's clearly a label — followed by a quote, or punctuated with a
// colon — so legitimate prose like "The change in pricing" is left intact), and
// any trailing period(s) that made the fragment look like a severed sentence.
function cleanLead(s: string): string {
  return s
    .replace(/^the\s+change\s+(?=["'“‘])/i, "")
    .replace(/^(?:the\s+change|change)\s*:\s*/i, "")
    .replace(/\s*\.+\s*$/, "")
    .trim();
}

function PopulationField({
  model,
  showLegend,
}: {
  model: FieldModel;
  showLegend: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduce =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const DPR = Math.min(window.devicePixelRatio || 1, 2);
    const agents = model.agents;
    const N = agents.length;

    let L = { padX: 0, axisY: 0, plotW: 0, padTop: 0 };
    function layout(W: number, H: number) {
      const padX = W * 0.07;
      const padTop = H * 0.2;
      const padBot = H * 0.3;
      const axisY = H - padBot;
      const plotW = W - padX * 2;
      const BINS = 48;
      const counts = new Array<number>(BINS).fill(0);
      for (let i = 0; i < N; i++) {
        const b = Math.min(BINS - 1, Math.floor(agents[i].score * BINS));
        agents[i].bin = b;
        agents[i].stack = counts[b]++;
      }
      const maxStack = counts.length ? Math.max(...counts) : 1;
      const colH = (axisY - padTop) / Math.max(maxStack, 18);
      for (let j = 0; j < N; j++) {
        const a = agents[j];
        a.tx = padX + a.score * plotW;
        a.ty = axisY - (a.stack + 0.5) * colH;
        a.sx = padX * 0.4 + a.rx * (W - padX * 0.8);
        a.sy = padTop * 0.5 + a.ry * (axisY - padTop * 0.4);
      }
      L = { padX, axisY, plotW, padTop };
    }

    function fit() {
      const cssW = canvas!.clientWidth;
      const cssH = canvas!.clientHeight;
      canvas!.width = Math.round(cssW * DPR);
      canvas!.height = Math.round(cssH * DPR);
      layout(canvas!.width, canvas!.height);
    }
    fit();

    const BET_START = 250;
    const BET_DUR = 900;
    const SETTLE_AT = BET_START + BET_DUR + 200;
    const DRIFT_PX = 2;
    let t0 = performance.now();
    let raf = 0;
    let lastDraw = 0;
    const FRAME_MS = 1000 / 30;

    function easeMech(t: number) {
      return t < 0 ? 0 : t > 1 ? 1 : 1 - Math.pow(1 - t, 3);
    }
    function colorFor(arm: number, mix: number): [number, number, number] {
      const c: [number, number, number] = model.armKnown
        ? arm === 1
          ? [224, 139, 196]
          : [79, 168, 224]
        : [198, 204, 216];
      const faint: [number, number, number] = [100, 110, 132];
      return [
        Math.round(faint[0] + (c[0] - faint[0]) * mix),
        Math.round(faint[1] + (c[1] - faint[1]) * mix),
        Math.round(faint[2] + (c[2] - faint[2]) * mix),
      ];
    }
    const driftSeed = (i: number) => (i * 1.61803) % 6.2831853;

    function draw(now: number) {
      const c = canvas!;
      const time = now - t0;
      ctx!.clearRect(0, 0, c.width, c.height);
      ctx!.globalCompositeOperation = "lighter";

      let betT = (time - BET_START) / BET_DUR;
      betT = betT < 0 ? 0 : betT > 1 ? 1 : betT;
      const settled = time >= SETTLE_AT;
      const wf =
        -0.15 + 1.3 * easeMech(Math.min(1, (time - BET_START) / (BET_DUR * 0.72)));
      const wfx = wf * c.width;
      const bandW = c.width * 0.16;
      const driftTime = reduce ? 0 : time;

      if (betT > 0.55) {
        const ribA = Math.min(1, (betT - 0.55) / 0.45) * 0.16;
        const meanX = L.padX + model.mean * L.plotW;
        ctx!.globalCompositeOperation = "source-over";
        if (model.ciHalf != null) {
          const ciW = L.plotW * Math.max(0.02, model.ciHalf);
          const grad = ctx!.createLinearGradient(meanX - ciW, 0, meanX + ciW, 0);
          grad.addColorStop(0, "rgba(201,180,122,0)");
          grad.addColorStop(0.5, `rgba(201,180,122,${ribA})`);
          grad.addColorStop(1, "rgba(201,180,122,0)");
          ctx!.fillStyle = grad;
          ctx!.fillRect(
            meanX - ciW,
            L.padTop * 0.7,
            ciW * 2,
            L.axisY - L.padTop * 0.7,
          );
        }
        ctx!.strokeStyle = `rgba(72,239,202,${Math.min(1, ribA * 4.2)})`;
        ctx!.lineWidth = 1.4 * DPR;
        ctx!.beginPath();
        ctx!.moveTo(meanX, L.padTop * 0.7);
        ctx!.lineTo(meanX, L.axisY);
        ctx!.stroke();
        ctx!.globalCompositeOperation = "lighter";
      }

      for (let i = 0; i < N; i++) {
        const a = agents[i];
        let lt = (betT - a.delay * 0.28) / (1 - a.delay * 0.28);
        lt = lt < 0 ? 0 : lt > 1 ? 1 : lt;
        const p = easeMech(lt);
        const ph = driftSeed(i);
        const dx = Math.sin(driftTime * 0.00045 + ph) * DRIFT_PX * DPR;
        const dy = Math.cos(driftTime * 0.00038 + ph * 1.3) * DRIFT_PX * DPR;
        const baseX = settled ? a.tx : a.sx + (a.tx - a.sx) * p;
        const baseY = settled ? a.ty : a.sy + (a.ty - a.sy) * p;
        const x = baseX + dx;
        const y = baseY + dy;

        let frontMix = settled ? 0 : 1 - Math.min(1, Math.abs(x - wfx) / bandW);
        frontMix = frontMix < 0 ? 0 : frontMix;
        const passed = x < wfx || settled ? 1 : 0;
        const col = colorFor(a.arm, Math.min(1, passed * 0.55 + p * 0.6));
        const size = (1.2 + frontMix * 1.6) * DPR;
        const alpha = 0.3 + p * 0.45 + frontMix * 0.35;

        ctx!.beginPath();
        ctx!.arc(x, y, size, 0, 6.2831853);
        if (frontMix > 0.55) {
          ctx!.fillStyle = `rgba(72,239,202,${0.55 * frontMix})`;
        } else {
          ctx!.fillStyle = `rgba(${col[0]},${col[1]},${col[2]},${alpha})`;
        }
        ctx!.fill();
      }

      if (!settled && betT < 1 && wfx > 0 && wfx < c.width) {
        ctx!.globalCompositeOperation = "lighter";
        const g2 = ctx!.createLinearGradient(
          wfx - bandW * 0.5,
          0,
          wfx + bandW * 0.5,
          0,
        );
        g2.addColorStop(0, "rgba(72,239,202,0)");
        g2.addColorStop(0.5, "rgba(72,239,202,0.10)");
        g2.addColorStop(1, "rgba(72,239,202,0)");
        ctx!.fillStyle = g2;
        ctx!.fillRect(wfx - bandW * 0.5, 0, bandW, c.height);
      }

      ctx!.globalCompositeOperation = "source-over";
      ctx!.strokeStyle = "rgba(51,64,92,0.55)";
      ctx!.lineWidth = 1 * DPR;
      ctx!.beginPath();
      ctx!.moveTo(L.padX * 0.5, L.axisY);
      ctx!.lineTo(c.width - L.padX * 0.5, L.axisY);
      ctx!.stroke();
    }

    function frame(now: number) {
      if (typeof document !== "undefined" && document.hidden) {
        raf = requestAnimationFrame(frame);
        return;
      }
      if (now - lastDraw >= FRAME_MS) {
        lastDraw = now;
        draw(now);
        if (now - t0 >= SETTLE_AT) {
          return;
        }
      }
      raf = requestAnimationFrame(frame);
    }

    if (reduce) {
      t0 = performance.now() - (SETTLE_AT + 10);
      draw(performance.now());
    } else {
      raf = requestAnimationFrame(frame);
    }

    const onResize = () => {
      fit();
      t0 = performance.now() - (SETTLE_AT + 10);
      draw(performance.now());
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, [model]);

  return (
    <section className="fieldwrap" aria-label="Population reaction field">
      <canvas id="rc-field" ref={canvasRef} width={2640} height={880} />
      <div className="field-vignette" />
      {/* Floating caption naming the green vertical line (the population mean
          reaction). Positioned at the same x the canvas draws the line:
          padX (7% of width) + mean × plotW (86% of width). */}
      <div
        className="mean-label"
        style={{ left: `${((0.07 + model.mean * 0.86) * 100).toFixed(1)}%` }}
      >
        MEAN
      </div>
      <div className="field-legend">
        <span className="hi">CH1</span>
        <span className="sep">·</span>
        <span>POPULATION REACTION</span>
        <span className="sep">·</span>
        <span className="unc">
          <span className="glyph-hollow">◇</span>
        </span>
        <span className="sep">·</span>
        <span>{showLegend}</span>
      </div>
    </section>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// MAIN — fork of SimulationDetailLegacy: identical data load / poll / state.
// ───────────────────────────────────────────────────────────────────────────
export default function SimulationDetailV2() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? "";

  const [sim, setSim] = useState<Simulation | null>(null);
  const [state, setState] = useState<SimulationRunState | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [agentMeta, setAgentMeta] = useState<AgentRow[] | null>(null);
  const [agentMetaError, setAgentMetaError] = useState<string | null>(null);
  const hadRunning = useRef(false);
  const [, setIsSettling] = useState(false);
  const [livePoints, setLivePoints] = useState<TracePoint[]>([]);
  const [liveTicks, setLiveTicks] = useState<number[]>([]);
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);

  // Reset settle state when the sim id changes so navigating from a running sim
  // to an already-terminal sim doesn't spuriously fire the settle transition.
  useLayoutEffect(() => {
    hadRunning.current = false;
    setIsSettling(false);
    setLivePoints([]);
    setLiveTicks([]);
    setSelectedPersona(null);
  }, [id]);

  // Initial fetch of the simulation.
  useEffect(() => {
    let cancelled = false;
    if (!id) return;
    (async () => {
      try {
        const s = await getSimulation(id);
        if (cancelled) return;
        setSim(s);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 404) {
          setNotFound(true);
        } else {
          setError(e instanceof Error ? e.message : String(e));
        }
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  // Polling loop for state + sim re-fetch on terminal.
  useEffect(() => {
    if (!id || !sim) return;
    if (isTerminalStatus(sim.status)) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    let cancelled = false;

    const tick = async () => {
      try {
        const st = await getSimulationState(id);
        if (cancelled) return;
        setState(st);
        setError(null);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 404) {
          // state.json not yet written — normal.
        } else {
          setError(e instanceof Error ? e.message : String(e));
        }
      }
      try {
        const s = await getSimulation(id);
        if (cancelled) return;
        setSim(s);
        if (isTerminalStatus(s.status) && intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } catch (e) {
        if (cancelled) return;
        if (!(e instanceof ApiError && e.status === 404)) {
          setError(e instanceof Error ? e.message : String(e));
        }
      }
    };

    // Kick off immediately, then every 5s.
    tick();
    intervalRef.current = setInterval(tick, 5000);

    return () => {
      cancelled = true;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [id, sim?.status]);

  // Cleanup on unmount.
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []);

  // Accumulate live trace data from poll ticks (§9.7). Event-driven: each
  // observation appends; no interpolation, no per-point tween.
  useEffect(() => {
    if (!state) return;
    const total = state.agents_total ?? 0;
    if (total <= 0) return;
    const done = (state.agents_complete ?? 0) + (state.agents_failed ?? 0);
    const x = Math.min(1, done / total);
    if (done > 0) {
      setLiveTicks((ts) => (ts[ts.length - 1] === x ? ts : [...ts, x]));
    }
    let score: number | null = state.partial_score ?? null;
    if (score == null) {
      for (const ev of state.recent_events ?? []) {
        if (ev.type !== "score.updated") continue;
        const s = ev.payload?.score;
        if (typeof s === "number" && Number.isFinite(s)) score = s;
      }
    }
    if (score == null) return;
    const y = score;
    setLivePoints((pts) => {
      const last = pts[pts.length - 1];
      if (last && last.x === x && last.y === y) return pts;
      return [...pts, { x, y }];
    });
  }, [state]);

  // Track running → terminal transition (drives the settle window). Kept
  // verbatim from legacy; the dark field settles itself, so the settle flag is
  // observed only to preserve the exact transition logic.
  useLayoutEffect(() => {
    if (!sim) return;
    if (!isTerminalStatus(sim.status)) {
      hadRunning.current = true;
    } else if (hadRunning.current) {
      hadRunning.current = false;
      setIsSettling(true);
      const t = setTimeout(() => setIsSettling(false), 800);
      return () => clearTimeout(t);
    }
  }, [sim?.status]);

  // Load the per-agent metadata once the simulation hits a terminal state.
  useEffect(() => {
    if (!sim || !isTerminalStatus(sim.status)) return;
    setAgentMetaError(null);
    if ((sim.agent_instance_ids ?? []).length === 0) {
      setAgentMeta([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const fetched = await listSimulationAgents(sim.id);
        if (cancelled) return;
        setAgentMeta(
          fetched.map((a) => ({
            agent_id: a.agent_id,
            persona_id: a.persona_id,
            persona_name: a.persona_name,
            sentiment: a.sentiment ?? null,
            sentiment_confidence: a.sentiment_confidence ?? null,
            top_quote: a.top_quote ?? null,
            arm:
              a.arm === "treatment" || a.arm === "control"
                ? (a.arm as Arm)
                : null,
          })),
        );
      } catch (e) {
        if (cancelled) return;
        setAgentMetaError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sim?.id, sim?.status]);

  // ── pre-content states (loading / not-found / load error) — restyled to the
  //    dark console quiet-state language. Each wraps in AppShellV2 + .rconsole.
  if (!loaded) {
    return (
      <AppShellV2 activeNav="simulations" title="Reading" surface="console">
        <div className="rconsole">
          <style dangerouslySetInnerHTML={{ __html: RCONSOLE_CSS }} />
          <div className="quiet-state">
            <div className="quiet-card">
              <div className="quiet-head pending">
                <span className="glyph-hollow">◇</span> LOADING SIMULATION…
              </div>
            </div>
          </div>
        </div>
      </AppShellV2>
    );
  }

  if (notFound) {
    return (
      <AppShellV2 activeNav="simulations" title="Reading" surface="console">
        <div className="rconsole">
          <style dangerouslySetInnerHTML={{ __html: RCONSOLE_CSS }} />
          <div className="quiet-state">
            <div className="quiet-card">
              <div className="quiet-head pending">SIMULATION NOT FOUND</div>
              <div className="quiet-body">
                No simulation exists with id{" "}
                <span className="mono" style={{ color: "var(--text-hi)" }}>
                  {id}
                </span>
                .
              </div>
              <div style={{ marginTop: 20 }}>
                <Link className="artlink" href="/simulations">
                  ← Back to simulations
                </Link>
              </div>
            </div>
          </div>
        </div>
      </AppShellV2>
    );
  }

  if (!sim) {
    return (
      <AppShellV2 activeNav="simulations" title="Reading" surface="console">
        <div className="rconsole">
          <style dangerouslySetInnerHTML={{ __html: RCONSOLE_CSS }} />
          <div className="quiet-state">
            <div className="quiet-card failed">
              <div className="quiet-head failed">UNABLE TO LOAD SIMULATION</div>
              <div className="quiet-body" role="alert">
                {error ?? "Unable to load simulation."}
              </div>
            </div>
          </div>
        </div>
      </AppShellV2>
    );
  }

  // ── derived state — byte-identical to legacy ───────────────────────────────
  const status = sim.status;
  const terminal = isTerminalStatus(status);
  const agentIds = sim.agent_instance_ids ?? [];
  const result = sim.result ?? null;
  const completeResult = status === "complete" ? result : null;
  const hasLift = sim.arm_split != null;

  const agentsTotal = state?.agents_total ?? 0;
  const agentsComplete = state?.agents_complete ?? 0;
  const agentsFailed = state?.agents_failed ?? 0;
  const done = agentsComplete + agentsFailed;
  const recent = (state?.recent_events ?? []).slice(-6).reverse();

  const verdict = verdictFor(status, result);
  // #311 / T2 — when the run abstained (out_of_scope), the verdict is withheld
  // at the HEADER and every downstream ship/no-ship policy readout must be
  // suppressed too — the raw agreement reading still prints.
  const abstained = completeResult?.instrument_scope === "out_of_scope";
  const personaGroups = agentMeta != null ? groupAgents(agentMeta) : null;
  const personaCount = personaGroups != null ? personaGroups.length : null;
  const model = modelDisplay(sim.model_id ?? null);

  const hypothesis: Hypothesis = sim.hypothesis;
  // Parse the composed prose into labeled blocks for legible display (null when
  // it doesn't match the canonical shape → caller falls back to raw prose).
  const claim = parseClaim(hypothesis.prose);
  const treatFrac = sim.arm_split?.treatment_fraction ?? null;
  const isAB = treatFrac != null;

  const whyLine = (() => {
    if (status === "failed")
      return "WHY: RUN TERMINATED BEFORE A READING SETTLED — POLICY DR-1 NOT EVALUATED";
    if (!completeResult)
      return `WHY: VERDICT PRINTS WHEN THE READING SETTLES — POLICY ${DECISION_POLICY.id} APPLIES AT THRESHOLD ${DECISION_POLICY.threshold}`;
    // #311 / T2: when the OEC is out of the instrument's scope, the policy is
    // deliberately NOT evaluated against the score — the verdict is withheld.
    if (completeResult.instrument_scope === "out_of_scope")
      return `WHY: THIS OEC IS OUTSIDE A FIRST-EXPOSURE SINGLE-SESSION PANEL'S RESOLVING POWER — POLICY ${DECISION_POLICY.id} WITHHELD (SEE INSTRUMENT-SCOPE NOTE)`;
    const s = completeResult.confidence_score;
    const cmp = s >= DECISION_POLICY.threshold ? "≥" : "<";
    const w = (completeResult.weaknesses ?? []).length;
    return `WHY: AGREEMENT ${s.toFixed(1)} ${cmp} THRESHOLD ${DECISION_POLICY.threshold} (POLICY ${DECISION_POLICY.id}) · ${w} WEAKNESS FINDING${w === 1 ? "" : "S"} · RAW SIM READING — UNCALIBRATED (LEDGER EMPTY)`;
  })();

  const armsLabel = (() => {
    if (sim.arm_split == null) return "SINGLE";
    const t = Math.round((sim.arm_split.treatment_fraction ?? 0.5) * 100);
    return `A/B ${t}/${100 - t}`;
  })();

  const readingsLabel = terminal
    ? `${agentIds.length}`
    : agentsTotal > 0
      ? `${done} OF ${agentsTotal}`
      : "—";

  // Field model — only when complete with a result.
  const fieldModel: FieldModel | null =
    completeResult != null ? buildFieldModel(sim, completeResult) : null;

  // Hero verdict figures (mock structure) — RAW, uncalibrated.
  const score = completeResult?.confidence_score ?? null;
  const scoreCi = completeResult?.confidence_score_ci ?? null;
  const scoreHalf = ciHalf(scoreCi);
  const pairedN = completeResult?.lift_paired_n ?? null;

  // reaction split (rejects/neutral/adopts) from per-agent sentiment, raw counts
  const per = completeResult?.per_agent_analyses ?? [];
  const split = (() => {
    if (per.length === 0) return null;
    let pos = 0;
    let neu = 0;
    let neg = 0;
    for (const a of per) {
      if (a.sentiment === "positive") pos++;
      else if (a.sentiment === "negative") neg++;
      else neu++;
    }
    const tot = per.length;
    return {
      rej: Math.round((neg / tot) * 100),
      neu: Math.round((neu / tot) * 100),
      adt: Math.round((pos / tot) * 100),
      tot,
    };
  })();

  return (
    <AppShellV2 activeNav="simulations" title="Reading" surface="console">
      <div className="rconsole">
        <style dangerouslySetInnerHTML={{ __html: RCONSOLE_CSS }} />

        {error && (
          <div role="alert" className="errbanner">
            {error}
          </div>
        )}

        {/* ════ CONTAINED POPULATION FIELD HERO + VERDICT READOUT ════ */}
        <div className="fieldhero">
          {completeResult != null && fieldModel != null ? (
            <>
              <PopulationField
                model={fieldModel}
                showLegend={
                  !isAB
                    ? "SINGLE ARM"
                    : fieldModel.armKnown
                      ? "A/B · BY ARM"
                      : "A/B · ARM POOLED"
                }
              />
              {/* x-axis caption: what left/right mean + what the green line is */}
              <div className="field-axis">
                <span className="rej">◀ rejects</span>
                <span className="mid">
                  position = sentiment · <span className="gl">green</span> ={" "}
                  population mean
                </span>
                <span className="adt">adopts ▶</span>
              </div>
              <div
                className="fieldwrap"
                style={{
                  borderTop: "1px solid var(--console-line)",
                  paddingBottom: 0,
                }}
              >
                <div
                  className="field-verdict"
                  style={{ position: "static", padding: 24 }}
                >
                  <div className="verdict-figure">
                    <div className="lab">
                      <span>SIMULATION AGREEMENT — RAW, UNCALIBRATED</span>
                      <span className="glyph-hollow">◇</span>
                    </div>
                    <div className="num">
                      <span>{fmt1(score as number)}</span>
                      {scoreHalf != null ? (
                        <span className="ci">±{fmt1(scoreHalf)}</span>
                      ) : (
                        <span className="ci glyph-hollow" style={{ fontSize: 18 }}>
                          ◇ UNCALIBRATED
                        </span>
                      )}
                      <span className="of">/ 100</span>
                      <span className="stamp">◇</span>
                    </div>
                    {/* Verdict tag — hollow glyph + WORD + qualifier; never a
                        ship-green / hold-red fill. Same verdict.label the
                        legacy header renders. Abstention text comes through the
                        label itself (NOT ANSWERABLE BY THIS INSTRUMENT). */}
                    <div className="verdict-tag">
                      <span className="vg">◇</span>
                      {verdict.label}
                    </div>
                  </div>

                  {split ? (
                    <div className="field-readout">
                      <div className="rlab">
                        <span className="rej">◀ rejects</span>
                        <span className="adt">adopts ▶</span>
                      </div>
                      <div
                        className="split-strip"
                        aria-label={`Reaction split: ${split.rej}% reject, ${split.neu}% neutral, ${split.adt}% adopt`}
                      >
                        <div className="seg">
                          <div className="pc">{split.rej}</div>
                          <div
                            className="bar"
                            style={{
                              height: `${Math.max(4, split.rej)}%`,
                              background: "var(--arm-control)",
                            }}
                          />
                          <div className="nm">reject</div>
                        </div>
                        <div className="seg">
                          <div className="pc">{split.neu}</div>
                          <div
                            className="bar"
                            style={{
                              height: `${Math.max(4, split.neu)}%`,
                              background: "#A797C9",
                            }}
                          />
                          <div className="nm">neutral</div>
                        </div>
                        <div className="seg">
                          <div className="pc">{split.adt}</div>
                          <div
                            className="bar"
                            style={{
                              height: `${Math.max(4, split.adt)}%`,
                              background: "var(--arm-treat)",
                            }}
                          />
                          <div className="nm">adopt</div>
                        </div>
                      </div>
                      <div className="rfoot">
                        reaction split · n={split.tot}{" "}
                        <span className="glyph-hollow">◇</span>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </>
          ) : (
            // Non-complete hero: a quiet field stand-in carrying the live /
            // pending / failed reading state honestly (no fabricated field).
            <div className="fieldwrap" style={{ paddingBottom: 0 }}>
              <div className="field-legend">
                <span className="hi">CH1</span>
                <span className="sep">·</span>
                <span>POPULATION REACTION</span>
                <span className="sep">·</span>
                <span className="unc">
                  <span className="glyph-hollow">◇</span>
                </span>
              </div>
              <div
                style={{
                  minHeight: 320,
                  display: "flex",
                  alignItems: "flex-end",
                  padding: 24,
                }}
              >
                <div className="verdict-figure">
                  <div
                    className={`quiet-head ${
                      status === "failed"
                        ? "failed"
                        : status === "running"
                          ? "running"
                          : "pending"
                    }`}
                    style={{ marginBottom: 16 }}
                  >
                    {status === "running" ? (
                      <>
                        <span className="live-dot" /> LIVE READING · TAKING A
                        READING
                      </>
                    ) : status === "failed" ? (
                      <>▲ RUN FAILED — NO VERDICT</>
                    ) : (
                      <>
                        <span className="glyph-hollow">◇</span> READING IN
                        PROGRESS
                      </>
                    )}
                  </div>
                  <div className="num">
                    <span className="of" style={{ fontSize: 64 }}>
                      ——
                    </span>
                    <span className="of">/ 100</span>
                  </div>
                  <div className="verdict-tag">
                    <span className="vg">◇</span>
                    {verdict.label}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ════ PAGE BODY ════ */}
        <div className="grid">
          <div className="col-main">
            {/* hypothesis header */}
            <section className="panel panel-pad">
              <div className="hcrumb">
                <Link href="/simulations">SIMULATIONS</Link> /{" "}
                <b>SIM-{sim.id.slice(0, 8).toUpperCase()}</b>
              </div>
              <div className="lineage">
                <span className="node">
                  <span
                    className={`sq ${status === "failed" ? "alert" : "fill"}`}
                  />
                  <span className="on">SIMULATED</span>
                </span>
                <span className="rule" />
                <span className="node">
                  <span
                    className={`sq ${status === "complete" ? "fill" : "open"}`}
                  />
                  <span className={status === "complete" ? "on" : "off"}>
                    DECISION
                  </span>
                </span>
                <span className="off">· NO LIVE OUTCOMES IN THIS LINEAGE</span>
              </div>

              {claim ? (
                <div className="hclaim">
                  {/* Headline reads as a complete claim: the change, then the
                      predicted outcome folded in ("→ engagement increases").
                      The separate PREDICT row is gone — it lived here now. */}
                  {claim.lead || claim.outcome ? (
                    <h1 className="hclaim-lead">
                      {claim.lead}
                      {claim.lead && claim.outcome ? (
                        <span className="hclaim-arrow"> → </span>
                      ) : null}
                      {claim.outcome ? (
                        <span className="hclaim-out">{claim.outcome}</span>
                      ) : null}
                    </h1>
                  ) : null}
                  {claim.treatment ? (
                    <div className="hclaim-row">
                      <span className="hk">TREATMENT</span>
                      <span className="hv">{claim.treatment}</span>
                    </div>
                  ) : null}
                  {claim.control ? (
                    <div className="hclaim-row">
                      <span className="hk">CONTROL</span>
                      <span className="hv">{claim.control}</span>
                    </div>
                  ) : null}
                </div>
              ) : (
                <h1
                  className={
                    hypothesis.prose.length > 120 ? "htitle htitle-long" : "htitle"
                  }
                >
                  {hypothesis.prose}
                </h1>
              )}

              {/* verdict chip — never renders without its policy designator
                  (§8.1). Hollow glyph + label; policy tag alongside. */}
              <div className="verdicttag-row">
                <span className="vchip">
                  <span className="vg">◇</span>
                  {verdict.label}
                </span>
                <span className="desig">POLICY {DECISION_POLICY.id}</span>
              </div>

              <div className="whyline">{whyLine}</div>

              {/* #311 / T2 — instrument-scope abstention note. Inspectable named
                  reasons: the withheld verdict always carries WHY. A data
                  condition, NOT an alarm — hairline note, message in ink. */}
              {completeResult?.instrument_scope === "out_of_scope" &&
                (completeResult.out_of_scope_reasons ?? []).length > 0 && (
                  <div className="note">
                    <div className="nh">INSTRUMENT SCOPE — VERDICT WITHHELD</div>
                    <ul>
                      {(completeResult.out_of_scope_reasons ?? []).map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

              {/* #312 / T3 — pre-flight input-lint disclosure (degrade-and-
                  disclose). Does NOT withhold the verdict — a disclosed INPUT
                  limitation alongside the normal reading. */}
              {completeResult?.input_flags &&
                (() => {
                  const flags = completeResult.input_flags;
                  const abstain = flags.state === "abstain";
                  return (
                    <div className="note">
                      <div className="nh">
                        {abstain
                          ? "INPUT LINT — INDETERMINATE, PLEASE CLARIFY"
                          : "INPUT LINT — DISCLOSED LIMITATION"}
                      </div>
                      <ul>
                        {(flags.reasons ?? []).map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                      {(flags.fixes ?? []).length > 0 && (
                        <>
                          <div className="nh" style={{ marginTop: 8 }}>
                            SUGGESTED FIXES
                          </div>
                          <ul>
                            {(flags.fixes ?? []).map((f, i) => (
                              <li key={i}>{f}</li>
                            ))}
                          </ul>
                        </>
                      )}
                    </div>
                  );
                })()}

              {/* telemetry strip */}
              <div className="tele">
                <TeleCell label="MODEL" value={model ? model.label : "—"} />
                <TeleCell label="CAPABILITY" value={hypothesis.capability_name} />
                <TeleCell label="READINGS" value={readingsLabel} />
                <TeleCell label="ARMS" value={armsLabel} />
                <TeleCell
                  label="POPULATION"
                  value={
                    sim.population_size != null
                      ? `${sim.population_size.toLocaleString()} · HAMILTON`
                      : "—"
                  }
                />
                <div className="cell">
                  <div className="k desig desig-sm">STATUS</div>
                  <div className="v">
                    {status.toUpperCase()}
                    {/* §9.5 live carrier — the only resting signal line. */}
                    {status === "running" && (
                      <span aria-hidden className="carrier" />
                    )}
                  </div>
                </div>
              </div>
            </section>

            {/* Failure card */}
            {status === "failed" && (
              <section className="panel panel-pad alert" role="alert">
                <h2 className="sechead" style={{ color: "var(--alert)" }}>
                  SIMULATION FAILED
                </h2>
                <div
                  className="wk-sum mono"
                  style={{ whiteSpace: "pre-wrap" }}
                >
                  {state?.error ?? "Unknown error."}
                </div>
              </section>
            )}

            {/* Zone 2 — glass agreement instrument (live readings only). */}
            {completeResult != null && (
              <GlassInstrument
                sim={sim}
                result={completeResult}
                hypothesis={hypothesis}
                personaCount={personaCount}
                abstained={abstained}
                isAB={isAB}
                pairedN={pairedN}
              />
            )}
            {!terminal && (
              <GlassLive
                done={done}
                total={agentsTotal}
                failed={agentsFailed}
                points={livePoints}
                ticks={liveTicks}
              />
            )}

            {/* Per-metric lift card (#280). */}
            {completeResult != null && <MetricLiftCard result={completeResult} />}

            {/* Run log — honest event feed while running. */}
            {!terminal && (
              <section className="panel panel-pad">
                <div
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    gap: 12,
                    marginBottom: 12,
                  }}
                >
                  <h2 className="sechead" style={{ margin: 0 }}>
                    RUN LOG
                  </h2>
                  {state?.phase && (
                    <span className="desig desig-sm">PHASE: {state.phase}</span>
                  )}
                  {agentsFailed > 0 && (
                    <span
                      className="desig desig-sm"
                      style={{ color: "var(--alert)" }}
                    >
                      {agentsFailed} FAILED
                    </span>
                  )}
                </div>
                {recent.length === 0 ? (
                  <div className="desig desig-sm">AWAITING FIRST EVENT</div>
                ) : (
                  <ul className="runlog">
                    {recent.map((ev, i) => (
                      <li key={`${ev.at}-${i}`}>{describeEvent(ev)}</li>
                    ))}
                  </ul>
                )}
              </section>
            )}

            {/* Degraded A/B notes — gated on sim.arm_split. */}
            {completeResult != null && hasLift && (
              <LiftDegradedNotes result={completeResult} />
            )}

            {completeResult != null && hasLift && (
              <PerArmDetailCard
                treatmentScore={
                  completeResult.treatment_score ?? completeResult.confidence_score
                }
                treatmentCi={completeResult.confidence_score_ci ?? null}
                controlScore={completeResult.control_score ?? null}
                sampledAgentCount={sim.sampled_agent_count ?? null}
                abstained={abstained}
              />
            )}

            {/* Phase 5 #101: cohort banner — only for persona-filtered runs. */}
            {status === "complete" && sim.selected_personas != null && (
              <CohortBanner
                selectedIds={sim.selected_personas}
                agentMeta={agentMeta}
              />
            )}

            {/* Weakness register. */}
            {(status === "complete" || status === "running") && (
              <WeaknessRegister result={completeResult} running={!terminal} />
            )}

            {/* Evidence register (#1 MiroFish-borrow) — provenance + counter-evidence. */}
            {(status === "complete" || status === "running") && (
              <EvidenceRegister result={completeResult} running={!terminal} />
            )}

            {/* Refinement queue. */}
            {completeResult?.refinement_suggestions != null &&
              completeResult.refinement_suggestions.length > 0 && (
                <RefinementQueue
                  suggestions={completeResult.refinement_suggestions}
                />
              )}

            {/* Method card. */}
            {completeResult != null && (
              <MethodCard
                modelId={sim.model_id ?? null}
                hasLift={hasLift}
                abstained={abstained}
              />
            )}

            {/* Cohort register — agents that participated. */}
            {agentIds.length > 0 && (
              <section className="panel panel-pad">
                <h2 className="sechead">
                  COHORT REGISTER — AGENTS THAT PARTICIPATED
                </h2>
                {agentMetaError && (
                  <div className="note alert" role="alert">
                    <p>
                      Persona breakdown failed to load ({agentMetaError}).
                      Showing raw IDs below.
                    </p>
                  </div>
                )}
                {agentMeta == null && !agentMetaError && (
                  <div className="desig desig-sm" style={{ marginBottom: 12 }}>
                    REGISTER PENDING — {agentIds.length} AGENT
                    {agentIds.length === 1 ? "" : "S"} TO JOIN
                  </div>
                )}
                {agentMeta != null ? (
                  <PersonaGroupedAgents agents={agentMeta} />
                ) : (
                  <ul className="cohort-fallback">
                    {agentIds.map((aid) => (
                      <li key={aid}>
                        <Link className="aid" href={`/agents/${aid}`}>
                          {aid.slice(0, 8)}
                        </Link>
                        <span className="afull">{aid}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            )}
          </div>

          {/* ── Zone 3 — inspector rail ──────────────────────────────────── */}
          <InspectorRail
            sim={sim}
            status={status}
            agentMeta={agentMeta}
            personaGroups={personaGroups}
            selectedPersona={selectedPersona}
            onSelectPersona={setSelectedPersona}
            abstained={abstained}
          />
        </div>
      </div>
    </AppShellV2>
  );
}

function TeleCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="cell">
      <div className="k desig desig-sm">{label}</div>
      <div className="v" title={value}>
        {value}
      </div>
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Glass agreement instrument — the big agreement number ±CI + ArmCompare.
// Reproduces GlassPanelComplete's data branches: threshold/margin/policy
// readout (suppressed when abstained), CI clears/below threshold clause,
// paired lift + CI + crosses-zero note, single-arm note. Restyled to the dark
// glass instrument from the mock.
// ───────────────────────────────────────────────────────────────────────────
function GlassInstrument({
  sim,
  result,
  personaCount,
  abstained = false,
  isAB,
  pairedN,
}: {
  sim: Simulation;
  result: SimulationResult;
  hypothesis: Hypothesis;
  personaCount: number | null;
  abstained?: boolean;
  isAB: boolean;
  pairedN: number | null;
}) {
  const score = result.confidence_score;
  const scoreCi = result.confidence_score_ci ?? null;
  const scoreHalf = ciHalf(scoreCi);
  const nReadings = (sim.agent_instance_ids ?? []).length;
  const THRESHOLD = DECISION_POLICY.threshold;

  return (
    <section className="glass">
      <div className="chan-legend">
        <span className="ch">CH1</span>
        <span className="sep">·</span>
        <span>AGREEMENT TRACE</span>
        <span className="sep">·</span>
        <span className="unc">
          <span className="glyph-hollow">◇</span>
        </span>
      </div>
      <div
        className="glassgrid"
        style={isAB ? undefined : { gridTemplateColumns: "1fr" }}
      >
        {/* left: agreement reading */}
        <div className={`glass-cell ${isAB ? "left" : "full"}`}>
          <div className="glass-lab">
            Agreement{" "}
            <span className="sub">— RAW, UNCALIBRATED (LEDGER EMPTY)</span>
          </div>
          <div className="reading-row">
            <span className="reading-num">{fmt1(score)}</span>
            {scoreHalf != null ? (
              <span className="reading-ci">±{fmt1(scoreHalf)}</span>
            ) : (
              <span className="reading-ci glyph-hollow">◇ UNCALIBRATED</span>
            )}
            <span className="stamp hollow">◇</span>
            <span className="reading-unit">AGREEMENT / 100 · SETTLED</span>
          </div>

          {/* Decision-rule readout (§8.1). #311/T2: abstained → NO threshold/
              margin evaluation, the raw agreement still prints. */}
          {abstained ? (
            <div className="axisnote" style={{ marginTop: 16 }}>
              POLICY {DECISION_POLICY.id} WITHHELD — OEC OUTSIDE INSTRUMENT
              SCOPE
              <br />
              RAW AGREEMENT SHOWN; NO THRESHOLD EVALUATION
            </div>
          ) : (
            <div className="kvrow">
              <div className="kv">
                <div className="k">THRESHOLD</div>
                <div className="v">{THRESHOLD} / 100</div>
              </div>
              <div className="kv">
                <div className="k">MARGIN</div>
                <div className="v">
                  {score >= THRESHOLD ? "+" : "−"}
                  {Math.abs(score - THRESHOLD).toFixed(1)}
                </div>
              </div>
              <div className="kv">
                <div className="k">POLICY</div>
                <div className="v">{DECISION_POLICY.id}</div>
              </div>
            </div>
          )}

          <div className="axisnote">
            {scoreCi ? (
              <>
                95% CI [{fmt1(scoreCi[0])}, {fmt1(scoreCi[1])}] —{" "}
                {scoreCi[0] >= THRESHOLD ? (
                  <>
                    LOWER BOUND <span className="clears">CLEARS</span> THRESHOLD{" "}
                    {THRESHOLD}
                  </>
                ) : (
                  <>LOWER BOUND BELOW THRESHOLD {THRESHOLD}</>
                )}{" "}
                · <span className="glyph-hollow">◇</span> UNCALIBRATED
              </>
            ) : (
              <>
                NO INTERVAL RETURNED · <span className="glyph-hollow">◇</span>{" "}
                UNCALIBRATED — the reading carries no ±
              </>
            )}
          </div>
        </div>

        {/* right: paired-arm comparison (A/B only) */}
        {isAB && (
          <div className="glass-cell">
            <div className="glass-lab">
              Paired arms{" "}
              <span className="sub">— TREATMENT − CONTROL (CONF POINTS)</span>
            </div>
            <ArmCompare result={result} pairedN={pairedN} />
          </div>
        )}
      </div>

      <div className="glass-foot">
        <span>
          n = {nReadings} READINGS · {personaCount != null ? personaCount : "—"}{" "}
          PERSONAS · SEED {sim.run_seed ?? "—"} (SINGLE RUN — NO SEED-VARIANCE
          ESTIMATE)
        </span>
        <span className="unc">
          <span className="glyph-hollow">◇</span> UNGRADED — NO LIVE OUTCOMES YET
        </span>
      </div>
    </section>
  );
}

// Paired-arm comparison sub-figure. Reproduces GlassPanelComplete's lift logic:
// liftStat only when the backend computed it (never synthesized from t−c),
// raw Δ-means shown plainly with the PAIRED-LIFT-UNCOMPUTED marker, CI clauses,
// crosses-zero note, paired-bootstrap + seed-variance disclosures.
function ArmCompare({
  result,
  pairedN,
}: {
  result: SimulationResult;
  pairedN: number | null;
}) {
  const c = result.control_score;
  const t = result.treatment_score;
  // Single-arm placeholder (no per-arm scores): say so plainly, mirroring the
  // legacy "LIFT UNCOMPUTABLE / no per-arm output" path.
  if (typeof c !== "number" || typeof t !== "number") {
    const lift = result.lift ?? null;
    const liftSign = lift == null ? "" : lift > 0 ? "+" : lift < 0 ? "−" : "±";
    return (
      <div className="armcompare">
        <div className="bignum muted" style={{ marginTop: 18 }}>
          {lift == null ? "—.—" : `${liftSign}${Math.abs(lift).toFixed(1)}`}
        </div>
        <div className="axisnote" style={{ marginTop: 8 }}>
          LIFT UNCOMPUTABLE — SEE NOTE BELOW THE GLASS
          <br />
          PAIRED BOOTSTRAP OVER PER-AGENT SENTIMENT DELTAS
          <br />
          SEED VARIANCE: SINGLE RUN — NOT ESTIMATED
        </div>
      </div>
    );
  }

  const toX = (sc: number) => Math.max(2, Math.min(98, 5 + (sc / 100) * 90));
  const cx = toX(c);
  const tx = toX(t);
  const liftStat = typeof result.lift === "number" ? result.lift : null;
  const rawDelta = t - c;
  const lh = ciHalf(result.lift_ci);
  const liftCi = result.lift_ci ?? null;
  const liftCrossesZero = liftCi != null && liftCi[0] <= 0 && liftCi[1] >= 0;
  const gapLeft = Math.min(cx, tx);
  const gapW = Math.abs(tx - cx);
  const gapMid = (cx + tx) / 2;

  return (
    <div className="armcompare">
      <div className="arm-track">
        <span className="lab">
          <span className="dot c" />
          CTRL
        </span>
        <div className="arm-plot">
          <div className="strip" />
          <div className="mean c" style={{ left: `${cx}%` }}>
            {/* per-arm AGREEMENT score (0–100), unsigned — only lift/Δ carry a
                sign (codex P2): a signed arm score reads as a delta. */}
            <span className="v">{fmt1(c)}</span>
          </div>
        </div>
      </div>
      <div className="arm-track">
        <span className="lab">
          <span className="dot t" />
          TREAT
        </span>
        <div className="arm-plot">
          <div className="strip" />
          <div className="mean t" style={{ left: `${tx}%` }}>
            {/* per-arm AGREEMENT score (0–100), unsigned (codex P2). */}
            <span className="v">{fmt1(t)}</span>
          </div>
        </div>
      </div>
      <div className="arm-gap">
        <div
          className="bracket"
          style={{ left: `${gapLeft}%`, width: `${Math.max(gapW, 1)}%` }}
        />
        <div className="glab" style={{ left: `${gapMid}%` }}>
          {liftStat != null ? (
            <>
              LIFT {fmtSigned1(liftStat)}{" "}
              {lh != null ? (
                <span className="ci">±{fmt1(lh)}</span>
              ) : (
                <span className="g glyph-hollow">◇ UNCALIBRATED</span>
              )}{" "}
              {lh != null ? <span className="g glyph-hollow">◇</span> : null}
            </>
          ) : (
            <>
              Δ MEANS {fmtSigned1(rawDelta)}{" "}
              <span className="g glyph-hollow">◇ PAIRED LIFT UNCOMPUTED</span>
            </>
          )}
        </div>
      </div>
      <div className="arm-scale desig desig-sm">
        <span>◀ REJECTS</span>
        <span>ADOPTS ▶</span>
      </div>
      <div className="axisnote" style={{ marginTop: 30 }}>
        {liftCi ? (
          <>
            95% CI [{fmtSigned1(liftCi[0])}, {fmtSigned1(liftCi[1])}] ·{" "}
            {liftCi[0] > 0 || liftCi[1] < 0
              ? "CI CLEARS ZERO"
              : "CI STRADDLES ZERO"}{" "}
            ·{" "}
          </>
        ) : null}
        {pairedN != null && pairedN > 0 ? `n = ${pairedN} PAIRED · ` : ""}
        SINGLE RUN
        {liftCrossesZero && (
          <>
            <br />
            CI CROSSES ZERO — NO EFFECT NOT RULED OUT
          </>
        )}
        <br />
        PAIRED BOOTSTRAP OVER PER-AGENT SENTIMENT DELTAS
        <br />
        SEED VARIANCE: SINGLE RUN — NOT ESTIMATED
      </div>
    </div>
  );
}

// Live (non-terminal) glass instrument — §9.7: the trace IS the progress
// indicator (spinners/progress bars are banned). Plots the accumulated live
// readings as they arrive: baseline ticks witness agents completing, the signal
// trace draws the partial-score readings. No settled NUMBER prints until the
// reading settles (§9.1) — the figure stays "——" until terminal, honestly.
function GlassLive({
  done,
  total,
  failed,
  points,
  ticks,
}: {
  done: number;
  total: number;
  failed: number;
  points: TracePoint[];
  ticks: number[];
}) {
  // y maps an agreement score 0..100 onto the viewBox (inverted: 100 = top).
  const thrY = 100 - DECISION_POLICY.threshold;
  const d = points.length
    ? points
        .map(
          (p, i) =>
            `${i === 0 ? "M" : "L"}${(p.x * 100).toFixed(2)} ${(
              100 - p.y
            ).toFixed(2)}`,
        )
        .join(" ")
    : "";
  return (
    <section className="glass">
      <div className="chan-legend">
        <span className="ch">CH1</span>
        <span className="sep">·</span>
        <span>AGREEMENT TRACE — LIVE READING (RAW, UNCALIBRATED)</span>
        <span className="sep">·</span>
        <span className="unc">
          <span className="glyph-hollow">◇</span>
        </span>
      </div>
      <div className="glassgrid" style={{ gridTemplateColumns: "1fr" }}>
        <div className="glass-cell full">
          {/* The live trace — readings plot as poll ticks arrive (§9.7). */}
          <div
            style={{ position: "relative", height: 120, margin: "6px 0 4px" }}
          >
            <svg
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              style={{
                position: "absolute",
                inset: 0,
                width: "100%",
                height: "100%",
                display: "block",
              }}
              aria-hidden
            >
              {/* Threshold reference — instrument, not data. */}
              <line
                x1="0"
                y1={thrY}
                x2="100"
                y2={thrY}
                stroke="var(--console-line)"
                strokeWidth={1}
                strokeDasharray="1.5 1.5"
                vectorEffect="non-scaling-stroke"
              />
              {/* Baseline progress ticks — agents completing; signal is the
                  live carrier. Honest "readings are arriving" signal for the
                  window before any score reading exists. */}
              {ticks.map((t, i) => (
                <line
                  key={`${t}-${i}`}
                  x1={(t * 100).toFixed(2)}
                  y1={100}
                  x2={(t * 100).toFixed(2)}
                  y2={97}
                  stroke="var(--signal)"
                  strokeWidth={1}
                  opacity={0.7}
                  vectorEffect="non-scaling-stroke"
                />
              ))}
              {d !== "" && (
                <>
                  {/* Phosphor underdraw — same path, wide + faint. */}
                  <path
                    d={d}
                    fill="none"
                    stroke="var(--signal)"
                    strokeWidth={5}
                    opacity={0.18}
                    vectorEffect="non-scaling-stroke"
                  />
                  <path
                    d={d}
                    fill="none"
                    stroke="var(--signal)"
                    strokeWidth={2}
                    vectorEffect="non-scaling-stroke"
                  />
                </>
              )}
            </svg>
          </div>
          <div className="reading-row" style={{ marginTop: 6 }}>
            <span className="reading-num muted" aria-label="Reading in progress">
              ——
            </span>
            <span className="reading-unit">
              {d !== "" ? "READING ARRIVING" : "READING IN PROGRESS"}
            </span>
          </div>
          <div className="axisnote" style={{ marginTop: 12 }}>
            {d !== ""
              ? "PARTIAL READINGS PLOT AS THEY ARRIVE — THE SETTLED NUMBER PRINTS AT SCORING END."
              : "AWAITING SCORE READING — PRINTS AT SCORING PHASE. No numbers are shown until the reading settles."}
          </div>
        </div>
      </div>
      <div className="glass-foot">
        <span>
          n = {total > 0 ? `${done} OF ${total}` : "—"} READINGS
          {failed > 0 ? ` · ${failed} FAILED` : ""}
        </span>
        <span className="unc">
          <span className="glyph-hollow">◇</span> UNGRADED — NO LIVE OUTCOMES YET
        </span>
      </div>
    </section>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Degraded A/B notes — paper notes below the glass (codex R1-P2 / R4-P2).
// Logic byte-identical to legacy LiftDegradedNotes.
// ───────────────────────────────────────────────────────────────────────────
function LiftDegradedNotes({ result }: { result: SimulationResult }) {
  const lift = result.lift ?? null;
  const pairedN = result.lift_paired_n ?? null;
  const unpairedTreatment = result.lift_unpaired_treatment ?? 0;
  const unpairedControl = result.lift_unpaired_control ?? 0;
  const sentimentFailureDrops = result.lift_sentiment_failure_drops ?? 0;
  const anyDrops =
    unpairedTreatment > 0 || unpairedControl > 0 || sentimentFailureDrops > 0;
  const noPairs = lift == null;
  if (!noPairs && !anyDrops) return null;

  return (
    <section className="panel" style={{ padding: "14px 18px" }}>
      {noPairs && pairedN != null && (
        <div className="note alert">
          <p>
            <strong>A/B run completed but lift is uncomputable.</strong> No
            matched (treatment, control) pairs were available — every agent in
            at least one arm was dropped (sentiment classification failure, no
            matching paired-sampling key, or one arm produced zero usable
            reactions). The treatment arm&rsquo;s confidence score is shown in
            the per-arm detail, but it is NOT a lift measurement — it&rsquo;s
            only the treatment arm in isolation. See the drop counters for which
            dropout caused this.
          </p>
        </div>
      )}
      {noPairs && pairedN == null && (
        <div className="note alert">
          <p>
            <strong>A/B run did not produce per-arm scoring output.</strong> The
            simulation finished but the backend returned a single-arm
            placeholder result — usually because no agents in either arm
            completed successfully (LLM outage, timeouts, or every agent
            erroring). Re-run the simulation, or check the run state for the
            failure reason.
          </p>
        </div>
      )}
      {anyDrops && (
        <div
          className="bodytext"
          style={{
            marginTop: noPairs ? 12 : 0,
            paddingTop: noPairs ? 12 : 0,
            borderTop: noPairs ? "1px solid var(--console-line)" : undefined,
            fontSize: 12,
          }}
        >
          Dropped from pairing:
          {unpairedTreatment > 0 && <> {unpairedTreatment} unpaired treatment;</>}
          {unpairedControl > 0 && <> {unpairedControl} unpaired control;</>}
          {sentimentFailureDrops > 0 && (
            <>
              {" "}
              {sentimentFailureDrops} sentiment classification failure
              {sentimentFailureDrops === 1 ? "" : "s"};
            </>
          )}{" "}
          excluded from the paired-delta statistic.
        </div>
      )}
    </section>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Per-metric lift card (#280). Logic byte-identical to legacy MetricLiftCard.
// ───────────────────────────────────────────────────────────────────────────
function MetricLiftCard({ result }: { result: SimulationResult }) {
  const metricName = result.metric_name ?? null;
  if (metricName == null) return null;

  const label = metricDisplayLabel(metricName);
  const liftPp = result.metric_lift_pp ?? null;
  const ciPp = result.metric_lift_ci_pp ?? null;
  const pairedN = result.metric_lift_paired_n ?? null;
  const regime = result.metric_regime ?? null;
  const relative = result.metric_lift_relative ?? null;
  const calibrated = result.metric_lift_calibrated === true;
  const unblindedFallback = result.metric_lift_unblinded_fallback === true;
  const paraphraseUnstable = result.metric_lift_paraphrase_unstable === true;

  const computable = liftPp != null && pairedN != null && pairedN > 0;
  const sign = liftPp == null ? "" : liftPp > 0 ? "+" : liftPp < 0 ? "−" : "±";

  return (
    <section className="panel panel-pad">
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 10,
          flexWrap: "wrap",
          marginBottom: 6,
        }}
      >
        <div className="desig">{label.toUpperCase()} LIFT — NATIVE UNITS</div>
        <div className="desig desig-sm">ALONGSIDE SENTIMENT AGREEMENT</div>
      </div>

      {computable ? (
        <>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: 10,
              margin: "10px 0 4px",
            }}
          >
            <div
              className="bignum"
              aria-label={`${label} lift ${
                liftPp! >= 0 ? "plus" : "minus"
              } ${Math.abs(liftPp!).toFixed(1)} percentage points`}
            >
              {sign}
              {Math.abs(liftPp!).toFixed(1)}
            </div>
            <div className="desig desig-sm">PP (PAIRED T−C)</div>
          </div>

          <div className="axisnote">
            {ciPp != null &&
              `95% CI [${ciPp[0] >= 0 ? "+" : "−"}${Math.abs(ciPp[0]).toFixed(
                1,
              )}, ${ciPp[1] >= 0 ? "+" : "−"}${Math.abs(ciPp[1]).toFixed(1)}] PP`}
            {ciPp != null && pairedN != null && " · "}
            {pairedN != null && `n = ${pairedN} PAIRED`}
            {regime != null && (
              <>
                <br />
                REGIME: {regime}
              </>
            )}
          </div>

          {/* The honesty statement — VERBATIM. */}
          {relative != null && relative.trim() !== "" && (
            <p className="bodytext" style={{ marginTop: 12 }}>
              {relative}
            </p>
          )}

          {/* Magnitude caveat — gated on !calibrated (#222). */}
          {!calibrated && (
            <p
              className="bodytext"
              style={{ marginTop: 8, fontSize: 12 }}
            >
              Uncalibrated — read this lift as rank and direction, not as a
              calibrated effect size. The magnitude is not yet mapped to a
              real-world scale (calibration ledger empty).
            </p>
          )}

          {/* Degraded-confidence warnings. */}
          {(unblindedFallback || paraphraseUnstable) && (
            <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
              {unblindedFallback && (
                <div className="note warn" role="note">
                  <p>
                    <strong>Unblinded fallback.</strong> At least one treatment
                    agent saw the unblinded prompt — the proposed change had no
                    faithful standalone view to blind against. The lift may carry
                    demand-characteristic bias; treat the direction as the
                    signal.
                  </p>
                </div>
              )}
              {paraphraseUnstable && (
                <div className="note warn" role="note">
                  <p>
                    <strong>Paraphrase-unstable.</strong> At least one
                    identity&rsquo;s metric propensity moved materially across
                    the question paraphrases — its answer was wording-driven. The
                    measured lift is sensitive to prompt phrasing.
                  </p>
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        <div className="bodytext" style={{ marginTop: 8 }}>
          The {label.toLowerCase()} metric was requested, but no paired lift
          could be computed — every agent in at least one arm was dropped (an
          empty arm, or all turn-2 decision elicitations failed). The sentiment
          agreement reading above is unaffected; re-run to collect a paired{" "}
          {label.toLowerCase()} delta.
        </div>
      )}
    </section>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Weakness register — bare freq bars + CI band, restyled to dark spread tokens.
// Logic byte-identical to legacy WeaknessRegister/RegisterFreqBar.
// ───────────────────────────────────────────────────────────────────────────
function RegisterFreqBar({
  frequency,
  ciLow,
  ciHigh,
}: {
  frequency: number;
  ciLow: number;
  ciHigh: number;
}) {
  const { v, lo, hi } = _safeRange(frequency, ciLow, ciHigh, 0, 1);
  return (
    <div
      className="freqbar"
      role="img"
      aria-label={`Frequency ${(v * 100).toFixed(0)}% with 95% CI from ${(lo * 100).toFixed(0)}% to ${(hi * 100).toFixed(0)}%`}
    >
      <div className="base" />
      <div
        className="ci"
        style={{
          left: `${lo * 100}%`,
          width: `${Math.max(0, (hi - lo) * 100)}%`,
        }}
      />
      <div className="val" style={{ width: `${v * 100}%` }} />
    </div>
  );
}

function WeaknessRegister({
  result,
  running,
}: {
  result: SimulationResult | null;
  running: boolean;
}) {
  const weaknesses: Weakness[] = result?.weaknesses ?? [];
  return (
    <section className="panel panel-pad">
      <div className="wk-headrow">
        <span>WEAKNESS REGISTER — FINDING</span>
        <span>FREQUENCY (95% CI)</span>
      </div>
      {running ? (
        <div className="wk-sum" style={{ paddingTop: 14, color: "var(--text-mut)" }}>
          REGISTER PENDING — FINDINGS PRINT AS READINGS COMPLETE
        </div>
      ) : weaknesses.length === 0 ? (
        <div className="wk-sum" style={{ paddingTop: 14, color: "var(--text-mut)" }}>
          NO WEAKNESS FINDINGS — NO AGENTS FLAGGED THIS RUN
        </div>
      ) : (
        weaknesses.map((w, idx) => {
          const hasFreq =
            w.frequency != null && w.ci_low != null && w.ci_high != null;
          return (
            <div className="wk-row" key={idx}>
              <div style={{ minWidth: 0 }}>
                <div className="wk-name">
                  {formatCategory(w.category)}
                  <WeaknessCategoryInfo category={w.category} />
                </div>
                <div className="wk-sum">{w.summary}</div>
              </div>
              <div>
                {hasFreq ? (
                  <>
                    <RegisterFreqBar
                      frequency={w.frequency!}
                      ciLow={w.ci_low!}
                      ciHigh={w.ci_high!}
                    />
                    <div className="freqlabel">
                      {(w.frequency! * 100).toFixed(0)}%{" "}
                      <span className="ci">
                        [{(w.ci_low! * 100).toFixed(0)}–
                        {(w.ci_high! * 100).toFixed(0)}%]
                      </span>
                    </div>
                  </>
                ) : (
                  <div className="freqlabel" style={{ color: "var(--text-mut)" }}>
                    — NOT MEASURED
                  </div>
                )}
              </div>
            </div>
          );
        })
      )}
    </section>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Evidence register (#1 MiroFish-borrow). Renders result.evidence_graph as an
// instrument register, NOT a force graph (the data has no real edge topology —
// a node-cloud would manufacture structure, DESIGN.md §10). Counter-evidence
// (contradicts / guardrail) is ordered first and weighted in ink so a positive
// verdict can't rest silently on supports_change alone — the prior-echo defense.
// Reuses the weakness register's classes: no new color, no pills, no graph dep.
// ───────────────────────────────────────────────────────────────────────────
type EvidenceRelation = NonNullable<EvidenceEdge["relation"]>;

const EVIDENCE_RELATION_LABEL: Record<EvidenceRelation, string> = {
  contradicts_change: "CONTRADICTS",
  guardrail_risk: "GUARDRAIL RISK",
  supports_change: "SUPPORTS",
  weak_or_inferred: "WEAK / INFERRED",
};
// Counter-evidence first — surfacing it beside the verdict is the whole point.
const EVIDENCE_RELATION_ORDER: EvidenceRelation[] = [
  "contradicts_change",
  "guardrail_risk",
  "supports_change",
  "weak_or_inferred",
];

function EvidenceRegister({
  result,
  running,
}: {
  result: SimulationResult | null;
  running: boolean;
}) {
  const graph = result?.evidence_graph ?? null;
  const nodeById = new Map((graph?.nodes ?? []).map((n) => [n.id, n]));
  const edges = [...(graph?.edges ?? [])].sort(
    (a, b) =>
      EVIDENCE_RELATION_ORDER.indexOf(a.relation) -
      EVIDENCE_RELATION_ORDER.indexOf(b.relation),
  );
  return (
    <section className="panel panel-pad">
      <div className="wk-headrow">
        <span>EVIDENCE REGISTER — WHAT THE READING RESTS ON</span>
        <span>RELATION · CONFIDENCE</span>
      </div>
      {running ? (
        <div className="wk-sum" style={{ paddingTop: 14, color: "var(--text-mut)" }}>
          REGISTER PENDING — EVIDENCE PRINTS AS READINGS COMPLETE
        </div>
      ) : edges.length === 0 ? (
        <div className="wk-sum" style={{ paddingTop: 14, color: "var(--text-mut)" }}>
          NO EVIDENCE GRAPH — RUN PREDATES THIS INSTRUMENT
        </div>
      ) : (
        edges.map((e, idx) => {
          const node = nodeById.get(e.source);
          const counter =
            e.relation === "contradicts_change" ||
            e.relation === "guardrail_risk";
          const provN = e.provenance?.length ?? 0;
          return (
            <div className="wk-row" key={idx}>
              <div style={{ minWidth: 0 }}>
                <div className="wk-name">{node?.label ?? e.source}</div>
                <div className="wk-sum">
                  {e.detail ?? node?.detail ?? "—"}
                  {provN > 0 ? (
                    <span style={{ color: "var(--text-mut)" }}>
                      {" "}
                      · {provN} agent{provN === 1 ? "" : "s"}
                    </span>
                  ) : null}
                </div>
              </div>
              <div>
                <div
                  className="freqlabel"
                  style={{
                    color: counter ? "var(--text-hi)" : "var(--text)",
                    fontWeight: counter ? 600 : 400,
                    letterSpacing: ".04em",
                  }}
                >
                  {EVIDENCE_RELATION_LABEL[e.relation]}
                  {e.confidence != null ? (
                    <span className="ci" style={{ color: "var(--text-mut)" }}>
                      {" "}
                      · {(e.confidence * 100).toFixed(0)}%
                    </span>
                  ) : null}
                </div>
              </div>
            </div>
          );
        })
      )}
    </section>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Refinement queue — opens a fresh hypothesis (no prefill contract).
// Logic byte-identical to legacy RefinementQueue.
// ───────────────────────────────────────────────────────────────────────────
function RefinementQueue({ suggestions }: { suggestions: string[] }) {
  return (
    <section className="panel panel-pad">
      <h2 className="sechead tight">REFINEMENT QUEUE</h2>
      <p
        className="bodytext"
        style={{ fontSize: 12.5, margin: "0 0 14px" }}
      >
        Queueing opens a fresh hypothesis in the wizard — suggestions are not
        prefilled. Copy the wording you want to keep.
      </p>
      {suggestions.map((s, i) => (
        <div className="refrow" key={i}>
          <div className="txt">{s}</div>
          <Link href="/simulations/new" className="chiplink">
            QUEUE AS HYPOTHESIS →
          </Link>
        </div>
      ))}
    </section>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Method card — how the reading is computed. Logic byte-identical to legacy.
// ───────────────────────────────────────────────────────────────────────────
function MethodCard({
  modelId,
  hasLift,
  abstained = false,
}: {
  modelId: string | null;
  hasLift: boolean;
  abstained?: boolean;
}) {
  const model = modelDisplay(modelId);
  const modelBody =
    model == null
      ? "Not tracked for this legacy run. New simulations store the selected model so comparisons can account for model variance."
      : `Ran on ${model.label} (${model.provider}). Reactions, classifiers, and lift reflect this model; comparing runs across models should be read as model variance, not only product variance.`;
  const rows: Array<{ k: string; v: string }> = [
    {
      k: "AGREEMENT",
      v: "Confidence-weighted mean of per-agent sentiment, shrunk toward neutral (Bayesian), penalized by weakness share, scaled 0–100. Raw simulation reading — no live-outcome calibration has been applied (ledger empty).",
    },
    {
      k: "INTERVAL",
      v: "Bootstrap percentile interval over agents; deterministic for a given run seed.",
    },
    ...(hasLift
      ? [
          {
            k: "LIFT",
            v: "Paired bootstrap over per-agent sentiment deltas (treatment − control), in confidence points. Unpaired or unclassifiable agents are dropped from the statistic and counted in the drop note.",
          },
        ]
      : []),
    {
      k: "DECISION RULE",
      v: abstained
        ? `${DECISION_POLICY.id} WITHHELD — the OEC falls outside this instrument's scope, so the ship/no-ship rubric is not applied. Raw readings are shown without threshold evaluation.`
        : `${DECISION_POLICY.id} — ${DECISION_POLICY.rule}. Display rubric applied by this page; the API does not return a policy object.`,
    },
    { k: "MODEL", v: modelBody },
  ];
  return (
    <section className="panel panel-pad">
      <h2 className="sechead">METHOD — HOW THIS READING IS COMPUTED</h2>
      {rows.map((r) => (
        <div className="method-row" key={r.k}>
          <span className="k">{r.k}</span>
          <span className="v">{r.v}</span>
        </div>
      ))}
    </section>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Inspector rail — persona readings + pinned quote + provenance + artifacts.
// Logic byte-identical to legacy InspectorRail.
// ───────────────────────────────────────────────────────────────────────────
function InspectorRail({
  sim,
  status,
  agentMeta,
  personaGroups,
  selectedPersona,
  onSelectPersona,
  abstained = false,
}: {
  sim: Simulation;
  status: SimulationStatus;
  agentMeta: AgentRow[] | null;
  personaGroups: PersonaGroup[] | null;
  selectedPersona: string | null;
  onSelectPersona: (pid: string) => void;
  abstained?: boolean;
}) {
  const isAbMode = agentMeta != null && agentMeta.some((a) => a.arm != null);
  const active =
    personaGroups != null && personaGroups.length > 0
      ? (personaGroups.find((g) => g.pid === selectedPersona) ?? personaGroups[0])
      : null;
  const activeQuote =
    active != null
      ? pickGroupQuote(
          isAbMode ? active.agents.filter((a) => a.arm === "treatment") : active.agents,
        )
      : null;
  const activeTreatmentN =
    active != null ? active.agents.filter((a) => a.arm === "treatment").length : 0;
  const activeControlN =
    active != null ? active.agents.filter((a) => a.arm === "control").length : 0;
  const model = modelDisplay(sim.model_id ?? null);
  const stimulus = [
    "PROSE",
    sim.hypothesis.proposed_prd ? "+ PRD" : null,
    sim.hypothesis.proposed_figma ? "+ FIGMA" : null,
  ]
    .filter(Boolean)
    .join(" ");

  const provRows: Array<{ k: string; v: React.ReactNode }> = [
    { k: "RUN", v: sim.id.slice(0, 8).toUpperCase() },
    { k: "CREATED", v: formatDateTime(sim.created_at) },
    { k: "CAPABILITY", v: sim.hypothesis.capability_name },
    { k: "PERSONA PACK", v: sim.persona_pack_version },
    { k: "FEATURE PACK", v: sim.feature_pack_version },
    { k: "STIMULUS", v: stimulus },
    {
      k: "COHORT",
      v:
        sim.selected_personas != null
          ? `FILTERED — ${sim.selected_personas.length} PERSONA${
              sim.selected_personas.length === 1 ? "" : "S"
            }`
          : "FULL PACK",
    },
    {
      k: "POPULATION",
      v:
        sim.population_size != null
          ? `${sim.population_size.toLocaleString()} · HAMILTON`
          : "—",
    },
    {
      k: "SAMPLED",
      v:
        sim.sampled_agent_count != null
          ? `${sim.sampled_agent_count}${sim.arm_split != null ? " PER ARM" : " AGENTS"}`
          : "—",
    },
    { k: "SEED", v: sim.run_seed != null ? `${sim.run_seed}` : "—" },
    { k: "MODEL", v: model ? model.label : "—" },
    {
      k: "POLICY",
      v: abstained
        ? `${DECISION_POLICY.id} WITHHELD (OEC OUT OF SCOPE)`
        : `${DECISION_POLICY.id} (DISPLAY RUBRIC)`,
    },
    { k: "GRADED", v: "NOT YET — LEDGER EMPTY" },
  ];

  return (
    <aside className="inspector">
      <h2 className="sechead tight">PERSONA READINGS</h2>
      {personaGroups == null ? (
        <div className="desig desig-sm" style={{ marginBottom: 16 }}>
          {status === "failed" ? "NO READINGS — RUN FAILED" : "REGISTER PENDING"}
        </div>
      ) : personaGroups.length === 0 ? (
        <div className="desig desig-sm" style={{ marginBottom: 16 }}>
          NO AGENTS IN THIS RUN
        </div>
      ) : (
        <div style={{ marginBottom: 16 }}>
          {personaGroups.map((g) => {
            const isActive = active != null && g.pid === active.pid;
            const counts = sentimentCounts(g.agents);
            return (
              <button
                key={g.pid}
                type="button"
                onClick={() => onSelectPersona(g.pid)}
                aria-pressed={isActive}
                className="pbtn"
              >
                <span className="pn">{g.persona_name}</span>
                <span className="pc">
                  +{counts.positive} ~{counts.neutral} −{counts.negative}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {active != null && (
        <div className="quotewell">
          <div className="ql">
            {isAbMode ? "PINNED QUOTE — TREATMENT ARM" : "PINNED QUOTE"}
          </div>
          {activeQuote != null ? (
            <div className="qt" style={{ marginBottom: 8 }}>
              &ldquo;{activeQuote}&rdquo;
            </div>
          ) : (
            <div className="qm" style={{ marginBottom: 8 }}>
              NO QUOTE CAPTURED FOR THIS PERSONA
            </div>
          )}
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {isAbMode ? (
              <>
                <RailChatLink
                  href={`/simulations/${sim.id}/personas/${active.pid}?arm=treatment`}
                  label="T →"
                  aria={
                    activeTreatmentN > 0
                      ? `Open treatment persona-group chat with ${active.persona_name}`
                      : `Treatment persona-group chat unavailable for ${active.persona_name}`
                  }
                  enabled={activeTreatmentN > 0}
                />
                <RailChatLink
                  href={`/simulations/${sim.id}/personas/${active.pid}?arm=control`}
                  label="C →"
                  aria={
                    activeControlN > 0
                      ? `Open control persona-group chat with ${active.persona_name}`
                      : `Control persona-group chat unavailable for ${active.persona_name}`
                  }
                  enabled={activeControlN > 0}
                />
              </>
            ) : (
              <RailChatLink
                href={`/simulations/${sim.id}/personas/${active.pid}`}
                label="GROUP CHAT →"
                aria={`Open persona-group chat with ${active.persona_name}`}
              />
            )}
          </div>
        </div>
      )}

      <h2 className="sechead tight">PROVENANCE</h2>
      <dl className="prov">
        {provRows.map((r) => (
          <div className="provrow" key={r.k}>
            <dt>{r.k}</dt>
            <dd>{r.v}</dd>
          </div>
        ))}
      </dl>

      <h2 className="sechead tight">ARTIFACTS</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <a
          className="artlink"
          href={`${API_BASE}/simulations/${sim.id}`}
          target="_blank"
          rel="noreferrer"
        >
          RESULT JSON →
        </a>
        <a
          className="artlink"
          href={`${API_BASE}/simulations/${sim.id}/agents`}
          target="_blank"
          rel="noreferrer"
        >
          AGENTS JSON →
        </a>
      </div>
    </aside>
  );
}

function RailChatLink({
  href,
  label,
  aria,
  enabled = true,
}: {
  href: string;
  label: string;
  aria: string;
  enabled?: boolean;
}) {
  if (!enabled) {
    return (
      <span
        className="chiplink disabled"
        aria-label={aria}
        title="No agents are available in this arm for the completed run."
      >
        {label}
      </span>
    );
  }
  return (
    <Link href={href} aria-label={aria} className="chiplink">
      {label}
    </Link>
  );
}

function sentimentCounts(agents: AgentRow[]): {
  positive: number;
  neutral: number;
  negative: number;
} {
  const counts = { positive: 0, neutral: 0, negative: 0 };
  for (const a of agents) {
    if (a.sentiment != null) counts[a.sentiment] += 1;
  }
  return counts;
}

type PersonaGroup = { pid: string; persona_name: string; agents: AgentRow[] };

function groupAgents(agents: AgentRow[]): PersonaGroup[] {
  const order: string[] = [];
  const byPersona = new Map<string, PersonaGroup>();
  for (const a of agents) {
    if (!byPersona.has(a.persona_id)) {
      byPersona.set(a.persona_id, {
        pid: a.persona_id,
        persona_name: a.persona_name,
        agents: [],
      });
      order.push(a.persona_id);
    }
    byPersona.get(a.persona_id)!.agents.push(a);
  }
  return order.map((pid) => byPersona.get(pid)!);
}

// ───────────────────────────────────────────────────────────────────────────
// Cohort banner — persona-filtered runs. Logic byte-identical to legacy.
// ───────────────────────────────────────────────────────────────────────────
function CohortBanner({
  selectedIds,
  agentMeta,
}: {
  selectedIds: string[];
  agentMeta: AgentRow[] | null;
}) {
  const idToName = new Map<string, string>();
  if (agentMeta != null) {
    for (const a of agentMeta) {
      if (!idToName.has(a.persona_id)) {
        idToName.set(a.persona_id, a.persona_name);
      }
    }
  }
  const names = selectedIds.map((pid) => idToName.get(pid) ?? pid);
  return (
    <section className="note warn" style={{ marginTop: 0 }}>
      <p>
        <strong>Persona-filtered run:</strong> this simulation was scoped to{" "}
        {selectedIds.length} persona
        {selectedIds.length === 1 ? "" : "s"}: {names.join(", ")}. Lift / scores
        are for the selected cohort, not the full Persona Pack — re-run with all
        personas to compare against the unfiltered baseline.
      </p>
    </section>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Per-arm detail card. Logic byte-identical to legacy PerArmDetailCard.
// ───────────────────────────────────────────────────────────────────────────
function PerArmDetailCard({
  treatmentScore,
  treatmentCi,
  controlScore,
  sampledAgentCount,
  abstained = false,
}: {
  treatmentScore: number;
  treatmentCi: [number, number] | null;
  controlScore: number | null;
  sampledAgentCount: number | null;
  abstained?: boolean;
}) {
  return (
    <section className="panel panel-pad">
      <div className="desig" style={{ marginBottom: 6 }}>
        PER-ARM DETAIL
      </div>
      <div className="bodytext" style={{ marginBottom: 14 }}>
        These diagnostic scores are not directly comparable. The treatment arm
        includes weakness penalties for the proposed change; the control arm is
        scored as the status-quo product and skips weakness classification. Use
        the paired lift on the glass for the apples-to-apples A/B read.
      </div>
      <div className="armtiles">
        <ArmScoreTile
          label="Treatment confidence"
          description="Proposed change, including weakness penalties."
          score={treatmentScore}
          ci={treatmentCi}
          sampledAgentCount={sampledAgentCount}
        />
        <ArmScoreTile
          label="Control status-quo score"
          description="Current product TODAY; weakness classifier is not run."
          score={controlScore}
          ci={null}
          sampledAgentCount={null}
        />
      </div>
      <div
        className="bodytext"
        style={{
          marginTop: 12,
          paddingTop: 12,
          borderTop: "1px solid var(--console-line)",
          fontSize: 12,
        }}
      >
        {abstained ? (
          <>
            Policy {DECISION_POLICY.id} is withheld for this run: the OEC is
            outside a first-exposure single-session panel&rsquo;s resolving
            power, so the treatment confidence score is not evaluated for a ship
            / no-ship decision. See the instrument-scope note above.
          </>
        ) : (
          <>
            Policy {DECISION_POLICY.id} still applies to the treatment confidence
            score: &ge;{DECISION_POLICY.threshold} = ship candidate; below =
            needs refinement.
          </>
        )}
      </div>
    </section>
  );
}

function ArmScoreTile({
  label,
  description,
  score,
  ci,
  sampledAgentCount,
}: {
  label: string;
  description: string;
  score: number | null;
  ci: [number, number] | null;
  sampledAgentCount: number | null;
}) {
  return (
    <div className="armtile" style={{ padding: "4px 0" }}>
      <div className="bodytext" style={{ fontSize: 12, marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
        <div className={`num${score == null ? " muted" : ""}`}>
          {score == null ? "—.—" : Math.round(score)}
        </div>
        {ci != null && (
          <ConfidenceIntervalLabel
            ciLow={ci[0]}
            ciHigh={ci[1]}
            sampledAgentCount={sampledAgentCount}
          />
        )}
      </div>
      <div className="bodytext" style={{ marginTop: 8, fontSize: 12 }}>
        {description}
      </div>
    </div>
  );
}

// Shared sanitizer for CI inputs. Verbatim from legacy.
function _safeRange(
  value: number,
  low: number,
  high: number,
  min: number,
  max: number,
): { v: number; lo: number; hi: number } {
  const clamp = (n: number, fallback: number) =>
    Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : fallback;
  const v = clamp(value, min);
  let lo = clamp(low, min);
  let hi = clamp(high, max);
  if (lo > hi) {
    [lo, hi] = [hi, lo];
  }
  return { v, lo, hi };
}

const _CI_COLLAPSE_THRESHOLD = 0.2;

function ConfidenceIntervalLabel({
  ciLow,
  ciHigh,
  sampledAgentCount,
}: {
  ciLow: number;
  ciHigh: number;
  sampledAgentCount: number | null;
}) {
  const isCollapsed = ciHigh - ciLow < _CI_COLLAPSE_THRESHOLD;
  if (isCollapsed) {
    return (
      <div className="bodytext" style={{ fontSize: 12 }}>
        Narrow interval
        {sampledAgentCount != null ? ` (n=${sampledAgentCount})` : ""}
      </div>
    );
  }
  return (
    <div className="bodytext" style={{ fontSize: 12 }}>
      95% CI: [{ciLow.toFixed(1)} &ndash; {ciHigh.toFixed(1)}]
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Cohort register — persona-grouped agents (interactive). Logic byte-identical
// to legacy PersonaGroupedAgents / PersonaGroupRow.
// ───────────────────────────────────────────────────────────────────────────
type Arm = "treatment" | "control";

type AgentRow = {
  agent_id: string;
  persona_id: string;
  persona_name: string;
  sentiment: "positive" | "neutral" | "negative" | null;
  sentiment_confidence: number | null;
  top_quote: string | null;
  arm: Arm | null;
};

function PersonaGroupedAgents({ agents }: { agents: AgentRow[] }) {
  const groups = groupAgents(agents);
  const isAbMode = agents.some((a) => a.arm != null);

  return (
    <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {groups.map((g) => (
        <PersonaGroupRow
          key={g.pid}
          personaId={g.pid}
          personaName={g.persona_name}
          agents={g.agents}
          isAbMode={isAbMode}
        />
      ))}
    </ul>
  );
}

function PersonaGroupRow({
  personaId,
  personaName,
  agents,
  isAbMode,
}: {
  personaId: string;
  personaName: string;
  agents: AgentRow[];
  isAbMode: boolean;
}) {
  const params = useParams<{ id: string }>();
  const simId = params?.id ?? "";
  const [open, setOpen] = useState(false);
  const listId = `persona-agents-${personaId}`;

  const groupSentiment = aggregateSentiment(agents);
  const treatmentAgents = agents.filter((a) => a.arm === "treatment");
  const controlAgents = agents.filter((a) => a.arm === "control");
  const untaggedAgents = agents.filter((a) => a.arm == null);
  const treatmentSentiment = aggregateSentiment(treatmentAgents);
  const groupQuote = pickGroupQuote(isAbMode ? treatmentAgents : agents);
  const controlSentiment = aggregateSentiment(controlAgents);

  return (
    <li className="prow">
      <div className="prow-head">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-controls={listId}
          className="prow-toggle"
        >
          <span aria-hidden className="prow-caret">
            {open ? "▾" : "▸"}
          </span>
          <span className="prow-name">{personaName}</span>
          <span className="prow-count">
            &times; {agents.length} agent{agents.length === 1 ? "" : "s"}
          </span>
          {isAbMode ? (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                flex: "0 0 auto",
              }}
            >
              <span aria-hidden className="armletter" title="Treatment arm">
                T
              </span>
              <SentimentChip
                sentiment={treatmentSentiment.label}
                intensity={treatmentSentiment.intensity}
              />
              <span
                aria-hidden
                className="armletter"
                title="Control arm"
                style={{ marginLeft: 4 }}
              >
                C
              </span>
              <SentimentChip
                sentiment={controlSentiment.label}
                intensity={controlSentiment.intensity}
              />
            </span>
          ) : (
            <SentimentChip
              sentiment={groupSentiment.label}
              intensity={groupSentiment.intensity}
            />
          )}
          <span className="prow-pid">{personaId}</span>
        </button>
        {isAbMode ? (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              flex: "0 0 auto",
              whiteSpace: "nowrap",
            }}
          >
            <ArmChatLink
              simId={simId}
              personaId={personaId}
              personaName={personaName}
              arm="treatment"
              enabled={treatmentAgents.length > 0}
            />
            <ArmChatLink
              simId={simId}
              personaId={personaId}
              personaName={personaName}
              arm="control"
              enabled={controlAgents.length > 0}
            />
          </span>
        ) : (
          <Link
            href={`/simulations/${simId}/personas/${personaId}`}
            aria-label={`Open persona-group chat with ${personaName}`}
            className="chiplink"
          >
            CHAT →
          </Link>
        )}
      </div>
      {groupQuote && (
        <TopQuoteLine text={groupQuote} armLabel={isAbMode ? "treatment" : null} />
      )}
      {open &&
        (isAbMode ? (
          <div id={listId} className="subgroup">
            <ArmAgentSubList label="Treatment" agents={treatmentAgents} />
            <ArmAgentSubList label="Control" agents={controlAgents} />
            {untaggedAgents.length > 0 && (
              <ArmAgentSubList label="Untagged" agents={untaggedAgents} />
            )}
          </div>
        ) : (
          <ul id={listId} className="subgroup" style={{ listStyle: "none", margin: 0 }}>
            {agents.map((a) => (
              <AgentLi key={a.agent_id} agent={a} />
            ))}
          </ul>
        ))}
    </li>
  );
}

function ArmChatLink({
  simId,
  personaId,
  personaName,
  arm,
  enabled,
}: {
  simId: string;
  personaId: string;
  personaName: string;
  arm: Arm;
  enabled: boolean;
}) {
  const isTreatment = arm === "treatment";
  const label = isTreatment ? "T →" : "C →";
  const armName = isTreatment ? "treatment" : "control";

  if (!enabled) {
    return (
      <span
        className="chiplink disabled"
        aria-label={`${armName} persona-group chat unavailable for ${personaName}`}
        title={`No ${armName} agents are available for this persona in the completed run.`}
      >
        {label}
      </span>
    );
  }

  return (
    <Link
      href={`/simulations/${simId}/personas/${personaId}?arm=${arm}`}
      aria-label={`Open ${armName} persona-group chat with ${personaName}`}
      className="chiplink"
    >
      {label}
    </Link>
  );
}

function AgentLi({ agent: a }: { agent: AgentRow }) {
  return (
    <li className="alirow" style={{ listStyle: "none" }}>
      <div className="alihead">
        <Link className="aliid" href={`/agents/${a.agent_id}`}>
          {a.agent_id.slice(0, 8)}
        </Link>
        <SentimentChip
          sentiment={a.sentiment}
          intensity={a.sentiment_confidence ?? null}
        />
        <span style={{ flex: 1 }} />
        <Link
          className="chiplink"
          href={`/agents/${a.agent_id}`}
          aria-label={`Open individual chat with ${a.agent_id}`}
        >
          CHAT 1:1 →
        </Link>
      </div>
      {a.top_quote && <TopQuoteLine text={a.top_quote} />}
    </li>
  );
}

function ArmAgentSubList({
  label,
  agents,
}: {
  label: "Treatment" | "Control" | "Untagged";
  agents: AgentRow[];
}) {
  if (agents.length === 0) {
    return (
      <div style={{ paddingTop: 6, paddingBottom: 4 }}>
        <div className="subhead" style={{ border: "none" }}>
          {label}
        </div>
        <div className="bodytext" style={{ fontSize: 12, paddingTop: 4 }}>
          — no agents in this arm —
        </div>
      </div>
    );
  }
  const sub = aggregateSentiment(agents);
  return (
    <div style={{ paddingTop: 6, paddingBottom: 4 }}>
      <div className="subhead">
        <span>{label}</span>
        <span className="n">
          ({agents.length} agent{agents.length === 1 ? "" : "s"})
        </span>
        <span style={{ marginLeft: "auto" }}>
          <SentimentChip sentiment={sub.label} intensity={sub.intensity} />
        </span>
      </div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {agents.map((a) => (
          <AgentLi key={a.agent_id} agent={a} />
        ))}
      </ul>
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// #51 — sentiment chip + top-quote helpers. Logic byte-identical to legacy;
// restyled to the dark console (sentiment is plain ink + glyph, no valence
// color — DESIGN.md §8.5 / Console LAW 3).
// ───────────────────────────────────────────────────────────────────────────
type SentimentLabel = "positive" | "neutral" | "negative" | null;

function SentimentChip({
  sentiment,
  intensity,
}: {
  sentiment: SentimentLabel;
  intensity: number | null;
}) {
  if (sentiment == null) {
    return (
      <span className="schip" aria-label="Sentiment not yet available">
        —
      </span>
    );
  }
  const glyph =
    sentiment === "positive" ? "+" : sentiment === "negative" ? "−" : "~";
  return (
    <span
      className="schip"
      title={`${sentiment} (confidence ${intensity != null ? intensity.toFixed(2) : "—"})`}
      aria-label={`Sentiment: ${sentiment}`}
    >
      <span aria-hidden className="g">
        {glyph}
      </span>
      {sentiment}
    </span>
  );
}

function TopQuoteLine({
  text,
  armLabel = null,
}: {
  text: string;
  armLabel?: "treatment" | "control" | null;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <button
      type="button"
      onClick={() => setExpanded((v) => !v)}
      aria-expanded={expanded}
      title={expanded ? "Click to collapse" : "Click to expand"}
      className={`quote ${expanded ? "open" : "clamp"}`}
    >
      {armLabel && (
        <span aria-label={`${armLabel} arm`} className="qtag">
          {armLabel}
        </span>
      )}
      <span aria-hidden style={{ marginRight: 6 }}>
        “
      </span>
      {text}
      <span aria-hidden style={{ marginLeft: 4 }}>
        ”
      </span>
    </button>
  );
}

function aggregateSentiment(agents: AgentRow[]): {
  label: SentimentLabel;
  intensity: number | null;
} {
  let weighted = 0;
  let total = 0;
  const valueOf = { positive: 1, neutral: 0, negative: -1 } as const;
  for (const a of agents) {
    if (a.sentiment == null) continue;
    const w = a.sentiment_confidence ?? 0.5;
    weighted += valueOf[a.sentiment] * w;
    total += w;
  }
  if (total === 0) return { label: null, intensity: null };
  const score = weighted / total;
  const label: SentimentLabel =
    score > 0.33 ? "positive" : score < -0.33 ? "negative" : "neutral";
  return { label, intensity: Math.abs(score) };
}

function pickGroupQuote(agents: AgentRow[]): string | null {
  let best: string | null = null;
  let bestLen = -1;
  for (const a of agents) {
    if (!a.top_quote) continue;
    if (a.top_quote.length > bestLen) {
      best = a.top_quote;
      bestLen = a.top_quote.length;
    }
  }
  return best;
}

// ───────────────────────────────────────────────────────────────────────────
// Weakness category info — PM-readable definitions + click-to-expand popover.
// Logic byte-identical to legacy WeaknessCategoryInfo (same categories, same
// open/close interaction); restyled to the dark popover.
// ───────────────────────────────────────────────────────────────────────────
type WeaknessCategory =
  | "wrong_metric"
  | "wrong_cohort"
  | "broken_mechanism"
  | "untestable_hypothesis"
  | "hidden_guardrail_risk"
  | "underpowered_design";

const WEAKNESS_INFO: Record<
  WeaknessCategory,
  { title: string; description: string }
> = {
  wrong_metric: {
    title: "Wrong Metric",
    description:
      "The change is being measured against the wrong signal. The metric the team is watching doesn't actually capture the behavior the change is trying to affect — so even if the change works, the metric won't move.",
  },
  wrong_cohort: {
    title: "Wrong Cohort",
    description:
      "The change is being tested on users who don't have a reason to respond to it. Even if the feature works as designed, this audience isn't the one it would meaningfully affect — so the experiment can't tell you whether the change matters to the users it SHOULD matter to. Fix: re-target the experiment at users whose behavior the change is actually trying to move.",
  },
  broken_mechanism: {
    title: "Broken Mechanism",
    description:
      "The cause-and-effect logic the hypothesis assumes doesn't hold. Users don't actually behave the way the team is betting they will — the change can't produce the predicted result by the route described, even if every other part of the experiment is sound.",
  },
  untestable_hypothesis: {
    title: "Untestable Hypothesis",
    description:
      "The hypothesis can't be falsified by the experiment as designed. Either the success criteria are vague, or no observable signal would distinguish a working change from a broken one — so any result is consistent with both.",
  },
  hidden_guardrail_risk: {
    title: "Hidden Guardrail Risk",
    description:
      "The change might move the headline metric while quietly harming an adjacent metric the team isn't watching — retention, fees, support load, etc. Worth instrumenting BEFORE the experiment runs, not discovering after.",
  },
  underpowered_design: {
    title: "Underpowered Design",
    description:
      "The experiment can't reliably detect the effect the team is looking for. Common causes: the targeted segment is too narrow, the expected effect size (MDE) is set too optimistically, the experiment duration is too short, or too many agent classifications failed to complete (a data-quality degradation gate fires when more than half fail). Fix depends on the cause: widen the segment, calibrate the MDE more conservatively, run longer, or rerun the simulation to recover failed classifications.",
  },
};

function WeaknessCategoryInfo({ category }: { category: string }) {
  const [open, setOpen] = useState(false);
  const info =
    category in WEAKNESS_INFO
      ? WEAKNESS_INFO[category as WeaknessCategory]
      : null;
  if (!info) return null;

  return (
    <span style={{ position: "relative", display: "inline-flex" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`What is ${info.title}?`}
        aria-expanded={open}
        title={open ? "Hide definition" : "Show definition"}
        className="wk-info"
      >
        i
      </button>
      {open && (
        <div role="dialog" aria-label={info.title} className="wk-pop">
          <div className="pt">{info.title}</div>
          <div className="pd">{info.description}</div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Close definition"
            className="pclose"
          >
            ×
          </button>
        </div>
      )}
    </span>
  );
}
