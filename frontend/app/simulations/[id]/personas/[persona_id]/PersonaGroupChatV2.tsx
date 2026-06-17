"use client";

// ───────────────────────────────────────────────────────────────────────────
// /simulations/[id]/personas/[persona_id] — the v2 dark "Reading Console"
// reskin of the persona-group chat (collective + individual fan-out, sharing
// one composer).
//
// FORK-AND-RESTYLE of PersonaGroupChatLegacy.tsx (the FROZEN source of truth
// for ALL behaviour). This file reproduces every data load (getSimulation +
// listSimulationAgents + getPersonaGroupTurns), the ?arm handling + invalidArm
// branch, the collective-vs-individual mode toggle, the optimistic
// send/refetch flow, the race-safe sessionStorage draft restore/persist, the
// unavailable-agents banner, [label] citation linkification, ThumbsControl
// feedback, the auto-scroll, the keydown handler, focus management (composerRef
// + requestAnimationFrame refocus), every <Link>, and every error / notFound /
// loading branch — BYTE-FOR-BYTE in LOGIC. ONLY the presentation (markup + CSS
// classes + layout) changes, into the dark Console chat language of
// design-rethink/mocks/agent-transcript.html (persona masthead + provenance
// bar + .turn articles + fan-out + dark composer).
//
// It renders INSIDE AppShellV2 surface="console" (the shell owns the dark rail +
// appbar). The body is scoped under a single `.rconsole` wrapper so the copied
// RCONSOLE_CSS applies; we do NOT emit the mock's own .shell/.rail/.topbar.
//
// Honesty law (DESIGN.md §8.1 / §9): no fabricated data — only fields the legacy
// renders appear (no invented verdict / sentiment / split, since the legacy
// turn log carries none). Arm labels (Treatment/Control), persona name, n, the
// mode toggle, and the fan-out failure state survive verbatim — restyled, not
// removed.
// ───────────────────────────────────────────────────────────────────────────

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  ApiError,
  getPersonaGroupTurns,
  getSimulation,
  listSimulationAgents,
  sendPersonaGroupMessage,
  sendPersonaGroupTurnFeedback,
  type AgentReference,
  type AgentSummary,
  type PerAgentReply,
  type PersonaGroupArm,
  type PersonaGroupMode,
  type PersonaGroupTurn,
  type Simulation,
  type UnavailableAgent,
} from "@/lib/api";
import { ThumbsControl } from "@/components/ThumbsControl";
import AppShellV2 from "@/components/v2/AppShellV2";

// sessionStorage key — round-trip continuity: a mid-typed question
// survives navigating to /agents/[id] and back.
const draftKey = (simId: string, personaId: string, arm: PersonaGroupArm | null) =>
  `pythia.personaGroupDraft.${simId}.${personaId}.${arm ?? "single"}`;

// ── scoped console tokens — same dark "Reading Console" chat language as the
//    1:1 surface (AgentChatV2), distilled from agent-transcript.html. Shared
//    masthead / turn / composer treatment so both chat surfaces read as one
//    instrument. Wrapped under `.rconsole` inside AppShellV2 surface="console".
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
.rconsole textarea:focus-visible,.rconsole input:focus-visible{
  outline:2px solid var(--signal-dim); outline-offset:2px;}

.rconsole .wrap{max-width:880px; margin:0 auto;}
.rconsole .desig{font-family:var(--font-mono); font-size:10px; font-weight:500;
  letter-spacing:.1em; text-transform:uppercase; color:var(--text-mut);}

/* backlink */
.rconsole .backlink{display:inline-flex; align-items:center; gap:7px;
  color:var(--text-mut); font-size:13px; margin-bottom:24px;
  transition:color 140ms var(--ease-out);}
.rconsole .backlink:hover{color:var(--text);}

/* quiet / error states */
.rconsole .quiet-card{background:var(--console-800);
  border:1px solid var(--console-line); border-radius:var(--r-panel);
  padding:24px; box-shadow:inset 0 1px 0 rgba(255,255,255,.04); max-width:560px;}
.rconsole .quiet-card.failed{border-color:rgba(240,104,60,.55);}
.rconsole .quiet-card strong{color:var(--text-hi); font-weight:600;}
.rconsole .quiet-card a{color:var(--text-hi); text-decoration:underline;
  text-decoration-color:var(--console-line);}
.rconsole .quiet-body{font-size:13.5px; color:var(--text); line-height:1.6;}

/* ── identity / hero reading region (persona masthead, from agent-transcript) ── */
.rconsole .identity{margin-bottom:var(--space-section,48px);}
.rconsole .prov-bar{display:flex; align-items:center; flex-wrap:wrap;
  font-family:var(--font-mono); font-size:11px; letter-spacing:.07em;
  text-transform:uppercase; color:var(--text-mut); margin-bottom:20px;}
.rconsole .prov-bar .seg{padding:0 12px; border-right:1px solid var(--console-line);
  white-space:nowrap;}
.rconsole .prov-bar .seg:first-child{padding-left:0;}
.rconsole .prov-bar .seg:last-child{border-right:none;}
.rconsole .prov-bar .ch.t{color:var(--arm-treat);}
.rconsole .prov-bar .ch.c{color:var(--arm-control);}

.rconsole h1.persona-title{font-size:2rem; line-height:1.08; letter-spacing:-.025em;
  font-weight:600; color:var(--text-hi); margin:0; text-wrap:balance;}
.rconsole .persona-title .n{font-size:1rem; color:var(--text-mut); font-weight:400;}
.rconsole .persona-id{font-family:var(--font-mono); font-size:12px;
  color:var(--text-mut); margin-top:8px;}
.rconsole .hyp-label{margin-top:22px; margin-bottom:7px;}
.rconsole .hyp-prose{font-size:15px; line-height:1.6; color:var(--text);
  max-width:64ch;}

/* ── conversation ── */
.rconsole .section-head{display:flex; align-items:baseline; gap:14px;
  margin-bottom:8px;}
.rconsole .section-head h2{font-size:1.25rem; letter-spacing:-.02em; font-weight:600;
  color:var(--text-hi); margin:0;}
.rconsole .scroll{max-height:55vh; overflow-y:auto; padding:0 4px;}
.rconsole .empty{font-size:14px; color:var(--text-mut); padding:8px 0;
  line-height:1.55; max-width:64ch;}
.rconsole .empty em{color:var(--text);}

.rconsole .thread{list-style:none; padding:0; margin:0; max-width:72ch;}
.rconsole .turn{padding:20px 0; border-top:1px solid var(--console-line);}
.rconsole .turn.first{border-top:none;}

.rconsole .turn-head{display:flex; align-items:center; gap:9px; margin-bottom:11px;}
.rconsole .turn-role{font-family:var(--font-mono); font-size:11px;
  letter-spacing:.08em; text-transform:uppercase; font-weight:500; color:var(--text);}
.rconsole .turn-role.pm{color:var(--text-mut);}
.rconsole .turn-role.coll{color:var(--text-hi);}
.rconsole .turn-role.coll .sub{color:var(--text-mut);}
.rconsole .turn-role.syn{color:var(--text-mut);}
.rconsole .turn-head .spacer{flex:1;}

/* PM turn */
.rconsole .pm-body{font-size:15px; line-height:1.6; color:var(--text);
  font-weight:400; max-width:64ch; white-space:pre-wrap;}

/* collective turn */
.rconsole .coll-body{border-left:2px solid var(--signal-dim); padding:4px 0 4px 18px;
  font-size:15px; line-height:1.62; color:var(--text); max-width:66ch;
  white-space:pre-wrap;}
.rconsole .cite{color:var(--text-hi);
  border-bottom:1px solid var(--console-line); padding-bottom:1px; font-weight:500;
  transition:border-color 140ms, color 140ms; white-space:nowrap;}
.rconsole .cite:hover{color:var(--text-hi); border-color:var(--text-mut);}

/* synthesis turn */
.rconsole .syn-line{font-size:15px; line-height:1.55; color:var(--text);
  font-weight:500; border-left:2px solid var(--spread); padding:4px 0 4px 16px;
  max-width:66ch; white-space:pre-wrap;}
.rconsole .fanout{margin-top:16px; list-style:none; padding:0;}
.rconsole .agent-reply{padding:14px 0; border-top:1px dashed var(--console-line);}
.rconsole .agent-reply-head{display:flex; align-items:baseline; gap:8px;
  margin-bottom:6px;}
.rconsole .agent-tag{font-family:var(--font-mono); font-size:11px;
  letter-spacing:.06em; text-transform:uppercase; font-weight:600; color:var(--text);}
.rconsole .agent-meta{font-family:var(--font-mono); font-size:10.5px;
  color:var(--text-mut);}
.rconsole .agent-1to1{margin-left:auto; font-family:var(--font-mono); font-size:11px;
  letter-spacing:.05em; text-transform:uppercase; color:var(--text-mut);
  display:inline-flex; align-items:center; gap:5px; transition:color 140ms;}
.rconsole .agent-1to1:hover{color:var(--text-hi);}
.rconsole .agent-body{font-size:14.5px; line-height:1.58; color:var(--text);
  max-width:64ch; white-space:pre-wrap;}
.rconsole .agent-fail{font-size:13px; color:var(--text);
  border:1px solid var(--alert); border-radius:var(--r-well); padding:8px 12px;}
.rconsole .agent-fail .ftag{font-family:var(--font-mono); font-size:10px;
  letter-spacing:.08em; text-transform:uppercase; color:var(--alert); margin-right:8px;}

/* ── composer ── */
.rconsole .composer{margin-top:var(--space-section,48px);
  border-top:1px solid var(--console-line); padding-top:24px; max-width:72ch;}
.rconsole .senderr{font-size:13px; color:var(--text-hi);
  background:rgba(240,104,60,.08); border:1px solid rgba(240,104,60,.55);
  border-radius:var(--r-well); padding:8px 12px; margin-bottom:12px;}
.rconsole .unavail{font-size:13px; color:var(--text);
  border:1px solid var(--edge-warn); border-radius:var(--r-well);
  padding:9px 13px; margin-bottom:14px;}
.rconsole .unavail strong{color:var(--text-hi); font-weight:600;}

.rconsole .modeline{display:flex; align-items:center; gap:8px; margin-bottom:14px;
  flex-wrap:wrap; border:none; padding:0;}
.rconsole .modeline legend{padding:0; font-family:var(--font-mono); font-size:11px;
  letter-spacing:.06em; text-transform:uppercase; color:var(--text-mut);
  margin-right:2px;}
.rconsole .mode-pill{display:inline-flex; align-items:center; gap:4px;
  font-family:var(--font-mono); font-size:11px; letter-spacing:.05em;
  text-transform:uppercase; border:1px solid var(--console-line);
  border-radius:var(--r-well); padding:5px 11px; color:var(--text-mut);
  cursor:pointer; transition:color 140ms, border-color 140ms, background 140ms;
  user-select:none;}
.rconsole .mode-pill:hover{color:var(--text); border-color:var(--console-line);}
.rconsole .mode-pill.on{color:var(--text-hi); border-color:var(--console-line);
  background:var(--console-750);}
.rconsole .mode-pill .nat{position:absolute; opacity:0; pointer-events:none;
  width:0; height:0;}

.rconsole .composer textarea{width:100%; background:var(--console-700);
  border:1px solid var(--console-line); border-radius:var(--r-well);
  color:var(--text-hi); font-size:15px; line-height:1.55; padding:12px 14px;
  resize:vertical; min-height:78px; outline:none;
  box-shadow:inset 0 1px 0 rgba(0,0,0,.18);
  transition:border-color 140ms var(--ease-out);}
.rconsole .composer textarea::placeholder{color:var(--text-mut); opacity:.7;}
.rconsole .composer textarea:focus{border-color:var(--signal-dim);}
.rconsole .composer textarea:disabled{opacity:.7;}

.rconsole .composer-foot{display:flex; align-items:center; justify-content:flex-end;
  margin-top:12px;}
.rconsole .btn-send{height:36px; padding:0 18px; border-radius:var(--r-well);
  background:var(--console-700); border:1px solid var(--console-line);
  color:var(--text-hi); font-size:14px; font-weight:500; cursor:pointer;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04);
  transition:background 140ms var(--ease-out);}
.rconsole .btn-send:hover:not(:disabled){background:var(--console-750);}

@media (prefers-reduced-motion:reduce){
  .rconsole *{animation:none!important;}
}
`;

export default function PersonaGroupChatV2() {
  const params = useParams<{ id: string; persona_id: string }>();
  const searchParams = useSearchParams();
  const simId = params?.id ?? "";
  const personaId = params?.persona_id ?? "";
  const armParam = searchParams.get("arm");
  const arm: PersonaGroupArm | null =
    armParam === "treatment" || armParam === "control" ? armParam : null;
  const invalidArm = armParam != null && arm == null;
  const armLabel =
    arm === "treatment" ? "Treatment" : arm === "control" ? "Control" : null;

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

  // Single effect that does BOTH restore (on route change) and persist
  // (on draft change within the same route). Codex #83 round-2 P2:
  // the prior two-effect split + StrictMode double-mount could race —
  // the persist effect fired on first mount with the initial `draft=""`
  // BEFORE the restore effect's setDraft committed, removing the cached
  // value from sessionStorage. The single-effect form distinguishes
  // route-change-firstrun (restore, never persist) from same-route
  // (persist), so the first mount never writes draft="" over a cached
  // value.
  const lastDraftKey = useRef<string | null>(null);
  useEffect(() => {
    if (!simId || !personaId) return;
    const key = draftKey(simId, personaId, arm);
    if (lastDraftKey.current !== key) {
      // First mount for this route key (or client-side navigation to a
      // different persona group). Restore from storage and DO NOT persist
      // on this run.
      lastDraftKey.current = key;
      try {
        const cached = sessionStorage.getItem(key);
        setDraft(cached ?? "");
      } catch {
        // sessionStorage can throw in SSR / sandboxed contexts.
        setDraft("");
      }
      return;
    }
    // Same route, draft changed → persist.
    try {
      if (draft) sessionStorage.setItem(key, draft);
      else sessionStorage.removeItem(key);
    } catch {
      // ignore
    }
  }, [simId, personaId, arm, draft]);

  // Initial load: sim (hypothesis) + agents (filter to persona) + turn log.
  useEffect(() => {
    if (!simId || !personaId || invalidArm) return;
    let cancelled = false;
    (async () => {
      try {
        const [simData, agents, turnLog] = await Promise.all([
          getSimulation(simId),
          listSimulationAgents(simId),
          getPersonaGroupTurns(simId, personaId, arm).catch((e) => {
            if (e instanceof ApiError && e.status === 404) {
              throw new _PersonaNotFound();
            }
            throw e;
          }),
        ]);
        if (cancelled) return;
        const filtered = agents.filter(
          (a) => a.persona_id === personaId && (arm == null || a.arm === arm),
        );
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
  }, [simId, personaId, arm, invalidArm]);

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
    // Codex #83 round-1 P2: DO NOT clear `unavailable` here — if the next
    // send fails and rolls back, the most-recently-visible collective
    // reply is still the prior partial one, and its warning must stay
    // accurate. Clear on success (after the new reply is in state).
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
        resp = await sendPersonaGroupMessage(simId, personaId, trimmed, mode, arm);
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

      if (resp) {
        // Codex #83 round-1 P2: derive the canonical PM + reply pair from
        // the response and apply it locally. The backend's group-log
        // append is best-effort (codex #82 round-1 P2 made it swallow
        // failures), so a refetched turn log might NOT contain the new
        // reply we just received. Trusting `resp` directly means a
        // successful POST is always visible to the PM, even when the
        // audit-trail write degraded.
        const replyTurn = _buildReplyTurnFromResponse(resp, trimmed);
        const canonicalPm: PersonaGroupTurn = {
          role: "pm",
          content: trimmed,
          created_at: resp.created_at,
          per_agent: null,
          references: null,
        };
        setTurns((current) => [
          ...current.filter((t) => t !== optimisticPm),
          canonicalPm,
          replyTurn,
        ]);

        // Surface unavailable_agents AFTER the new reply is in state, so
        // a subsequent failed send can't strand a stale "reflects X of N"
        // warning over the wrong reply.
        setUnavailable(resp.unavailable_agents ?? []);

        // Phase 2: refetch as a verification step. If the log includes
        // our new reply, prefer it (canonical ordering, server timestamps).
        // If the log is shorter than what we just appended (best-effort
        // append failed), keep the locally-derived turns.
        try {
          const fresh = await getPersonaGroupTurns(simId, personaId, arm);
          setTurns((current) => (fresh.length >= current.length ? fresh : current));
        } catch (e) {
          // The locally-derived turns are already in state; don't roll
          // them back — just inform the user the refresh failed.
          setSendError(
            e instanceof Error
              ? `Sent. Couldn't fetch the canonical log (${e.message}); the reply you see is from the response payload.`
              : "Sent. Couldn't fetch the canonical log; the reply you see is from the response payload.",
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

  if (invalidArm) {
    return (
      <AppShellV2 activeNav="simulations" title="Persona reactions" surface="console">
        <div className="rconsole">
          <style>{RCONSOLE_CSS}</style>
          <div className="wrap">
            {/* Error cards: alert is accent-only — severity on the border,
                message in ink (§4.3/§7.7). */}
            <div role="alert" className="quiet-card failed">
              <div className="quiet-body">
                <strong>Unknown persona-group chat arm.</strong>{" "}
                <Link href={`/simulations/${simId}`}>Back to simulation</Link>
              </div>
            </div>
          </div>
        </div>
      </AppShellV2>
    );
  }

  if (notFound) {
    return (
      <AppShellV2 activeNav="simulations" title="Persona reactions" surface="console">
        <div className="rconsole">
          <style>{RCONSOLE_CSS}</style>
          <div className="wrap">
            <div role="alert" className="quiet-card failed">
              <div className="quiet-body">
                <strong>Persona group not found.</strong>{" "}
                <Link href={`/simulations/${simId}`}>Back to simulation</Link>
              </div>
            </div>
          </div>
        </div>
      </AppShellV2>
    );
  }
  if (loadError) {
    return (
      <AppShellV2 activeNav="simulations" title="Persona reactions" surface="console">
        <div className="rconsole">
          <style>{RCONSOLE_CSS}</style>
          <div className="wrap">
            <div role="alert" className="quiet-card failed">
              <div className="quiet-body">
                <strong>Failed to load:</strong> {loadError}
              </div>
            </div>
          </div>
        </div>
      </AppShellV2>
    );
  }
  if (!sim || !personaName) {
    return (
      <AppShellV2 activeNav="simulations" title="Persona reactions" surface="console">
        <div className="rconsole">
          <style>{RCONSOLE_CSS}</style>
          <div className="wrap">
            <div className="quiet-card">
              <div className="quiet-body">
                <span className="glyph-hollow">◇</span> Loading persona group…
              </div>
            </div>
          </div>
        </div>
      </AppShellV2>
    );
  }

  const hypothesisProse = sim.hypothesis?.prose ?? null;
  const n = agentsInPersona.length;

  return (
    <AppShellV2 activeNav="simulations" title="Persona reactions" surface="console">
      <div className="rconsole">
        <style>{RCONSOLE_CSS}</style>
        <div className="wrap">
          <Link href={`/simulations/${simId}`} className="backlink">
            ← back to simulation
          </Link>

          {/* ── IDENTITY + provenance bar (persona masthead) ── */}
          <section className="identity" aria-label="Persona group identity">
            <div className="prov-bar" aria-label="Provenance">
              <span className="seg">
                <span
                  className={
                    arm === "treatment"
                      ? "ch t"
                      : arm === "control"
                        ? "ch c"
                        : undefined
                  }
                >
                  {personaName.toUpperCase()}
                  {armLabel ? ` · ${armLabel.toUpperCase()}` : ""}
                </span>
              </span>
              <span className="seg">n={n}</span>
              <span className="seg">{personaId}</span>
            </div>

            <h1 className="persona-title">
              {personaName} <span className="n">(n={n})</span>
            </h1>
            <div className="persona-id">{personaId}</div>

            {hypothesisProse && (
              <>
                <div className="desig hyp-label">Hypothesis under test</div>
                <p className="hyp-prose">{hypothesisProse}</p>
              </>
            )}
          </section>

          {/* ── CONVERSATION ── */}
          <section aria-label="Conversation">
            <div className="section-head">
              <h2>Conversation</h2>
            </div>
            <div className="scroll">
              {turns.length === 0 ? (
                <div className="empty">
                  No questions yet. Ask the group something below — the default
                  answer is the collective voice of the persona (with inline links
                  to drill into any agent). Switch to <em>individual fan-out</em> to
                  hear each of the {n} agent
                  {n === 1 ? "" : "s"} reply separately.
                </div>
              ) : (
                <ul className="thread">
                  {turns.map((turn, i) => {
                    // #56: shared onSet for any non-PM turn at index i.
                    // Updates the local turn state on success so subsequent
                    // toggles read the new flag.
                    const setFlag = async (next: boolean | null) => {
                      await sendPersonaGroupTurnFeedback(simId, personaId, i, next, arm);
                      setTurns((current) =>
                        current.map((t, idx) =>
                          idx === i ? { ...t, realistic_flag: next } : t,
                        ),
                      );
                    };
                    return (
                      <li
                        key={`${turn.created_at}-${i}`}
                        className={i === 0 ? "turn first" : "turn"}
                      >
                        {turn.role === "pm" ? (
                          <PmTurn content={turn.content} />
                        ) : turn.role === "collective" ? (
                          <CollectiveTurn
                            content={turn.content}
                            references={turn.references ?? []}
                            personaName={personaName}
                            flag={turn.realistic_flag ?? null}
                            onSetFlag={setFlag}
                          />
                        ) : (
                          <SynthesisTurn
                            synthesis={turn.content}
                            perAgent={turn.per_agent ?? []}
                            personaName={personaName}
                            flag={turn.realistic_flag ?? null}
                            onSetFlag={setFlag}
                          />
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
              <div ref={conversationEndRef} />
            </div>
          </section>

          {/* ── COMPOSER ── */}
          <section className="composer" aria-label="Send a message to the group">
            {sendError && (
              <div aria-live="polite" className="senderr">
                {sendError}
              </div>
            )}
            {unavailable.length > 0 && (
              <div aria-live="polite" className="unavail">
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
            />
            <div className="composer-foot">
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
          </section>
        </div>
      </div>
    </AppShellV2>
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
  // Codex #83 round-1 P2: use native <input type="radio"> for the
  // expected keyboard model (ArrowLeft/Right cycles, Tab enters/exits
  // the group, only the checked radio is in the tab order). Wraps the
  // native input in a styled <label> so the pill chrome stays.
  const groupName = "persona-group-mode";
  return (
    <fieldset className="modeline">
      <legend>Ask the group as</legend>
      <ModeRadio
        name={groupName}
        value="collective"
        checked={mode === "collective"}
        onSelect={() => setMode("collective")}
        disabled={disabled}
        label="collective"
        title={`One voice speaking for all ${n} agent${n === 1 ? "" : "s"}; cites individuals inline.`}
      />
      <ModeRadio
        name={groupName}
        value="individual"
        checked={mode === "individual"}
        onSelect={() => setMode("individual")}
        disabled={disabled}
        label="individual fan-out"
        title={`Send to all ${n} agent${n === 1 ? "" : "s"} separately; see every reply.`}
      />
    </fieldset>
  );
}

function ModeRadio({
  name,
  value,
  checked,
  onSelect,
  disabled,
  label,
  title,
}: {
  name: string;
  value: PersonaGroupMode;
  checked: boolean;
  onSelect: () => void;
  disabled: boolean;
  label: string;
  title: string;
}) {
  return (
    <label
      title={title}
      className={checked ? "mode-pill on" : "mode-pill"}
      style={{
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.6 : 1,
      }}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        disabled={disabled}
        onChange={() => onSelect()}
        // Visually hide the native control but keep it in the a11y tree
        // so screen readers + keyboard arrow-nav still work.
        className="nat"
      />
      {label}
    </label>
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
      <div className="turn-head">
        <span className="turn-role pm">You · PM</span>
        <span className="spacer" />
      </div>
      <div className="pm-body">{content}</div>
    </>
  );
}

function CollectiveTurn({
  content,
  references,
  personaName,
  flag,
  onSetFlag,
}: {
  content: string;
  references: AgentReference[];
  personaName: string;
  flag: boolean | null;
  onSetFlag: (next: boolean | null) => Promise<void>;
}) {
  return (
    <>
      <div className="turn-head">
        <span className="turn-role coll">
          {personaName} <span className="sub">· collective voice of the group</span>
        </span>
        <span className="spacer" />
        <ThumbsControl
          ariaLabel="Was this collective reply useful?"
          flag={flag}
          onSet={onSetFlag}
        />
      </div>
      <div className="coll-body">
        <RenderWithCitations content={content} references={references} />
      </div>
    </>
  );
}

function SynthesisTurn({
  synthesis,
  perAgent,
  personaName,
  flag,
  onSetFlag,
}: {
  synthesis: string;
  perAgent: PerAgentReply[];
  personaName: string;
  flag: boolean | null;
  onSetFlag: (next: boolean | null) => Promise<void>;
}) {
  return (
    <>
      <div className="turn-head">
        <span className="turn-role syn">Synthesis · individual fan-out</span>
        <span className="spacer" />
        <ThumbsControl
          ariaLabel="Was this synthesis line accurate?"
          flag={flag}
          onSet={onSetFlag}
        />
      </div>
      <div className="syn-line">{synthesis}</div>
      {perAgent.length > 0 && (
        <ul className="fanout">
          {perAgent.map((slot) => (
            <li key={slot.agent_id} className="agent-reply">
              <div className="agent-reply-head">
                <span className="agent-tag">{slot.agent_label}</span>
                <span className="agent-meta">· {personaName}</span>
                <span className="spacer" style={{ flex: 1 }} />
                {slot.error == null && (
                  <Link
                    href={`/agents/${slot.agent_id}`}
                    aria-label={`Open individual chat with ${slot.agent_label}`}
                    className="agent-1to1"
                  >
                    💬 chat 1:1
                  </Link>
                )}
              </div>
              {slot.error == null ? (
                <div className="agent-body">{slot.content}</div>
              ) : (
                <div className="agent-fail">
                  <span className="ftag">FAILED</span>
                  {slot.error}
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
        <Link key={`cite-${n}-${label}`} href={`/agents/${agentId}`} className="cite">
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

// Build the reply turn locally from the response so a best-effort
// group-log append failure on the backend (codex #82 round-1 P2) doesn't
// hide the reply from the PM. Mirrors the shape the server would have
// written to turns.jsonl.
function _buildReplyTurnFromResponse(
  resp: Awaited<ReturnType<typeof sendPersonaGroupMessage>>,
  _pmContent: string,
): PersonaGroupTurn {
  if (resp.role === "collective") {
    return {
      role: "collective",
      content: resp.content ?? "",
      created_at: resp.created_at,
      references: resp.references ?? null,
      per_agent: null,
    };
  }
  return {
    role: "synthesis",
    content: resp.synthesis ?? "",
    created_at: resp.created_at,
    per_agent: resp.per_agent ?? null,
    references: null,
  };
}
