"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  ApiError,
  getSimulation,
  getSimulationState,
  isTerminalStatus,
  listSimulationAgents,
  type RunEvent,
  type Simulation,
  type SimulationRunState,
  type SimulationStatus,
} from "@/lib/api";

const STATUS_COLORS: Record<SimulationStatus, { bg: string; fg: string }> = {
  pending: { bg: "#eee", fg: "#555" },
  running: { bg: "#e6f0ff", fg: "#1d4ed8" },
  complete: { bg: "#e7f6ec", fg: "#0a7d3a" },
  failed: { bg: "#fdecec", fg: "#a30000" },
};

function scoreColor(score: number): string {
  if (score >= 80) return "#0a7d3a";
  if (score >= 60) return "#a86b00";
  return "#a30000";
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

const cardStyle: React.CSSProperties = {
  border: "1px solid #eee",
  borderRadius: 8,
  padding: 24,
  marginBottom: 24,
};

export default function SimulationDetailPage() {
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
  const [agentMeta, setAgentMeta] = useState<
    {
      agent_id: string;
      persona_id: string;
      persona_name: string;
      sentiment: "positive" | "neutral" | "negative" | null;
      sentiment_confidence: number | null;
      top_quote: string | null;
    }[] | null
  >(null);
  const [agentMetaError, setAgentMetaError] = useState<string | null>(null);

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
      <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px" }}>
        <p style={{ textAlign: "center", color: "#555", fontSize: 16 }}>
          Loading simulation...
        </p>
      </main>
    );
  }

  if (notFound) {
    return (
      <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px" }}>
        <h1 style={{ fontSize: 22, color: "#111", marginBottom: 12 }}>
          Simulation not found
        </h1>
        <p style={{ color: "#555", fontSize: 16 }}>
          We couldn't find a simulation with id <code>{id}</code>.
        </p>
        <p style={{ marginTop: 16 }}>
          <Link href="/simulations" style={{ color: "#1d4ed8" }}>
            ← Back to simulations
          </Link>
        </p>
      </main>
    );
  }

  if (!sim) {
    return (
      <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px" }}>
        <p style={{ color: "#a30000", fontSize: 14 }}>
          {error ?? "Unable to load simulation."}
        </p>
      </main>
    );
  }

  const status = sim.status;
  const statusColor = STATUS_COLORS[status];
  const terminal = isTerminalStatus(status);
  const agentIds = sim.agent_instance_ids ?? [];
  const result = sim.result ?? null;

  const agentsTotal = state?.agents_total ?? 0;
  const agentsComplete = state?.agents_complete ?? 0;
  const agentsFailed = state?.agents_failed ?? 0;
  const done = agentsComplete + agentsFailed;
  const progressPct =
    agentsTotal > 0 ? Math.min(100, Math.round((done / agentsTotal) * 100)) : 0;
  const recent = (state?.recent_events ?? []).slice(-5).reverse();

  return (
    <main style={{ maxWidth: 960, margin: "48px auto", padding: "0 24px" }}>
      {error && (
        <div
          style={{
            border: "1px solid #f5b5b5",
            background: "#fdecec",
            color: "#a30000",
            borderRadius: 6,
            padding: "8px 12px",
            marginBottom: 16,
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      {/* Header */}
      <section style={cardStyle}>
        <div
          style={{
            fontSize: 13,
            color: "#888",
            textTransform: "uppercase",
            letterSpacing: 0.5,
            marginBottom: 8,
          }}
        >
          Simulation
        </div>
        <h1
          style={{
            fontSize: 22,
            lineHeight: 1.35,
            color: "#111",
            margin: 0,
            marginBottom: 16,
            fontWeight: 600,
          }}
        >
          {sim.hypothesis.prose}
        </h1>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <Pill label="capability" value={sim.hypothesis.capability_name} />
          <Pill label="personas" value={sim.persona_pack_version} />
          <Pill label="features" value={sim.feature_pack_version} />
          <span
            style={{
              fontSize: 13,
              padding: "4px 10px",
              borderRadius: 999,
              background: statusColor.bg,
              color: statusColor.fg,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: 0.5,
            }}
          >
            {status}
          </span>
        </div>
      </section>

      {/* Live progress (while not terminal) */}
      {!terminal && (
        <section style={cardStyle}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              marginBottom: 16,
            }}
          >
            <span
              style={{
                display: "inline-block",
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "#1d4ed8",
              }}
            />
            <h2 style={{ fontSize: 20, color: "#111", margin: 0 }}>Running…</h2>
            {state?.phase && (
              <span style={{ color: "#888", fontSize: 13 }}>
                phase: {state.phase}
              </span>
            )}
          </div>

          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                fontSize: 14,
                color: "#555",
                marginBottom: 6,
              }}
            >
              agents reacting: {done} of {agentsTotal}
              {agentsFailed > 0 && (
                <span style={{ color: "#a30000", marginLeft: 8 }}>
                  ({agentsFailed} failed)
                </span>
              )}
            </div>
            <div
              style={{
                height: 8,
                background: "#eee",
                borderRadius: 4,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${progressPct}%`,
                  background: "#1d4ed8",
                  transition: "width 200ms ease",
                }}
              />
            </div>
          </div>

          <div>
            <div
              style={{
                fontSize: 13,
                color: "#888",
                textTransform: "uppercase",
                letterSpacing: 0.5,
                marginBottom: 8,
              }}
            >
              Recent events
            </div>
            {recent.length === 0 ? (
              <div style={{ color: "#888", fontSize: 14 }}>
                Waiting for first event…
              </div>
            ) : (
              <ul
                style={{
                  listStyle: "none",
                  padding: 12,
                  margin: 0,
                  background: "#fafafa",
                  borderRadius: 6,
                  fontFamily:
                    "ui-monospace, SFMono-Regular, Menlo, Monaco, monospace",
                  fontSize: 13,
                  color: "#111",
                }}
              >
                {recent.map((ev, i) => (
                  <li key={`${ev.at}-${i}`} style={{ padding: "2px 0" }}>
                    {describeEvent(ev)}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      )}

      {/* Result (complete) */}
      {status === "complete" && result && (
        <>
          {(sim?.population_size != null ||
            sim?.sampled_agent_count != null) && (
            <section
              style={{
                ...cardStyle,
                padding: "12px 16px",
                background: "#f7f8fb",
                color: "#444",
                fontSize: 14,
              }}
            >
              <strong style={{ color: "#111" }}>Population:</strong>{" "}
              {sim.population_size?.toLocaleString() ?? "—"} (sampled:{" "}
              {sim.sampled_agent_count ?? "—"} agent
              {sim.sampled_agent_count === 1 ? "" : "s"} in proportion to
              persona weights)
            </section>
          )}

          <section style={cardStyle}>
            <div
              style={{
                fontSize: 13,
                color: "#888",
                textTransform: "uppercase",
                letterSpacing: 0.5,
                marginBottom: 8,
              }}
            >
              Confidence score
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
              <div
                style={{
                  fontSize: 64,
                  fontWeight: 700,
                  lineHeight: 1,
                  color: scoreColor(result.confidence_score),
                }}
              >
                {Math.round(result.confidence_score)}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {result.confidence_score_ci && (
                  <ConfidenceIntervalLabel
                    ciLow={result.confidence_score_ci[0]}
                    ciHigh={result.confidence_score_ci[1]}
                    sampledAgentCount={sim?.sampled_agent_count ?? null}
                  />
                )}
                <div style={{ fontSize: 14, color: "#555", maxWidth: 480 }}>
                  &ge;80 = validated; below = needs refinement.
                </div>
              </div>
            </div>
            {result.confidence_score_ci && (
              <ScoreCiBar
                score={result.confidence_score}
                ciLow={result.confidence_score_ci[0]}
                ciHigh={result.confidence_score_ci[1]}
              />
            )}
          </section>

          {result.weaknesses && result.weaknesses.length > 0 && (
            <section style={cardStyle}>
              <h2
                style={{
                  fontSize: 20,
                  color: "#111",
                  margin: 0,
                  marginBottom: 16,
                }}
              >
                Weaknesses
              </h2>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {result.weaknesses.map((w, idx) => {
                  // `w.supporting_agent_ids` is intentionally NOT surfaced as a
                  // count here — the backend caps it at 5 (it's a sample for a
                  // future click-to-expand interaction, not an accurate count).
                  // The `N/M agents flagged this` line in `w.summary` is the
                  // truthful count. See #69 for the prior "5 agents flagged
                  // this" footer that was always literally 5 and misled PMs.
                  const hasFreq =
                    w.frequency != null &&
                    w.ci_low != null &&
                    w.ci_high != null;
                  return (
                    <li
                      key={idx}
                      style={{
                        padding: "12px 0",
                        borderTop: idx === 0 ? "none" : "1px solid #eee",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "baseline",
                          justifyContent: "space-between",
                          gap: 16,
                          marginBottom: 4,
                        }}
                      >
                        <div
                          style={{
                            fontSize: 15,
                            fontWeight: 600,
                            color: "#111",
                          }}
                        >
                          {formatCategory(w.category)}
                        </div>
                        {hasFreq && (
                          <div
                            style={{
                              fontSize: 13,
                              color: "#444",
                              fontVariantNumeric: "tabular-nums",
                            }}
                          >
                            {(w.frequency! * 100).toFixed(0)}% [
                            {(w.ci_low! * 100).toFixed(0)}&ndash;
                            {(w.ci_high! * 100).toFixed(0)}%]
                          </div>
                        )}
                      </div>
                      {hasFreq && (
                        <WeaknessFrequencyBar
                          frequency={w.frequency!}
                          ciLow={w.ci_low!}
                          ciHigh={w.ci_high!}
                        />
                      )}
                      <div
                        style={{
                          fontSize: 14,
                          color: "#333",
                          marginTop: hasFreq ? 8 : 0,
                          lineHeight: 1.5,
                        }}
                      >
                        {w.summary}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {result.refinement_suggestions &&
            result.refinement_suggestions.length > 0 && (
              <section style={cardStyle}>
                <h2
                  style={{
                    fontSize: 20,
                    color: "#111",
                    margin: 0,
                    marginBottom: 16,
                  }}
                >
                  Suggested refinements
                </h2>
                <ol
                  style={{
                    paddingLeft: 24,
                    margin: 0,
                    color: "#111",
                    fontSize: 15,
                    lineHeight: 1.6,
                  }}
                >
                  {result.refinement_suggestions.map((s, i) => (
                    <li key={i} style={{ marginBottom: 6 }}>
                      {s}
                    </li>
                  ))}
                </ol>
              </section>
            )}
        </>
      )}

      {/* Failure */}
      {status === "failed" && (
        <section
          style={{
            ...cardStyle,
            border: "1px solid #f5b5b5",
            background: "#fdecec",
          }}
        >
          <h2
            style={{
              fontSize: 18,
              color: "#a30000",
              margin: 0,
              marginBottom: 8,
            }}
          >
            Simulation failed
          </h2>
          <div
            style={{
              fontFamily:
                "ui-monospace, SFMono-Regular, Menlo, Monaco, monospace",
              fontSize: 13,
              color: "#a30000",
              whiteSpace: "pre-wrap",
            }}
          >
            {state?.error ?? "Unknown error."}
          </div>
        </section>
      )}

      {/* Agents that participated — grouped by persona */}
      {agentIds.length > 0 && (
        <section style={cardStyle}>
          <h2
            style={{
              fontSize: 20,
              color: "#111",
              margin: 0,
              marginBottom: 16,
            }}
          >
            Agents that participated
          </h2>
          {agentMetaError && (
            <div
              style={{
                fontSize: 13,
                color: "#a30000",
                marginBottom: 12,
              }}
            >
              Couldn&rsquo;t load persona breakdown ({agentMetaError}).
              Showing raw IDs below.
            </div>
          )}
          {agentMeta == null && !agentMetaError && (
            <div style={{ fontSize: 13, color: "#888", marginBottom: 12 }}>
              Loading persona breakdown for {agentIds.length} agent
              {agentIds.length === 1 ? "" : "s"}…
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
                    borderTop: i === 0 ? "none" : "1px solid #eee",
                    fontFamily:
                      "ui-monospace, SFMono-Regular, Menlo, Monaco, monospace",
                    fontSize: 14,
                  }}
                >
                  <Link
                    href={`/agents/${aid}`}
                    style={{ color: "#1d4ed8", textDecoration: "none" }}
                  >
                    {aid.slice(0, 8)}
                  </Link>
                  <span style={{ color: "#888", marginLeft: 8, fontSize: 12 }}>
                    {aid}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  );
}

// Shared sanitizer for CI bar inputs (codex P2 round 1).
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
// genuinely-tight-but-real intervals. Shared between the label and
// ScoreCiBar so a future tweak lands in one place.
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
    // in round 2. The ScoreCiBar's aria-label carries a fuller explanation
    // for screen-reader users; sighted users can read the docs if they want
    // the math behind why the CI collapsed.
    return (
      <div
        style={{
          fontSize: 14,
          color: "#444",
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
        color: "#444",
        fontVariantNumeric: "tabular-nums",
      }}
    >
      95% CI: [{ciLow.toFixed(1)} &ndash; {ciHigh.toFixed(1)}]
    </div>
  );
}

function ScoreCiBar({
  score,
  ciLow,
  ciHigh,
}: {
  score: number;
  ciLow: number;
  ciHigh: number;
}) {
  // Map 0-100 score onto a 0-100% bar. Marker = point estimate; band = CI.
  const { v, lo, hi } = _safeRange(score, ciLow, ciHigh, 0, 100);
  // Same threshold as ConfidenceIntervalLabel — see #71. Hairline-width
  // band looks like a render bug; hide it and show just the marker. The
  // label above already explains the "Strong agreement" framing.
  const isCollapsed = hi - lo < _CI_COLLAPSE_THRESHOLD;
  return (
    <div style={{ marginTop: 16, paddingTop: 4 }}>
      <div
        role="img"
        aria-label={
          isCollapsed
            ? `Confidence score ${v.toFixed(1)} with a narrow confidence interval that collapsed to a single point at this display resolution.`
            : `Confidence score ${v.toFixed(1)} with 95% CI from ${lo.toFixed(1)} to ${hi.toFixed(1)}`
        }
        style={{
          position: "relative",
          height: 12,
          background: "#eee",
          borderRadius: 6,
          // overflow:hidden so the marker can't escape the track at edges
          // (codex P2 round 1: 2px marker centered on left:0% or left:100%
          // protruded 1px outside the rounded background).
          overflow: "hidden",
        }}
      >
        {!isCollapsed && (
          <div
            style={{
              position: "absolute",
              left: `${lo}%`,
              width: `${Math.max(0, hi - lo)}%`,
              top: 0,
              bottom: 0,
              background: "rgba(29, 78, 216, 0.25)",
            }}
          />
        )}
        <div
          style={{
            position: "absolute",
            left: `${v}%`,
            top: 0,
            bottom: 0,
            width: 2,
            background: scoreColor(v),
            transform: "translateX(-1px)",
          }}
        />
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 11,
          color: "#888",
          marginTop: 4,
          fontVariantNumeric: "tabular-nums",
        }}
        aria-hidden
      >
        <span>0</span>
        <span>50</span>
        <span>100</span>
      </div>
    </div>
  );
}

function WeaknessFrequencyBar({
  frequency,
  ciLow,
  ciHigh,
}: {
  frequency: number;
  ciLow: number;
  ciHigh: number;
}) {
  // 0..1 frequencies onto a 0-100% bar; same sanitizer as the score bar.
  const { v, lo, hi } = _safeRange(frequency, ciLow, ciHigh, 0, 1);
  const f = v * 100;
  const loPct = lo * 100;
  const hiPct = hi * 100;
  return (
    <div
      role="img"
      aria-label={`Frequency ${f.toFixed(0)}% with 95% CI from ${loPct.toFixed(
        0,
      )}% to ${hiPct.toFixed(0)}%`}
      style={{
        position: "relative",
        height: 10,
        background: "#f1f1f1",
        borderRadius: 5,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: `${loPct}%`,
          width: `${Math.max(0, hiPct - loPct)}%`,
          top: 0,
          bottom: 0,
          background: "rgba(168, 107, 0, 0.35)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: `${f}%`,
          top: 0,
          bottom: 0,
          width: 2,
          background: "#a86b00",
          transform: "translateX(-1px)",
        }}
      />
    </div>
  );
}

// Row shape for the result table: agent metadata + sentiment/top_quote
// joined from the persisted result (#51). Defined once so the result-table
// component tree stays consistent.
type AgentRow = {
  agent_id: string;
  persona_id: string;
  persona_name: string;
  sentiment: "positive" | "neutral" | "negative" | null;
  sentiment_confidence: number | null;
  top_quote: string | null;
};

function PersonaGroupedAgents({ agents }: { agents: AgentRow[] }) {
  // Group by persona_id (stable key); persona_name is the human label.
  // Preserve first-seen order so the visual order matches the simulator's
  // allocation order (largest persona first under largest-remainder).
  const order: string[] = [];
  const byPersona = new Map<string, { persona_name: string; agents: AgentRow[] }>();
  for (const a of agents) {
    if (!byPersona.has(a.persona_id)) {
      byPersona.set(a.persona_id, { persona_name: a.persona_name, agents: [] });
      order.push(a.persona_id);
    }
    byPersona.get(a.persona_id)!.agents.push(a);
  }

  return (
    <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {order.map((pid, i) => {
        const group = byPersona.get(pid)!;
        return (
          <PersonaGroupRow
            key={pid}
            personaId={pid}
            personaName={group.persona_name}
            agents={group.agents}
            isFirst={i === 0}
          />
        );
      })}
    </ul>
  );
}

function PersonaGroupRow({
  personaId,
  personaName,
  agents,
  isFirst,
}: {
  personaId: string;
  personaName: string;
  agents: AgentRow[];
  isFirst: boolean;
}) {
  const params = useParams<{ id: string }>();
  const simId = params?.id ?? "";
  const [open, setOpen] = useState(false);
  const listId = `persona-agents-${personaId}`;

  // #51: aggregate sentiment + pick top quote across the group.
  const groupSentiment = aggregateSentiment(agents);
  const groupQuote = pickGroupQuote(agents);

  return (
    <li
      style={{
        padding: "12px 0",
        borderTop: isFirst ? "none" : "1px solid #eee",
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
            color: "#888",
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
            color: "#111",
            flex: "0 1 auto",
            minWidth: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {personaName}
        </span>
        <span style={{ fontSize: 14, color: "#444", flex: "0 0 auto" }}>
          &times; {agents.length} agent{agents.length === 1 ? "" : "s"}
        </span>
        <SentimentChip
          sentiment={groupSentiment.label}
          intensity={groupSentiment.intensity}
        />
        <span
          style={{
            fontSize: 12,
            color: "#aaa",
            marginLeft: "auto",
            fontFamily:
              "ui-monospace, SFMono-Regular, Menlo, Monaco, monospace",
            minWidth: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {personaId}
        </span>
      </button>
      <Link
        href={`/simulations/${simId}/personas/${personaId}`}
        aria-label={`Open persona-group chat with ${personaName}`}
        style={{
          fontSize: 13,
          color: "#1d4ed8",
          textDecoration: "none",
          flex: "0 0 auto",
          whiteSpace: "nowrap",
        }}
      >
        💬 chat
      </Link>
      </div>
      {groupQuote && <TopQuoteLine text={groupQuote} />}
      {open && (
        <ul
          id={listId}
          style={{
            listStyle: "none",
            padding: "8px 0 0 24px",
            margin: 0,
          }}
        >
          {agents.map((a) => (
            <li
              key={a.agent_id}
              style={{
                padding: "8px 0",
                borderTop: "1px dashed #f0f0f0",
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
                    color: "#1d4ed8",
                    textDecoration: "none",
                    fontFamily:
                      "ui-monospace, SFMono-Regular, Menlo, Monaco, monospace",
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
                    fontSize: 12,
                    color: "#1d4ed8",
                    textDecoration: "none",
                    flex: "0 0 auto",
                    whiteSpace: "nowrap",
                  }}
                >
                  💬 chat 1:1
                </Link>
              </div>
              {a.top_quote && <TopQuoteLine text={a.top_quote} />}
            </li>
          ))}
        </ul>
      )}
    </li>
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
          color: "#aaa",
          flex: "0 0 auto",
          padding: "2px 8px",
          borderRadius: 999,
          background: "#f5f5f5",
          border: "1px solid #eee",
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
  const palette = {
    positive: { bgR: 231, bgG: 246, bgB: 236, fg: "#0a7d3a", glyph: "+" },
    neutral: { bgR: 241, bgG: 241, bgB: 241, fg: "#555", glyph: "~" },
    negative: { bgR: 253, bgG: 236, bgB: 236, fg: "#a30000", glyph: "−" },
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
        borderRadius: 999,
        background: `rgba(${p.bgR}, ${p.bgG}, ${p.bgB}, ${bgAlpha})`,
        border: `1px solid ${p.fg}22`,
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

function TopQuoteLine({ text }: { text: string }) {
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
        color: "#666",
        lineHeight: 1.5,
        whiteSpace: expanded ? "normal" : "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
      }}
    >
      <span aria-hidden style={{ color: "#bbb", marginRight: 6 }}>
        “
      </span>
      {text}
      <span aria-hidden style={{ color: "#bbb", marginLeft: 4 }}>
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

function Pill({ label, value }: { label: string; value: string }) {
  return (
    <span
      style={{
        fontSize: 13,
        padding: "4px 10px",
        borderRadius: 999,
        background: "#fafafa",
        border: "1px solid #eee",
        color: "#555",
      }}
    >
      <span style={{ color: "#888", marginRight: 6 }}>{label}:</span>
      <span style={{ color: "#111" }}>{value}</span>
    </span>
  );
}
