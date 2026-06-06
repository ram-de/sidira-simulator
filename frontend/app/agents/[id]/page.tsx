"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  ApiError,
  getAgent,
  getSimulation,
  sendAgentMessage,
  sendAgentTurnFeedback,
  type AgentChatTurn,
  type AgentInstance,
  type Simulation,
} from "@/lib/api";
import { ThumbsControl } from "@/components/ThumbsControl";
import { TOKENS, FONT_SANS } from "@/lib/design";

// sessionStorage key — drafts survive nav round-trips
// (e.g. clicking through to /agents/[id] from a persona-group [label]
// citation and back).
const draftKey = (agentId: string) => `pythia.agentDraft.${agentId}`;

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

  // Single effect that does BOTH restore (on route change) and persist
  // (on draft change within the same route). Codex #83 round-2 P2: the
  // two-effect split raced under StrictMode double-mount — persist could
  // fire with the initial `draft=""` before restore's setDraft committed,
  // deleting the cached value. Distinguishing route-change-firstrun from
  // same-route fixes the race; see the mirror comment on the persona-group
  // page for the full trace.
  const lastDraftKey = useRef<string | null>(null);
  useEffect(() => {
    if (!agentId) return;
    const key = draftKey(agentId);
    if (lastDraftKey.current !== key) {
      lastDraftKey.current = key;
      try {
        const cached = sessionStorage.getItem(key);
        setDraft(cached ?? "");
      } catch {
        setDraft("");
      }
      return;
    }
    try {
      if (draft) sessionStorage.setItem(key, draft);
      else sessionStorage.removeItem(key);
    } catch {
      // ignore
    }
  }, [agentId, draft]);

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
    // The exact object reference is captured here so the rollback path can
    // filter precisely this turn out without disturbing any concurrent
    // updates that may have appended other turns in the meantime.
    // (codex #53 round-2 P2)
    const optimisticPm: AgentChatTurn = {
      role: "pm",
      content: trimmed,
      created_at: new Date().toISOString(),
      realistic_flag: null,
    };
    setAgent((current) =>
      current
        ? {
            ...current,
            // Read from current.conversation, NOT a closure-captured baseline,
            // so concurrent appends aren't clobbered.
            conversation: [...(current.conversation ?? []), optimisticPm],
          }
        : current,
    );
    setDraft("");

    // setSending(false) in finally so a future edit can't strand the
    // composer in the sending state (codex #53 round-2 nit).
    try {
      // Phase 1: send. Failure here means the server persisted nothing
      // (server-side #52 ordering); safe to remove the optimistic turn.
      let sendOk = false;
      try {
        await sendAgentMessage(agentId, trimmed);
        sendOk = true;
      } catch (e) {
        // Remove ONLY the optimistic turn by reference, not the whole
        // conversation, so any concurrent updates survive.
        setAgent((current) =>
          current
            ? {
                ...current,
                conversation: (current.conversation ?? []).filter(
                  (t) => t !== optimisticPm,
                ),
              }
            : current,
        );
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
      }

      // Phase 2: refetch to get canonical timestamps + the agent's reply.
      // Codex #53 round-1 P1: SEPARATE failure class. A refetch error
      // here does NOT mean the send failed — both turns are already
      // persisted server-side. Rolling back would prompt a retry that
      // duplicates the persisted PM turn. Instead keep the optimistic
      // PM turn visible and show a refresh-only error.
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
    } finally {
      setSending(false);
    }

    // Refocus the composer after every send — chat UX is a type → send →
    // read reply → type next loop, so keeping focus in the composer is
    // what the user wants. (Codex #53 round-3 P2: the prior conditional
    // `if (sendError != null || draft)` read stale closure values and
    // fired on success too; the right move is to just not guard.)
    // Deferred via requestAnimationFrame so the textarea is no longer
    // `disabled` (sending=false) by the time we call .focus() — some
    // browsers ignore focus on a still-disabled element.
    requestAnimationFrame(() => composerRef.current?.focus());
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
        <div style={{ ...cardStyle, color: TOKENS.alert, background: TOKENS.paperRecessed }}>
          <strong>Agent not found.</strong>
        </div>
      </main>
    );
  }
  if (loadError) {
    return (
      <main style={pageStyle}>
        <div style={{ ...cardStyle, color: TOKENS.alert, background: TOKENS.paperRecessed }}>
          <strong>Failed to load agent:</strong> {loadError}
        </div>
      </main>
    );
  }
  if (!agent) {
    return (
      <main style={pageStyle}>
        <div style={{ color: TOKENS.inkMuted, fontSize: 14 }}>Loading agent…</div>
      </main>
    );
  }

  const seed = agent.identity_seed;
  const persona = agent.metadata.persona_name;
  const hypothesisProse = sim?.hypothesis?.prose ?? null;
  const groupArm =
    agent.metadata.arm === "treatment" || agent.metadata.arm === "control"
      ? agent.metadata.arm
      : null;
  const personaGroupHref = `/simulations/${agent.metadata.simulation_id}/personas/${agent.metadata.persona_id}${
    groupArm ? `?arm=${groupArm}` : ""
  }`;
  const personaGroupLabel = groupArm ? `${groupArm} group chat` : "group chat";

  return (
    <main style={pageStyle}>
      <div
        style={{
          display: "flex",
          gap: 16,
          marginBottom: 16,
          flexWrap: "wrap",
        }}
      >
        <Link
          href={`/simulations/${agent.metadata.simulation_id}`}
          style={{ color: TOKENS.ink, textDecoration: "none", fontSize: 13 }}
        >
          ← back to simulation
        </Link>
        <Link
          href={personaGroupHref}
          style={{ color: TOKENS.ink, textDecoration: "none", fontSize: 13 }}
        >
          ← back to {persona} ({personaGroupLabel})
        </Link>
      </div>

      {/* Identity card (pinned to top via sticky) */}
      <section
        style={{ ...cardStyle, position: "sticky", top: 12, zIndex: 2 }}
        aria-label="Agent identity"
      >
        <div style={labelStyle}>Persona</div>
        <div style={{ fontSize: 20, fontWeight: 600, color: TOKENS.ink }}>
          {persona}
        </div>
        <div style={{ fontSize: 12, color: TOKENS.inkMuted, marginTop: 2 }}>
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
            <div style={{ fontSize: 14, color: TOKENS.ink, lineHeight: 1.5 }}>
              {hypothesisProse}
            </div>
            <div
              style={{
                margin: "16px 0 8px 0",
                borderTop: `0.75px solid ${TOKENS.rule}`,
              }}
            />
          </>
        )}
        <div style={labelStyle}>Initial reaction</div>
        <div
          style={{
            fontSize: 14,
            color: TOKENS.ink,
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
          <div style={{ fontSize: 14, color: TOKENS.inkMuted, padding: "8px 0" }}>
            No follow-ups yet. Ask a question below to start.
          </div>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {(agent.conversation ?? []).map((turn, i) => (
              <li
                key={`${turn.created_at}-${i}`}
                style={{
                  padding: "10px 0",
                  borderTop: i === 0 ? "none" : `0.75px solid ${TOKENS.rule}`,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 4,
                  }}
                >
                  <span
                    style={{
                      fontSize: 11,
                      color: turn.role === "pm" ? "#1d4ed8" : "#0a7d3a",
                      textTransform: "uppercase",
                      letterSpacing: 0.5,
                      fontWeight: 600,
                    }}
                  >
                    {turn.role === "pm" ? "You" : persona}
                  </span>
                  <span style={{ flex: 1 }} />
                  {/* #56: calibration thumbs only on agent replies. PM
                      turns are the PM's own writing — no calibration
                      target. */}
                  {turn.role === "agent" && (
                    <ThumbsControl
                      ariaLabel="Was this reply realistic?"
                      flag={turn.realistic_flag ?? null}
                      onSet={async (next) => {
                        await sendAgentTurnFeedback(agentId, i, next);
                        // Update the local turn so a subsequent toggle
                        // reads the new server-confirmed state.
                        setAgent((current) =>
                          current
                            ? {
                                ...current,
                                conversation: (current.conversation ?? []).map(
                                  (t, idx) =>
                                    idx === i
                                      ? { ...t, realistic_flag: next }
                                      : t,
                                ),
                              }
                            : current,
                        );
                      }}
                    />
                  )}
                </div>
                <div
                  style={{
                    fontSize: 14,
                    color: TOKENS.ink,
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
            // Use aria-live="polite" alone, not role="alert" + aria-live —
            // role="alert" already implies assertive live-region behavior;
            // pairing them is contradictory. Polite is correct here: a
            // failed send isn't urgent enough to interrupt the user's
            // current narration (codex #53 round-2 nit).
            aria-live="polite"
            style={{
              fontSize: 13,
              color: TOKENS.alert,
              background: TOKENS.paperRecessed,
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
            border: `0.75px solid ${TOKENS.rule}`,
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
              background: TOKENS.ink,
              color: TOKENS.paper,
              border: `0.75px solid ${TOKENS.ink}`,
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
      <span style={{ color: TOKENS.inkMuted }}>{label}</span>
      <span style={{ color: TOKENS.ink }}>{value || "—"}</span>
    </>
  );
}

const pageStyle: React.CSSProperties = {
  maxWidth: 720,
  margin: "32px auto 64px",
  padding: "0 24px",
};

const cardStyle: React.CSSProperties = {
  border: `0.75px solid ${TOKENS.rule}`,
  borderRadius: 4,
  padding: 20,
  marginBottom: 16,
  background: TOKENS.paperElevated,
};

const labelStyle: React.CSSProperties = {
  fontSize: 11,
  color: TOKENS.inkMuted,
  textTransform: "uppercase",
  letterSpacing: 0.5,
  marginBottom: 6,
  fontWeight: 600,
};
