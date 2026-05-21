"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  ApiError,
  getSimulation,
  getSimulationState,
  isTerminalStatus,
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
              <div style={{ fontSize: 14, color: "#555", maxWidth: 480 }}>
                ≥80 = validated; below = needs refinement.
              </div>
            </div>
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
                  const supporters = w.supporting_agent_ids ?? [];
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
                          fontSize: 15,
                          fontWeight: 600,
                          color: "#111",
                          marginBottom: 4,
                        }}
                      >
                        {formatCategory(w.category)}
                      </div>
                      <div
                        style={{
                          fontSize: 14,
                          color: "#333",
                          marginBottom: 6,
                          lineHeight: 1.5,
                        }}
                      >
                        {w.summary}
                      </div>
                      <div style={{ fontSize: 13, color: "#888" }}>
                        {supporters.length} agent
                        {supporters.length === 1 ? "" : "s"} flagged this
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

      {/* Agents that participated */}
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
        </section>
      )}
    </main>
  );
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
