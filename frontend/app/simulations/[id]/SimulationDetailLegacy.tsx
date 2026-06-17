"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  ApiError,
  getSimulation,
  getSimulationState,
  isTerminalStatus,
  listSimulationAgents,
  type RunEvent,
  type Simulation,
  type SimulationResult,
  type SimulationRunState,
  type SimulationStatus,
} from "@/lib/api";
import {
  TOKENS,
  FONT_SANS,
  FONT_NARROW,
  FONT_MONO,
  EASE_MECH,
  EASE_SETTLE,
  TNUM,
  DUO_SID,
  DUO_AVIRA,
} from "@/lib/design";

// ───────────────────────────────────────────────────────────────────────
// Instrument panel — DESIGN.md §7/§8/§9 (R2 PR 4, #166).
// Paper = the static record (hypothesis, registers, provenance);
// glass = live computed readings only (agreement trace, CI axis, lift).
// ───────────────────────────────────────────────────────────────────────

// Recessed-paper chips differentiated by fg only — tinted backgrounds are off
// the R2 palette. Running reads as ink (live = §9.5 lime carrier, never lime
// or invented-blue text).
const STATUS_COLORS: Record<SimulationStatus, { bg: string; fg: string }> = {
  pending: { bg: TOKENS.paperRecessed, fg: TOKENS.inkMuted },
  running: { bg: TOKENS.paperRecessed, fg: TOKENS.ink },
  complete: { bg: TOKENS.paperRecessed, fg: TOKENS.success },
  failed: { bg: TOKENS.paperRecessed, fg: TOKENS.alert },
};

// Only the extremes get semantic color; mid-range scores read as muted ink.
// TOKENS.warn (#D9A300) is ~2:1 contrast on paper — accent-only, never text
// (codex review on #164).
function scoreColor(score: number): string {
  if (score >= 80) return TOKENS.success;
  if (score >= 60) return TOKENS.inkMuted;
  return TOKENS.alert;
}

function formatCategory(cat: string): string {
  return cat
    .split("_")
    .map((w) => (w.length > 0 ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

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

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour12: false });
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

// Per-metric display labels — mirrors METRIC_LABELS in the wizard
// (simulations/new/page.tsx). `metric_name` arrives as a free `str | null` on
// SimulationResult (the discriminator), so an unrecognised value falls back to
// its uppercased self rather than crashing — the #275 registry is open-ended.
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
function verdictFor(
  status: SimulationStatus,
  result: SimulationResult | null,
): { label: string; fg: string } {
  if (status === "failed")
    return { label: "RUN FAILED — NO VERDICT", fg: TOKENS.alert };
  if (status !== "complete" || !result)
    return { label: "READING IN PROGRESS", fg: TOKENS.inkMuted };
  // #311 / T2 — instrument-fit abstention takes precedence over the numeric
  // ship/directional verdict (DESIGN.md §8.2): when the OEC is unresolvable by a
  // first-exposure single-session panel, the score is still computed but the
  // ship/no-ship verdict is categorically WITHHELD. This composes with the
  // `underpowered_design` flip below — abstention is the outermost branch.
  // `ink-muted` like UNDERPOWERED: a measurement-scope condition, not an alarm.
  if (result.instrument_scope === "out_of_scope")
    return { label: "NOT ANSWERABLE BY THIS INSTRUMENT", fg: TOKENS.inkMuted };
  const underpowered = (result.weaknesses ?? []).some(
    (w) => w.category === "underpowered_design",
  );
  if (underpowered)
    return { label: "UNDERPOWERED — TREAT AS DIRECTIONAL", fg: TOKENS.inkMuted };
  const s = result.confidence_score;
  if (s >= DECISION_POLICY.threshold)
    return { label: "HIGH SIM AGREEMENT · SHIP CANDIDATE", fg: TOKENS.success };
  if (s >= 60)
    return { label: "DIRECTIONAL — BELOW SHIP THRESHOLD", fg: TOKENS.inkMuted };
  // Codex P3 (#166): a sub-60 score IS low agreement — say so.
  return { label: "LOW SIM AGREEMENT · DO NOT SHIP", fg: TOKENS.alert };
}

const cardStyle: React.CSSProperties = {
  border: `0.75px solid ${TOKENS.rule}`,
  borderRadius: 4,
  padding: 24,
  marginBottom: 24,
  fontFamily: FONT_SANS,
};

const monoLabelStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10,
  letterSpacing: 0.8,
  textTransform: "uppercase",
  color: TOKENS.inkMuted,
};

const glassLabelStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10,
  letterSpacing: 0.8,
  textTransform: "uppercase",
  color: TOKENS.glassMuted,
};

// §9.4 reading choreography. Every class animates FROM a hidden state with
// `backwards` fill, so the element's resting CSS is the settled end frame —
// prefers-reduced-motion simply removes the animations and the panel renders
// fully settled. Fires once per data arrival (the result DOM mounts once;
// polling stops at terminal status).
const PAGE_STYLE = `
@keyframes simd-wipe { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
/* #185: dasharray lives in the keyframes, NOT the class. Browsers compute
   pathLength + non-scaling-stroke + dasharray inconsistently, so a lingering
   dasharray paints the settled line as disconnected dashes. Scoped to the
   animation it reverts to none at the end (no fill-forwards), and
   reduced-motion users (animation: none) never see it at all. */
@keyframes simd-draw { from { stroke-dasharray: 1; stroke-dashoffset: 1; } to { stroke-dasharray: 1; stroke-dashoffset: 0; } }
@keyframes simd-fade { from { opacity: 0; } to { opacity: 1; } }
@keyframes simd-rise { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
@keyframes simd-scalex { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes simd-pulse { 0%, 100% { opacity: 0.45; } 50% { opacity: 1; } }
.simd-wipe { animation: simd-wipe 240ms ${EASE_MECH} backwards; }
.simd-draw { animation: simd-draw 800ms ${EASE_SETTLE} 120ms backwards; }
.simd-num { animation: simd-fade 120ms ease-out 800ms backwards; }
.simd-band { transform-box: fill-box; transform-origin: left center; animation: simd-scalex 220ms ${EASE_MECH} 940ms backwards; }
.simd-lift { animation: simd-fade 800ms ${EASE_SETTLE} 280ms backwards; }
.simd-row { animation: simd-rise 180ms ${EASE_MECH} backwards; }
.simd-late { animation: simd-fade 220ms ease-out 960ms backwards; }
.simd-carrier { animation: simd-pulse 3.4s ease-in-out infinite; }
.simd-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 24px; align-items: start; }
.simd-glassgrid { display: grid; grid-template-columns: 1.4fr 1fr; }
.simd-tele { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }
/* !important: the link sets color inline, which would otherwise win and
   leave ink-on-ink text while the hover background is applied. */
.simd-qbtn:hover { background: ${TOKENS.ink}; color: ${TOKENS.paper} !important; }
@media (max-width: 1023px) { .simd-grid { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 859px) {
  .simd-glassgrid { grid-template-columns: 1fr; }
  .simd-tele { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (prefers-reduced-motion: reduce) {
  .simd-wipe, .simd-draw, .simd-num, .simd-band, .simd-lift, .simd-row, .simd-late { animation: none !important; }
  .simd-carrier { animation: none !important; opacity: 1 !important; }
}
`;

export default function SimulationDetailLegacy() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? "";

  const [sim, setSim] = useState<Simulation | null>(null);
  const [state, setState] = useState<SimulationRunState | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Agent metadata for the persona-grouped table. Lazy: only fetched once
  // the simulation lands in a terminal state and we know which agents ran.
  // #51: now carries sentiment + top_quote so the result-table cells render
  // without N extra fetches (backend joins these from the persisted
  // result_json.per_agent_analyses).
  const [agentMeta, setAgentMeta] = useState<AgentRow[] | null>(null);
  const [agentMetaError, setAgentMetaError] = useState<string | null>(null);
  const hadRunning = useRef(false);
  const [isSettling, setIsSettling] = useState(false);
  // §9.7 live plotting: one accumulated point per observed score reading.
  // The backend exposes no time series; this is the only honest source of a
  // trace — readings the page actually witnessed while polling. Score
  // sources: partial_score (forward-compatible — today's runner never sets
  // it mid-run) and `score.updated` events in the recent-events window
  // (codex P2 on #166). Progress ticks accumulate independently so the
  // instrument shows readings arriving even before any score exists.
  const [livePoints, setLivePoints] = useState<TracePoint[]>([]);
  const [liveTicks, setLiveTicks] = useState<number[]>([]);
  // Inspector rail selection — null = first persona group.
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);

  // Reset settle state when the sim id changes so navigating from a running sim
  // to an already-terminal sim doesn't spuriously fire the aperture-close animation.
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
  //
  // Codex P2 (#166): today's runner only emits a score via the
  // `score.updated` event (at scoring end) — `partial_score` is never set
  // mid-run. So the trace harvests BOTH sources, and progress ticks
  // accumulate from completion counts alone so the glass shows readings
  // arriving even while no score reading exists yet.
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

  // Track when the sim transitions from running → terminal to drive the
  // 800ms aperture-close settle window (DESIGN.md §9.1 + §9.2).
  // useLayoutEffect fires before paint so markAnimating stays true on the
  // terminal render — avoids a one-frame static flash before settle starts.
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
  // Uses the lightweight /simulations/{id}/agents endpoint (one call returning
  // the persona-grouped summary) rather than fanning out N parallel /agents/{id}
  // requests, since the full /agents/{id} route is intentionally stubbed
  // until Phase 4 chat lands.
  //
  // Key on simulation id + terminal status so a polling refresh of `sim`
  // doesn't re-trigger this fetch.
  useEffect(() => {
    if (!sim || !isTerminalStatus(sim.status)) return;
    // Clear any stale error from a prior fetch before deciding what to do.
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

  if (!loaded) {
    return (
      <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px", fontFamily: FONT_SANS }}>
        {/* Honest pending text — no spinner (DESIGN.md §10). */}
        <p style={{ textAlign: "center", color: TOKENS.inkMuted, fontSize: 14, fontFamily: FONT_MONO, letterSpacing: 0.5 }}>
          LOADING SIMULATION&hellip;
        </p>
      </main>
    );
  }

  if (notFound) {
    return (
      <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px", fontFamily: FONT_SANS }}>
        <h1 style={{ fontSize: 22, color: TOKENS.ink, marginBottom: 12, fontFamily: FONT_NARROW }}>
          Simulation not found
        </h1>
        <p style={{ color: TOKENS.inkMuted, fontSize: 16 }}>
          No simulation exists with id <code style={{ fontFamily: FONT_MONO }}>{id}</code>.
        </p>
        <p style={{ marginTop: 16 }}>
          <Link href="/simulations" style={{ color: TOKENS.ink }}>
            ← Back to simulations
          </Link>
        </p>
      </main>
    );
  }

  if (!sim) {
    return (
      <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px", fontFamily: FONT_SANS }}>
        <p
          role="alert"
          style={{
            color: TOKENS.ink,
            fontSize: 14,
            padding: "12px 16px",
            background: TOKENS.paperRecessed,
            border: `0.75px solid ${TOKENS.alert}`,
            borderRadius: 2,
            margin: 0,
            maxWidth: "52ch",
          }}
        >
          {error ?? "Unable to load simulation."}
        </p>
      </main>
    );
  }

  const status = sim.status;
  const statusColor = STATUS_COLORS[status];
  const terminal = isTerminalStatus(status);
  const markAnimating = !terminal || isSettling;
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
  // at the HEADER and every downstream ship/no-ship policy readout (glass
  // decision-rule, CI clears-threshold clause, A/B "ship candidate") must be
  // suppressed too — the raw agreement reading still prints (the score is
  // computed), but no ship/no-ship judgment is rendered against it.
  const abstained = completeResult?.instrument_scope === "out_of_scope";
  const personaGroups = agentMeta != null ? groupAgents(agentMeta) : null;
  const personaCount = personaGroups != null ? personaGroups.length : null;
  const model = modelDisplay(sim.model_id ?? null);

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

  return (
    <main style={{ maxWidth: 1320, margin: "32px auto", padding: "0 24px", fontFamily: FONT_SANS }}>
      <style dangerouslySetInnerHTML={{ __html: PAGE_STYLE }} />
      {error && (
        <div
          role="alert"
          style={{
            border: `0.75px solid ${TOKENS.alert}`,
            background: TOKENS.paperRecessed,
            // alert is accent-only (border) — message in ink (§4.3/§7.7).
            color: TOKENS.ink,
            borderRadius: 2,
            padding: "8px 12px",
            marginBottom: 16,
            fontSize: 13,
            fontFamily: FONT_SANS,
          }}
        >
          {error}
        </div>
      )}

      <div className="simd-grid">
        {/* ── Evidence column ─────────────────────────────────────────── */}
        <div style={{ minWidth: 0 }}>
          {/* Zone 1 — hypothesis header strip (§7.2) */}
          <section style={{ ...cardStyle, paddingBottom: 20 }}>
            <div style={{ ...monoLabelStyle, marginBottom: 12 }}>
              <Link href="/simulations" style={{ color: TOKENS.inkMuted, textDecoration: "none" }}>
                SIMULATIONS
              </Link>
              {" / "}
              <span style={{ color: TOKENS.ink }}>SIM-{sim.id.slice(0, 8).toUpperCase()}</span>
            </div>

            {/* Lineage rail — SIMULATED → DECISION only. No live-outcome
                stage exists yet (ledger empty); inventing one would be
                synthetic lineage. */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                ...monoLabelStyle,
                marginBottom: 16,
              }}
            >
              <span
                aria-hidden
                style={{
                  width: 6,
                  height: 6,
                  background: status === "failed" ? TOKENS.alert : TOKENS.ink,
                  display: "inline-block",
                }}
              />
              <span style={{ color: TOKENS.ink }}>SIMULATED</span>
              <span
                aria-hidden
                style={{ width: 32, height: 0.75, background: TOKENS.rule, display: "inline-block" }}
              />
              <span
                aria-hidden
                style={{
                  width: 6,
                  height: 6,
                  display: "inline-block",
                  background: status === "complete" ? TOKENS.ink : "transparent",
                  border: `0.75px solid ${status === "complete" ? TOKENS.ink : TOKENS.inkMuted}`,
                }}
              />
              <span style={{ color: status === "complete" ? TOKENS.ink : TOKENS.inkMuted }}>
                DECISION
              </span>
              <span style={{ color: TOKENS.inkMuted }}>· NO LIVE OUTCOMES IN THIS LINEAGE</span>
            </div>

            <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
              <ApertureMark size={32} animating={markAnimating} />
              <div style={{ minWidth: 0, flex: 1 }}>
                <h1
                  style={{
                    fontSize: 24,
                    lineHeight: 1.3,
                    color: TOKENS.ink,
                    margin: 0,
                    marginBottom: 10,
                    fontWeight: 600,
                    fontFamily: FONT_NARROW,
                  }}
                >
                  {sim.hypothesis.prose}
                </h1>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  {/* Decision-rule primitive (§8.1): verdict chip never
                      renders without its policy designator. */}
                  <span
                    style={{
                      fontFamily: FONT_MONO,
                      fontSize: 11,
                      letterSpacing: 0.6,
                      padding: "3px 8px",
                      borderRadius: 2,
                      background: TOKENS.paperRecessed,
                      border: `0.75px solid ${TOKENS.rule}`,
                      color: verdict.fg,
                      fontWeight: 600,
                    }}
                  >
                    {verdict.label}
                  </span>
                  <span style={{ ...monoLabelStyle }}>POLICY {DECISION_POLICY.id}</span>
                </div>
                <div
                  style={{
                    ...monoLabelStyle,
                    marginTop: 8,
                    letterSpacing: 0.5,
                    lineHeight: 1.6,
                    textTransform: "none",
                    ...TNUM,
                  }}
                >
                  {whyLine}
                </div>
                {/* #311 / T2 — instrument-scope abstention note. Inspectable
                    named reasons (DESIGN.md §8.2 / refuse-list optics): the
                    withheld verdict always carries WHY it was withheld. Reuses
                    the §7.7 note anatomy on a hairline `rule` border with the
                    message in `ink` — a data condition, NOT an alarm, so no
                    semantic tone (matches the verdict-chip law §8.2). */}
                {completeResult?.instrument_scope === "out_of_scope" &&
                  (completeResult.out_of_scope_reasons ?? []).length > 0 && (
                    <div
                      style={{
                        marginTop: 12,
                        border: `0.75px solid ${TOKENS.rule}`,
                        background: TOKENS.paperRecessed,
                        borderRadius: 2,
                        padding: "10px 12px",
                      }}
                    >
                      <div style={{ ...monoLabelStyle, marginBottom: 6 }}>
                        INSTRUMENT SCOPE — VERDICT WITHHELD
                      </div>
                      <ul
                        style={{
                          margin: 0,
                          paddingLeft: 18,
                          color: TOKENS.ink,
                          fontFamily: FONT_SANS,
                          fontSize: 13,
                          lineHeight: 1.5,
                        }}
                      >
                        {(completeResult.out_of_scope_reasons ?? []).map((r, i) => (
                          <li key={i} style={{ marginBottom: 4 }}>
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                {/* #312 / T3 — pre-flight input-lint disclosure (degrade-and-
                    disclose). UNLIKE the T2 abstention above, this does NOT
                    withhold the verdict — the run produced its normal reading
                    and this note sits alongside as a disclosed INPUT limitation
                    (vague / leading prose, or an indeterminate paraphrase-
                    unstable verdict). A data caution, NOT an alarm: reuses the
                    §7.7 note anatomy on a hairline `rule` border with the
                    message in `ink` — no semantic tone (matches the verdict-chip
                    law §8.2). */}
                {completeResult?.input_flags &&
                  (() => {
                    const flags = completeResult.input_flags;
                    const abstain = flags.state === "abstain";
                    return (
                      <div
                        style={{
                          marginTop: 12,
                          border: `0.75px solid ${TOKENS.rule}`,
                          background: TOKENS.paperRecessed,
                          borderRadius: 2,
                          padding: "10px 12px",
                        }}
                      >
                        <div style={{ ...monoLabelStyle, marginBottom: 6 }}>
                          {abstain
                            ? "INPUT LINT — INDETERMINATE, PLEASE CLARIFY"
                            : "INPUT LINT — DISCLOSED LIMITATION"}
                        </div>
                        <ul
                          style={{
                            margin: 0,
                            paddingLeft: 18,
                            color: TOKENS.ink,
                            fontFamily: FONT_SANS,
                            fontSize: 13,
                            lineHeight: 1.5,
                          }}
                        >
                          {(flags.reasons ?? []).map((r, i) => (
                            <li key={i} style={{ marginBottom: 4 }}>
                              {r}
                            </li>
                          ))}
                        </ul>
                        {(flags.fixes ?? []).length > 0 && (
                          <>
                            <div style={{ ...monoLabelStyle, marginTop: 8, marginBottom: 6 }}>
                              SUGGESTED FIXES
                            </div>
                            <ul
                              style={{
                                margin: 0,
                                paddingLeft: 18,
                                color: TOKENS.ink,
                                fontFamily: FONT_SANS,
                                fontSize: 13,
                                lineHeight: 1.5,
                              }}
                            >
                              {(flags.fixes ?? []).map((f, i) => (
                                <li key={i} style={{ marginBottom: 4 }}>
                                  {f}
                                </li>
                              ))}
                            </ul>
                          </>
                        )}
                      </div>
                    );
                  })()}
              </div>
            </div>

            {/* Telemetry strip — wipes in (§9.4, 0–240ms). */}
            <div
              className="simd-tele simd-wipe"
              style={{
                marginTop: 20,
                paddingTop: 14,
                borderTop: `0.75px solid ${TOKENS.rule}`,
              }}
            >
              <TeleCell label="MODEL" value={model ? model.label : "—"} />
              <TeleCell label="CAPABILITY" value={sim.hypothesis.capability_name} />
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
              <div style={{ minWidth: 0 }}>
                <div style={{ ...monoLabelStyle, marginBottom: 4 }}>STATUS</div>
                <div
                  style={{
                    fontSize: 13,
                    color: statusColor.fg,
                    fontFamily: FONT_MONO,
                    textTransform: "uppercase",
                    letterSpacing: 0.6,
                    display: "inline-block",
                  }}
                >
                  {status}
                  {/* §9.5 live carrier — 2px lime underline, 3.4s breathe.
                      The only resting lime on this page; carrier, not text. */}
                  {status === "running" && (
                    <span
                      aria-hidden
                      className="simd-carrier"
                      style={{ display: "block", height: 2, background: TOKENS.signal, marginTop: 3 }}
                    />
                  )}
                </div>
              </div>
            </div>
          </section>

          {/* Failure card */}
          {status === "failed" && (
            <section
              role="alert"
              style={{
                ...cardStyle,
                border: `0.75px solid ${TOKENS.alert}`,
                background: TOKENS.paperRecessed,
              }}
            >
              <h2 style={{ fontSize: 18, color: TOKENS.ink, margin: 0, marginBottom: 8, fontFamily: FONT_NARROW }}>
                Simulation failed
              </h2>
              <div
                style={{
                  fontFamily: FONT_MONO,
                  fontSize: 13,
                  // severity lives on the card's alert border — the words
                  // read in ink (§4.3/§7.7).
                  color: TOKENS.ink,
                  whiteSpace: "pre-wrap",
                }}
              >
                {state?.error ?? "Unknown error."}
              </div>
            </section>
          )}

          {/* Zone 2 — glass instrument (live readings only, §4.2). */}
          {completeResult != null && (
            <GlassPanelComplete
              sim={sim}
              result={completeResult}
              livePoints={livePoints}
              personaCount={personaCount}
              abstained={abstained}
            />
          )}
          {!terminal && (
            <GlassPanelLive
              livePoints={livePoints}
              liveTicks={liveTicks}
              done={done}
              total={agentsTotal}
              failed={agentsFailed}
            />
          )}

          {/* Per-metric lift card (#280) — native-unit behavioral reading
              ALONGSIDE the glass sentiment confidence above. Self-gates on
              metric_name: renders nothing for a sentiment-only run (the
              default), an honest empty-state when the metric was requested but
              no paired lift could be computed. */}
          {completeResult != null && (
            <MetricLiftCard result={completeResult} />
          )}

          {/* Run log — honest event feed; the trace above is the progress
              indicator (§9.7 — no progress bar, no spinner). */}
          {!terminal && (
            <section style={cardStyle}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 12 }}>
                <h2 style={{ ...monoLabelStyle, fontSize: 11, margin: 0 }}>RUN LOG</h2>
                {state?.phase && (
                  <span style={{ ...monoLabelStyle, letterSpacing: 0.5 }}>
                    PHASE: {state.phase}
                  </span>
                )}
                {agentsFailed > 0 && (
                  <span style={{ ...monoLabelStyle, color: TOKENS.alert, letterSpacing: 0.5 }}>
                    {agentsFailed} FAILED
                  </span>
                )}
              </div>
              {recent.length === 0 ? (
                <div style={{ fontFamily: FONT_MONO, fontSize: 12, color: TOKENS.inkMuted }}>
                  AWAITING FIRST EVENT
                </div>
              ) : (
                <ul
                  style={{
                    listStyle: "none",
                    padding: 12,
                    margin: 0,
                    background: TOKENS.paperElevated,
                    borderRadius: 2,
                    fontFamily: FONT_MONO,
                    fontSize: 12,
                    color: TOKENS.ink,
                    ...TNUM,
                  }}
                >
                  {recent.map((ev, i) => (
                    <li key={`${ev.at}-${i}`} style={{ padding: "2px 0" }}>
                      {describeEvent(ev)}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {/* Degraded A/B notes — paper, below the glass. Gated on
              sim.arm_split (request-level ground truth, codex R1-P2/R4-P2). */}
          {completeResult != null && hasLift && (
            <LiftDegradedNotes result={completeResult} />
          )}

          {completeResult != null && hasLift && (
            <PerArmDetailCard
              treatmentScore={completeResult.treatment_score ?? completeResult.confidence_score}
              treatmentCi={completeResult.confidence_score_ci ?? null}
              controlScore={completeResult.control_score ?? null}
              sampledAgentCount={sim.sampled_agent_count ?? null}
              abstained={abstained}
            />
          )}

          {/* Phase 5 #101: cohort banner — only for persona-filtered runs. */}
          {status === "complete" && sim.selected_personas != null && (
            <CohortBanner selectedIds={sim.selected_personas} agentMeta={agentMeta} />
          )}

          {/* Weakness register (§8.4 — bare bars, no tracks). */}
          {(status === "complete" || status === "running") && (
            <WeaknessRegister result={completeResult} running={!terminal} />
          )}

          {/* Refinement queue */}
          {completeResult?.refinement_suggestions != null &&
            completeResult.refinement_suggestions.length > 0 && (
              <RefinementQueue suggestions={completeResult.refinement_suggestions} />
            )}

          {/* Method card */}
          {completeResult != null && (
            <MethodCard modelId={sim.model_id ?? null} hasLift={hasLift} abstained={abstained} />
          )}

          {/* Cohort register — agents that participated */}
          {agentIds.length > 0 && (
            <section style={cardStyle}>
              <h2 style={{ ...monoLabelStyle, fontSize: 11, margin: 0, marginBottom: 16 }}>
                COHORT REGISTER — AGENTS THAT PARTICIPATED
              </h2>
              {agentMetaError && (
                <div
                  role="alert"
                  style={{
                    fontSize: 13,
                    color: TOKENS.ink,
                    marginBottom: 12,
                    padding: "8px 12px",
                    background: TOKENS.paperRecessed,
                    border: `0.75px solid ${TOKENS.alert}`,
                    borderRadius: 2,
                  }}
                >
                  Persona breakdown failed to load ({agentMetaError}). Showing raw IDs below.
                </div>
              )}
              {agentMeta == null && !agentMetaError && (
                <div style={{ fontFamily: FONT_MONO, fontSize: 12, color: TOKENS.inkMuted, marginBottom: 12 }}>
                  REGISTER PENDING — {agentIds.length} AGENT
                  {agentIds.length === 1 ? "" : "S"} TO JOIN
                </div>
              )}
              {agentMeta != null ? (
                <PersonaGroupedAgents agents={agentMeta} />
              ) : (
                <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {agentIds.map((aid, i) => (
                    <li
                      key={aid}
                      style={{
                        padding: "8px 0",
                        borderTop: i === 0 ? "none" : `0.75px solid ${TOKENS.rule}`,
                        fontFamily: FONT_MONO,
                        fontSize: 14,
                      }}
                    >
                      <Link
                        href={`/agents/${aid}`}
                        style={{ color: TOKENS.ink, textDecoration: "underline", textDecorationColor: TOKENS.rule }}
                      >
                        {aid.slice(0, 8)}
                      </Link>
                      <span style={{ color: TOKENS.inkMuted, marginLeft: 8, fontSize: 12 }}>
                        {aid}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </div>

        {/* ── Zone 3 — inspector rail (§7.2, 340px paper-elevated) ────── */}
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
    </main>
  );
}

function TeleCell({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ minWidth: 0 }}>
      <div style={{ ...monoLabelStyle, marginBottom: 4 }}>{label}</div>
      <div
        style={{
          fontSize: 13,
          color: TOKENS.ink,
          fontFamily: FONT_MONO,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          ...TNUM,
        }}
        title={value}
      >
        {value}
      </div>
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────
// Glass instrument — DESIGN.md §4.2 / §8.2 / §9.4 / §9.7.
// ───────────────────────────────────────────────────────────────────────

// Trace geometry: viewBox 0..100 × 0..56, stretched to the container with
// preserveAspectRatio="none". Only lines/rects/paths live inside the SVG
// (non-scaling strokes); ALL text labels are HTML overlay rows so glyphs
// never stretch.
const TRACE_H = 56;
const traceY = (score: number) =>
  52 - (Math.max(0, Math.min(100, score)) / 100) * 48;
const traceX = (t: number) => Math.max(0, Math.min(1, t)) * 100;

function tracePath(pts: TracePoint[], flatFullWidth: boolean): string {
  if (pts.length === 0) return "";
  if (pts.length === 1) {
    const y = traceY(pts[0].y).toFixed(2);
    if (flatFullWidth) return `M 0 ${y} L 100 ${y}`;
    const x = traceX(pts[0].x);
    return `M ${Math.max(0, x - 1).toFixed(2)} ${y} L ${Math.min(100, x + 1).toFixed(2)} ${y}`;
  }
  return pts
    .map(
      (p, i) =>
        `${i === 0 ? "M" : "L"} ${traceX(p.x).toFixed(2)} ${traceY(p.y).toFixed(2)}`,
    )
    .join(" ");
}

function GlassTrace({
  points,
  ticks = [],
  settle,
  flatFullWidth,
  readingsLabel,
  emptyLabel = "AWAITING FIRST READING",
}: {
  points: TracePoint[];
  // Progress ticks (live runs): one baseline tick per observed completion
  // fraction. Honest "readings are arriving" signal for the window where no
  // score reading exists yet (codex P2 on #166 — today's backend emits the
  // score only at scoring end).
  ticks?: number[];
  settle: boolean;
  flatFullWidth: boolean;
  readingsLabel: string;
  emptyLabel?: string;
}) {
  const d = tracePath(points, flatFullWidth);
  const thrY = traceY(DECISION_POLICY.threshold).toFixed(2);
  return (
    <div style={{ position: "relative", height: 120, margin: "10px 0 4px" }}>
      <svg
        viewBox={`0 0 100 ${TRACE_H}`}
        preserveAspectRatio="none"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", display: "block" }}
        aria-hidden
      >
        {/* Threshold reference — part of the instrument, not the data. */}
        <line
          x1="0"
          y1={thrY}
          x2="100"
          y2={thrY}
          stroke={TOKENS.glassMuted}
          strokeWidth={1}
          strokeDasharray="1.5 1.5"
          vectorEffect="non-scaling-stroke"
        />
        {/* Baseline progress ticks — lime is the live-state carrier (§4.2). */}
        {ticks.map((t) => (
          <line
            key={t}
            x1={traceX(t)}
            y1={traceY(0)}
            x2={traceX(t)}
            y2={traceY(0) - 3}
            stroke={TOKENS.signal}
            strokeWidth={1}
            opacity={0.7}
            vectorEffect="non-scaling-stroke"
          />
        ))}
        {d !== "" && (
          <>
            {/* Phosphor underdraw — same path, wide + faint. */}
            <path
              className={settle ? "simd-draw" : undefined}
              d={d}
              fill="none"
              stroke={TOKENS.signal}
              strokeWidth={5}
              opacity={0.18}
              vectorEffect="non-scaling-stroke"
              pathLength={1}
            />
            <path
              className={settle ? "simd-draw" : undefined}
              d={d}
              fill="none"
              stroke={TOKENS.signal}
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
              pathLength={1}
            />
          </>
        )}
      </svg>
      {d === "" && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            ...glassLabelStyle,
          }}
        >
          {emptyLabel}
        </div>
      )}
      {/* HTML overlay labels (never stretched SVG text). */}
      <div style={{ position: "absolute", top: 2, right: 0, ...glassLabelStyle, fontSize: 9 }}>
        THR {DECISION_POLICY.threshold}
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: -14,
          display: "flex",
          justifyContent: "space-between",
          ...glassLabelStyle,
          fontSize: 9,
          ...TNUM,
        }}
      >
        <span>0</span>
        <span>READINGS</span>
        <span>{readingsLabel}</span>
      </div>
    </div>
  );
}

// CI axis on glass: baseline + ticks + dashed threshold + CI band (scaleX
// settle) + lime point marker. Labels live in HTML rows above/below.
function GlassCiAxis({
  score,
  ciLow,
  ciHigh,
  abstained = false,
}: {
  score: number;
  ciLow: number | null;
  ciHigh: number | null;
  abstained?: boolean;
}) {
  const hasCi = ciLow != null && ciHigh != null;
  const { v, lo, hi } = _safeRange(score, ciLow ?? score, ciHigh ?? score, 0, 100);
  const collapsed = !hasCi || hi - lo < _CI_COLLAPSE_THRESHOLD;
  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          ...glassLabelStyle,
          fontSize: 9,
          marginBottom: 2,
        }}
      >
        <span>AGREEMENT SCALE 0–100</span>
        <span>THR {DECISION_POLICY.threshold}</span>
      </div>
      <svg
        viewBox="0 0 100 20"
        preserveAspectRatio="none"
        style={{ width: "100%", height: 28, display: "block" }}
        aria-hidden
      >
        <line x1="0" y1="14" x2="100" y2="14" stroke={TOKENS.glassRule} strokeWidth={1} vectorEffect="non-scaling-stroke" />
        {[0, 25, 50, 75, 100].map((t) => (
          <line
            key={t}
            x1={t}
            y1="11"
            x2={t}
            y2="17"
            stroke={TOKENS.glassRule}
            strokeWidth={1}
            vectorEffect="non-scaling-stroke"
          />
        ))}
        <line
          x1={DECISION_POLICY.threshold}
          y1="2"
          x2={DECISION_POLICY.threshold}
          y2="18"
          stroke={TOKENS.glassMuted}
          strokeWidth={1}
          strokeDasharray="1.5 1.5"
          vectorEffect="non-scaling-stroke"
        />
        {!collapsed && (
          <rect
            className="simd-band"
            x={lo}
            y="6"
            width={Math.max(0, hi - lo)}
            height="8"
            fill={TOKENS.glassText}
            fillOpacity={0.13}
          />
        )}
        <line
          x1={v}
          y1="4"
          x2={v}
          y2="16"
          stroke={TOKENS.signal}
          strokeWidth={2}
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          ...glassLabelStyle,
          fontSize: 9,
          marginTop: 2,
          ...TNUM,
        }}
      >
        <span>0</span>
        <span>50</span>
        <span>100</span>
      </div>
      <div style={{ ...glassLabelStyle, marginTop: 8, letterSpacing: 0.5, lineHeight: 1.6, ...TNUM }}>
        {!hasCi
          ? "CI UNAVAILABLE FOR THIS RUN"
          : collapsed
            ? "NARROW INTERVAL — BAND BELOW DISPLAY RESOLUTION"
            : abstained
              ? // #311/T2: show the raw interval but WITHHOLD the clears-threshold
                // judgment — the OEC is outside the instrument's resolving power.
                `95% CI [${lo.toFixed(1)}, ${hi.toFixed(1)}] — THRESHOLD EVALUATION WITHHELD (OEC OUT OF SCOPE)`
              : `95% CI [${lo.toFixed(1)}, ${hi.toFixed(1)}] — LOWER BOUND ${
                  lo >= DECISION_POLICY.threshold ? "CLEARS" : "DOES NOT CLEAR"
                } THRESHOLD ${DECISION_POLICY.threshold}`}
      </div>
    </div>
  );
}

// Paired-lift axis: delta scale centred on the control baseline (0). The
// treatment tick is the live marker; the CI band is glassText at 0.13.
function GlassLiftAxis({ lift, ci }: { lift: number; ci: [number, number] | null }) {
  const vals = [0, lift, ...(ci ?? [])];
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const span = Math.max(hi - lo, 1);
  const pad = span * 0.18;
  const min = lo - pad;
  const max = hi + pad;
  const xOf = (v: number) => ((v - min) / (max - min)) * 100;
  const clampPct = (p: number) => Math.max(8, Math.min(92, p));
  const sign = lift > 0 ? "+" : lift < 0 ? "−" : "±";
  return (
    <div style={{ position: "relative", paddingTop: 14, paddingBottom: 14 }}>
      <span
        style={{
          position: "absolute",
          top: 0,
          left: `${clampPct(xOf(lift))}%`,
          transform: "translateX(-50%)",
          ...glassLabelStyle,
          fontSize: 9,
          color: TOKENS.glassText,
          whiteSpace: "nowrap",
          ...TNUM,
        }}
      >
        T {sign}{Math.abs(lift).toFixed(1)}
      </span>
      <svg
        viewBox="0 0 100 16"
        preserveAspectRatio="none"
        style={{ width: "100%", height: 24, display: "block" }}
        aria-hidden
      >
        <line x1="0" y1="8" x2="100" y2="8" stroke={TOKENS.glassRule} strokeWidth={1} vectorEffect="non-scaling-stroke" />
        {ci != null && (
          <rect
            className="simd-band"
            x={Math.min(xOf(ci[0]), xOf(ci[1]))}
            y="4"
            width={Math.abs(xOf(ci[1]) - xOf(ci[0]))}
            height="8"
            fill={TOKENS.glassText}
            fillOpacity={0.13}
          />
        )}
        <line
          x1={xOf(0)}
          y1="1"
          x2={xOf(0)}
          y2="15"
          stroke={TOKENS.glassMuted}
          strokeWidth={1}
          strokeDasharray="1.5 1.5"
          vectorEffect="non-scaling-stroke"
        />
        <line
          x1={xOf(lift)}
          y1="2"
          x2={xOf(lift)}
          y2="14"
          stroke={TOKENS.signal}
          strokeWidth={2}
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <span
        style={{
          position: "absolute",
          bottom: 0,
          left: `${clampPct(xOf(0))}%`,
          transform: "translateX(-50%)",
          ...glassLabelStyle,
          fontSize: 9,
          whiteSpace: "nowrap",
        }}
      >
        C 0 (BASELINE)
      </span>
    </div>
  );
}

function GlassPanelComplete({
  sim,
  result,
  livePoints,
  personaCount,
  abstained = false,
}: {
  sim: Simulation;
  result: SimulationResult;
  livePoints: TracePoint[];
  personaCount: number | null;
  abstained?: boolean;
}) {
  const hasLift = sim.arm_split != null;
  const ci = result.confidence_score_ci ?? null;
  const lift = result.lift ?? null;
  const liftCi = result.lift_ci ?? null;
  const pairedN = result.lift_paired_n ?? null;
  const nReadings = (sim.agent_instance_ids ?? []).length;

  // Settled trace = every point the page witnessed live, plus the final
  // reading. A page opened after completion has no witnessed points — the
  // trace settles as a flat line at the final score (honest: one reading).
  const pts: TracePoint[] = [...livePoints];
  const last = pts[pts.length - 1];
  if (!last || last.x !== 1 || last.y !== result.confidence_score) {
    pts.push({ x: 1, y: result.confidence_score });
  }

  const liftCrossesZero = liftCi != null && liftCi[0] <= 0 && liftCi[1] >= 0;
  const liftSign = lift == null ? "" : lift > 0 ? "+" : lift < 0 ? "−" : "±";

  return (
    <section
      style={{
        background: TOKENS.glass,
        border: `0.75px solid ${TOKENS.glassRule}`,
        borderRadius: 4,
        marginBottom: 24,
        overflow: "hidden",
        fontFamily: FONT_SANS,
      }}
    >
      <div
        className="simd-glassgrid"
        style={hasLift ? undefined : { gridTemplateColumns: "1fr" }}
      >
        <div
          style={{
            padding: 20,
            borderRight: hasLift ? `0.75px solid ${TOKENS.glassRule}` : undefined,
            minWidth: 0,
          }}
        >
          {/* Honesty containment: raw + uncalibrated, in the headline. */}
          <div style={glassLabelStyle}>
            SIMULATION AGREEMENT — RAW, UNCALIBRATED (LEDGER EMPTY)
          </div>
          <GlassTrace
            points={pts}
            settle
            flatFullWidth
            readingsLabel={`${nReadings}`}
          />
          {/* #185: a flat full-width line drawn from a single reading must
              say so — otherwise it reads as N identical readings. Only
              mid-run readings (x < 1) give the trace a real shape; a page
              opened after completion still harvests the terminal
              score.updated event into livePoints at x = 1 (codex P2). */}
          {!livePoints.some((p) => p.x < 1) && (
            <div style={{ ...glassLabelStyle, fontSize: 9, marginTop: 18 }}>
              FLAT LINE = FINAL READING ONLY — NO MID-RUN TRACE WITNESSED
            </div>
          )}
          <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginTop: 20 }}>
            <div
              className="simd-num"
              style={{
                fontSize: 64,
                fontWeight: 600,
                lineHeight: 1,
                color: TOKENS.glassText,
                fontFamily: FONT_MONO,
                ...TNUM,
              }}
            >
              {result.confidence_score.toFixed(1)}
            </div>
            <div style={{ ...glassLabelStyle, fontSize: 10 }}>AGREEMENT / 100</div>
          </div>
          {/* Decision-rule readout (§8.1). #311/T2: an abstained run shows NO
              threshold/margin policy evaluation — the agreement number above is
              a raw reading, but the ship/no-ship judgment is withheld. */}
          {abstained ? (
            <div
              style={{
                ...glassLabelStyle,
                margin: "14px 0 16px",
                lineHeight: 1.6,
                letterSpacing: 0.5,
              }}
            >
              POLICY {DECISION_POLICY.id} WITHHELD — OEC OUTSIDE INSTRUMENT SCOPE
              <br />
              RAW AGREEMENT SHOWN; NO THRESHOLD EVALUATION
            </div>
          ) : (
            <div
              className="simd-num"
              style={{
                display: "flex",
                gap: 20,
                flexWrap: "wrap",
                margin: "14px 0 16px",
                ...TNUM,
              }}
            >
              <GlassKv k="THRESHOLD" v={`${DECISION_POLICY.threshold} / 100`} />
              <GlassKv
                k="MARGIN"
                v={`${result.confidence_score >= DECISION_POLICY.threshold ? "+" : "−"}${Math.abs(
                  result.confidence_score - DECISION_POLICY.threshold,
                ).toFixed(1)}`}
              />
              <GlassKv k="POLICY" v={DECISION_POLICY.id} />
            </div>
          )}
          <GlassCiAxis
            score={result.confidence_score}
            ciLow={ci != null ? ci[0] : null}
            ciHigh={ci != null ? ci[1] : null}
            abstained={abstained}
          />
        </div>

        {hasLift && (
          <div className="simd-lift" style={{ padding: 20, minWidth: 0 }}>
            <div style={glassLabelStyle}>
              PAIRED LIFT — TREATMENT − CONTROL (CONFIDENCE POINTS)
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 10, margin: "18px 0 6px" }}>
              <div
                style={{
                  fontSize: 40,
                  fontWeight: 600,
                  lineHeight: 1,
                  color: TOKENS.glassText,
                  fontFamily: FONT_MONO,
                  ...TNUM,
                }}
                aria-label={
                  lift == null
                    ? "Paired lift not available"
                    : `Paired lift ${lift >= 0 ? "plus" : "minus"} ${Math.abs(lift).toFixed(1)} confidence points`
                }
              >
                {lift == null ? "—.—" : `${liftSign}${Math.abs(lift).toFixed(1)}`}
              </div>
              {lift != null && <div style={{ ...glassLabelStyle, fontSize: 10 }}>PTS</div>}
            </div>
            {lift != null ? (
              <>
                <GlassLiftAxis lift={lift} ci={liftCi} />
                <div
                  style={{
                    ...glassLabelStyle,
                    letterSpacing: 0.5,
                    lineHeight: 1.7,
                    marginTop: 8,
                    ...TNUM,
                  }}
                >
                  {liftCi != null &&
                    `95% CI [${liftCi[0] >= 0 ? "+" : ""}${liftCi[0].toFixed(1)}, ${
                      liftCi[1] >= 0 ? "+" : ""
                    }${liftCi[1].toFixed(1)}]`}
                  {pairedN != null && pairedN > 0 && ` · n = ${pairedN} PAIRED`}
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
              </>
            ) : (
              <div style={{ ...glassLabelStyle, letterSpacing: 0.5, lineHeight: 1.7 }}>
                LIFT UNCOMPUTABLE — SEE NOTE BELOW THE GLASS
              </div>
            )}
          </div>
        )}
      </div>

      <GlassFooter
        left={`n = ${nReadings} READINGS · ${
          personaCount != null ? personaCount : "—"
        } PERSONAS · SEED ${sim.run_seed ?? "—"} (SINGLE RUN — NO SEED-VARIANCE ESTIMATE)`}
      />
    </section>
  );
}

function GlassPanelLive({
  livePoints,
  liveTicks,
  done,
  total,
  failed,
}: {
  livePoints: TracePoint[];
  liveTicks: number[];
  done: number;
  total: number;
  failed: number;
}) {
  return (
    <section
      style={{
        background: TOKENS.glass,
        border: `0.75px solid ${TOKENS.glassRule}`,
        borderRadius: 4,
        marginBottom: 24,
        overflow: "hidden",
        fontFamily: FONT_SANS,
      }}
    >
      <div style={{ padding: 20 }}>
        <div style={glassLabelStyle}>
          SIMULATION AGREEMENT — LIVE READING (RAW, UNCALIBRATED)
        </div>
        {/* §9.7: readings plot as they arrive from poll ticks; the trace is
            the progress indicator. No settle classes while live. Baseline
            ticks carry progress while no score reading exists — today's
            backend only emits a score at the scoring phase. */}
        <GlassTrace
          points={livePoints}
          ticks={liveTicks}
          settle={false}
          flatFullWidth={false}
          readingsLabel={total > 0 ? `${done} OF ${total}` : "—"}
          emptyLabel="AWAITING SCORE READING — PRINTS AT SCORING PHASE"
        />
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginTop: 20 }}>
          <div
            style={{
              fontSize: 64,
              fontWeight: 600,
              lineHeight: 1,
              color: TOKENS.glassMuted,
              fontFamily: FONT_MONO,
              ...TNUM,
            }}
            aria-label="Reading in progress"
          >
            ——
          </div>
          <div style={{ ...glassLabelStyle, fontSize: 10 }}>READING IN PROGRESS</div>
        </div>
      </div>
      <GlassFooter
        left={`n = ${total > 0 ? `${done} OF ${total}` : "—"} READINGS${
          failed > 0 ? ` · ${failed} FAILED` : ""
        }`}
      />
    </section>
  );
}

function GlassKv({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <div style={{ ...glassLabelStyle, fontSize: 9, marginBottom: 2 }}>{k}</div>
      <div style={{ fontFamily: FONT_MONO, fontSize: 13, color: TOKENS.glassText, ...TNUM }}>
        {v}
      </div>
    </div>
  );
}

function GlassFooter({ left }: { left: string }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        gap: 16,
        flexWrap: "wrap",
        padding: "10px 20px",
        borderTop: `0.75px solid ${TOKENS.glassRule}`,
        ...glassLabelStyle,
        fontSize: 9,
        ...TNUM,
      }}
    >
      <span>{left}</span>
      {/* Honesty containment footer — no live outcomes have graded this run. */}
      <span>UNGRADED — NO LIVE OUTCOMES YET</span>
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────
// Paper notes below the glass — degraded A/B shapes (codex R1-P2 / R4-P2).
// pairedN === 0  → A/B ran, scoring found no matched pairs.
// pairedN == null → backend returned a single-arm placeholder (no per-arm
// output at all). Both must surface distinctly; drop counters print when
// any agent was excluded from the paired statistic.
// ───────────────────────────────────────────────────────────────────────
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
    <section style={{ ...cardStyle, padding: "14px 18px" }}>
      {noPairs && pairedN != null && (
        <div
          style={{
            fontSize: 13,
            // §7.7 note anatomy — alert border carries severity, prose in ink.
            color: TOKENS.ink,
            lineHeight: 1.5,
            padding: "10px 14px",
            background: TOKENS.paperRecessed,
            border: `0.75px solid ${TOKENS.alert}`,
            borderRadius: 2,
          }}
        >
          <strong>A/B run completed but lift is uncomputable.</strong> No
          matched (treatment, control) pairs were available — every agent in
          at least one arm was dropped (sentiment classification failure, no
          matching paired-sampling key, or one arm produced zero usable
          reactions). The treatment arm&rsquo;s confidence score is shown in
          the per-arm detail, but it is NOT a lift measurement — it&rsquo;s
          only the treatment arm in isolation. See the drop counters for
          which dropout caused this.
        </div>
      )}
      {noPairs && pairedN == null && (
        <div
          style={{
            fontSize: 13,
            color: TOKENS.ink,
            lineHeight: 1.5,
            padding: "10px 14px",
            background: TOKENS.paperRecessed,
            border: `0.75px solid ${TOKENS.alert}`,
            borderRadius: 2,
          }}
        >
          {/* Codex R4-P2: backend returned a generic placeholder result with
              no per-arm fields at all. Common cause: zero successful agents
              in either arm (LLM outage, every agent timing out). Distinct
              from the no-pairs case above — there scoring ran but found no
              pairs; here scoring never produced per-arm output. */}
          <strong>A/B run did not produce per-arm scoring output.</strong>{" "}
          The simulation finished but the backend returned a single-arm
          placeholder result — usually because no agents in either arm
          completed successfully (LLM outage, timeouts, or every agent
          erroring). Re-run the simulation, or check the run state for the
          failure reason.
        </div>
      )}
      {anyDrops && (
        <div
          style={{
            marginTop: noPairs ? 12 : 0,
            paddingTop: noPairs ? 12 : 0,
            borderTop: noPairs ? `0.75px solid ${TOKENS.rule}` : undefined,
            fontSize: 12,
            color: TOKENS.inkMuted,
            lineHeight: 1.5,
            ...TNUM,
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

// ───────────────────────────────────────────────────────────────────────
// Per-metric lift card (#280) — the native-unit behavioral reading that sits
// ALONGSIDE the glass sentiment confidence score, never replacing it.
//
// This is a paper RECORD, not a glass reading (§8 split): `metric_lift_pp` is a
// derived, uncalibrated behavioral statistic — the settle-trace (§9.1) is
// reserved for the confidence score and the sentiment paired-lift on glass, so
// the metric lift renders static in mono tabular numerals on paper.
//
//   • metric_name == null  → the component is never mounted (sentiment-only
//     run, today's default — the result page is byte-identical).
//   • metric_lift_pp == null OR metric_lift_paired_n falsy → honest empty
//     state (requested but uncomputable: empty arm / all elicitations failed),
//     never a NaN/broken card.
//   • metric_lift_relative → printed VERBATIM (§3a honesty: it carries the
//     direction/separation phrasing + the weak-behavioral-signal caveat —
//     never paraphrased or summarised here).
//   • the uncalibrated qualifier is gated on !metric_lift_calibrated (#222);
//     when the backend reports a fitted calibrator the magnitude caveat lifts.
// ───────────────────────────────────────────────────────────────────────
function MetricLiftCard({ result }: { result: SimulationResult }) {
  const metricName = result.metric_name ?? null;
  // Sentiment-only run — render nothing (no card, no layout shift).
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

  // No-lift-computable: the metric was requested but no paired delta exists
  // (empty arm, all turn-2 elicitations failed). Honest empty state — never a
  // NaN headline. paired_n of 0 is the same condition as a null pp.
  const computable = liftPp != null && pairedN != null && pairedN > 0;

  const sign = liftPp == null ? "" : liftPp > 0 ? "+" : liftPp < 0 ? "−" : "±";

  return (
    <section
      style={{
        ...cardStyle,
        padding: "16px 18px",
        background: TOKENS.paperElevated,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 10,
          flexWrap: "wrap",
          marginBottom: 6,
        }}
      >
        <div style={{ ...monoLabelStyle, fontSize: 11 }}>
          {label.toUpperCase()} LIFT — NATIVE UNITS
        </div>
        {/* The metric-lift sits beside (not above) the sentiment confidence
            score — the headline reading stays the glass agreement number. */}
        <div style={{ ...monoLabelStyle, fontSize: 10, letterSpacing: 0.6 }}>
          ALONGSIDE SENTIMENT AGREEMENT
        </div>
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
              style={{
                fontSize: 40,
                fontWeight: 600,
                lineHeight: 1,
                color: TOKENS.ink,
                fontFamily: FONT_MONO,
                ...TNUM,
              }}
              aria-label={`${label} lift ${
                liftPp! >= 0 ? "plus" : "minus"
              } ${Math.abs(liftPp!).toFixed(1)} percentage points`}
            >
              {sign}
              {Math.abs(liftPp!).toFixed(1)}
            </div>
            <div style={{ ...monoLabelStyle, fontSize: 10 }}>PP (PAIRED T−C)</div>
          </div>

          {/* CI + paired-n register — mono tabular, right of the headline pp. */}
          <div
            style={{
              ...monoLabelStyle,
              letterSpacing: 0.5,
              lineHeight: 1.7,
              textTransform: "none",
              ...TNUM,
            }}
          >
            {ciPp != null &&
              `95% CI [${ciPp[0] >= 0 ? "+" : "−"}${Math.abs(ciPp[0]).toFixed(
                1,
              )}, ${ciPp[1] >= 0 ? "+" : "−"}${Math.abs(ciPp[1]).toFixed(
                1,
              )}] PP`}
            {ciPp != null && pairedN != null && " · "}
            {pairedN != null && `n = ${pairedN} PAIRED`}
            {regime != null && (
              <>
                <br />
                REGIME: {regime}
              </>
            )}
          </div>

          {/* The honesty statement — VERBATIM. It carries the direction /
              separation phrasing + the "weak behavioral signal, read as
              rank/direction not calibrated magnitude" caveat. Rendered as the
              §4.3/§8.5 cautionary secondary text (ink-muted body), NOT an
              alarming banner — a data caveat is not an error. */}
          {relative != null && relative.trim() !== "" && (
            <p
              style={{
                margin: "12px 0 0",
                fontSize: 13,
                color: TOKENS.inkMuted,
                lineHeight: 1.5,
                maxWidth: "68ch",
              }}
            >
              {relative}
            </p>
          )}

          {/* Magnitude caveat — gated on !calibrated (#222). If the backend's
              metric_lift_relative already encodes it, this is a backstop; once
              a fitted calibrator lands (calibrated === true) it lifts. */}
          {!calibrated && (
            <p
              style={{
                margin: "8px 0 0",
                fontSize: 12,
                color: TOKENS.inkMuted,
                lineHeight: 1.5,
                maxWidth: "68ch",
              }}
            >
              Uncalibrated — read this lift as rank and direction, not as a
              calibrated effect size. The magnitude is not yet mapped to a
              real-world scale (calibration ledger empty).
            </p>
          )}

          {/* Degraded-confidence warnings — §7.7 note anatomy: warn border
              carries severity (caution, not alarm), the words carry meaning,
              prose in ink. Co-signalled by wording + border (§7.8). */}
          {(unblindedFallback || paraphraseUnstable) && (
            <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
              {unblindedFallback && (
                <div
                  role="note"
                  style={{
                    fontSize: 12,
                    color: TOKENS.ink,
                    lineHeight: 1.5,
                    padding: "8px 12px",
                    background: TOKENS.paperRecessed,
                    border: `0.75px solid ${TOKENS.warn}`,
                    borderRadius: 2,
                  }}
                >
                  <strong>Unblinded fallback.</strong> At least one treatment
                  agent saw the unblinded prompt — the proposed change had no
                  faithful standalone view to blind against. The lift may carry
                  demand-characteristic bias; treat the direction as the signal.
                </div>
              )}
              {paraphraseUnstable && (
                <div
                  role="note"
                  style={{
                    fontSize: 12,
                    color: TOKENS.ink,
                    lineHeight: 1.5,
                    padding: "8px 12px",
                    background: TOKENS.paperRecessed,
                    border: `0.75px solid ${TOKENS.warn}`,
                    borderRadius: 2,
                  }}
                >
                  <strong>Paraphrase-unstable.</strong> At least one
                  identity&rsquo;s metric propensity moved materially across the
                  question paraphrases — its answer was wording-driven. The
                  measured lift is sensitive to prompt phrasing.
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        // No-lift-computable empty state — requested but uncomputable.
        <div
          style={{
            fontSize: 13,
            color: TOKENS.inkMuted,
            lineHeight: 1.5,
            maxWidth: "68ch",
            marginTop: 8,
          }}
        >
          The {label.toLowerCase()} metric was requested, but no paired lift
          could be computed — every agent in at least one arm was dropped (an
          empty arm, or all turn-2 decision elicitations failed). The sentiment
          agreement reading above is unaffected; re-run to collect a paired
          {" "}
          {label.toLowerCase()} delta.
        </div>
      )}
    </section>
  );
}

// ───────────────────────────────────────────────────────────────────────
// Weakness register — §8.4. Bare 2px ink frequency bars on a hairline
// baseline (no tracks, no radius); CI band in warn at token-derived alpha.
// Rows stagger in at 960ms+ (§9.4).
// ───────────────────────────────────────────────────────────────────────
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
      role="img"
      aria-label={`Frequency ${(v * 100).toFixed(0)}% with 95% CI from ${(lo * 100).toFixed(0)}% to ${(hi * 100).toFixed(0)}%`}
      style={{ position: "relative", height: 8 }}
    >
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: 0.75,
          background: TOKENS.rule,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: `${lo * 100}%`,
          width: `${Math.max(0, (hi - lo) * 100)}%`,
          top: 1,
          height: 6,
          // CI band — TOKENS.warn at 35% (accent-only, never text).
          background: `${TOKENS.warn}59`,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 0,
          width: `${v * 100}%`,
          bottom: 0,
          height: 2,
          background: TOKENS.ink,
        }}
      />
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
  const weaknesses = result?.weaknesses ?? [];
  return (
    <section style={cardStyle}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) 220px",
          gap: 16,
          paddingBottom: 8,
          borderBottom: `0.75px solid ${TOKENS.rule}`,
          ...monoLabelStyle,
          fontSize: 11,
        }}
      >
        <span>WEAKNESS REGISTER — FINDING</span>
        <span>FREQUENCY (95% CI)</span>
      </div>
      {running ? (
        <div style={{ fontFamily: FONT_MONO, fontSize: 12, color: TOKENS.inkMuted, padding: "14px 0 4px" }}>
          REGISTER PENDING — FINDINGS PRINT AS READINGS COMPLETE
        </div>
      ) : weaknesses.length === 0 ? (
        <div style={{ fontFamily: FONT_MONO, fontSize: 12, color: TOKENS.inkMuted, padding: "14px 0 4px" }}>
          NO WEAKNESS FINDINGS — NO AGENTS FLAGGED THIS RUN
        </div>
      ) : (
        weaknesses.map((w, idx) => {
          // `w.supporting_agent_ids` is intentionally NOT surfaced as a
          // count here — the backend caps it at 5 (it's a sample for a
          // future click-to-expand interaction, not an accurate count).
          // The `N/M agents flagged this` line in `w.summary` is the
          // truthful count. See #69 for the prior "5 agents flagged
          // this" footer that was always literally 5 and misled PMs.
          const hasFreq =
            w.frequency != null && w.ci_low != null && w.ci_high != null;
          return (
            <div
              key={idx}
              className="simd-row"
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1fr) 220px",
                gap: 16,
                padding: "12px 0",
                borderTop: idx === 0 ? "none" : `0.75px solid ${TOKENS.rule}`,
                animationDelay: `${960 + idx * 30}ms`,
              }}
            >
              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: 14,
                    fontWeight: 600,
                    color: TOKENS.ink,
                    marginBottom: 4,
                  }}
                >
                  {formatCategory(w.category)}
                  <WeaknessCategoryInfo category={w.category} />
                </div>
                <div style={{ fontSize: 13, color: TOKENS.ink, lineHeight: 1.5 }}>
                  {w.summary}
                </div>
              </div>
              <div>
                {hasFreq ? (
                  <>
                    <RegisterFreqBar
                      frequency={w.frequency!}
                      ciLow={w.ci_low!}
                      ciHigh={w.ci_high!}
                    />
                    <div
                      style={{
                        fontFamily: FONT_MONO,
                        fontSize: 11,
                        color: TOKENS.inkMuted,
                        marginTop: 6,
                        ...TNUM,
                      }}
                    >
                      {(w.frequency! * 100).toFixed(0)}% [
                      {(w.ci_low! * 100).toFixed(0)}&ndash;
                      {(w.ci_high! * 100).toFixed(0)}%]
                    </div>
                  </>
                ) : (
                  <div style={{ fontFamily: FONT_MONO, fontSize: 11, color: TOKENS.inkMuted }}>
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

// ───────────────────────────────────────────────────────────────────────
// Refinement queue — refinement_suggestions with a queue action. The wizard
// has no prefill contract (no backend support), so the action opens a fresh
// hypothesis and the microcopy says so honestly.
// ───────────────────────────────────────────────────────────────────────
function RefinementQueue({ suggestions }: { suggestions: string[] }) {
  return (
    <section style={cardStyle}>
      <h2 style={{ ...monoLabelStyle, fontSize: 11, margin: 0, marginBottom: 4 }}>
        REFINEMENT QUEUE
      </h2>
      <div style={{ fontSize: 12, color: TOKENS.inkMuted, marginBottom: 12, lineHeight: 1.5 }}>
        Queueing opens a fresh hypothesis in the wizard — suggestions are not
        prefilled. Copy the wording you want to keep.
      </div>
      {suggestions.map((s, i) => (
        <div
          key={i}
          className="simd-row"
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1fr) auto",
            gap: 16,
            alignItems: "center",
            padding: "12px 0",
            borderTop: `0.75px solid ${TOKENS.rule}`,
            animationDelay: `${960 + i * 30}ms`,
          }}
        >
          <div style={{ fontSize: 14, color: TOKENS.ink, lineHeight: 1.5 }}>{s}</div>
          <Link
            href="/simulations/new"
            className="simd-qbtn"
            style={{
              fontFamily: FONT_MONO,
              fontSize: 10,
              letterSpacing: 0.8,
              textTransform: "uppercase",
              color: TOKENS.ink,
              textDecoration: "none",
              border: `0.75px solid ${TOKENS.rule}`,
              borderRadius: 2,
              padding: "6px 10px",
              whiteSpace: "nowrap",
            }}
          >
            QUEUE AS HYPOTHESIS →
          </Link>
        </div>
      ))}
    </section>
  );
}

// ───────────────────────────────────────────────────────────────────────
// Method card — how the reading is computed, in PM-readable lines. Honest
// about the DR-1 rubric being a page-level display rule, not API output.
// ───────────────────────────────────────────────────────────────────────
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
    <section style={cardStyle}>
      <h2 style={{ ...monoLabelStyle, fontSize: 11, margin: 0, marginBottom: 14 }}>
        METHOD — HOW THIS READING IS COMPUTED
      </h2>
      {rows.map((r, i) => (
        <div
          key={r.k}
          style={{
            display: "grid",
            gridTemplateColumns: "130px minmax(0, 1fr)",
            gap: 16,
            padding: "10px 0",
            borderTop: i === 0 ? "none" : `0.75px solid ${TOKENS.rule}`,
          }}
        >
          <span style={{ ...monoLabelStyle, paddingTop: 2 }}>{r.k}</span>
          <span style={{ fontSize: 13, color: TOKENS.ink, lineHeight: 1.55 }}>{r.v}</span>
        </div>
      ))}
    </section>
  );
}

// ───────────────────────────────────────────────────────────────────────
// Inspector rail — §7.2 zone 3. Paper-elevated, 340px, sticky. Persona
// readings + pinned quote well + provenance + raw artifacts. Fades in last
// in the choreography (§9.4).
// ───────────────────────────────────────────────────────────────────────
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
  // Codex P2 (#166): a persona can land entirely in one arm — the chat page
  // 404s an arm with zero agents, so disable that arm's rail link (same
  // gating the cohort register's ArmChatLink applies).
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
    <aside
      className="simd-late"
      style={{
        background: TOKENS.paperElevated,
        border: `0.75px solid ${TOKENS.rule}`,
        borderRadius: 4,
        padding: 20,
        position: "sticky",
        top: 24,
        fontFamily: FONT_SANS,
        minWidth: 0,
      }}
    >
      <h2 style={{ ...monoLabelStyle, fontSize: 11, margin: 0, marginBottom: 12 }}>
        PERSONA READINGS
      </h2>
      {personaGroups == null ? (
        <div style={{ fontFamily: FONT_MONO, fontSize: 12, color: TOKENS.inkMuted, marginBottom: 16 }}>
          {status === "failed" ? "NO READINGS — RUN FAILED" : "REGISTER PENDING"}
        </div>
      ) : personaGroups.length === 0 ? (
        <div style={{ fontFamily: FONT_MONO, fontSize: 12, color: TOKENS.inkMuted, marginBottom: 16 }}>
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
                style={{
                  display: "flex",
                  alignItems: "baseline",
                  gap: 8,
                  width: "100%",
                  textAlign: "left",
                  background: isActive ? TOKENS.paperRecessed : "transparent",
                  border: "none",
                  borderTop: `0.75px solid ${TOKENS.rule}`,
                  borderRadius: 0,
                  padding: "8px 6px",
                  cursor: "pointer",
                }}
              >
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: isActive ? 600 : 400,
                    color: TOKENS.ink,
                    minWidth: 0,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    flex: 1,
                  }}
                >
                  {g.persona_name}
                </span>
                {/* Negative counts read as muted ink, never alert (§8.5). */}
                <span
                  style={{
                    fontFamily: FONT_MONO,
                    fontSize: 11,
                    color: TOKENS.inkMuted,
                    whiteSpace: "nowrap",
                    ...TNUM,
                  }}
                >
                  +{counts.positive} ~{counts.neutral} −{counts.negative}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {active != null && (
        <div
          style={{
            background: TOKENS.paperRecessed,
            borderRadius: 2,
            padding: 12,
            marginBottom: 20,
          }}
        >
          <div style={{ ...monoLabelStyle, fontSize: 9, marginBottom: 6 }}>
            {isAbMode ? "PINNED QUOTE — TREATMENT ARM" : "PINNED QUOTE"}
          </div>
          {activeQuote != null ? (
            <div style={{ fontSize: 13, color: TOKENS.ink, lineHeight: 1.55, marginBottom: 8 }}>
              &ldquo;{activeQuote}&rdquo;
            </div>
          ) : (
            <div style={{ fontFamily: FONT_MONO, fontSize: 11, color: TOKENS.inkMuted, marginBottom: 8 }}>
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

      <h2 style={{ ...monoLabelStyle, fontSize: 11, margin: 0, marginBottom: 8 }}>
        PROVENANCE
      </h2>
      <dl style={{ margin: 0, marginBottom: 16 }}>
        {provRows.map((r) => (
          <div
            key={r.k}
            style={{
              display: "grid",
              gridTemplateColumns: "110px minmax(0, 1fr)",
              gap: 8,
              padding: "5px 0",
              borderTop: `0.75px solid ${TOKENS.rule}`,
            }}
          >
            <dt style={{ ...monoLabelStyle, fontSize: 9, paddingTop: 1 }}>{r.k}</dt>
            <dd
              style={{
                margin: 0,
                fontFamily: FONT_MONO,
                fontSize: 11,
                color: TOKENS.ink,
                overflowWrap: "anywhere",
                ...TNUM,
              }}
            >
              {r.v}
            </dd>
          </div>
        ))}
      </dl>

      <h2 style={{ ...monoLabelStyle, fontSize: 11, margin: 0, marginBottom: 8 }}>
        ARTIFACTS
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {/* Raw JSON the backend exposes today — the only artifact endpoints
            that exist. No readings.csv / transcript bundle / decision record
            yet (flagged as a data gap in #166). */}
        <a
          href={`${API_BASE}/simulations/${sim.id}`}
          target="_blank"
          rel="noreferrer"
          style={{ fontFamily: FONT_MONO, fontSize: 11, letterSpacing: 0.6, color: TOKENS.ink, textDecoration: "none" }}
        >
          RESULT JSON →
        </a>
        <a
          href={`${API_BASE}/simulations/${sim.id}/agents`}
          target="_blank"
          rel="noreferrer"
          style={{ fontFamily: FONT_MONO, fontSize: 11, letterSpacing: 0.6, color: TOKENS.ink, textDecoration: "none" }}
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
  const style: React.CSSProperties = {
    fontFamily: FONT_MONO,
    fontSize: 10,
    letterSpacing: 0.8,
    textTransform: "uppercase",
    color: TOKENS.ink,
    textDecoration: "none",
    border: `0.75px solid ${TOKENS.rule}`,
    borderRadius: 2,
    padding: "4px 8px",
    whiteSpace: "nowrap",
  };
  if (!enabled) {
    // Arm with zero agents — the chat page would 404 (codex P2 on #166).
    return (
      <span
        aria-label={aria}
        title="No agents are available in this arm for the completed run."
        style={{ ...style, color: TOKENS.inkMuted, cursor: "not-allowed" }}
      >
        {label}
      </span>
    );
  }
  return (
    <Link href={href} aria-label={aria} style={style}>
      {label}
    </Link>
  );
}

function formatDateTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString([], { hour12: false });
  } catch {
    return iso;
  }
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

// Group by persona_id (stable key); persona_name is the human label.
// Preserve first-seen order so the visual order matches the simulator's
// allocation order (largest persona first under largest-remainder).
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

// ───────────────────────────────────────────────────────────────────────
// Per-arm diagnostic + cohort banner (paper record).
// ───────────────────────────────────────────────────────────────────────

// Phase 5 #101: cohort banner. Renders above the registers when the sim was
// submitted with a persona filter. Joins selected persona_ids against
// agentMeta (loaded by the result page on terminal status) to surface human
// names — falls back to IDs if agentMeta hasn't joined yet. Absent entirely
// when the sim wasn't filtered (sim.selected_personas is null).
function CohortBanner({
  selectedIds,
  agentMeta,
}: {
  selectedIds: string[];
  agentMeta: AgentRow[] | null;
}) {
  // Build {persona_id -> persona_name} from agentMeta. Deduped because
  // multiple agents in a persona group all share the same persona_name.
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
    <section
      style={{
        ...cardStyle,
        padding: "12px 16px",
        background: TOKENS.paperRecessed,
        // Warn as a border ACCENT only — never warn text (codex on #164).
        border: `0.75px solid ${TOKENS.warn}`,
        color: TOKENS.ink,
        fontSize: 14,
      }}
    >
      <strong style={{ color: TOKENS.ink }}>Persona-filtered run:</strong>{" "}
      this simulation was scoped to {selectedIds.length} persona
      {selectedIds.length === 1 ? "" : "s"}: {names.join(", ")}.
      {" "}Lift / scores are for the selected cohort, not the full
      Persona Pack — re-run with all personas to compare against the
      unfiltered baseline.
    </section>
  );
}

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
    <section
      style={{
        ...cardStyle,
        padding: "16px 18px",
        background: TOKENS.paperElevated,
      }}
    >
      <div style={{ ...monoLabelStyle, fontSize: 11, marginBottom: 6 }}>
        PER-ARM DETAIL
      </div>
      <div
        style={{
          fontSize: 13,
          color: TOKENS.inkMuted,
          lineHeight: 1.5,
          maxWidth: 760,
          marginBottom: 14,
        }}
      >
        These diagnostic scores are not directly comparable. The treatment arm
        includes weakness penalties for the proposed change; the control arm is
        scored as the status-quo product and skips weakness classification. Use
        the paired lift on the glass for the apples-to-apples A/B read.
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: 12,
        }}
      >
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
        style={{
          marginTop: 12,
          paddingTop: 12,
          borderTop: `0.75px solid ${TOKENS.rule}`,
          fontSize: 12,
          color: TOKENS.inkMuted,
          lineHeight: 1.5,
        }}
      >
        {abstained ? (
          <>
            Policy {DECISION_POLICY.id} is withheld for this run: the OEC is
            outside a first-exposure single-session panel&rsquo;s resolving
            power, so the treatment confidence score is not evaluated for a
            ship / no-ship decision. See the instrument-scope note above.
          </>
        ) : (
          <>
            Policy {DECISION_POLICY.id} still applies to the treatment
            confidence score: &ge;{DECISION_POLICY.threshold} = ship candidate;
            below = needs refinement.
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
    <div style={{ padding: "4px 0" }}>
      <div style={{ fontSize: 12, color: TOKENS.inkMuted, marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
        <div
          style={{
            fontSize: 28,
            lineHeight: 1,
            fontWeight: 700,
            color: score == null ? TOKENS.inkMuted : scoreColor(score),
            fontFamily: FONT_MONO,
            ...TNUM,
          }}
        >
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
      <div
        style={{
          marginTop: 8,
          fontSize: 12,
          color: TOKENS.inkMuted,
          lineHeight: 1.4,
        }}
      >
        {description}
      </div>
    </div>
  );
}

// Shared sanitizer for CI inputs (codex P2 round 1).
// - Coerces non-finite values to a safe default.
// - Clamps to [min, max].
// - Swaps low/high when ci_low > ci_high (shouldn't happen from backend
//   today, but defensive: keep the interval visible rather than collapse
//   to width 0).
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

// #71: when the bootstrap CI width is below this threshold on the 0-100
// scale, the rendering treats it as "collapsed" — we hide the band and
// switch the label from "95% CI: [X – Y]" to "Narrow interval". This is
// a PRESENTATION threshold; the backend doesn't surface an explicit
// unanimity flag, so the copy describes the OBSERVATION (a narrow
// interval) rather than CLAIMING the cause (every agent agreed). 0.2
// catches both truly-zero CIs and rounded-to-zero CIs without grabbing
// genuinely-tight-but-real intervals. Shared between the labels and the
// glass CI axis so a future tweak lands in one place.
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
    // No info icon: the phrase is self-explanatory and avoids the focusable-
    // span / outline-none / tooltip-discoverability rabbit hole codex flagged
    // in round 2.
    return (
      <div
        style={{
          fontSize: 14,
          color: TOKENS.inkMuted,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        Narrow interval
        {sampledAgentCount != null ? ` (n=${sampledAgentCount})` : ""}
      </div>
    );
  }
  return (
    <div
      style={{
        fontSize: 14,
        color: TOKENS.inkMuted,
        fontVariantNumeric: "tabular-nums",
      }}
    >
      95% CI: [{ciLow.toFixed(1)} &ndash; {ciHigh.toFixed(1)}]
    </div>
  );
}

// Row shape for the result table: agent metadata + sentiment/top_quote
// joined from the persisted result (#51). Defined once so the result-table
// component tree stays consistent.
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

  // Phase 4.6 #91: A/B mode is detected at the table level — if ANY agent in
  // the sim has an arm tag, we treat the table as arm-split and render two
  // chips per persona row. Detecting per-persona would be wrong: a persona
  // that happens to land entirely in one arm should still render with the
  // arm-split layout so the table visual stays consistent across personas.
  const isAbMode = agents.some((a) => a.arm != null);

  return (
    <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {groups.map((g, i) => (
        <PersonaGroupRow
          key={g.pid}
          personaId={g.pid}
          personaName={g.persona_name}
          agents={g.agents}
          isFirst={i === 0}
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
  isFirst,
  isAbMode,
}: {
  personaId: string;
  personaName: string;
  agents: AgentRow[];
  isFirst: boolean;
  isAbMode: boolean;
}) {
  const params = useParams<{ id: string }>();
  const simId = params?.id ?? "";
  const [open, setOpen] = useState(false);
  const listId = `persona-agents-${personaId}`;

  // #51: aggregate sentiment across the group.
  const groupSentiment = aggregateSentiment(agents);

  // Phase 4.6 #91: split agents into arms for A/B render. Untagged agents
  // (legacy or partial-rollout) fall into neither bucket and are listed
  // separately at the bottom of the expanded view.
  const treatmentAgents = agents.filter((a) => a.arm === "treatment");
  const controlAgents = agents.filter((a) => a.arm === "control");
  const untaggedAgents = agents.filter((a) => a.arm == null);
  const treatmentSentiment = aggregateSentiment(treatmentAgents);

  // #51: pick top quote across the group.
  // Codex R3-P2 on #91: in A/B mode the longest quote could come from a
  // control agent, but the collapsed persona summary reads as "what this
  // persona thought about the proposed change." Pin the summary quote to
  // the treatment arm (which is the only arm that saw the change). Single-
  // arm sims fall through to the original pick across all agents.
  const groupQuote = pickGroupQuote(isAbMode ? treatmentAgents : agents);
  const controlSentiment = aggregateSentiment(controlAgents);

  return (
    <li
      style={{
        padding: "12px 0",
        borderTop: isFirst ? "none" : `0.75px solid ${TOKENS.rule}`,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 12,
          width: "100%",
          minWidth: 0,
        }}
      >
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-controls={listId}
          style={{
            background: "transparent",
            border: "none",
            padding: 0,
            cursor: "pointer",
            display: "flex",
            alignItems: "baseline",
            gap: 12,
            flex: 1,
            textAlign: "left",
            // minWidth:0 + the truncating persona-id below = no horizontal
            // scroll on narrow viewports (codex P2 round 1).
            minWidth: 0,
          }}
        >
          <span
            aria-hidden
            style={{
              fontSize: 12,
              color: TOKENS.inkMuted,
              width: 12,
              display: "inline-block",
              flex: "0 0 auto",
            }}
          >
            {open ? "▾" : "▸"}
          </span>
          <span
            style={{
              fontSize: 15,
              fontWeight: 600,
              color: TOKENS.ink,
              flex: "0 1 auto",
              minWidth: 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {personaName}
          </span>
          <span style={{ fontSize: 14, color: TOKENS.inkMuted, flex: "0 0 auto", ...TNUM }}>
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
              {/* Arm designators carry ink-weight, never color (§5.4). */}
              <span
                aria-hidden
                style={{ fontSize: 11, color: TOKENS.inkMuted, fontWeight: 600 }}
                title="Treatment arm"
              >
                T
              </span>
              <SentimentChip
                sentiment={treatmentSentiment.label}
                intensity={treatmentSentiment.intensity}
              />
              <span
                aria-hidden
                style={{
                  fontSize: 11,
                  color: TOKENS.inkMuted,
                  fontWeight: 600,
                  marginLeft: 4,
                }}
                title="Control arm"
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
          <span
            style={{
              fontSize: 12,
              color: TOKENS.inkMuted,
              marginLeft: "auto",
              fontFamily: FONT_MONO,
              minWidth: 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {personaId}
          </span>
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
            style={{
              fontFamily: FONT_MONO,
              fontSize: 10,
              letterSpacing: 0.8,
              textTransform: "uppercase",
              color: TOKENS.ink,
              textDecoration: "none",
              flex: "0 0 auto",
              whiteSpace: "nowrap",
            }}
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
          <div id={listId} style={{ padding: "8px 0 0 24px" }}>
            <ArmAgentSubList label="Treatment" agents={treatmentAgents} />
            <ArmAgentSubList label="Control" agents={controlAgents} />
            {untaggedAgents.length > 0 && (
              <ArmAgentSubList label="Untagged" agents={untaggedAgents} />
            )}
          </div>
        ) : (
          <ul
            id={listId}
            style={{
              listStyle: "none",
              padding: "8px 0 0 24px",
              margin: 0,
            }}
          >
            {agents.map((a) => (
              <AgentLi key={a.agent_id} agent={a} />
            ))}
          </ul>
        ))}
    </li>
  );
}

// Text chat link per arm — was an emoji "💬 T" pill; §10 bans emoji
// affordances, so the affordance is now a mono uppercase text link with the
// 2px input radius.
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
  const style: React.CSSProperties = {
    fontFamily: FONT_MONO,
    fontSize: 10,
    letterSpacing: 0.8,
    textTransform: "uppercase",
    textDecoration: "none",
    border: `0.75px solid ${TOKENS.rule}`,
    borderRadius: 2,
    padding: "3px 7px",
    background: isTreatment ? TOKENS.paperRecessed : TOKENS.paperElevated,
    color: TOKENS.ink,
    whiteSpace: "nowrap",
  };

  if (!enabled) {
    return (
      <span
        aria-label={`${armName} persona-group chat unavailable for ${personaName}`}
        title={`No ${armName} agents are available for this persona in the completed run.`}
        style={{
          ...style,
          color: TOKENS.inkMuted,
          background: TOKENS.paperRecessed,
          cursor: "not-allowed",
        }}
      >
        {label}
      </span>
    );
  }

  return (
    <Link
      href={`/simulations/${simId}/personas/${personaId}?arm=${arm}`}
      aria-label={`Open ${armName} persona-group chat with ${personaName}`}
      style={style}
    >
      {label}
    </Link>
  );
}

// Phase 4.6 #91: single agent row, factored out so the A/B sub-sections and
// the single-arm flat list share the exact same row markup. Touching this
// once flows through both branches.
function AgentLi({ agent: a }: { agent: AgentRow }) {
  return (
    <li
      style={{
        padding: "8px 0",
        borderTop: `1px dashed ${TOKENS.rule}`,
        listStyle: "none",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 12,
          fontSize: 13,
        }}
      >
        <Link
          href={`/agents/${a.agent_id}`}
          style={{
            color: TOKENS.ink,
            textDecoration: "none",
            fontFamily: FONT_MONO,
            flex: "0 0 auto",
          }}
        >
          {a.agent_id.slice(0, 8)}
        </Link>
        <SentimentChip
          sentiment={a.sentiment}
          intensity={a.sentiment_confidence ?? null}
        />
        <span style={{ flex: 1 }} />
        <Link
          href={`/agents/${a.agent_id}`}
          aria-label={`Open individual chat with ${a.agent_id}`}
          style={{
            fontFamily: FONT_MONO,
            fontSize: 10,
            letterSpacing: 0.8,
            textTransform: "uppercase",
            color: TOKENS.ink,
            textDecoration: "none",
            flex: "0 0 auto",
            whiteSpace: "nowrap",
          }}
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
        <div
          style={{
            fontSize: 11,
            color: TOKENS.inkMuted,
            textTransform: "uppercase",
            letterSpacing: 0.5,
            fontWeight: 600,
          }}
        >
          {label}
        </div>
        <div style={{ fontSize: 12, color: TOKENS.inkMuted, paddingTop: 4 }}>
          — no agents in this arm —
        </div>
      </div>
    );
  }
  const sub = aggregateSentiment(agents);
  return (
    <div style={{ paddingTop: 6, paddingBottom: 4 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 11,
          color: TOKENS.inkMuted,
          textTransform: "uppercase",
          letterSpacing: 0.5,
          fontWeight: 600,
          padding: "4px 0",
          borderBottom: `0.75px solid ${TOKENS.rule}`,
        }}
      >
        <span>{label}</span>
        <span style={{ color: TOKENS.inkMuted, fontWeight: 400 }}>
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

// ───────────────────────────────────────────────────────────────────────
// #51 — sentiment chip + top-quote helpers
// ───────────────────────────────────────────────────────────────────────

type SentimentLabel = "positive" | "neutral" | "negative" | null;

function SentimentChip({
  sentiment,
  intensity,
}: {
  sentiment: SentimentLabel;
  intensity: number | null;
}) {
  if (sentiment == null) {
    // Sentiment not yet classified — spec calls for "—" placeholder.
    return (
      <span
        aria-label="Sentiment not yet available"
        style={{
          fontSize: 12,
          color: TOKENS.inkMuted,
          flex: "0 0 auto",
          padding: "2px 8px",
          borderRadius: 4,
          background: TOKENS.paperRecessed,
          border: `0.75px solid ${TOKENS.rule}`,
        }}
      >
        —
      </span>
    );
  }
  // Three-step palette (spec leaves five-step as open Q; three reads
  // cleaner on a table cell). Intensity is encoded via the glyph + the
  // confidence-driven background tint. Codex #84 round-1 P2: alpha is
  // applied to the BACKGROUND only, not to the whole chip — fading text
  // along with the background hurt WCAG contrast on low-confidence
  // states.
  // R2 sweep: all three chips sit on recessed paper (235,229,216 =
  // TOKENS.paperRecessed) with a rule border; the fg + glyph carry the
  // signal. Negative is ink-muted, never alert-red — DESIGN.md §8.5: a
  // persona disliking a feature is information, not an emergency.
  const palette = {
    positive: {
      bgR: 235,
      bgG: 229,
      bgB: 216,
      fg: TOKENS.success,
      border: TOKENS.rule,
      glyph: "+",
    },
    neutral: {
      bgR: 235,
      bgG: 229,
      bgB: 216,
      fg: TOKENS.inkMuted,
      border: TOKENS.rule,
      glyph: "~",
    },
    negative: {
      bgR: 235,
      bgG: 229,
      bgB: 216,
      fg: TOKENS.inkMuted,
      border: TOKENS.rule,
      glyph: "−",
    },
  } as const;
  const p = palette[sentiment];
  // Confidence in [0.6, 1.0] drives the background alpha so low-confidence
  // chips read as muted without affecting label legibility.
  const bgAlpha = Math.max(0.6, Math.min(1, intensity ?? 0.8));
  return (
    <span
      title={`${sentiment} (confidence ${intensity != null ? intensity.toFixed(2) : "—"})`}
      aria-label={`Sentiment: ${sentiment}`}
      style={{
        fontSize: 12,
        color: p.fg,
        flex: "0 0 auto",
        padding: "2px 8px",
        borderRadius: 4,
        background: `rgba(${p.bgR}, ${p.bgG}, ${p.bgB}, ${bgAlpha})`,
        // Codex #84 round-2 P2: opaque border (was an 8-digit hex alpha
        // `${p.fg}22` which kept the border ~13% opacity even after the
        // round-1 opacity fix). Mid-tone opaque hex stays visually light
        // without dropping legibility.
        border: `1px solid ${p.border}`,
        // No `opacity` on the chip itself — text + glyph stay fully opaque
        // for accessibility (codex #84 round-1 P2).
        textTransform: "lowercase",
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
      }}
    >
      <span aria-hidden style={{ fontWeight: 600 }}>{p.glyph}</span>
      {sentiment}
    </span>
  );
}

function TopQuoteLine({
  text,
  armLabel = null,
}: {
  text: string;
  // When set, prefixes the quote with a small "[treatment]" or "[control]"
  // tag so the PM can tell which arm spoke when the collapsed persona
  // summary chooses a single quote across an A/B run. Null in single-arm
  // mode keeps the original visual untouched.
  armLabel?: "treatment" | "control" | null;
}) {
  const [expanded, setExpanded] = useState(false);
  // Inline-expand on click (spec: "click expands inline (no nav)").
  // Collapsed: single-line ellipsis; expanded: full wrap.
  return (
    <button
      type="button"
      onClick={() => setExpanded((v) => !v)}
      aria-expanded={expanded}
      title={expanded ? "Click to collapse" : "Click to expand"}
      style={{
        display: "block",
        width: "100%",
        textAlign: "left",
        background: "transparent",
        border: "none",
        padding: "4px 0 0 24px",
        margin: 0,
        cursor: "pointer",
        fontSize: 13,
        color: TOKENS.inkMuted,
        lineHeight: 1.5,
        whiteSpace: expanded ? "normal" : "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
      }}
    >
      {armLabel && (
        <span
          aria-label={`${armLabel} arm`}
          style={{
            fontSize: 10,
            color: TOKENS.inkMuted,
            textTransform: "uppercase",
            letterSpacing: 0.5,
            fontWeight: 600,
            marginRight: 8,
            padding: "1px 6px",
            background: TOKENS.paperRecessed,
            border: `0.75px solid ${TOKENS.rule}`,
            borderRadius: 2,
          }}
        >
          {armLabel}
        </span>
      )}
      <span aria-hidden style={{ color: TOKENS.inkMuted, marginRight: 6 }}>
        “
      </span>
      {text}
      <span aria-hidden style={{ color: TOKENS.inkMuted, marginLeft: 4 }}>
        ”
      </span>
    </button>
  );
}

// Order-weighted sentiment aggregation. Maps each agent's sentiment to a
// numeric value (positive=+1, neutral=0, negative=-1) and confidence-weights
// the mean. Returns the chip-renderable {label, intensity} pair.
//
// Tie-breaking: any agent with `sentiment == null` is skipped (still
// classifying / pre-#51 result). If EVERY agent is unclassified, returns
// {null, null} so the chip renders the "—" placeholder.
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
  // Buckets: > +0.33 positive; < -0.33 negative; else neutral.
  const label: SentimentLabel =
    score > 0.33 ? "positive" : score < -0.33 ? "negative" : "neutral";
  return { label, intensity: Math.abs(score) };
}

// Pick the longest top_quote across the group as the persona-row quote
// (spec: "most-cited or longest verbatim across the group"). Longest is
// the heuristic — no citation count yet. Ties broken by first agent in
// allocation order so the choice is deterministic across reloads.
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

// ───────────────────────────────────────────────────────────────────────
// Weakness category info — PM-readable definitions for each weakness type
// surfaced in the result. Click the info button next to a category to read
// what that category means in plain English (not statistician-speak).
// ───────────────────────────────────────────────────────────────────────

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
  // Unknown categories (forward-compat: a new category lands server-side
  // before the frontend ships its definition) render nothing rather than
  // a broken popover. The PM still sees the category name + summary.
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
        style={{
          background: open ? TOKENS.ink : "transparent",
          color: open ? TOKENS.paper : TOKENS.ink,
          border: `0.75px solid ${open ? TOKENS.ink : TOKENS.rule}`,
          borderRadius: 4,
          width: 18,
          height: 18,
          padding: 0,
          fontSize: 11,
          lineHeight: 1,
          fontWeight: 700,
          cursor: "pointer",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          flex: "0 0 auto",
        }}
      >
        i
      </button>
      {open && (
        <div
          role="dialog"
          aria-label={info.title}
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            left: 0,
            zIndex: 20,
            width: 320,
            maxWidth: "85vw",
            background: TOKENS.paperElevated,
            border: `0.75px solid ${TOKENS.rule}`,
            borderRadius: 6,
            boxShadow: "0 4px 16px rgba(14, 26, 43, 0.08)",
            padding: 14,
          }}
        >
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: TOKENS.ink,
              marginBottom: 6,
            }}
          >
            {info.title}
          </div>
          <div
            style={{
              fontSize: 13,
              color: TOKENS.inkMuted,
              lineHeight: 1.55,
              fontWeight: 400,
            }}
          >
            {info.description}
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Close definition"
            style={{
              position: "absolute",
              top: 6,
              right: 6,
              background: "transparent",
              border: "none",
              color: TOKENS.inkMuted,
              fontSize: 16,
              lineHeight: 1,
              cursor: "pointer",
              padding: "4px 6px",
            }}
          >
            ×
          </button>
        </div>
      )}
    </span>
  );
}

// ───────────────────────────────────────────────────────────────────────
// Aperture-close animation — DESIGN.md §9.2
// ───────────────────────────────────────────────────────────────────────

const APERTURE_STYLE = `
  @keyframes sidira-aperture-spin {
    0%, 100% { transform: rotate(0deg) scale(1); }
    40%, 60% { transform: rotate(-8deg) scale(0.86); }
  }
  @keyframes sidira-aperture-mono-fade {
    0%, 38%, 62%, 100% { opacity: 1; }
    44%, 56% { opacity: 0; }
  }
  @keyframes sidira-aperture-duo-fade {
    0%, 38%, 62%, 100% { opacity: 0; }
    44%, 56% { opacity: 1; }
  }
  .sidira-aperture-spin { transition: transform 0.25s ease-out; }
  .sidira-aperture-mono { transition: opacity 0.25s ease-out; }
  .sidira-aperture-duo { transition: opacity 0.25s ease-out; }
  @media (prefers-reduced-motion: reduce) {
    .sidira-aperture-spin { animation: none !important; transform: none !important; transition: none !important; }
    .sidira-aperture-mono { animation: none !important; opacity: 1 !important; transition: none !important; }
    .sidira-aperture-duo { display: none !important; }
  }
`;

function ApertureMark({ size = 32, animating }: { size?: number; animating: boolean }) {
  return (
    <div
      aria-hidden
      style={{ position: "relative", width: size, height: size, flexShrink: 0, color: TOKENS.ink }}
    >
      <style dangerouslySetInnerHTML={{ __html: APERTURE_STYLE }} />
      <div
        className="sidira-aperture-spin"
        style={{
          position: "absolute",
          inset: 0,
          animation: animating ? "sidira-aperture-spin 3.4s ease-in-out infinite" : undefined,
        }}
      >
        {/* Monochrome mark — visible at rest; fades out at the held frame */}
        <div
          className="sidira-aperture-mono"
          style={{
            position: "absolute",
            inset: 0,
            animation: animating ? "sidira-aperture-mono-fade 3.4s ease-in-out infinite" : undefined,
          }}
        >
          <svg viewBox="0 0 100 100" fill="none" style={{ width: "100%", height: "100%" }}>
            <g stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round">
              <polygon points="84.641,70 50,90 50,63 61.260,56.5"/>
              <polygon points="50,90 15.359,70 38.740,56.5 50,63"/>
              <polygon points="15.359,70 15.359,30 38.740,43.5 38.740,56.5"/>
              <polygon points="15.359,30 50,10 50,37 38.740,43.5"/>
              <polygon points="50,10 84.641,30 61.260,43.5 50,37"/>
              <polygon points="84.641,30 84.641,70 61.260,56.5 61.260,43.5"/>
            </g>
          </svg>
        </div>
        {/* Dual-color mark — visible only at the held frame (40%–60%) */}
        <div
          className="sidira-aperture-duo"
          style={{
            position: "absolute",
            inset: 0,
            opacity: 0,
            animation: animating ? "sidira-aperture-duo-fade 3.4s ease-in-out infinite" : undefined,
          }}
        >
          <svg viewBox="0 0 100 100" fill="none" style={{ width: "100%", height: "100%" }}>
            <g strokeWidth="1.1" strokeLinejoin="round" fill="none">
              <g stroke={DUO_SID}>
                <polygon points="50,90 15.359,70 38.740,56.5 50,63"/>
                <polygon points="15.359,70 15.359,30 38.740,43.5 38.740,56.5"/>
                <polygon points="15.359,30 50,10 50,37 38.740,43.5"/>
              </g>
              <g stroke={DUO_AVIRA}>
                <polygon points="84.641,70 50,90 50,63 61.260,56.5"/>
                <polygon points="50,10 84.641,30 61.260,43.5 50,37"/>
                <polygon points="84.641,30 84.641,70 61.260,56.5 61.260,43.5"/>
              </g>
            </g>
          </svg>
        </div>
      </div>
    </div>
  );
}
