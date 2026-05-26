"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  ApiError,
  getPersonaGroupTurns,
  getSimulation,
  listSimulationAgents,
  sendPersonaGroupMessage,
  type AgentSummary,
  type PerAgentReply,
  type PersonaGroupTurn,
  type Simulation,
} from "@/lib/api";

// Phase 4 #55: persona-group chat surface.
// Spec layout (docs/agent-chat-ui-spec.md "Surface 2"):
//   1. Persona-group header — name, N, hypothesis prose, link back to sim.
//   2. Chat log — pm turns alternating with synthesis turns; each synthesis
//      turn shows its one-line synthesis on top and the per-agent replies
//      below (each with a 💬 link to drill into /agents/[id]).
//   3. Composer at bottom — Enter to send, Shift+Enter for newline, IME guard.
//
// Identity-continuity guarantee: every fan-out reply is appended to each
// agent's individual conversation log server-side (pinned by
// test_persona_group_individual_chat_log_grew_too). Clicking 💬 on a
// per-agent answer lands on /agents/[id] showing the same PM/agent turn pair.

export default function PersonaGroupChatPage() {
  const params = useParams<{ id: string; persona_id: string }>();
  const simId = params?.id ?? "";
  const personaId = params?.persona_id ?? "";

  const [sim, setSim] = useState<Simulation | null>(null);
  const [agentsInPersona, setAgentsInPersona] = useState<AgentSummary[]>([]);
  const [personaName, setPersonaName] = useState<string | null>(null);
  const [turns, setTurns] = useState<PersonaGroupTurn[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const conversationEndRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);

  // Initial load: sim (for hypothesis) + agents-in-sim (filter to persona) +
  // turn log. We run these in parallel — none of them depend on each other.
  useEffect(() => {
    if (!simId || !personaId) return;
    let cancelled = false;
    (async () => {
      try {
        const [simData, agents, turnLog] = await Promise.all([
          getSimulation(simId),
          listSimulationAgents(simId),
          // turns endpoint also enforces "persona exists in sim" — 404 if
          // the persona had no agents in this sim. We treat that as notFound.
          getPersonaGroupTurns(simId, personaId).catch((e) => {
            if (e instanceof ApiError && e.status === 404) {
              throw new _PersonaNotFound();
            }
            throw e;
          }),
        ]);
        if (cancelled) return;
        const filtered = agents.filter((a) => a.persona_id === personaId);
        if (filtered.length === 0) {
          // Defensive: sim exists but no agents in the persona. Same UX as
          // the route's 404.
          setNotFound(true);
          return;
        }
        setSim(simData);
        setAgentsInPersona(filtered);
        setPersonaName(filtered[0].persona_name);
        setTurns(turnLog);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof _PersonaNotFound) {
          setNotFound(true);
          return;
        }
        if (e instanceof ApiError && e.status === 404) {
          setNotFound(true);
        } else {
          setLoadError(e instanceof Error ? e.message : String(e));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [simId, personaId]);

  // Auto-scroll within the bounded conversation container (same pattern as
  // #53 — sticky header above must not get covered by new turns).
  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
    });
  }, [turns.length]);

  async function handleSend() {
    const trimmed = draft.trim();
    if (!trimmed || sending) return;
    setSendError(null);
    setSending(true);

    // Optimistic PM turn so the UI doesn't feel dead during fan-out + synth.
    // Capture exact reference for filter-by-reference rollback (codex #53
    // round-2 P2 pattern; same applies here for the persona-group log).
    const optimisticPm: PersonaGroupTurn = {
      role: "pm",
      content: trimmed,
      created_at: new Date().toISOString(),
      per_agent: null,
    };
    setTurns((current) => [...current, optimisticPm]);
    setDraft("");

    try {
      // Phase 1: send. POST is the source of truth — backend persists PM
      // turn + synthesis turn before returning. If POST raises, server has
      // NOT persisted the group-log entry (codex #80 round-2 fix actually
      // allows partial — group-log append failures degrade silently and
      // the route still 200s — but the synthesis response carries the data
      // either way). So a POST failure here means "nothing happened
      // server-side that the next retry would duplicate at the group-log
      // layer". Per-agent logs may already have the PM turn though, so the
      // PM should retry the SAME message (matching individual chat semantics).
      let sendOk = false;
      try {
        await sendPersonaGroupMessage(simId, personaId, trimmed);
        sendOk = true;
      } catch (e) {
        // Remove ONLY the optimistic turn by reference; preserve any other
        // updates (e.g. a concurrent send from another tab — improbable but
        // we don't pay much to be correct).
        setTurns((current) => current.filter((t) => t !== optimisticPm));
        setDraft(trimmed);
        if (e instanceof ApiError) {
          if (e.status === 502) {
            setSendError(
              "All agents failed to respond. Try again.",
            );
          } else {
            setSendError(
              `Send failed (HTTP ${e.status}): ${e.body || e.message}`,
            );
          }
        } else {
          setSendError(e instanceof Error ? e.message : "Send failed.");
        }
      }

      // Phase 2: refetch the canonical turn log. Codex #53 round-1 P1
      // pattern: SEPARATE failure class — a refetch error here doesn't
      // mean the send failed. Keep the optimistic PM visible and warn.
      if (sendOk) {
        try {
          const fresh = await getPersonaGroupTurns(simId, personaId);
          setTurns(fresh);
        } catch (e) {
          setSendError(
            e instanceof Error
              ? `Sent, but couldn't refresh the conversation: ${e.message}. Reload to see the synthesis.`
              : "Sent, but couldn't refresh the conversation. Reload to see the synthesis.",
          );
        }
      }
    } finally {
      setSending(false);
    }

    // Unconditional refocus (codex #53 round-3 P2 — guards read stale
    // closure values; just always refocus, deferred so disabled→enabled
    // transition completes first).
    requestAnimationFrame(() => composerRef.current?.focus());
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (
      e.key === "Enter" &&
      !e.shiftKey &&
      !(e.nativeEvent as KeyboardEvent).isComposing
    ) {
      e.preventDefault();
      void handleSend();
    }
  }

  // ─── Render ────────────────────────────────────────────────────────────

  if (notFound) {
    return (
      <main style={pageStyle}>
        <div style={{ ...cardStyle, color: "#a30000", background: "#fdecec" }}>
          <strong>Persona group not found.</strong>{" "}
          <Link
            href={`/simulations/${simId}`}
            style={{ color: "#1d4ed8", textDecoration: "underline" }}
          >
            Back to simulation
          </Link>
        </div>
      </main>
    );
  }
  if (loadError) {
    return (
      <main style={pageStyle}>
        <div style={{ ...cardStyle, color: "#a30000", background: "#fdecec" }}>
          <strong>Failed to load:</strong> {loadError}
        </div>
      </main>
    );
  }
  if (!sim || !personaName) {
    return (
      <main style={pageStyle}>
        <div style={{ color: "#666", fontSize: 14 }}>Loading persona group…</div>
      </main>
    );
  }

  const hypothesisProse = sim.hypothesis?.prose ?? null;
  const n = agentsInPersona.length;

  return (
    <main style={pageStyle}>
      <div style={{ marginBottom: 16 }}>
        <Link
          href={`/simulations/${simId}`}
          style={{ color: "#1d4ed8", textDecoration: "none", fontSize: 13 }}
        >
          ← back to simulation
        </Link>
      </div>

      {/* Persona-group header (sticky — analogous to #53 identity card) */}
      <section
        style={{ ...cardStyle, position: "sticky", top: 12, zIndex: 2 }}
        aria-label="Persona group identity"
      >
        <div style={labelStyle}>Persona group</div>
        <div style={{ fontSize: 20, fontWeight: 600, color: "#111" }}>
          {personaName}{" "}
          <span style={{ fontSize: 14, color: "#888", fontWeight: 400 }}>
            (n={n})
          </span>
        </div>
        <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>
          {personaId}
        </div>
        {hypothesisProse && (
          <>
            <div style={{ ...labelStyle, marginTop: 14 }}>
              Hypothesis under test
            </div>
            <div style={{ fontSize: 14, color: "#333", lineHeight: 1.5 }}>
              {hypothesisProse}
            </div>
          </>
        )}
      </section>

      {/* Chat — bounded scroll so the sticky header doesn't cover new turns */}
      <section style={cardStyle} aria-label="Conversation">
        <div style={labelStyle}>Conversation</div>
        <div
          style={{
            maxHeight: "55vh",
            overflowY: "auto",
            padding: "0 4px",
          }}
        >
          {turns.length === 0 ? (
            <div style={{ fontSize: 14, color: "#888", padding: "8px 0" }}>
              No questions yet. Ask the group something below — your question
              fans out to all {n} agent{n === 1 ? "" : "s"}; you get one
              synthesis line + each agent&apos;s reply.
            </div>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {turns.map((turn, i) => (
                <li
                  key={`${turn.created_at}-${i}`}
                  style={{
                    padding: "12px 0",
                    borderTop: i === 0 ? "none" : "1px solid #f0f0f0",
                  }}
                >
                  {turn.role === "pm" ? (
                    <PmTurn content={turn.content} />
                  ) : (
                    <SynthesisTurn
                      synthesis={turn.content}
                      perAgent={turn.per_agent ?? []}
                      personaName={personaName}
                    />
                  )}
                </li>
              ))}
            </ul>
          )}
          <div ref={conversationEndRef} />
        </div>
      </section>

      {/* Composer */}
      <section style={cardStyle} aria-label="Send a message to the group">
        {sendError && (
          <div
            aria-live="polite"
            style={{
              fontSize: 13,
              color: "#a30000",
              background: "#fdecec",
              padding: "8px 12px",
              borderRadius: 4,
              marginBottom: 8,
            }}
          >
            {sendError}
          </div>
        )}
        <textarea
          ref={composerRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={sending}
          rows={3}
          placeholder={
            sending
              ? `Fanning out to ${n} agent${n === 1 ? "" : "s"}…`
              : `Ask all ${n} agent${n === 1 ? "" : "s"}… (Enter to send, Shift+Enter for newline)`
          }
          aria-label="Message to the persona group"
          style={{
            width: "100%",
            padding: "10px 12px",
            borderRadius: 6,
            border: "1px solid #ddd",
            fontFamily: "inherit",
            fontSize: 14,
            resize: "vertical",
            boxSizing: "border-box",
          }}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            marginTop: 8,
          }}
        >
          <button
            type="button"
            onClick={() => void handleSend()}
            disabled={sending || !draft.trim()}
            style={{
              background: "#111",
              color: "#fff",
              border: "1px solid #111",
              borderRadius: 6,
              padding: "8px 16px",
              fontSize: 14,
              fontWeight: 500,
              cursor: sending || !draft.trim() ? "not-allowed" : "pointer",
              opacity: sending || !draft.trim() ? 0.5 : 1,
            }}
          >
            {sending ? "Sending…" : "Send"}
          </button>
        </div>
      </section>
    </main>
  );
}

// ───────────────────────────────────────────────────────────────────────
// Turn renderers
// ───────────────────────────────────────────────────────────────────────

function PmTurn({ content }: { content: string }) {
  return (
    <>
      <div style={pmLabelStyle}>You</div>
      <div style={turnBodyStyle}>{content}</div>
    </>
  );
}

function SynthesisTurn({
  synthesis,
  perAgent,
  personaName,
}: {
  synthesis: string;
  perAgent: PerAgentReply[];
  personaName: string;
}) {
  return (
    <>
      <div style={synthesisLabelStyle}>Synthesis</div>
      <div
        style={{
          ...turnBodyStyle,
          fontWeight: 500,
          background: "#fafaf2",
          padding: "8px 12px",
          borderLeft: "3px solid #b08d00",
          borderRadius: "0 4px 4px 0",
        }}
      >
        {synthesis}
      </div>
      {perAgent.length > 0 && (
        <ul
          style={{
            listStyle: "none",
            padding: 0,
            margin: "12px 0 0 0",
          }}
        >
          {perAgent.map((slot) => (
            <li
              key={slot.agent_id}
              style={{
                padding: "8px 0",
                borderTop: "1px dashed #f0f0f0",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "baseline",
                  gap: 8,
                  marginBottom: 4,
                }}
              >
                <span
                  style={{
                    fontSize: 11,
                    color: "#0a7d3a",
                    textTransform: "uppercase",
                    letterSpacing: 0.5,
                    fontWeight: 600,
                  }}
                >
                  {slot.agent_label}
                </span>
                <span style={{ fontSize: 11, color: "#aaa" }}>
                  · {personaName}
                </span>
                <span style={{ flex: 1 }} />
                {slot.error == null && (
                  <Link
                    href={`/agents/${slot.agent_id}`}
                    aria-label={`Open individual chat with ${slot.agent_label}`}
                    style={{
                      fontSize: 12,
                      color: "#1d4ed8",
                      textDecoration: "none",
                    }}
                  >
                    💬 chat 1:1
                  </Link>
                )}
              </div>
              {slot.error == null ? (
                <div style={turnBodyStyle}>{slot.content}</div>
              ) : (
                <div
                  style={{
                    fontSize: 13,
                    color: "#a30000",
                    background: "#fdecec",
                    padding: "6px 10px",
                    borderRadius: 4,
                  }}
                >
                  failed — {slot.error}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

// Internal sentinel for the load-effect "persona not found" branch — lets
// us distinguish a 404 on the turns endpoint (persona doesn't exist in
// this sim) from other failures, without resorting to error.message
// substring matching.
class _PersonaNotFound extends Error {}

// ───────────────────────────────────────────────────────────────────────
// Styles
// ───────────────────────────────────────────────────────────────────────

const pageStyle: React.CSSProperties = {
  maxWidth: 720,
  margin: "32px auto 64px",
  padding: "0 24px",
};

const cardStyle: React.CSSProperties = {
  border: "1px solid #eee",
  borderRadius: 8,
  padding: 20,
  marginBottom: 16,
  background: "#fff",
};

const labelStyle: React.CSSProperties = {
  fontSize: 11,
  color: "#888",
  textTransform: "uppercase",
  letterSpacing: 0.5,
  marginBottom: 6,
  fontWeight: 600,
};

const pmLabelStyle: React.CSSProperties = {
  fontSize: 11,
  color: "#1d4ed8",
  textTransform: "uppercase",
  letterSpacing: 0.5,
  fontWeight: 600,
  marginBottom: 4,
};

const synthesisLabelStyle: React.CSSProperties = {
  fontSize: 11,
  color: "#b08d00",
  textTransform: "uppercase",
  letterSpacing: 0.5,
  fontWeight: 600,
  marginBottom: 4,
};

const turnBodyStyle: React.CSSProperties = {
  fontSize: 14,
  color: "#222",
  lineHeight: 1.55,
  whiteSpace: "pre-wrap",
};
