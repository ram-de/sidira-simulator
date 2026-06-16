"use client";

// ───────────────────────────────────────────────────────────────────────────
// THE READING CONSOLE — an experimental, locally-scoped simulation-results
// surface. Faithful port of design-rethink/mocks/simulation-results.html, wired
// to REAL live `Simulation` data. ALL of its visual system is scoped under the
// `.rconsole` wrapper class — it deliberately does NOT touch lib/design.ts,
// DESIGN.md, or the production results page. Delete this file to remove.
//
// THE LAWS (distilled from design-system-v2.md / v2.1-patch) it obeys:
//   1. CANDOR — every inferred figure wears ± from a REAL CI, or a "◇" marker
//      when no CI exists. Identifiers/counts/seeds/timestamps print BARE.
//   2. VERDICT GATED ON CALIBRATION — hedged, never "SHIP" on uncalibrated.
//   3. SIGNAL BUDGET — exactly one --signal carrier per region (the field
//      mean line). Sentiment is ink + glyph, no valence color.
//   4. DRIFT/MOTION — canvas ≤2px amplitude, ≤30fps, pauses when hidden,
//      freezes under reduced-motion (settled poster frame).
//   5. POPULATION FIELD — real per-agent / per-arm distribution, settled.
//   6. ALL STATES — pending/running/failed/complete, empty data, null CIs.
// ───────────────────────────────────────────────────────────────────────────

import Link from "next/link";
import { useEffect, useMemo, useRef } from "react";
import type {
  Hypothesis,
  Simulation,
  SimulationResult,
  Weakness,
} from "@/lib/api";
// `AgentAnalysisSummary` is not re-exported from lib/api — pull it straight
// from the generated OpenAPI schema map so the type stays in lockstep with the
// backend without us redefining it.
import type { components } from "@/lib/api-types";

type AgentAnalysisSummary = components["schemas"]["AgentAnalysisSummary"];

// ── model labels — mirrors the production page's MODEL_LABELS convention ─────
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
  return (
    MODEL_LABELS[modelId] ?? { label: modelId, provider: "selected provider" }
  );
}

// ── weakness category formatting — mirrors production formatCategory ─────────
function formatCategory(cat: string): string {
  return cat
    .split("_")
    .map((w) => (w.length > 0 ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString([], { hour12: false });
  } catch {
    return iso;
  }
}

const METRIC_DISPLAY_LABELS: Record<string, string> = {
  conversion: "Conversion",
  retention: "Retention",
  ctr: "CTR",
};

function metricDisplayLabel(name: string | null | undefined): string | null {
  if (!name) return null;
  return METRIC_DISPLAY_LABELS[name] ?? name.toUpperCase();
}

// ── number helpers ───────────────────────────────────────────────────────────
function fmt1(n: number): string {
  return n.toFixed(1);
}
function fmtSigned1(n: number): string {
  return `${n >= 0 ? "+" : ""}${n.toFixed(1)}`;
}
function fmtSigned2(n: number): string {
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}`;
}

// Half-width of a CI: ±(high − low)/2. Returns null if the interval is absent.
function ciHalf(ci: [number, number] | null | undefined): number | null {
  if (!ci || ci.length !== 2) return null;
  const [lo, hi] = ci;
  if (typeof lo !== "number" || typeof hi !== "number") return null;
  return Math.abs(hi - lo) / 2;
}

// Short, bare run reference (the mock's "SIM-7C4A1E9F" / "7C4A1E9F").
function shortId(id: string): string {
  const tail = id.replace(/^sim[_-]?/i, "").slice(-8);
  return tail.toUpperCase();
}

function seedHex(seed: number | null | undefined): string | null {
  if (seed == null || !Number.isFinite(seed)) return null;
  // Seeds may be signed / wider than 32 bits — never truncate (it's a bare
  // provenance fact). BigInt-format the exact integer; fall back to decimal.
  try {
    const b = BigInt(Math.trunc(seed));
    return b < 0n ? `-0x${(-b).toString(16)}` : `0x${b.toString(16)}`;
  } catch {
    return String(seed);
  }
}

// ── verdict, gated on calibration (LAW 2) ────────────────────────────────────
type Verdict = {
  // The leading word(s) of the verdict tag.
  word: string;
  // A trailing qualifier (e.g. "TEST FIRST"), or null.
  qualifier: string | null;
  // The signed delta to display (lift), or null for single-arm.
  delta: number | null;
  // The ± on that delta, or null when uncalibrated.
  deltaCi: number | null;
  // Whether to print the hollow ◇ uncalibrated glyph.
  uncalibrated: boolean;
};

function deriveVerdict(result: SimulationResult): Verdict {
  const lift = typeof result.lift === "number" ? result.lift : null;
  const liftCiArr = result.lift_ci ?? null;
  const half = ciHalf(liftCiArr);
  // An A/B run is one that reported two arm scores. If lift / its CI is missing
  // on an A/B run, the comparison is simply uncomputable — we must NOT borrow
  // the single-arm score to manufacture a directional read.
  const isAB =
    typeof result.treatment_score === "number" &&
    typeof result.control_score === "number";

  if (lift == null || !liftCiArr) {
    // A/B but lift uncomputed → inconclusive, full stop (no lift evidence).
    if (isAB) {
      return {
        word: "INCONCLUSIVE",
        qualifier: null,
        delta: null,
        deltaCi: null,
        uncalibrated: true,
      };
    }
    // True single-arm run: classify the agreement directionally, no ship word.
    const score = result.confidence_score ?? 0;
    return {
      word: score >= 80 ? "DIRECTIONAL" : "INCONCLUSIVE",
      qualifier: score >= 80 ? "TEST FIRST" : null,
      delta: null,
      deltaCi: null,
      uncalibrated: true,
    };
  }

  const [lo, hi] = liftCiArr;
  const straddlesZero = lo <= 0 && hi >= 0;
  if (straddlesZero) {
    return {
      word: "INCONCLUSIVE",
      qualifier: null,
      delta: lift,
      deltaCi: half,
      uncalibrated: true,
    };
  }
  return {
    word: "DIRECTIONAL",
    qualifier: "TEST FIRST",
    delta: lift,
    deltaCi: half,
    uncalibrated: true,
  };
}

// ── sentiment glyph (ink only — no valence color, LAW 3) ─────────────────────
function sentimentGlyph(s: AgentAnalysisSummary["sentiment"]): string {
  if (s === "positive") return "▲";
  if (s === "negative") return "▼";
  return "▬";
}

// ── scoped tokens (LAW: all Console tokens live under .rconsole) ─────────────
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
  --font-mono:var(--font-mono,ui-monospace,"JetBrains Mono",SFMono-Regular,monospace);
  background:var(--console-850); color:var(--text);
  font-family:var(--font-mono); font-size:15px; line-height:1.55;
  min-height:100vh; -webkit-font-smoothing:antialiased;
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

/* preview ribbon */
.rconsole .preview-ribbon{
  display:flex; align-items:center; gap:14px; flex-wrap:wrap;
  padding:7px 24px; background:var(--console-900);
  border-bottom:1px solid var(--console-line);
  font-size:10.5px; letter-spacing:.08em; text-transform:uppercase;
  color:var(--text-mut); position:sticky; top:0; z-index:40;
}
.rconsole .preview-ribbon .lead{color:var(--text);}
.rconsole .preview-ribbon .back{margin-left:auto; color:var(--text-mut);
  border:1px solid var(--console-line); border-radius:var(--r-well);
  padding:3px 9px;}
.rconsole .preview-ribbon .back:hover, .rconsole .preview-ribbon .back:focus-visible{
  color:var(--text-hi); border-color:var(--text-mut);}

/* top bar / masthead */
.rconsole .topbar{display:flex; align-items:center; gap:16px; flex-wrap:wrap;
  padding:0 24px; height:52px; background:var(--console-850);
  border-bottom:1px solid var(--console-line);}
.rconsole .wordmark{font-weight:600; font-size:15px; letter-spacing:.06em;
  color:var(--text-hi);}
.rconsole .crumb{color:var(--text-mut);}
.rconsole .crumb b{color:var(--text-hi); font-weight:500;}
.rconsole .topbar-legend{margin-left:auto; display:flex; align-items:center;
  gap:12px; flex-wrap:wrap; font-size:11px; letter-spacing:.05em;
  color:var(--text-mut);}
.rconsole .topbar-legend .sep{color:var(--console-line);}
.rconsole .live-dot{width:7px; height:7px; border-radius:9999px;
  background:var(--signal); display:inline-block;
  animation:rc-breath 2s ease-in-out infinite;}
@keyframes rc-breath{0%,100%{opacity:.5;}50%{opacity:1;}}

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
.rconsole .verdict-tag .delta{color:var(--text-hi);}
.rconsole .verdict-tag .vci{color:var(--spread);}

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
.rconsole .page{max-width:1320px; margin:0 auto; padding:48px 24px 96px;}
.rconsole .grid{display:grid; grid-template-columns:minmax(0,1fr) 348px; gap:48px;
  align-items:start;}
.rconsole .col-main{min-width:0; display:flex; flex-direction:column; gap:48px;}

/* panels */
.rconsole .panel{background:var(--console-800);
  border:1px solid var(--console-line); border-radius:var(--r-panel);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04);}
.rconsole .panel-pad{padding:24px;}
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
.rconsole .hcrumb b{color:var(--text); font-weight:500;}
.rconsole .lineage{display:flex; align-items:center; gap:9px; margin-bottom:18px;
  flex-wrap:wrap; font-size:11px; letter-spacing:.08em; text-transform:uppercase;}
.rconsole .lineage .node{display:inline-flex; align-items:center; gap:7px;}
.rconsole .lineage .sq{width:6px; height:6px; display:inline-block;}
.rconsole .lineage .sq.fill{background:var(--text);}
.rconsole .lineage .sq.open{border:1px solid var(--text-mut); background:transparent;}
.rconsole .lineage .rule{width:30px; height:1px; background:var(--console-line);}
.rconsole .lineage .on{color:var(--text);}
.rconsole .lineage .off{color:var(--text-mut);}
.rconsole h1.htitle{font-weight:600; font-size:32px; line-height:1.08;
  letter-spacing:-.025em; color:var(--text-hi); margin:0 0 12px;
  text-wrap:balance; max-width:36ch;}
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

.rconsole .tele{display:grid; grid-template-columns:repeat(6,minmax(0,1fr));
  gap:14px; margin-top:22px; padding-top:16px;
  border-top:1px solid var(--console-line);}
.rconsole .tele .cell .k{margin-bottom:5px;}
.rconsole .tele .cell .v{font-size:13.5px; color:var(--text-hi);
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}

/* glass instrument grid */
.rconsole .glassgrid{display:grid; grid-template-columns:1.42fr 1fr;}
.rconsole .glass-cell{padding:24px; min-width:0;}
.rconsole .glass-cell.left{border-right:1px solid var(--console-line);}
.rconsole .glass-lab{font-size:12.5px; font-weight:450; color:var(--text);}
.rconsole .glass-lab .sub{color:var(--text-mut);}
.rconsole .reading-row{display:flex; align-items:baseline; gap:14px;
  margin-top:20px; flex-wrap:wrap;}
.rconsole .reading-num{font-weight:500; font-size:64px; line-height:1;
  color:var(--text-hi); letter-spacing:-.01em;}
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
.rconsole .arm-plot .pt{position:absolute; top:50%; width:3px; height:3px;
  border-radius:9999px; transform:translate(-50%,-50%);}
.rconsole .arm-plot .pt.c{background:var(--arm-control); opacity:.6;}
.rconsole .arm-plot .pt.t{background:var(--arm-treat); opacity:.6;}
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
  margin-bottom:4px; display:flex; align-items:center; gap:7px;}
.rconsole .wk-info{font-size:10px; color:var(--text-mut);
  border:1px solid var(--console-line); border-radius:9999px; width:14px;
  height:14px; display:inline-flex; align-items:center; justify-content:center;
  cursor:help;}
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

/* cohort table */
.rconsole .logbook{width:100%; border-collapse:collapse;}
.rconsole .logbook th{text-align:left; font-size:11px; letter-spacing:.05em;
  text-transform:uppercase; color:var(--text-mut); font-weight:500;
  padding:0 12px 9px; border-bottom:1px solid var(--console-line);}
.rconsole .logbook th.num, .rconsole .logbook td.num{text-align:right;}
.rconsole .logbook td{padding:9px 12px;
  border-bottom:1px solid rgba(51,64,92,.32); font-size:13.5px;}
.rconsole .logbook tbody tr:hover td{background:var(--console-750);}
.rconsole .logbook .pname{color:var(--text-hi); font-weight:500;}
.rconsole .logbook .pid{font-size:11px; color:var(--text-mut);}
.rconsole .sentcell{color:var(--text);}
.rconsole .sentcell .gly{color:var(--text-mut); margin-right:6px;}
.rconsole .miniquote{color:var(--text-mut); font-style:normal; font-size:12.5px;}
.rconsole .scell{font-size:12.5px; color:var(--text-mut);}

/* refinement queue */
.rconsole .refrow{display:grid; grid-template-columns:minmax(0,1fr);
  gap:8px; padding:13px 0; border-top:1px solid var(--console-line);}
.rconsole .refrow:first-of-type{border-top:none;}
.rconsole .refrow .txt{font-size:14px; color:var(--text); line-height:1.5;}
.rconsole .refrow .txt b{color:var(--text-hi); font-weight:500;}

/* inspector rail */
.rconsole .inspector{position:sticky; top:120px; align-self:start;
  background:var(--console-800); border:1px solid var(--console-line);
  border-radius:var(--r-panel); box-shadow:inset 0 1px 0 rgba(255,255,255,.04);
  padding:20px;}
.rconsole .quotewell{background:var(--console-900);
  border:1px solid var(--console-line); border-radius:var(--r-well); padding:13px;
  margin:6px 0 20px;}
.rconsole .quotewell .ql{font-size:10px; letter-spacing:.05em;
  text-transform:uppercase; color:var(--text-mut); margin-bottom:8px;}
.rconsole .quotewell .qt{font-size:13.5px; color:var(--text-hi); line-height:1.55;}
.rconsole .prov{margin:0 0 18px;}
.rconsole .provrow{display:grid; grid-template-columns:118px minmax(0,1fr);
  gap:8px; padding:6px 0; border-top:1px solid rgba(51,64,92,.4);}
.rconsole .provrow:first-child{border-top:none;}
.rconsole .provrow dt{font-size:10px; letter-spacing:.04em; text-transform:uppercase;
  color:var(--text-mut); padding-top:1px;}
.rconsole .provrow dd{margin:0; font-size:11.5px; color:var(--text-hi);
  overflow-wrap:anywhere;}
.rconsole .provrow dd.unc{color:var(--text-mut);}

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

// ── the showpiece canvas (LAW 4 + 5) ─────────────────────────────────────────
type FieldAgent = {
  arm: 0 | 1; // 0 control, 1 treatment
  score: number; // reaction in [0,1]; 0=rejects, 1=adopts
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
  // mean reaction in [0,1] used for the signal mean line
  mean: number;
  // CI half-width in reaction units (0..1) for the spread ribbon, or null
  ciHalf: number | null;
  // True ONLY when each dot's arm is a real per-arm fact (the synthesized
  // two-cloud fallback built from real treatment/control centers). For the
  // per-agent path the data carries no arm, so dots render pooled (neutral).
  armKnown: boolean;
};

// Deterministic PRNG so the frozen frame is reproducible.
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

// Build the field model from REAL data (LAW 5).
//   - If per_agent_analyses exist: one dot per agent, x from sentiment +
//     confidence (positive→right, negative→left), arm derived from index via
//     arm_split.treatment_fraction.
//   - Else if treatment/control scores exist: two settled gaussian clouds.
//   - Else: a single cloud centered on confidence_score.
function buildFieldModel(
  sim: Simulation,
  result: SimulationResult,
): FieldModel {
  const rnd = mulberry((sim.run_seed ?? 0x4f17) >>> 0);
  const agents: FieldAgent[] = [];
  const treatFrac = sim.arm_split?.treatment_fraction ?? null;
  const isAB = treatFrac != null;

  const per = result.per_agent_analyses ?? [];
  const blank = (): Omit<
    FieldAgent,
    "arm" | "score"
  > => ({
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
      // sentiment → base position; confidence → distance from center
      const dir = a.sentiment === "positive" ? 1 : a.sentiment === "negative" ? -1 : 0;
      const conf = Math.max(0, Math.min(1, a.sentiment_confidence));
      // neutral sits near center with a little jitter
      const signed = dir === 0 ? (rnd() - 0.5) * 0.18 : dir * (0.18 + conf * 0.42);
      const score = Math.max(0.02, Math.min(0.98, 0.5 + signed));
      // The per-agent summary carries NO arm — so we do not invent one. Every
      // real-agent dot is pooled (arm 0, rendered neutral). The arm split is
      // only ever drawn where it is a real per-arm fact (ArmCompare / the
      // synthesized two-cloud fallback below).
      agents.push({ arm: 0, score, ...blank() });
    });
  } else {
    // Synthesize a settled cloud from scores. Honest: this is a distribution
    // implied by the run's summary statistics, not fabricated per-agent reads.
    const n = sim.sampled_agent_count ?? 120;
    const tScore = result.treatment_score;
    const cScore = result.control_score;
    const haveArms =
      isAB && typeof tScore === "number" && typeof cScore === "number";
    // These synthesized dots ARE assigned an arm — but only because each cloud
    // is generated around a real per-arm center (treatment_score/control_score).
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

  // Spread ribbon from the confidence CI (mapped to 0..1), if present.
  const ch = ciHalf(result.confidence_score_ci);
  return { agents, mean, ciHalf: ch != null ? ch / 100 : null, armKnown };
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
    const BET_DUR = 900; // ≤900ms one-shot settle (LAW 5)
    const SETTLE_AT = BET_START + BET_DUR + 200;
    const DRIFT_PX = 2; // hard ≤2px ceiling (LAW 4)
    let t0 = performance.now();
    let raf = 0;
    let lastDraw = 0;
    const FRAME_MS = 1000 / 30; // cap at 30fps (LAW 4)

    function easeMech(t: number) {
      return t < 0 ? 0 : t > 1 ? 1 : 1 - Math.pow(1 - t, 3);
    }
    function colorFor(arm: number, mix: number): [number, number, number] {
      // Arm tint ONLY when arm is real (model.armKnown). Otherwise the dots are
      // a pooled population → neutral slate, never blue/pink (no fake arm split).
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

      // ── spread ribbon (amber) + the ONE signal mean line (LAW 3) ──
      if (betT > 0.55) {
        const ribA = Math.min(1, (betT - 0.55) / 0.45) * 0.16;
        const meanX = L.padX + model.mean * L.plotW;
        ctx!.globalCompositeOperation = "source-over";
        // Spread ribbon ONLY when a REAL confidence interval exists. No CI →
        // no band: the candor law forbids implying an interval we don't have.
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
        // settled mean line — a real fact (the mean), the lone --signal carrier
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

        let frontMix = settled
          ? 0
          : 1 - Math.min(1, Math.abs(x - wfx) / bandW);
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

      // wavefront crest (signal) ONLY while the single bet sweeps
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

      // axis baseline (source-over)
      ctx!.globalCompositeOperation = "source-over";
      ctx!.strokeStyle = "rgba(51,64,92,0.55)";
      ctx!.lineWidth = 1 * DPR;
      ctx!.beginPath();
      ctx!.moveTo(L.padX * 0.5, L.axisY);
      ctx!.lineTo(c.width - L.padX * 0.5, L.axisY);
      ctx!.stroke();
    }

    function frame(now: number) {
      // pause when the document is hidden (LAW 4)
      if (typeof document !== "undefined" && document.hidden) {
        raf = requestAnimationFrame(frame);
        return;
      }
      if (now - lastDraw >= FRAME_MS) {
        lastDraw = now;
        draw(now);
        // After settle, stop the loop — the field rests as a settled poster.
        if (now - t0 >= SETTLE_AT) {
          return;
        }
      }
      raf = requestAnimationFrame(frame);
    }

    if (reduce) {
      // single settled poster frame, no loop (LAW 4)
      t0 = performance.now() - (SETTLE_AT + 10);
      draw(performance.now());
    } else {
      raf = requestAnimationFrame(frame);
    }

    const onResize = () => {
      fit();
      // redraw a settled frame after a resize
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

// ── small bare-fact helpers for the masthead legend ──────────────────────────
function MastheadLegend({ sim }: { sim: Simulation }) {
  const model = modelDisplay(sim.model_id);
  const seed = seedHex(sim.run_seed);
  const n = sim.sampled_agent_count;
  const parts: Array<{ key: string; node: string }> = [];
  // CH reference
  parts.push({ key: "ch", node: "CH1" });
  if (n != null) parts.push({ key: "n", node: `n=${n}` });
  if (seed) parts.push({ key: "seed", node: `seed ${seed}` });
  if (model)
    parts.push({
      key: "model",
      node: `${model.provider.toLowerCase()}/${model.label}`,
    });

  return (
    <div className="topbar-legend">
      {parts.map((p, i) => (
        <span key={p.key} style={{ display: "inline-flex", gap: 12 }}>
          {i > 0 ? <span className="sep">·</span> : null}
          <span>{p.node}</span>
        </span>
      ))}
      <span className="sep">·</span>
      <span className="unc">
        <span className="glyph-hollow">◇</span> UNCALIBRATED
      </span>
    </div>
  );
}

// ── quiet non-complete states (LAW 6) ────────────────────────────────────────
function QuietState({ sim }: { sim: Simulation }) {
  const isFailed = sim.status === "failed";
  const isRunning = sim.status === "running";
  const headClass = isFailed ? "failed" : isRunning ? "running" : "pending";
  const model = modelDisplay(sim.model_id);

  return (
    <div className="quiet-state">
      <div className={`quiet-card${isFailed ? " failed" : ""}`}>
        <div className={`quiet-head ${headClass}`}>
          {isRunning ? (
            <>
              <span className="live-dot" /> LIVE READING · TAKING A READING
            </>
          ) : isFailed ? (
            <>▲ RUN FAILED — NO VERDICT</>
          ) : (
            <>
              <span className="glyph-hollow">◇</span> READING IN PROGRESS
            </>
          )}
        </div>
        <div className="quiet-body">
          {isFailed
            ? "The run terminated before a verdict could be drawn. No reading exists for this lineage. Re-run the hypothesis to take a fresh reading — nothing here is fabricated to fill the gap."
            : isRunning
              ? "Readings plot as they arrive; the score prints at the scoring phase. No numbers are shown until the reading settles — the console refuses to imply a verdict from a partial run."
              : "This reading has not started. The axis and CI grid stay bare until a run fills them."}
        </div>

        {/* provenance that already exists prints BARE (LAW 1) */}
        <dl className="prov" style={{ marginTop: 24 }}>
          <div className="provrow">
            <dt>RUN</dt>
            <dd>{shortId(sim.id)}</dd>
          </div>
          <div className="provrow">
            <dt>CREATED</dt>
            <dd>{formatDateTime(sim.created_at)}</dd>
          </div>
          <div className="provrow">
            <dt>STATUS</dt>
            <dd>{sim.status.toUpperCase()}</dd>
          </div>
          <div className="provrow">
            <dt>PERSONA PACK</dt>
            <dd>{sim.persona_pack_version}</dd>
          </div>
          <div className="provrow">
            <dt>FEATURE PACK</dt>
            <dd>{sim.feature_pack_version}</dd>
          </div>
          {model ? (
            <div className="provrow">
              <dt>MODEL</dt>
              <dd>{model.label}</dd>
            </div>
          ) : null}
        </dl>
      </div>
    </div>
  );
}

// ── arm comparison sub-figure ────────────────────────────────────────────────
function ArmCompare({
  result,
  pairedN,
}: {
  result: SimulationResult;
  pairedN: number | null;
}) {
  const c = result.control_score;
  const t = result.treatment_score;
  if (typeof c !== "number" || typeof t !== "number") return null;

  // map 0..100 scores onto a -1..+1 reaction strip → 0..100% positions.
  const toX = (score: number) => Math.max(2, Math.min(98, 5 + (score / 100) * 90));
  const cx = toX(c);
  const tx = toX(t);
  // The PAIRED LIFT statistic — only when the backend actually computed it.
  // We never synthesize it from t − c (lift:null can mean "no matched pairs",
  // a real uncomputable, not zero-effect). t − c is shown separately, plainly
  // labelled as the raw difference of the two reported arm means.
  const liftStat = typeof result.lift === "number" ? result.lift : null;
  const rawDelta = t - c;
  const lh = ciHalf(result.lift_ci);
  const liftCi = result.lift_ci ?? null;
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
            <span className="v">{fmtSigned1(c)}</span>
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
            <span className="v">{fmtSigned1(t)}</span>
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
        {pairedN != null ? `n = ${pairedN} PAIRED · ` : ""}SINGLE RUN
      </div>
    </div>
  );
}

// ── MAIN ─────────────────────────────────────────────────────────────────────
export function ReadingConsoleResults({ sim }: { sim: Simulation }) {
  const hypothesis: Hypothesis = sim.hypothesis;
  const result: SimulationResult | null = sim.result ?? null;
  const isComplete = sim.status === "complete" && result != null;

  // Build the field model only when complete (hook order stays stable: always
  // call useMemo; bail to null inside).
  const fieldModel = useMemo<FieldModel | null>(() => {
    if (!isComplete || !result) return null;
    return buildFieldModel(sim, result);
  }, [isComplete, result, sim]);

  return (
    <div className="rconsole">
      <style>{RCONSOLE_CSS}</style>

      {/* preview ribbon + quiet link back to production page */}
      <div className="preview-ribbon">
        <span className="lead">EXPERIMENTAL PREVIEW</span>
        <span className="sep">·</span>
        <span>READING CONSOLE</span>
        <Link className="back" href={`/simulations/${sim.id}`}>
          ← production results
        </Link>
      </div>

      {/* masthead / provenance bar */}
      <header className="topbar">
        <span className="wordmark">SIDIRA</span>
        <span className="crumb desig">
          / SIMULATIONS / <b>SIM-{shortId(sim.id)}</b>
        </span>
        <MastheadLegend sim={sim} />
      </header>

      {!isComplete || !result || !fieldModel ? (
        <QuietState sim={sim} />
      ) : (
        <CompleteReading
          sim={sim}
          result={result}
          hypothesis={hypothesis}
          fieldModel={fieldModel}
        />
      )}
    </div>
  );
}

function CompleteReading({
  sim,
  result,
  hypothesis,
  fieldModel,
}: {
  sim: Simulation;
  result: SimulationResult;
  hypothesis: Hypothesis;
  fieldModel: FieldModel;
}) {
  const score = result.confidence_score;
  const scoreCi = result.confidence_score_ci ?? null;
  const scoreHalf = ciHalf(scoreCi);
  const verdict = deriveVerdict(result);
  const model = modelDisplay(sim.model_id);
  const metric = metricDisplayLabel(hypothesis.metric_name);
  const per = result.per_agent_analyses ?? [];
  const weaknesses: Weakness[] = result.weaknesses ?? [];
  const refinements = result.refinement_suggestions ?? [];
  const treatFrac = sim.arm_split?.treatment_fraction ?? null;
  const isAB = treatFrac != null;
  const pairedN = result.lift_paired_n ?? null;
  const THRESHOLD = 80;

  // reaction split (rejects/neutral/adopts) from per-agent sentiment, raw counts
  const split = useMemo(() => {
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
  }, [per]);

  // pinned quote — first positive, else first available
  const pinnedQuote = useMemo(() => {
    if (per.length === 0) return null;
    return per.find((a) => a.sentiment === "positive") ?? per[0];
  }, [per]);

  return (
    <>
      {/* ════ THE POPULATION FIELD (showpiece) ════ */}
      {/* Legend stays honest about the field: an A/B run whose per-agent arm
          can't be resolved is drawn POOLED, and says so — it never implies an
          arm split the data can't support. */}
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

      {/* hero verdict band overlaid below the field (static, no animation) */}
      <div
        className="fieldwrap"
        style={{ borderTop: "none", paddingBottom: 0 }}
        aria-hidden={false}
      >
        <div className="field-verdict" style={{ position: "static", padding: 24 }}>
          <div className="verdict-figure">
            <div className="lab">
              <span>SIMULATION AGREEMENT</span>
              <span className="glyph-hollow">◇</span>
            </div>
            <div className="num">
              <span>{fmt1(score)}</span>
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
            <div className="verdict-tag">
              <span className="vg">◇</span>
              {verdict.word}
              {verdict.delta != null ? (
                <>
                  {" "}
                  <span className="delta">{fmtSigned1(verdict.delta)}</span>
                  {verdict.deltaCi != null ? (
                    <span className="vci">±{fmt1(verdict.deltaCi)}</span>
                  ) : (
                    <span className="vci glyph-hollow">◇</span>
                  )}
                </>
              ) : null}
              {verdict.qualifier ? <> · {verdict.qualifier}</> : null}
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

      {/* ════ PAGE BODY ════ */}
      <div className="page">
        <div className="grid">
          <div className="col-main">
            {/* hypothesis header */}
            <section className="panel panel-pad">
              <div className="hcrumb">
                SIMULATIONS / <b>SIM-{shortId(sim.id)}</b>
              </div>
              <div className="lineage">
                <span className="node">
                  <span className="sq fill" />
                  <span className="on">SIMULATED</span>
                </span>
                <span className="rule" />
                <span className="node">
                  <span className="sq open" />
                  <span className="off">DECISION</span>
                </span>
                <span className="off">· NO LIVE OUTCOMES IN THIS LINEAGE</span>
              </div>

              <h1 className="htitle">{hypothesis.prose}</h1>
              <div className="verdicttag-row">
                <span className="vchip">
                  <span className="vg">◇</span>POLICY DR-1
                  {verdict.qualifier ? ` · ${verdict.qualifier}` : ""}
                </span>
                <span className="desig">UNGRADED — LEDGER EMPTY</span>
              </div>
              <div className="whyline">
                {verdict.word === "DIRECTIONAL" ? (
                  <>
                    Agreement reads{" "}
                    <span className="em">{fmt1(score)} / 100</span>
                    {verdict.delta != null ? (
                      <>
                        {" "}
                        with a {verdict.delta >= 0 ? "positive" : "negative"}{" "}
                        lift of{" "}
                        <span className="em">{fmtSigned1(verdict.delta)}</span>
                      </>
                    ) : null}{" "}
                    — the rule reads <span className="em">directional</span>, not
                    ship, until a graded run populates the ledger.
                  </>
                ) : (
                  <>
                    The reading is <span className="em">inconclusive</span>
                    {result.lift_ci ? (
                      <>
                        {" "}
                        — the lift interval straddles zero, so no direction can
                        be claimed from this run.
                      </>
                    ) : (
                      <> on the available evidence.</>
                    )}
                  </>
                )}
              </div>

              <div className="tele">
                <div className="cell">
                  <div className="k desig desig-sm">MODEL</div>
                  <div className="v">{model ? model.label : "—"}</div>
                </div>
                <div className="cell">
                  <div className="k desig desig-sm">CAPABILITY</div>
                  <div className="v" title={hypothesis.capability_name}>
                    {hypothesis.capability_name}
                  </div>
                </div>
                <div className="cell">
                  <div className="k desig desig-sm">READINGS</div>
                  <div className="v">{sim.sampled_agent_count ?? "—"}</div>
                </div>
                <div className="cell">
                  <div className="k desig desig-sm">ARMS</div>
                  <div className="v">
                    {isAB
                      ? `A/B ${Math.round((treatFrac as number) * 100)}/${
                          100 - Math.round((treatFrac as number) * 100)
                        }`
                      : "SINGLE"}
                  </div>
                </div>
                <div className="cell">
                  <div className="k desig desig-sm">POPULATION</div>
                  <div
                    className="v"
                    title={
                      sim.population_size != null
                        ? `${sim.population_size.toLocaleString()} · HAMILTON`
                        : undefined
                    }
                  >
                    {sim.population_size != null
                      ? `${sim.population_size.toLocaleString()} · HAMILTON`
                      : "—"}
                  </div>
                </div>
                <div className="cell">
                  <div className="k desig desig-sm">STATUS</div>
                  <div className="v">{sim.status.toUpperCase()}</div>
                </div>
              </div>
            </section>

            {/* glass instrument */}
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
              <div className="glassgrid">
                {/* left: agreement reading */}
                <div className="glass-cell left">
                  <div className="glass-lab">
                    Agreement <span className="sub">— the settled reading</span>
                  </div>
                  <div className="reading-row">
                    <span className="reading-num" style={{ fontSize: 40 }}>
                      {fmt1(score)}
                    </span>
                    {scoreHalf != null ? (
                      <span className="reading-ci">±{fmt1(scoreHalf)}</span>
                    ) : (
                      <span className="reading-ci glyph-hollow">
                        ◇ UNCALIBRATED
                      </span>
                    )}
                    <span className="stamp hollow">◇</span>
                    <span className="reading-unit">AGREEMENT / 100 · SETTLED</span>
                  </div>

                  <div className="kvrow">
                    <div className="kv">
                      <div className="k">THRESHOLD</div>
                      <div className="v">{THRESHOLD} / 100</div>
                    </div>
                    <div className="kv">
                      <div className="k">MARGIN</div>
                      <div className="v">
                        {fmtSigned1(score - THRESHOLD)}{" "}
                        {scoreHalf != null ? (
                          <span className="ci">±{fmt1(scoreHalf)}</span>
                        ) : (
                          <span className="g">◇</span>
                        )}{" "}
                        <span className="g">◇</span>
                      </div>
                    </div>
                    {metric ? (
                      <div className="kv">
                        <div className="k">METRIC</div>
                        <div className="v">{metric}</div>
                      </div>
                    ) : null}
                  </div>

                  <div className="axisnote">
                    {scoreCi ? (
                      <>
                        95% CI [{fmt1(scoreCi[0])}, {fmt1(scoreCi[1])}] —{" "}
                        {scoreCi[0] >= THRESHOLD ? (
                          <>
                            LOWER BOUND <span className="clears">CLEARS</span>{" "}
                            THRESHOLD {THRESHOLD}
                          </>
                        ) : (
                          <>LOWER BOUND BELOW THRESHOLD {THRESHOLD}</>
                        )}{" "}
                        · <span className="glyph-hollow">◇</span> UNCALIBRATED
                      </>
                    ) : (
                      <>
                        NO INTERVAL RETURNED ·{" "}
                        <span className="glyph-hollow">◇</span> UNCALIBRATED —
                        the reading carries no ±
                      </>
                    )}
                  </div>
                </div>

                {/* right: paired-arm comparison (A/B only) */}
                <div className="glass-cell">
                  <div className="glass-lab">
                    {isAB ? (
                      <>
                        Paired arms{" "}
                        <span className="sub">— the same cohort, two worlds</span>
                      </>
                    ) : (
                      <>
                        Single arm{" "}
                        <span className="sub">— no control to compare</span>
                      </>
                    )}
                  </div>
                  {isAB ? (
                    <ArmCompare result={result} pairedN={pairedN} />
                  ) : (
                    <div className="axisnote" style={{ marginTop: 18 }}>
                      This run has one arm. There is no control world to settle
                      against, so no lift is computed — the agreement reading
                      above stands alone.
                    </div>
                  )}
                </div>
              </div>

              <div className="glass-foot">
                <span>
                  n = {sim.sampled_agent_count ?? "—"} READINGS
                  {pairedN != null ? ` · ${pairedN} PAIRED` : ""} · SINGLE RUN
                </span>
                <span className="unc">
                  <span className="glyph-hollow">◇</span> UNGRADED
                </span>
              </div>
            </section>

            {/* weakness register */}
            <section className="panel panel-pad">
              <div className="wk-headrow">
                <span>WEAKNESS REGISTER — FINDING</span>
                <span>FREQUENCY (95% CI)</span>
              </div>
              {weaknesses.length === 0 ? (
                <div
                  className="wk-sum"
                  style={{ paddingTop: 14, color: "var(--text-mut)" }}
                >
                  No weaknesses flagged for this reading.
                </div>
              ) : (
                weaknesses.map((w, i) => {
                  const freq =
                    typeof w.frequency === "number" ? w.frequency : null;
                  const lo = typeof w.ci_low === "number" ? w.ci_low : null;
                  const hi = typeof w.ci_high === "number" ? w.ci_high : null;
                  const haveCi = lo != null && hi != null;
                  const pct = (n: number) => Math.round(n * 100);
                  return (
                    <div className="wk-row" key={`${w.category}-${i}`}>
                      <div>
                        <div className="wk-name">
                          {formatCategory(w.category)}
                          <span className="wk-info" title={w.summary} aria-hidden>
                            i
                          </span>
                        </div>
                        <div className="wk-sum">{w.summary}</div>
                      </div>
                      <div>
                        {freq != null ? (
                          <>
                            <div className="freqbar">
                              <div className="base" />
                              {haveCi ? (
                                <div
                                  className="ci"
                                  style={{
                                    left: `${pct(lo as number)}%`,
                                    width: `${Math.max(
                                      2,
                                      pct(hi as number) - pct(lo as number),
                                    )}%`,
                                  }}
                                />
                              ) : null}
                              <div
                                className="val"
                                style={{ width: `${pct(freq)}%` }}
                              />
                            </div>
                            <div className="freqlabel">
                              {pct(freq)}%{" "}
                              {haveCi ? (
                                <span className="ci">
                                  [{pct(lo as number)}–{pct(hi as number)}%]
                                </span>
                              ) : (
                                <span className="glyph-hollow">
                                  ◇ UNCALIBRATED
                                </span>
                              )}{" "}
                              {haveCi ? (
                                <span
                                  className="stamp hollow"
                                  style={{ fontSize: 11 }}
                                >
                                  ◇
                                </span>
                              ) : null}
                            </div>
                          </>
                        ) : (
                          <div className="freqlabel">
                            <span className="glyph-hollow">
                              ◇ FREQUENCY NOT REPORTED
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </section>

            {/* cohort register */}
            <section className="panel panel-pad">
              <h2 className="sechead">
                COHORT REGISTER — {per.length} AGENT
                {per.length === 1 ? "" : "S"}
                {isAB ? " · A/B" : ""}
              </h2>
              {per.length === 0 ? (
                <div className="wk-sum" style={{ color: "var(--text-mut)" }}>
                  No per-agent analyses were persisted for this reading (it may
                  predate per-agent capture). The pooled figures above still
                  stand.
                </div>
              ) : (
                <table className="logbook">
                  <thead>
                    <tr>
                      <th>AGENT</th>
                      <th>SENTIMENT</th>
                      <th className="num">CONF</th>
                      <th>TOP REACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {per.slice(0, 40).map((a) => (
                      <tr key={a.agent_id}>
                        <td>
                          <span className="pid">{a.agent_id.slice(0, 12)}</span>
                        </td>
                        <td className="sentcell">
                          <span className="gly" aria-hidden>
                            {sentimentGlyph(a.sentiment)}
                          </span>
                          <span className="scell">{a.sentiment}</span>
                        </td>
                        <td className="num scell">
                          {a.sentiment_confidence.toFixed(2)}
                        </td>
                        <td className="miniquote">
                          {a.top_quote ? `"${a.top_quote}"` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <div
                className="desig desig-sm"
                style={{ marginTop: 12, color: "var(--text-mut)" }}
              >
                SENTIMENT IS PLAIN INK + GLYPH (▲ POSITIVE ▬ NEUTRAL ▼ NEGATIVE)
                <span className="glyph-hollow"> ◇</span> · CONFIDENCE + AGENT IDS
                ARE RAW
                {per.length > 40 ? ` · SHOWING 40 OF ${per.length}` : ""}
              </div>
            </section>

            {/* refinement queue */}
            {refinements.length > 0 ? (
              <section className="panel panel-pad">
                <h2 className="sechead tight">REFINEMENT QUEUE</h2>
                <p
                  style={{
                    fontSize: 12.5,
                    color: "var(--text-mut)",
                    margin: "0 0 14px",
                    lineHeight: 1.5,
                  }}
                >
                  Suggestions from the reading. They are not prefilled into a new
                  hypothesis — copy the wording you want to keep.
                </p>
                {refinements.map((r, i) => (
                  <div className="refrow" key={i}>
                    <div className="txt">{r}</div>
                  </div>
                ))}
              </section>
            ) : null}

            {/* method card */}
            <section className="panel panel-pad">
              <h2 className="sechead">METHOD — HOW THIS READING IS COMPUTED</h2>
              <div className="method-row">
                <span className="k">AGREEMENT</span>
                <span className="v">
                  Confidence-weighted mean of per-agent sentiment, shrunk toward
                  neutral (Bayesian), penalized by weakness share, scaled 0–100.
                  Raw simulation reading — no live-outcome calibration has been
                  applied (ledger empty), so the verdict stays directional.
                </span>
              </div>
              <div className="method-row">
                <span className="k">INTERVAL</span>
                <span className="v">
                  {scoreCi
                    ? "Bootstrap percentile interval over agents; deterministic for a given run seed."
                    : "No interval was returned for this reading — the agreement figure prints without a ±, marked uncalibrated."}
                </span>
              </div>
              <div className="method-row">
                <span className="k">LIFT</span>
                <span className="v">
                  {isAB
                    ? "Paired bootstrap over per-agent sentiment deltas (treatment − control), in agreement points. Unpaired or unclassifiable agents are dropped from the statistic."
                    : "Not computed — this is a single-arm run with no control world to settle against."}
                </span>
              </div>
              <div className="method-row">
                <span className="k">DECISION RULE</span>
                <span className="v">
                  DR-1 — DIRECTIONAL · TEST FIRST when agreement ≥ {THRESHOLD} /
                  100 on an uncalibrated reading. &ldquo;Ship&rdquo; is reserved
                  for a graded reading once live outcomes populate the ledger.
                  Display rubric applied by this page; the API does not return a
                  policy object.
                </span>
              </div>
              {model ? (
                <div className="method-row">
                  <span className="k">MODEL</span>
                  <span className="v">
                    Ran on {model.label} ({model.provider}). Reactions,
                    classifiers, and lift reflect this model; comparing runs
                    across models reads as model variance, not only product
                    variance.
                  </span>
                </div>
              ) : null}
            </section>
          </div>

          {/* inspector rail */}
          <aside className="inspector">
            {pinnedQuote ? (
              <>
                <h2 className="sechead tight">PINNED REACTION</h2>
                <div className="quotewell">
                  <div className="ql">
                    {sentimentGlyph(pinnedQuote.sentiment)}{" "}
                    {pinnedQuote.sentiment} · conf{" "}
                    {pinnedQuote.sentiment_confidence.toFixed(2)}
                  </div>
                  <div className="qt">
                    {pinnedQuote.top_quote
                      ? `"${pinnedQuote.top_quote}"`
                      : "(no quote captured)"}
                  </div>
                </div>
              </>
            ) : null}

            <h2 className="sechead tight">PROVENANCE</h2>
            <dl className="prov">
              <div className="provrow">
                <dt>RUN</dt>
                <dd>{shortId(sim.id)}</dd>
              </div>
              <div className="provrow">
                <dt>CREATED</dt>
                <dd>{formatDateTime(sim.created_at)}</dd>
              </div>
              <div className="provrow">
                <dt>CAPABILITY</dt>
                <dd>{hypothesis.capability_name}</dd>
              </div>
              <div className="provrow">
                <dt>PERSONA PACK</dt>
                <dd>{sim.persona_pack_version}</dd>
              </div>
              <div className="provrow">
                <dt>FEATURE PACK</dt>
                <dd>{sim.feature_pack_version}</dd>
              </div>
              {sim.population_size != null ? (
                <div className="provrow">
                  <dt>POPULATION</dt>
                  <dd>{sim.population_size.toLocaleString()} · HAMILTON</dd>
                </div>
              ) : null}
              {sim.sampled_agent_count != null ? (
                <div className="provrow">
                  <dt>SAMPLED</dt>
                  <dd>{sim.sampled_agent_count}</dd>
                </div>
              ) : null}
              {seedHex(sim.run_seed) ? (
                <div className="provrow">
                  <dt>SEED</dt>
                  <dd>{seedHex(sim.run_seed)}</dd>
                </div>
              ) : null}
              {model ? (
                <div className="provrow">
                  <dt>MODEL</dt>
                  <dd>{model.label}</dd>
                </div>
              ) : null}
              {pairedN != null ? (
                <div className="provrow">
                  <dt>PAIRED N</dt>
                  <dd>{pairedN}</dd>
                </div>
              ) : null}
              <div className="provrow">
                <dt>POLICY</dt>
                <dd>DR-1 (DISPLAY RUBRIC)</dd>
              </div>
              <div className="provrow">
                <dt>GRADED</dt>
                <dd className="unc">
                  <span className="glyph-hollow">◇</span> NOT YET — LEDGER EMPTY
                </dd>
              </div>
            </dl>

            <h2 className="sechead tight">ARTIFACTS</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <Link
                href={`/simulations/${sim.id}`}
                style={{ fontSize: 11.5, color: "var(--text)" }}
              >
                PRODUCTION RESULTS →
              </Link>
            </div>
          </aside>
        </div>
      </div>
    </>
  );
}
