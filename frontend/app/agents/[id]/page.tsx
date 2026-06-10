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
import { FONT_MONO, TNUM, TOKENS } from "@/lib/design";

// sessionStorage key — drafts survive nav round-trips
// (e.g. clicking through to /agents/[id] from a persona-group [label]
// citation and back).
const draftKey = (agentId: string) => `pythia.agentDraft.${agentId}`;

// Phase 4 #53: individual-agent chat surface.
// R2 #170 evidentiary restyle (DESIGN.md §7.4 "evidentiary but human"):
//   1. Header strip — persona name + HYP/RUN designators linking back to
//      the run (the hypothesis lives on the simulation page).
//   2. Rooms rail — paper-elevated, selected-row inset marker; rooms are
//      the surfaces that exist today (arm-scoped persona group chats +
//      this 1:1). The rail also carries the identity.md-frozen seed and
//      the provenance grid (§8.7).
//   3. Thread — sys-line in sentence-case body font (mono for designators
//      only); every message carries mono provenance meta + actions
//      (transcripts are evidence).
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
  // document, so the header above stays in place and the new turn doesn't
  // get covered by it. `block: "nearest"` is the safety belt for browsers
  // that fall back to document-level scrolling.
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
        <div style={{ ...errorCardStyle }}>
          <strong>Agent not found.</strong>
        </div>
      </main>
    );
  }
  if (loadError) {
    return (
      <main style={pageStyle}>
        <div style={{ ...errorCardStyle }}>
          <strong>Failed to load agent:</strong> {loadError}
        </div>
      </main>
    );
  }
  if (!agent) {
    return (
      <main style={pageStyle}>
        <div style={{ fontSize: 14, color: TOKENS.inkMuted }}>Loading agent…</div>
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
  const personaGroupBase = `/simulations/${agent.metadata.simulation_id}/personas/${agent.metadata.persona_id}`;
  const personaGroupHref = `${personaGroupBase}${groupArm ? `?arm=${groupArm}` : ""}`;

  const simId = agent.metadata.simulation_id;
  const simHref = `/simulations/${simId}`;
  // Honest designators: there is no run-number sequence in the data — the
  // run designator IS the simulation id (truncated for the strip, full id
  // on the title attribute). Same for the agent id in the provenance grid.
  const runDesignator = `RUN ${simId.slice(0, 8)}`;
  const conversation = agent.conversation ?? [];

  return (
    <main style={pageStyle}>
      {/* Header strip — links back to the hypothesis + run */}
      <header style={pageStripStyle}>
        <h1 style={pageTitleStyle}>{persona}</h1>
        <span style={pageSubStyle}>
          {sim?.hypothesis?.capability_name && (
            <>
              <Link href={simHref} style={subLinkStyle} title="Open the hypothesis">
                HYP · {sim.hypothesis.capability_name.toUpperCase()}
              </Link>
              {" · "}
            </>
          )}
          <Link href={simHref} style={subLinkStyle} title={simId}>
            {runDesignator}
          </Link>
          {" · 1:1 INTERROGATION"}
        </span>
        <span style={pageTagStyle}>TRANSCRIPTS ARE EVIDENCE</span>
      </header>

      {/* Hypothesis under test — record, on paper */}
      {hypothesisProse && (
        <section style={hypothesisStripStyle} aria-label="Hypothesis under test">
          <div style={labelStyle}>Hypothesis under test</div>
          <div style={{ fontSize: 14, color: TOKENS.ink, lineHeight: 1.5, maxWidth: "72ch" }}>
            {hypothesisProse}
          </div>
        </section>
      )}

      <div style={chatPanelStyle}>
        {/* Rooms rail — the chat surfaces that exist today */}
        <aside style={roomsRailStyle} aria-label="Rooms">
          <div style={railHeadStyle}>
            <span style={labelStyle}>Rooms</span>
          </div>
          {groupArm ? (
            <>
              <Link
                href={`${personaGroupBase}?arm=treatment`}
                style={roomRowStyle}
                title={`${persona} group chat — treatment arm`}
              >
                <span style={roomNameStyle}>Arm · treatment</span>
                <span style={roomMetaStyle}>GROUP</span>
              </Link>
              <Link
                href={`${personaGroupBase}?arm=control`}
                style={roomRowStyle}
                title={`${persona} group chat — control arm`}
              >
                <span style={roomNameStyle}>Arm · control</span>
                <span style={roomMetaStyle}>GROUP</span>
              </Link>
            </>
          ) : (
            <Link
              href={personaGroupHref}
              style={roomRowStyle}
              title={`${persona} group chat`}
            >
              <span style={roomNameStyle}>Cohort · {persona}</span>
              <span style={roomMetaStyle}>GROUP</span>
            </Link>
          )}
          <div style={roomRowSelectedStyle} aria-current="page">
            <span style={{ ...roomNameStyle, fontWeight: 600 }}>1:1 · {persona}</span>
            <span style={{ ...roomMetaStyle, ...TNUM }}>TURN {conversationLen}</span>
          </div>

          {/* identity.md — the slice frozen at materialization */}
          {seed && (
            <div style={identitySectionStyle} aria-label="Frozen identity seed">
              <span style={{ ...labelStyle, display: "block", marginBottom: 8 }}>
                identity.md — frozen
              </span>
              <dl style={seedGridStyle}>
                <SeedRow label="Age" value={seed.age_band} />
                <SeedRow label="Locale" value={seed.locale_band} />
                <SeedRow label="Tenure" value={seed.tenure_band} />
                <SeedRow label="Currently" value={seed.current_state} />
                <SeedRow label="Recent gripe" value={seed.recent_gripe} />
              </dl>
            </div>
          )}

          {/* Provenance grid — §8.7 */}
          <dl style={provenanceStyle} aria-label="Provenance">
            <dt style={provDtStyle}>Run</dt>
            <dd style={provDdStyle}>
              <Link href={simHref} style={provLinkStyle} title={simId}>
                {runDesignator}
              </Link>
            </dd>
            <dt style={provDtStyle}>Agent</dt>
            <dd style={provDdStyle} title={agent.metadata.id}>
              {agent.metadata.id.slice(0, 8)}
            </dd>
            <dt style={provDtStyle}>Pack</dt>
            <dd style={provDdStyle}>{agent.metadata.persona_pack_version}</dd>
            <dt style={provDtStyle}>Arm</dt>
            <dd style={provDdStyle}>{groupArm ? groupArm.toUpperCase() : "—"}</dd>
            <dt style={provDtStyle}>Seed</dt>
            <dd style={{ ...provDdStyle, ...TNUM }}>
              {sim?.run_seed != null ? String(sim.run_seed) : "—"}
            </dd>
            <dt style={provDtStyle}>Model</dt>
            <dd style={provDdStyle}>{sim?.model_id ?? "—"}</dd>
            <dt style={provDtStyle}>Frozen</dt>
            <dd style={{ ...provDdStyle, ...TNUM }}>
              {fmtDate(agent.metadata.created_at)}
            </dd>
          </dl>
        </aside>

        {/* Thread */}
        <div style={chatThreadStyle}>
          <div style={chatScrollStyle}>
            {/* Sys-line: sentence-case body font; mono for designators only */}
            <div style={sysLineStyle}>
              {groupArm ? (
                <>
                  1:1 room opened from{" "}
                  <span style={sysMonoStyle}>{runDesignator}</span> · arm-scoped —
                  this agent saw the {groupArm} arm only.
                </>
              ) : (
                <>
                  1:1 room opened from{" "}
                  <span style={sysMonoStyle}>{runDesignator}</span> — this agent
                  retains its run memory.
                </>
              )}
            </div>

            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {/* Initial reaction — the agent's first turn, evidence like
                  every other. Timestamp = materialization (metadata.created_at);
                  the turn itself carries no timestamp field. */}
              <li style={msgAgentStyle}>
                <div style={msgMetaStyle}>
                  <span style={msgWhoAgentStyle}>{persona.toUpperCase()}</span>
                  <span style={armTagStyle}>INITIAL REACTION</span>
                  {groupArm && (
                    <span style={armTagStyle}>{groupArm.toUpperCase()}</span>
                  )}
                  <span style={TNUM}>{fmtTime(agent.metadata.created_at)}</span>
                </div>
                <div style={msgBodyAgentStyle}>{agent.initial_reaction}</div>
                <MsgActions simHref={simHref} runDesignator={runDesignator} />
              </li>

              {conversation.length === 0 ? (
                <li style={{ fontSize: 13.5, color: TOKENS.inkMuted, padding: "8px 0" }}>
                  No follow-ups yet. Ask a question below to start.
                </li>
              ) : (
                conversation.map((turn, i) =>
                  turn.role === "pm" ? (
                    <li key={`${turn.created_at}-${i}`} style={msgPmStyle}>
                      <div style={{ ...msgMetaStyle, justifyContent: "flex-end" }}>
                        <span style={msgWhoPmStyle}>YOU · PM</span>
                        <span style={TNUM}>{fmtTime(turn.created_at)}</span>
                      </div>
                      <div style={msgBodyPmStyle}>{turn.content}</div>
                    </li>
                  ) : (
                    <li key={`${turn.created_at}-${i}`} style={msgAgentStyle}>
                      <div style={msgMetaStyle}>
                        {/* Role designators are ink-weight, not color-coded —
                            semantic colors are reserved for outcomes (§4.3). */}
                        <span style={msgWhoAgentStyle}>{persona.toUpperCase()}</span>
                        {groupArm && (
                          <span style={armTagStyle}>{groupArm.toUpperCase()}</span>
                        )}
                        <span style={TNUM}>{fmtTime(turn.created_at)}</span>
                        <span style={{ flex: 1 }} />
                        {/* #56: calibration feedback only on agent replies. PM
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
                                      conversation: (
                                        current.conversation ?? []
                                      ).map((t, idx) =>
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
                      <div style={msgBodyAgentStyle}>{turn.content}</div>
                      <MsgActions
                        simHref={simHref}
                        runDesignator={runDesignator}
                      />
                    </li>
                  ),
                )
              )}
            </ul>

            {/* Honest in-flight state — text, never a spinner (§8.6) */}
            {sending && (
              <div style={typingStyle}>{persona.toUpperCase()} COMPOSING</div>
            )}
            <div ref={conversationEndRef} />
          </div>

          {/* Composer */}
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
                padding: "8px 16px",
                borderTop: `1px solid ${TOKENS.rule}`,
              }}
            >
              {sendError}
            </div>
          )}
          <div style={chatInputStyle}>
            <textarea
              ref={composerRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sending}
              rows={2}
              placeholder={
                sending
                  ? "Sending…"
                  : `Ask ${persona}… (Enter to send, Shift+Enter for newline)`
              }
              aria-label="Message to the agent"
              style={composerStyle}
            />
            <button
              type="button"
              onClick={() => void handleSend()}
              disabled={sending || !draft.trim()}
              style={{
                ...sendButtonStyle,
                cursor: sending || !draft.trim() ? "not-allowed" : "pointer",
                opacity: sending || !draft.trim() ? 0.5 : 1,
              }}
            >
              {sending ? "Sending…" : "Send"}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}

// Per-message actions — transcripts are evidence. VIEW RUN READING links to
// the real reading; PIN TO DECISION RECORD is the evidentiary affordance,
// disabled until the decision record exists in the backend (no pin API yet —
// an enabled control would be a broken promise).
function MsgActions({
  simHref,
  runDesignator,
}: {
  simHref: string;
  runDesignator: string;
}) {
  return (
    <div style={msgActionsStyle}>
      <button
        type="button"
        disabled
        title="Pinning lands with the decision record — not yet available"
        style={pinDisabledStyle}
      >
        PIN TO DECISION RECORD
      </button>
      <Link href={simHref} style={msgActionLinkStyle}>
        VIEW {runDesignator} READING
      </Link>
    </div>
  );
}

function SeedRow({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  // Seed values are persona context prose, not machine designators —
  // body font, sentence case (§5.4).
  return (
    <>
      <dt style={seedDtStyle}>{label}</dt>
      <dd style={seedDdStyle}>{value || "—"}</dd>
    </>
  );
}

function fmtTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.toISOString().slice(11, 19)}Z`;
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toISOString().slice(0, 10);
}

// ─── Styles ──────────────────────────────────────────────────────────────

const pageStyle: React.CSSProperties = {
  maxWidth: 1080,
  margin: "24px auto 64px",
  padding: "0 24px",
};

const pageStripStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "baseline",
  gap: 16,
  flexWrap: "wrap",
  padding: "0 0 14px",
  borderBottom: `1px solid ${TOKENS.rule}`,
};

const pageTitleStyle: React.CSSProperties = {
  fontSize: 20,
  fontWeight: 600,
  letterSpacing: "-0.01em",
  color: TOKENS.ink,
  margin: 0,
};

const pageSubStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 11,
  color: TOKENS.inkMuted,
  letterSpacing: "0.06em",
};

const subLinkStyle: React.CSSProperties = {
  color: TOKENS.inkMuted,
  textDecoration: "none",
  borderBottom: `1px dotted ${TOKENS.inkMuted}`,
};

const pageTagStyle: React.CSSProperties = {
  marginLeft: "auto",
  fontFamily: FONT_MONO,
  fontSize: 10,
  letterSpacing: "0.08em",
  color: TOKENS.inkMuted,
  border: `1px solid ${TOKENS.rule}`,
  borderRadius: 2,
  padding: "3px 8px",
  whiteSpace: "nowrap",
};

const hypothesisStripStyle: React.CSSProperties = {
  padding: "14px 0",
  borderBottom: `1px solid ${TOKENS.rule}`,
};

const labelStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 500,
  letterSpacing: "0.16em",
  textTransform: "uppercase",
  color: TOKENS.inkMuted,
  marginBottom: 6,
};

const chatPanelStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  marginTop: 16,
  border: `1px solid ${TOKENS.rule}`,
  borderRadius: 4,
  background: TOKENS.paper,
  overflow: "hidden",
};

const roomsRailStyle: React.CSSProperties = {
  flex: "1 0 248px",
  maxWidth: "100%",
  display: "flex",
  flexDirection: "column",
  borderRight: `1px solid ${TOKENS.rule}`,
  background: TOKENS.paperElevated,
  boxShadow: "inset -1px 0 0 rgba(255, 255, 255, 0.55)",
};

const railHeadStyle: React.CSSProperties = {
  padding: "14px 18px 10px",
  borderBottom: `1px solid ${TOKENS.rule}`,
};

const roomRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "baseline",
  gap: 10,
  padding: "11px 18px",
  borderBottom: `1px solid ${TOKENS.rule}`,
  textDecoration: "none",
  transition: "background 80ms ease-out",
};

const roomRowSelectedStyle: React.CSSProperties = {
  ...roomRowStyle,
  background: TOKENS.paperRecessed,
  boxShadow: `inset 2px 0 0 ${TOKENS.ink}`,
};

const roomNameStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 500,
  color: TOKENS.ink,
  flex: 1,
};

const roomMetaStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10.5,
  color: TOKENS.inkMuted,
  letterSpacing: "0.04em",
};

const identitySectionStyle: React.CSSProperties = {
  padding: "14px 18px 16px",
};

const seedGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "auto 1fr",
  gap: "4px 14px",
  margin: 0,
};

const seedDtStyle: React.CSSProperties = {
  fontSize: 10,
  letterSpacing: "0.12em",
  textTransform: "uppercase",
  color: TOKENS.inkMuted,
  paddingTop: 2,
};

const seedDdStyle: React.CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.45,
  color: TOKENS.ink,
  margin: 0,
};

const provenanceStyle: React.CSSProperties = {
  marginTop: "auto",
  marginBottom: 0,
  padding: "14px 18px 16px",
  borderTop: `1px solid ${TOKENS.rule}`,
  display: "grid",
  gridTemplateColumns: "auto 1fr",
  gap: "3px 16px",
};

const provDtStyle: React.CSSProperties = {
  fontSize: 11,
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: TOKENS.inkMuted,
  paddingTop: 1,
};

const provDdStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 12,
  color: TOKENS.ink,
  margin: 0,
};

const provLinkStyle: React.CSSProperties = {
  color: TOKENS.ink,
  textDecoration: "none",
  borderBottom: `1px dotted ${TOKENS.inkMuted}`,
};

const chatThreadStyle: React.CSSProperties = {
  flex: "999 1 480px",
  minWidth: 0,
  display: "flex",
  flexDirection: "column",
};

const chatScrollStyle: React.CSSProperties = {
  flex: 1,
  maxHeight: "56vh",
  minHeight: 280,
  overflowY: "auto",
  padding: "20px 24px",
};

const sysLineStyle: React.CSSProperties = {
  fontSize: 12,
  color: TOKENS.inkMuted,
  textAlign: "center",
  padding: "4px 0 18px",
};

const sysMonoStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 11,
  letterSpacing: "0.04em",
};

const msgMetaStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10.5,
  color: TOKENS.inkMuted,
  letterSpacing: "0.05em",
  marginBottom: 4,
  display: "flex",
  alignItems: "baseline",
  gap: 8,
};

// Role designators are ink-weight, never color (§4.3): pm = ink,
// agent = inkMuted, distinguished by weight.
const msgWhoPmStyle: React.CSSProperties = {
  color: TOKENS.ink,
  fontWeight: 500,
};

const msgWhoAgentStyle: React.CSSProperties = {
  color: TOKENS.inkMuted,
  fontWeight: 500,
};

const armTagStyle: React.CSSProperties = {
  border: `1px solid ${TOKENS.rule}`,
  borderRadius: 2,
  padding: "1px 5px",
  fontSize: 9.5,
};

const msgAgentStyle: React.CSSProperties = {
  maxWidth: "64ch",
  marginBottom: 18,
};

const msgPmStyle: React.CSSProperties = {
  maxWidth: "64ch",
  marginBottom: 18,
  marginLeft: "auto",
};

const msgBodyAgentStyle: React.CSSProperties = {
  fontSize: 13.5,
  lineHeight: 1.5,
  color: TOKENS.ink,
  whiteSpace: "pre-wrap",
  borderLeft: `1px solid ${TOKENS.rule}`,
  paddingLeft: 12,
};

const msgBodyPmStyle: React.CSSProperties = {
  fontSize: 13.5,
  lineHeight: 1.5,
  color: TOKENS.ink,
  whiteSpace: "pre-wrap",
  background: TOKENS.paperElevated,
  border: `1px solid ${TOKENS.rule}`,
  borderRadius: 2,
  boxShadow: "inset 0 1px 0 rgba(255, 255, 255, 0.55)",
  padding: "9px 12px",
};

const msgActionsStyle: React.CSSProperties = {
  marginTop: 5,
  display: "flex",
  gap: 12,
  alignItems: "baseline",
};

const msgActionLinkStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10,
  letterSpacing: "0.04em",
  color: TOKENS.inkMuted,
  textDecoration: "none",
  borderBottom: `1px dotted ${TOKENS.inkMuted}`,
};

const pinDisabledStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10,
  letterSpacing: "0.04em",
  color: TOKENS.inkMuted,
  background: "none",
  border: "none",
  borderBottom: `1px dotted ${TOKENS.rule}`,
  padding: 0,
  opacity: 0.5,
  cursor: "not-allowed",
};

const typingStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10.5,
  color: TOKENS.inkMuted,
  letterSpacing: "0.06em",
  paddingBottom: 8,
};

const chatInputStyle: React.CSSProperties = {
  display: "flex",
  gap: 10,
  padding: "14px 24px",
  borderTop: `1px solid ${TOKENS.rule}`,
  background: TOKENS.paper,
  alignItems: "flex-end",
};

const composerStyle: React.CSSProperties = {
  flex: 1,
  fontFamily: "inherit",
  fontSize: 14,
  color: TOKENS.ink,
  background: TOKENS.paperElevated,
  border: `1px solid ${TOKENS.rule}`,
  borderRadius: 2,
  padding: "8px 11px",
  lineHeight: 1.45,
  resize: "vertical",
  minHeight: 40,
  boxSizing: "border-box",
};

const sendButtonStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 500,
  whiteSpace: "nowrap",
  background: TOKENS.ink,
  color: TOKENS.paper,
  border: `1px solid ${TOKENS.ink}`,
  borderRadius: 2,
  padding: "8px 16px",
};

const errorCardStyle: React.CSSProperties = {
  border: `1px solid ${TOKENS.rule}`,
  borderRadius: 4,
  padding: 20,
  color: TOKENS.alert,
  background: TOKENS.paperRecessed,
  fontSize: 14,
};
