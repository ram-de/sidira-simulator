"use client";

// ───────────────────────────────────────────────────────────────────────────
// /agents/[id] — the v2 dark "Reading Console" reskin of the 1:1 agent chat.
//
// FORK-AND-RESTYLE of AgentChatLegacy.tsx (the FROZEN source of truth for ALL
// behaviour). This file reproduces every data load (getAgent + getSimulation),
// the optimistic-send/refetch flow, the sessionStorage draft key + race-safe
// restore/persist effect, the auto-scroll, the keydown handler, focus
// management (composerRef + requestAnimationFrame refocus), every <Link>, every
// error / notFound / loading branch, and the ThumbsControl feedback — BYTE-FOR-
// BYTE in LOGIC. ONLY the presentation (markup + CSS classes + layout) changes,
// into the dark Console chat language of design-rethink/mocks/agent-detail.html.
//
// It renders INSIDE AppShellV2 surface="console" (the shell owns the dark rail +
// appbar). The body is scoped under a single `.rconsole` wrapper so the copied
// RCONSOLE_CSS applies; we do NOT emit the mock's own .app/.left-rail/.topbar
// (the shell owns that chrome).
//
// Honesty law (DESIGN.md §8.1 / §9): no fabricated data — only fields the legacy
// renders appear. Sentiment / scoring overlays from the static mock are NOT
// invented here (the legacy 1:1 has no per-turn sentiment). "TRANSCRIPTS ARE
// EVIDENCE" framing and the disabled PIN affordance survive verbatim.
// ───────────────────────────────────────────────────────────────────────────

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
import AppShellV2 from "@/components/v2/AppShellV2";

// sessionStorage key — drafts survive nav round-trips
// (e.g. clicking through to /agents/[id] from a persona-group [label]
// citation and back).
const draftKey = (agentId: string) => `pythia.agentDraft.${agentId}`;

// ── scoped console tokens (dark "Reading Console" chat language, distilled from
//    design-rethink/mocks/agent-detail.html + agent-transcript.html). Shared
//    bubble / composer / masthead treatment across both chat surfaces. Wrapped
//    under `.rconsole` so the dark palette applies inside AppShellV2's
//    surface="console" main (which already pads with var(--space-section)). ──
const RCONSOLE_CSS = `
.rconsole{
  --console-900:#0B1220; --console-850:#10192A; --console-800:#161F32;
  --console-750:#1D2740; --console-700:#26314C; --console-line:#33405C;
  --text-hi:#F2F4F8; --text:#C6CCD8; --text-mut:#929BAE; --text-faint:#646E84;
  --signal:#48EFCA; --signal-dim:#39B894; --signal-wash:rgba(72,239,202,.12);
  --spread:#C8B68A; --spread-dim:#90815F;
  --arm-control:#4FA8E0; --arm-treat:#E08BC4;
  --edge-warn:#C9A227; --alert:#F0683C;
  --r-well:4px; --r-panel:8px; --r-frame:10px; --r-dot:9999px;
  --ease-out:cubic-bezier(.22,1,.36,1);
  --font-mono:var(--v2-font-mono,var(--font-mono,ui-monospace,"JetBrains Mono",SFMono-Regular,monospace));
  --font-sans:var(--v2-font-sans,inherit);
  color:var(--text); font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased; font-variant-numeric:tabular-nums;
}
.rconsole *{box-sizing:border-box; font-variant-numeric:tabular-nums;}
.rconsole a{color:inherit; text-decoration:none;}
.rconsole ::selection{background:var(--signal-wash); color:var(--text-hi);}
.rconsole .mono{font-family:var(--font-mono);}
.rconsole .glyph-hollow{color:var(--spread-dim);}
.rconsole button,.rconsole textarea{font-family:inherit;}
.rconsole a:focus-visible,.rconsole button:focus-visible,
.rconsole textarea:focus-visible{
  outline:2px solid var(--signal-dim); outline-offset:2px;}

/* centered measured column */
.rconsole .wrap{max-width:1080px; margin:0 auto;}

/* quiet states (loading / not-found / load error) */
.rconsole .quiet-card{background:var(--console-800);
  border:1px solid var(--console-line); border-radius:var(--r-panel);
  padding:32px; box-shadow:inset 0 1px 0 rgba(255,255,255,.04); max-width:560px;}
.rconsole .quiet-card.failed{border-color:rgba(240,104,60,.55);}
.rconsole .quiet-head{font-family:var(--font-mono); font-size:12px;
  letter-spacing:.06em; text-transform:uppercase; color:var(--text-hi);
  margin-bottom:12px;}
.rconsole .quiet-head.failed{color:var(--alert);}
.rconsole .quiet-body{font-size:13.5px; color:var(--text-mut); line-height:1.6;}

/* ── masthead (agent identity + provenance, from agent-detail.html) ── */
.rconsole .masthead{margin-bottom:var(--space-section,48px);}
.rconsole .mh-eyebrow{display:flex; align-items:center; gap:8px; flex-wrap:wrap;
  margin-bottom:12px;}
.rconsole .chip{display:inline-flex; align-items:center; gap:5px;
  font-family:var(--font-mono); font-size:10.5px; font-weight:500;
  letter-spacing:.07em; text-transform:uppercase; color:var(--text-mut);
  border:1px solid var(--console-line); border-radius:var(--r-well);
  padding:2px 8px; line-height:1.4; white-space:nowrap;}
.rconsole .chip.arm-treat{color:var(--arm-treat); border-color:rgba(224,139,196,.4);}
.rconsole .chip.arm-control{color:var(--arm-control); border-color:rgba(79,168,224,.4);}
.rconsole h1.mh-title{font-weight:600; font-size:2rem; line-height:1.08;
  letter-spacing:-.025em; color:var(--text-hi); margin:0 0 8px; text-wrap:balance;}
.rconsole .mh-sub{display:flex; align-items:center; gap:9px; flex-wrap:wrap;
  font-family:var(--font-mono); font-size:11px; letter-spacing:.05em;
  color:var(--text-mut);}
.rconsole .mh-sub a{border-bottom:1px dotted rgba(146,155,174,.4); padding-bottom:1px;}
.rconsole .mh-sub a:hover{color:var(--text); border-color:var(--text-mut);}
.rconsole .mh-sub .sep{opacity:.5;}
.rconsole .mh-tag{margin-left:auto; font-family:var(--font-mono); font-size:10px;
  letter-spacing:.08em; color:var(--text-mut); border:1px solid var(--console-line);
  border-radius:var(--r-well); padding:3px 8px; white-space:nowrap;}

/* hypothesis strip + identity facts */
.rconsole .hyp-strip{margin-bottom:var(--space-section,48px);}
.rconsole .desig{font-family:var(--font-mono); font-size:10px; font-weight:500;
  letter-spacing:.12em; text-transform:uppercase; color:var(--text-mut);
  margin-bottom:7px;}
.rconsole .hyp-prose{font-size:14.5px; line-height:1.6; color:var(--text);
  max-width:72ch;}

/* ── chat panel: identity rail + thread (2-col, collapses) ── */
.rconsole .panel{display:flex; flex-wrap:wrap;
  border:1px solid var(--console-line); border-radius:var(--r-panel);
  background:var(--console-800); overflow:hidden;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04);}

/* rooms / identity rail */
.rconsole .rail{flex:1 0 248px; max-width:100%; display:flex; flex-direction:column;
  border-right:1px solid var(--console-line); background:var(--console-850);
  min-width:0;}
.rconsole .rail-head{padding:14px 18px 10px; border-bottom:1px solid var(--console-line);}
.rconsole .room{display:flex; align-items:baseline; gap:10px; padding:11px 18px;
  border-bottom:1px solid var(--console-line);
  transition:background 140ms var(--ease-out);}
.rconsole a.room:hover{background:var(--console-800);}
.rconsole .room.sel{background:var(--console-750);
  box-shadow:inset 2px 0 0 var(--signal-dim);}
.rconsole .room-name{font-size:13px; font-weight:500; color:var(--text-hi); flex:1;
  min-width:0; overflow:hidden; text-overflow:ellipsis;}
.rconsole .room.sel .room-name{font-weight:600;}
.rconsole .room-meta{font-family:var(--font-mono); font-size:10.5px;
  color:var(--text-mut); letter-spacing:.04em; white-space:nowrap;}

.rconsole .identity-seed{padding:14px 18px 16px;}
.rconsole .seedgrid{display:grid; grid-template-columns:auto 1fr; gap:4px 14px;
  margin:0;}
.rconsole .seedgrid dt{font-family:var(--font-mono); font-size:10px;
  letter-spacing:.1em; text-transform:uppercase; color:var(--text-mut); padding-top:2px;}
.rconsole .seedgrid dd{font-size:12.5px; line-height:1.45; color:var(--text); margin:0;}

.rconsole .prov{margin-top:auto; padding:14px 18px 16px;
  border-top:1px solid var(--console-line); display:grid;
  grid-template-columns:auto 1fr; gap:3px 16px;}
.rconsole .prov dt{font-family:var(--font-mono); font-size:10px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--text-mut); padding-top:1px;}
.rconsole .prov dd{font-family:var(--font-mono); font-size:11.5px; color:var(--text-hi);
  margin:0; overflow-wrap:anywhere;}
.rconsole .prov dd a{border-bottom:1px dotted rgba(146,155,174,.5);}
.rconsole .prov dd a:hover{color:var(--text-hi); border-color:var(--text-mut);}

/* thread column */
.rconsole .thread{flex:999 1 480px; min-width:0; display:flex; flex-direction:column;}
.rconsole .scroll{flex:1; max-height:56vh; min-height:280px; overflow-y:auto;
  padding:24px 28px;}
.rconsole .sysline{text-align:center; font-size:12px; color:var(--text-mut);
  padding:2px 0 var(--space-room,24px); border-bottom:1px solid rgba(51,64,92,.35);
  margin-bottom:var(--space-room,24px);}
.rconsole .sysline .mono{font-family:var(--font-mono); font-size:11px;
  letter-spacing:.04em; color:var(--text);}

.rconsole .empty{font-size:13.5px; color:var(--text-mut); padding:8px 0;}

/* message bubbles */
.rconsole .msg{margin-bottom:var(--space-section,48px); max-width:64ch;}
.rconsole .msg.pm{margin-left:auto;}
.rconsole .msg-meta{display:flex; align-items:baseline; gap:9px; margin-bottom:6px;
  font-family:var(--font-mono); font-size:10px; letter-spacing:.05em;
  color:var(--text-mut);}
.rconsole .msg-meta.right{justify-content:flex-end;}
.rconsole .msg-meta .who{font-weight:500; color:var(--text);}
.rconsole .msg-meta .who.pm{color:var(--text-hi);}
.rconsole .msg-meta .spacer{flex:1;}
.rconsole .tag{border:1px solid var(--console-line); border-radius:var(--r-well);
  padding:1px 6px; font-size:9px; letter-spacing:.06em; color:var(--text-mut);}
.rconsole .tag.first{color:var(--text); border-color:rgba(146,155,174,.45);}
.rconsole .msg-body{font-size:14.5px; line-height:1.62; color:var(--text);
  white-space:pre-wrap;}
.rconsole .msg.agent .msg-body{border-left:1px solid var(--console-line);
  padding-left:16px;}
.rconsole .msg.pm .msg-body{background:var(--console-750);
  border:1px solid var(--console-line); border-radius:var(--r-well);
  padding:11px 14px; box-shadow:inset 0 1px 0 rgba(255,255,255,.04);}

.rconsole .msg-actions{margin-top:10px; display:flex; align-items:center; gap:14px;}
.rconsole .act{font-family:var(--font-mono); font-size:10px; letter-spacing:.04em;
  color:var(--text-mut); display:inline-flex; align-items:center; gap:5px;
  border-bottom:1px dotted rgba(146,155,174,.4); padding-bottom:1px;
  background:none; border-left:none; border-right:none; border-top:none;
  cursor:pointer; transition:color 140ms var(--ease-out);}
.rconsole .act:hover{color:var(--text);}
.rconsole .act.disabled{color:var(--text-faint);
  border-bottom-color:rgba(100,110,132,.4); cursor:not-allowed; opacity:1;}

/* composing — the ONE sanctioned status-dot breath */
.rconsole .composing{font-family:var(--font-mono); font-size:10.5px;
  letter-spacing:.06em; color:var(--text-mut); display:flex; align-items:center;
  gap:9px; padding:0 0 var(--space-room,24px);}
.rconsole .composing .cdot{width:7px; height:7px; border-radius:var(--r-dot);
  background:var(--signal); flex-shrink:0; animation:rc-breathe 2s var(--ease-out) infinite;}
@keyframes rc-breathe{0%,100%{opacity:1;}50%{opacity:.5;}}

/* send-error strip — border accent, message in ink (§8.1/§9) */
.rconsole .senderr{font-size:13px; color:var(--text-hi);
  background:rgba(240,104,60,.08); border-top:1px solid rgba(240,104,60,.55);
  padding:8px 28px;}

/* composer */
.rconsole .composer{display:flex; gap:12px; align-items:flex-end;
  padding:14px 28px; border-top:1px solid var(--console-line);
  background:var(--console-800);}
.rconsole .composer textarea{flex:1; font-size:14.5px; color:var(--text-hi);
  background:var(--console-700); border:1px solid var(--console-line);
  border-radius:var(--r-well); padding:10px 13px; line-height:1.5; resize:vertical;
  min-height:44px; outline:none; transition:border-color 140ms var(--ease-out);}
.rconsole .composer textarea::placeholder{color:var(--text-mut); opacity:.7;}
.rconsole .composer textarea:focus{border-color:var(--signal-dim);}
.rconsole .composer textarea:disabled{opacity:.7;}
.rconsole .btn-send{height:42px; padding:0 18px; border-radius:var(--r-well);
  font-size:13.5px; font-weight:500; white-space:nowrap;
  background:var(--console-700); color:var(--text-hi);
  border:1px solid var(--console-line); cursor:pointer;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04);
  transition:background 140ms var(--ease-out);}
.rconsole .btn-send:hover:not(:disabled){background:var(--console-750);}

@media (max-width:760px){
  .rconsole .scroll{max-height:none;}
}
@media (prefers-reduced-motion:reduce){
  .rconsole *{animation:none!important;}
}
`;

// ───────────────────────────────────────────────────────────────────────────
// MAIN — fork of AgentChatLegacy: identical data load / send / draft / focus.
// ───────────────────────────────────────────────────────────────────────────
export default function AgentChatV2() {
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
      <AppShellV2 activeNav="simulations" title="Agent" surface="console">
        <div className="rconsole">
          <style>{RCONSOLE_CSS}</style>
          <div className="wrap">
            <div role="alert" className="quiet-card failed">
              <div className="quiet-head failed">AGENT NOT FOUND</div>
            </div>
          </div>
        </div>
      </AppShellV2>
    );
  }
  if (loadError) {
    return (
      <AppShellV2 activeNav="simulations" title="Agent" surface="console">
        <div className="rconsole">
          <style>{RCONSOLE_CSS}</style>
          <div className="wrap">
            <div role="alert" className="quiet-card failed">
              <div className="quiet-head failed">FAILED TO LOAD AGENT</div>
              <div className="quiet-body">{loadError}</div>
            </div>
          </div>
        </div>
      </AppShellV2>
    );
  }
  if (!agent) {
    return (
      <AppShellV2 activeNav="simulations" title="Agent" surface="console">
        <div className="rconsole">
          <style>{RCONSOLE_CSS}</style>
          <div className="wrap">
            <div className="quiet-card">
              <div className="quiet-head">
                <span className="glyph-hollow">◇</span> LOADING AGENT…
              </div>
            </div>
          </div>
        </div>
      </AppShellV2>
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
    <AppShellV2 activeNav="simulations" title="Agent" surface="console">
      <div className="rconsole">
        <style>{RCONSOLE_CSS}</style>
        <div className="wrap">
          {/* Masthead — agent identity + links back to the hypothesis + run */}
          <header className="masthead">
            <div className="mh-eyebrow">
              <span className="chip">AGENT {agent.metadata.id.slice(0, 8)}</span>
              {groupArm && (
                <span
                  className={`chip ${groupArm === "treatment" ? "arm-treat" : "arm-control"}`}
                >
                  {groupArm.toUpperCase()} ARM
                </span>
              )}
              <span className="mh-tag">TRANSCRIPTS ARE EVIDENCE</span>
            </div>
            <h1 className="mh-title">{persona}</h1>
            <div className="mh-sub">
              {sim?.hypothesis?.capability_name && (
                <>
                  <Link href={simHref} title="Open the hypothesis">
                    HYP · {sim.hypothesis.capability_name.toUpperCase()}
                  </Link>
                  <span className="sep">·</span>
                </>
              )}
              <Link href={simHref} title={simId}>
                {runDesignator}
              </Link>
              <span className="sep">·</span>
              <span>1:1 INTERROGATION</span>
            </div>
          </header>

          {/* Hypothesis under test — record */}
          {hypothesisProse && (
            <section className="hyp-strip" aria-label="Hypothesis under test">
              <div className="desig">Hypothesis under test</div>
              <div className="hyp-prose">{hypothesisProse}</div>
            </section>
          )}

          <div className="panel">
            {/* Rooms rail — the chat surfaces that exist today */}
            <aside className="rail" aria-label="Rooms">
              <div className="rail-head">
                <span className="desig" style={{ marginBottom: 0 }}>
                  Rooms
                </span>
              </div>
              {groupArm ? (
                <>
                  <Link
                    href={`${personaGroupBase}?arm=treatment`}
                    className="room"
                    title={`${persona} group chat — treatment arm`}
                  >
                    <span className="room-name">Arm · treatment</span>
                    <span className="room-meta">GROUP</span>
                  </Link>
                  <Link
                    href={`${personaGroupBase}?arm=control`}
                    className="room"
                    title={`${persona} group chat — control arm`}
                  >
                    <span className="room-name">Arm · control</span>
                    <span className="room-meta">GROUP</span>
                  </Link>
                </>
              ) : (
                <Link
                  href={personaGroupHref}
                  className="room"
                  title={`${persona} group chat`}
                >
                  <span className="room-name">Cohort · {persona}</span>
                  <span className="room-meta">GROUP</span>
                </Link>
              )}
              <div className="room sel" aria-current="page">
                <span className="room-name">1:1 · {persona}</span>
                <span className="room-meta">TURN {conversationLen}</span>
              </div>

              {/* identity.md — the slice frozen at materialization */}
              {seed && (
                <div className="identity-seed" aria-label="Frozen identity seed">
                  <span className="desig">identity.md — frozen</span>
                  <dl className="seedgrid">
                    <SeedRow label="Age" value={seed.age_band} />
                    <SeedRow label="Locale" value={seed.locale_band} />
                    <SeedRow label="Tenure" value={seed.tenure_band} />
                    <SeedRow label="Currently" value={seed.current_state} />
                    <SeedRow label="Recent gripe" value={seed.recent_gripe} />
                  </dl>
                </div>
              )}

              {/* Provenance grid — §8.7 */}
              <dl className="prov" aria-label="Provenance">
                <dt>Run</dt>
                <dd>
                  <Link href={simHref} title={simId}>
                    {runDesignator}
                  </Link>
                </dd>
                <dt>Agent</dt>
                <dd title={agent.metadata.id}>{agent.metadata.id.slice(0, 8)}</dd>
                <dt>Pack</dt>
                <dd>{agent.metadata.persona_pack_version}</dd>
                <dt>Arm</dt>
                <dd>{groupArm ? groupArm.toUpperCase() : "—"}</dd>
                <dt>Seed</dt>
                <dd>{sim?.run_seed != null ? String(sim.run_seed) : "—"}</dd>
                <dt>Model</dt>
                <dd>{sim?.model_id ?? "—"}</dd>
                <dt>Frozen</dt>
                <dd>{fmtDate(agent.metadata.created_at)}</dd>
              </dl>
            </aside>

            {/* Thread */}
            <div className="thread">
              <div className="scroll">
                {/* Sys-line: sentence-case body font; mono for designators only */}
                <div className="sysline">
                  {groupArm ? (
                    <>
                      1:1 room opened from{" "}
                      <span className="mono">{runDesignator}</span> · arm-scoped —
                      this agent saw the {groupArm} arm only.
                    </>
                  ) : (
                    <>
                      1:1 room opened from{" "}
                      <span className="mono">{runDesignator}</span> — this agent
                      retains its run memory.
                    </>
                  )}
                </div>

                <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {/* Initial reaction — the agent's first turn, evidence like
                      every other. Timestamp = materialization (metadata.created_at);
                      the turn itself carries no timestamp field. */}
                  <li className="msg agent">
                    <div className="msg-meta">
                      <span className="who">{persona.toUpperCase()}</span>
                      <span className="tag first">INITIAL REACTION</span>
                      {groupArm && (
                        <span className="tag">{groupArm.toUpperCase()}</span>
                      )}
                      <span className="spacer" />
                      <span className="time">
                        {fmtTime(agent.metadata.created_at)}
                      </span>
                    </div>
                    <div className="msg-body">{agent.initial_reaction}</div>
                    <MsgActions simHref={simHref} runDesignator={runDesignator} />
                  </li>

                  {conversation.length === 0 ? (
                    <li className="empty">
                      No follow-ups yet. Ask a question below to start.
                    </li>
                  ) : (
                    conversation.map((turn, i) =>
                      turn.role === "pm" ? (
                        <li key={`${turn.created_at}-${i}`} className="msg pm">
                          <div className="msg-meta right">
                            <span className="who pm">YOU · PM</span>
                            <span className="time">{fmtTime(turn.created_at)}</span>
                          </div>
                          <div className="msg-body">{turn.content}</div>
                        </li>
                      ) : (
                        <li key={`${turn.created_at}-${i}`} className="msg agent">
                          <div className="msg-meta">
                            {/* Role designators are ink-weight, not color-coded —
                                semantic colors are reserved for outcomes (§4.3). */}
                            <span className="who">{persona.toUpperCase()}</span>
                            {groupArm && (
                              <span className="tag">{groupArm.toUpperCase()}</span>
                            )}
                            <span className="time">{fmtTime(turn.created_at)}</span>
                            <span className="spacer" />
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
                          <div className="msg-body">{turn.content}</div>
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
                  <div className="composing" aria-live="polite">
                    <span className="cdot" />
                    {persona.toUpperCase()} COMPOSING
                  </div>
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
                  className="senderr"
                >
                  {sendError}
                </div>
              )}
              <div className="composer">
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
                />
                <button
                  type="button"
                  onClick={() => void handleSend()}
                  disabled={sending || !draft.trim()}
                  className="btn-send"
                  style={{
                    cursor: sending || !draft.trim() ? "not-allowed" : "pointer",
                    opacity: sending || !draft.trim() ? 0.5 : 1,
                  }}
                >
                  {sending ? "Sending…" : "Send"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShellV2>
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
    <div className="msg-actions">
      <button
        type="button"
        disabled
        title="Pinning lands with the decision record — not yet available"
        className="act disabled"
      >
        PIN TO DECISION RECORD
      </button>
      <Link href={simHref} className="act">
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
      <dt>{label}</dt>
      <dd>{value || "—"}</dd>
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
