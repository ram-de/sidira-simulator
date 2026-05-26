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
  const composerRef = useRef<HTMLTextAreaElement | null>(null);

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
  // Codex #53 P2: scroll WITHIN the bounded conversation container, not the
  // document, so the sticky identity card above stays in place and the new
  // turn doesn't get covered by it. `block: "nearest"` is the safety belt
  // for browsers that fall back to document-level scrolling.
  const conversationLen = agent?.conversation?.length ?? 0;
  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
    });
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
    setAgent((current) =>
      current
        ? { ...current, conversation: [...baselineConversation, optimisticPm] }
        : current,
    );
    setDraft("");

    // Phase 1: send. Failure here means the server persisted nothing
    // (server-side #52 ordering); safe to roll back the optimistic turn.
    let sendOk = false;
    try {
      await sendAgentMessage(agentId, trimmed);
      sendOk = true;
    } catch (e) {
      setAgent((current) =>
        current ? { ...current, conversation: baselineConversation } : current,
      );
      setDraft(trimmed); // restore so the user can retry without re-typing
      // Refocus the composer so retry is one keystroke away.
      composerRef.current?.focus();
      if (e instanceof ApiError) {
        setSendError(
          e.status === 502
            ? "The agent took too long to respond. Try again."
            : `Send failed (HTTP ${e.status}): ${e.body || e.message}`,
        );
      } else {
        setSendError(e instanceof Error ? e.message : "Send failed.");
      }
    }

    // Phase 2: refetch to get canonical timestamps + the agent's reply.
    // Codex #53 P1: this is a SEPARATE failure class. A refetch error here
    // does NOT mean the send failed — both turns are already persisted
    // server-side. Rolling back would tell the user "your message didn't
    // go through" and prompt a retry that duplicates the persisted PM turn.
    // Instead: keep the optimistic PM turn visible, show a refresh-only
    // error, and let the user reload manually.
    if (sendOk) {
      try {
        const fresh = await getAgent(agentId);
        setAgent(fresh);
      } catch (e) {
        setSendError(
          e instanceof Error
            ? `Sent, but couldn't refresh the conversation: ${e.message}. Reload the page to see the latest.`
            : "Sent, but couldn't refresh the conversation. Reload the page to see the latest.",
        );
      }
    }

    setSending(false);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter to send; Shift+Enter for newline. Ignore Enter during IME
    // composition (Japanese/Chinese/Korean input methods commit a candidate
    // with Enter — submitting then would lose the user's in-progress text).
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

      {/* Conversation — bounded scroll so the sticky identity card above
          doesn't cover newly-appended turns (codex #53 P2). */}
      <section style={cardStyle} aria-label="Conversation">
        <div style={labelStyle}>Conversation</div>
        <div
          style={{
            maxHeight: "50vh",
            overflowY: "auto",
            // Light inset so the scroll edge isn't flush with the section border.
            padding: "0 4px",
          }}
        >
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
        </div>
      </section>

      {/* Composer */}
      <section style={cardStyle} aria-label="Send a message">
        {sendError && (
          <div
            role="alert"
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
