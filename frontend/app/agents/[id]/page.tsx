"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  ApiError,
  getAgent,
  getSimulation,
  sendAgentMessage,
  type AgentChatTurn,
  type AgentInstance,
  type Simulation,
} from "@/lib/api";

// Phase 4 #53: individual-agent chat surface.
// Spec layout (docs/agent-chat-ui-spec.md "Surface 3"):
//   1. Identity card — pinned, top. Persona name + identity_seed key fields.
//   2. Hypothesis prose + initial reaction — pinned. Both in view together.
//   3. Conversation log — scrollable; auto-scrolls on new turn.
//   4. Composer — bottom, enter-to-send, multi-line via shift+enter.
// Identity-continuity guarantee is enforced server-side; the UI just renders.

export default function AgentChatPage() {
  const params = useParams<{ id: string }>();
  const agentId = params?.id ?? "";

  const [agent, setAgent] = useState<AgentInstance | null>(null);
  const [sim, setSim] = useState<Simulation | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const conversationEndRef = useRef<HTMLDivElement | null>(null);

  // Initial fetch — agent + its parent simulation (for the hypothesis prose).
  useEffect(() => {
    if (!agentId) return;
    let cancelled = false;
    (async () => {
      try {
        const a = await getAgent(agentId);
        if (cancelled) return;
        setAgent(a);
        try {
          const s = await getSimulation(a.metadata.simulation_id);
          if (!cancelled) setSim(s);
        } catch {
          // Sim fetch failure is non-fatal — we just hide the hypothesis pane.
          // The chat itself still works.
        }
      } catch (e) {
        if (cancelled) return;
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
  }, [agentId]);

  // Auto-scroll to the newest turn whenever the conversation grows.
  const conversationLen = agent?.conversation?.length ?? 0;
  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversationLen]);

  async function handleSend() {
    const trimmed = draft.trim();
    if (!trimmed || sending || !agent) return;
    setSendError(null);
    setSending(true);

    // Optimistic PM turn so the UI doesn't feel dead while the LLM responds.
    // A refetch after success replaces optimistic with canonical.
    const optimisticPm: AgentChatTurn = {
      role: "pm",
      content: trimmed,
      created_at: new Date().toISOString(),
      realistic_flag: null,
    };
    const baselineConversation = agent.conversation ?? [];
    setAgent({
      ...agent,
      conversation: [...baselineConversation, optimisticPm],
    });
    setDraft("");

    try {
      await sendAgentMessage(agentId, trimmed);
      // Server persisted both turns. Refetch to get canonical timestamps +
      // the agent reply with the same shape the server stored.
      const fresh = await getAgent(agentId);
      setAgent(fresh);
    } catch (e) {
      // Roll back the optimistic PM turn — the server's #52 ordering means
      // a failed call persists neither turn, so local state should mirror.
      setAgent({
        ...agent,
        conversation: baselineConversation,
      });
      setDraft(trimmed); // restore so the user can retry without re-typing
      if (e instanceof ApiError) {
        setSendError(
          e.status === 502
            ? "The agent took too long to respond. Try again."
            : `Send failed (HTTP ${e.status}): ${e.body || e.message}`,
        );
      } else {
        setSendError(e instanceof Error ? e.message : "Send failed.");
      }
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter to send; Shift+Enter for newline.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  // ─── Render ────────────────────────────────────────────────────────────

  if (notFound) {
    return (
      <main style={pageStyle}>
        <div style={{ ...cardStyle, color: "#a30000", background: "#fdecec" }}>
          <strong>Agent not found.</strong>
        </div>
      </main>
    );
  }
  if (loadError) {
    return (
      <main style={pageStyle}>
        <div style={{ ...cardStyle, color: "#a30000", background: "#fdecec" }}>
          <strong>Failed to load agent:</strong> {loadError}
        </div>
      </main>
    );
  }
  if (!agent) {
    return (
      <main style={pageStyle}>
        <div style={{ color: "#666", fontSize: 14 }}>Loading agent…</div>
      </main>
    );
  }

  const seed = agent.identity_seed;
  const persona = agent.metadata.persona_name;
  const hypothesisProse = sim?.hypothesis?.prose ?? null;

  return (
    <main style={pageStyle}>
      <div style={{ marginBottom: 16 }}>
        <Link
          href={`/simulations/${agent.metadata.simulation_id}`}
          style={{ color: "#1d4ed8", textDecoration: "none", fontSize: 13 }}
        >
          ← back to simulation
        </Link>
      </div>

      {/* Identity card (pinned to top via sticky) */}
      <section
        style={{ ...cardStyle, position: "sticky", top: 12, zIndex: 2 }}
        aria-label="Agent identity"
      >
        <div style={labelStyle}>Persona</div>
        <div style={{ fontSize: 20, fontWeight: 600, color: "#111" }}>
          {persona}
        </div>
        <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>
          {agent.metadata.persona_id} · pack {agent.metadata.persona_pack_version}
        </div>
        {seed && (
          <ul
            style={{
              listStyle: "none",
              padding: 0,
              margin: "12px 0 0 0",
              display: "grid",
              gridTemplateColumns: "auto 1fr",
              columnGap: 12,
              rowGap: 4,
              fontSize: 13,
            }}
          >
            <SeedRow label="Age" value={seed.age_band} />
            <SeedRow label="Locale" value={seed.locale_band} />
            <SeedRow label="Tenure" value={seed.tenure_band} />
            <SeedRow label="Currently" value={seed.current_state} />
            <SeedRow label="Recent gripe" value={seed.recent_gripe} />
          </ul>
        )}
      </section>

      {/* Hypothesis + initial reaction */}
      <section style={cardStyle} aria-label="Hypothesis and initial reaction">
        {hypothesisProse && (
          <>
            <div style={labelStyle}>Hypothesis under test</div>
            <div style={{ fontSize: 14, color: "#333", lineHeight: 1.5 }}>
              {hypothesisProse}
            </div>
            <div
              style={{
                margin: "16px 0 8px 0",
                borderTop: "1px solid #eee",
              }}
            />
          </>
        )}
        <div style={labelStyle}>Initial reaction</div>
        <div
          style={{
            fontSize: 14,
            color: "#222",
            lineHeight: 1.6,
            whiteSpace: "pre-wrap",
          }}
        >
          {agent.initial_reaction}
        </div>
      </section>

      {/* Conversation */}
      <section style={cardStyle} aria-label="Conversation">
        <div style={labelStyle}>Conversation</div>
        {(agent.conversation ?? []).length === 0 ? (
          <div style={{ fontSize: 14, color: "#888", padding: "8px 0" }}>
            No follow-ups yet. Ask a question below to start.
          </div>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {(agent.conversation ?? []).map((turn, i) => (
              <li
                key={`${turn.created_at}-${i}`}
                style={{
                  padding: "10px 0",
                  borderTop: i === 0 ? "none" : "1px solid #f0f0f0",
                }}
              >
                <div
                  style={{
                    fontSize: 11,
                    color: turn.role === "pm" ? "#1d4ed8" : "#0a7d3a",
                    textTransform: "uppercase",
                    letterSpacing: 0.5,
                    fontWeight: 600,
                    marginBottom: 4,
                  }}
                >
                  {turn.role === "pm" ? "You" : persona}
                </div>
                <div
                  style={{
                    fontSize: 14,
                    color: "#222",
                    lineHeight: 1.55,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {turn.content}
                </div>
              </li>
            ))}
          </ul>
        )}
        <div ref={conversationEndRef} />
      </section>

      {/* Composer */}
      <section style={cardStyle} aria-label="Send a message">
        {sendError && (
          <div
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
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={sending}
          rows={3}
          placeholder={
            sending
              ? "Sending…"
              : "Ask a follow-up… (Enter to send, Shift+Enter for newline)"
          }
          aria-label="Message to the agent"
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

function SeedRow({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  return (
    <>
      <span style={{ color: "#888" }}>{label}</span>
      <span style={{ color: "#222" }}>{value || "—"}</span>
    </>
  );
}

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
