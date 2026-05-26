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
  type AgentReference,
  type AgentSummary,
  type PerAgentReply,
  type PersonaGroupMode,
  type PersonaGroupTurn,
  type Simulation,
  type UnavailableAgent,
} from "@/lib/api";

// Phase 4 #55 + collective mode (PR #82): persona-group chat surface.
// Spec: docs/agent-chat-ui-spec.md Surface 2 — two modes share one composer.
//
// Default mode = collective: one LLM reply speaks for the persona group;
// inline [label] tokens become drill-down links to /agents/[id]. Use for
// meta questions ("what's the consensus?", "who reacted negatively?").
//
// Individual fan-out (toggle): N replies side-by-side + counted synthesis
// line. Use when the PM wants disagreement-as-signal ("what would YOU
// change about checkout?").

// sessionStorage key — round-trip continuity: a mid-typed question
// survives navigating to /agents/[id] and back.
const draftKey = (simId: string, personaId: string) =>
  `pythia.personaGroupDraft.${simId}.${personaId}`;

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

  // Mode is reactive — flipping it doesn't reset the chat log; both modes
  // write to the same turn log on the backend and the renderer branches
  // on each turn's role.
  const [mode, setMode] = useState<PersonaGroupMode>("collective");

  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  // Most-recent per-turn unavailable_agents banner. Cleared on the next
  // successful send. Backend surfaces this when a collective load partially
  // fails (codex #82 P2) so the PM knows "answer reflects X of N agents".
  const [unavailable, setUnavailable] = useState<UnavailableAgent[]>([]);

  const conversationEndRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);

  // Restore draft from sessionStorage on mount.
  useEffect(() => {
    if (!simId || !personaId) return;
    try {
      const cached = sessionStorage.getItem(draftKey(simId, personaId));
      if (cached) setDraft(cached);
    } catch {
      // sessionStorage can throw in SSR or sandboxed contexts — non-fatal.
    }
  }, [simId, personaId]);

  // Persist draft on every change.
  useEffect(() => {
    if (!simId || !personaId) return;
    try {
      if (draft) sessionStorage.setItem(draftKey(simId, personaId), draft);
      else sessionStorage.removeItem(draftKey(simId, personaId));
    } catch {
      // ignore
    }
  }, [simId, personaId, draft]);

  // Initial load: sim (hypothesis) + agents (filter to persona) + turn log.
  useEffect(() => {
    if (!simId || !personaId) return;
    let cancelled = false;
    (async () => {
      try {
        const [simData, agents, turnLog] = await Promise.all([
          getSimulation(simId),
          listSimulationAgents(simId),
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

  // Auto-scroll within the bounded conversation container.
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
    setUnavailable([]);
    setSending(true);

    // Optimistic PM turn (matches #53 / prior #55 pattern). Capture exact
    // ref for filter-by-reference rollback.
    const optimisticPm: PersonaGroupTurn = {
      role: "pm",
      content: trimmed,
      created_at: new Date().toISOString(),
      per_agent: null,
      references: null,
    };
    setTurns((current) => [...current, optimisticPm]);
    setDraft("");

    try {
      // Phase 1: POST. Failure → rollback optimistic; restore draft.
      let resp: Awaited<ReturnType<typeof sendPersonaGroupMessage>> | null = null;
      try {
        resp = await sendPersonaGroupMessage(simId, personaId, trimmed, mode);
      } catch (e) {
        setTurns((current) => current.filter((t) => t !== optimisticPm));
        setDraft(trimmed);
        if (e instanceof ApiError) {
          if (e.status === 502) {
            setSendError(
              mode === "collective"
                ? "Could not reach the agents. Try again."
                : "All agents failed to respond. Try again.",
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

      // Phase 2: refetch canonical turn log. Codex #53 round-1 P1 pattern —
      // refetch failure ≠ send failure; keep optimistic, surface warn.
      if (resp) {
        if (resp.unavailable_agents && resp.unavailable_agents.length > 0) {
          setUnavailable(resp.unavailable_agents);
        }
        try {
          const fresh = await getPersonaGroupTurns(simId, personaId);
          setTurns(fresh);
        } catch (e) {
          setSendError(
            e instanceof Error
              ? `Sent, but couldn't refresh: ${e.message}. Reload to see the reply.`
              : "Sent, but couldn't refresh. Reload to see the reply.",
          );
        }
      }
    } finally {
      setSending(false);
    }

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
              No questions yet. Ask the group something below — the default
              answer is the collective voice of the persona (with inline
              links to drill into any agent). Switch to <em>individual
              fan-out</em> to hear each of the {n} agent
              {n === 1 ? "" : "s"} reply separately.
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
                  ) : turn.role === "collective" ? (
                    <CollectiveTurn
                      content={turn.content}
                      references={turn.references ?? []}
                      personaName={personaName}
                    />
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
        {unavailable.length > 0 && (
          <div
            aria-live="polite"
            style={{
              fontSize: 13,
              color: "#a86b00",
              background: "#fff7e6",
              padding: "8px 12px",
              borderRadius: 4,
              marginBottom: 8,
            }}
          >
            <strong>Heads up:</strong> the last reply reflects{" "}
            {n - unavailable.length} of {n} agents.{" "}
            {unavailable.length === 1
              ? "One agent"
              : `${unavailable.length} agents`}{" "}
            could not be loaded:{" "}
            {unavailable.map((u) => u.agent_label).join(", ")}.
          </div>
        )}

        <ModeToggle mode={mode} setMode={setMode} disabled={sending} n={n} />

        <textarea
          ref={composerRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={sending}
          rows={3}
          placeholder={composerPlaceholder(mode, n, sending)}
          aria-label={`Message to the persona group (${mode} mode)`}
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
// Mode toggle
// ───────────────────────────────────────────────────────────────────────

function ModeToggle({
  mode,
  setMode,
  disabled,
  n,
}: {
  mode: PersonaGroupMode;
  setMode: (m: PersonaGroupMode) => void;
  disabled: boolean;
  n: number;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Persona-group chat mode"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        marginBottom: 8,
        fontSize: 12,
        color: "#555",
      }}
    >
      <span style={{ color: "#888" }}>Ask the group as</span>
      <ModeRadio
        checked={mode === "collective"}
        onSelect={() => setMode("collective")}
        disabled={disabled}
        label="collective"
        title={`One voice speaking for all ${n} agent${n === 1 ? "" : "s"}; cites individuals inline.`}
      />
      <ModeRadio
        checked={mode === "individual"}
        onSelect={() => setMode("individual")}
        disabled={disabled}
        label="individual fan-out"
        title={`Send to all ${n} agent${n === 1 ? "" : "s"} separately; see every reply.`}
      />
    </div>
  );
}

function ModeRadio({
  checked,
  onSelect,
  disabled,
  label,
  title,
}: {
  checked: boolean;
  onSelect: () => void;
  disabled: boolean;
  label: string;
  title: string;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={checked}
      title={title}
      onClick={onSelect}
      disabled={disabled}
      style={{
        background: checked ? "#111" : "transparent",
        color: checked ? "#fff" : "#444",
        border: "1px solid #ddd",
        borderRadius: 14,
        padding: "2px 10px",
        fontSize: 12,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.6 : 1,
      }}
    >
      {label}
    </button>
  );
}

function composerPlaceholder(
  mode: PersonaGroupMode,
  n: number,
  sending: boolean,
): string {
  if (sending) {
    return mode === "collective"
      ? "Composing the group's reply…"
      : `Fanning out to ${n} agent${n === 1 ? "" : "s"}…`;
  }
  return mode === "collective"
    ? `Ask the group… (Enter to send, Shift+Enter for newline)`
    : `Ask each of the ${n} agent${n === 1 ? "" : "s"}… (Enter to send, Shift+Enter for newline)`;
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

function CollectiveTurn({
  content,
  references,
  personaName,
}: {
  content: string;
  references: AgentReference[];
  personaName: string;
}) {
  return (
    <>
      <div style={collectiveLabelStyle}>
        {personaName} <span style={{ color: "#888" }}>(collective)</span>
      </div>
      <div
        style={{
          ...turnBodyStyle,
          background: "#f4f8ff",
          padding: "10px 14px",
          borderLeft: "3px solid #1d4ed8",
          borderRadius: "0 4px 4px 0",
        }}
      >
        <RenderWithCitations content={content} references={references} />
      </div>
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
      <div style={synthesisLabelStyle}>Synthesis (fan-out)</div>
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

// ───────────────────────────────────────────────────────────────────────
// [label] linkification
// ───────────────────────────────────────────────────────────────────────

// Mirrors the backend's _CITATION_RE — word chars + dash, no whitespace,
// no punctuation. Tokens that don't match the strict shape stay as plain
// prose. Tokens that match but don't resolve to a known reference also
// stay plain (the backend already dropped hallucinated labels from
// references; we just don't auto-link them).
const CITATION_RE = /\[([\w-]+)\]/g;

function RenderWithCitations({
  content,
  references,
}: {
  content: string;
  references: AgentReference[];
}) {
  const labelToId = new Map(references.map((r) => [r.agent_label, r.agent_id]));
  const out: React.ReactNode[] = [];
  let lastIdx = 0;
  let match: RegExpExecArray | null;
  // Reset stateful regex between renders.
  CITATION_RE.lastIndex = 0;
  let n = 0;
  while ((match = CITATION_RE.exec(content)) !== null) {
    const [token, label] = match;
    if (match.index > lastIdx) {
      out.push(content.slice(lastIdx, match.index));
    }
    const agentId = labelToId.get(label);
    if (agentId) {
      out.push(
        <Link
          key={`cite-${n}-${label}`}
          href={`/agents/${agentId}`}
          style={{
            color: "#1d4ed8",
            textDecoration: "underline",
            fontWeight: 500,
          }}
        >
          {label}
        </Link>,
      );
    } else {
      // Hallucinated or stripped token — render the raw `[label]` so the
      // PM sees what the model wrote without a broken link.
      out.push(token);
    }
    lastIdx = match.index + token.length;
    n += 1;
  }
  if (lastIdx < content.length) {
    out.push(content.slice(lastIdx));
  }
  return <>{out}</>;
}

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

const collectiveLabelStyle: React.CSSProperties = {
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
