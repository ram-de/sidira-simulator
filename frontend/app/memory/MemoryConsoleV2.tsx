"use client";

// ───────────────────────────────────────────────────────────────────────────
// /memory — Experiment Memory (#28, #31, #32, #41), v2 Console reskin.
//
// ONE archive front-door: "Ask the archive" — a grounded, multi-turn conversation
// across two kinds of evidence (real MEASURED A/B experiments and Sidira's own
// PREDICTED simulations). Each answer cites the items it drew from, labeled
// MEASURED or PREDICTED (DESIGN.md §8.2/§8.3).
//
// #41 — PERSISTENT, MULTI-THREAD. The conversation is no longer ephemeral client
// state: threads persist server-side (tenant-scoped), so a tab-switch / reload
// never loses the conversation. A thread-list rail lets the PM keep several
// independent threads, switch between them, rename, and delete — Claude / ChatGPT
// style. Each thread auto-titles from its first question. Turns are persisted to
// the backend as they happen (optimistic UI); the SAME fused answer logic powers
// each turn (POST /conversations/{id}/turns reuses the /experiments/conversation
// path), so the YOU/ARCHIVE bubbles, inline citation links, PREDICTED/MEASURED
// rows, and follow-up chips are all unchanged.
//
// Token-driven only; all layout lives in styles/v2-theme.css (.v2-mem-*), so
// this island ships no inline <style> (no hydration risk). The whole subtree
// sits under AppShellV2 -> ConsoleShell's `.v2-console`.
// ───────────────────────────────────────────────────────────────────────────

import { Fragment, useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  appendConversationTurn,
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  renameConversation,
  type CitationSource,
  type ConversationSummary,
  type FusedCitation,
} from "@/lib/api";
import AppShellV2 from "@/components/v2/AppShellV2";
import { Button, Panel } from "@/components/v2";

// The Clerk session token (the __session cookie) is short-lived and refreshed by
// Clerk's browser SDK; an idle tab can fire a follow-up carrying a stale one, which
// the /api auth gate rejects with 401 ("Authentication required"). We read Clerk off
// its browser global rather than the useAuth() hook ON PURPOSE: ClerkProvider mounts
// only when Clerk is configured (app/layout.tsx), so a hook would crash the keyless
// local/demo build. window.Clerk is simply absent there, and we no-op.
type ClerkGlobal = {
  session?: { getToken: (opts?: { skipCache?: boolean }) => Promise<string | null> };
};

// Force a fresh session token so a retried request carries a valid cookie. Returns
// true only if a refresh was actually attempted (Clerk present + a live session).
async function refreshClerkSession(): Promise<boolean> {
  const clerk = (globalThis as { Clerk?: ClerkGlobal }).Clerk;
  if (!clerk?.session) return false;
  try {
    await clerk.session.getToken({ skipCache: true });
    return true;
  } catch {
    return false;
  }
}

function isAuthError(e: unknown): boolean {
  return e instanceof ApiError && e.status === 401;
}

// The last-active thread id is remembered in localStorage so a reload restores
// the exact thread the PM was in (the persisted store is the source of truth for
// CONTENT; this is just which one to re-open). Scoped by a fixed key — the
// backend already tenant-scopes the threads themselves.
const LAST_THREAD_KEY = "sidira.memory.lastThreadId";

function readLastThreadId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(LAST_THREAD_KEY);
  } catch {
    return null;
  }
}

function writeLastThreadId(id: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (id) window.localStorage.setItem(LAST_THREAD_KEY, id);
    else window.localStorage.removeItem(LAST_THREAD_KEY);
  } catch {
    /* private-mode / disabled storage — restore just falls back to most-recent */
  }
}

// One rendered exchange in the conversation thread (#32). Carries the user's
// question, the grounded answer, its per-answer citations, suggested follow-ups,
// and provenance (extractive vs composed). `pending` marks the turn whose answer
// is still streaming in — its reading choreography (DESIGN.md §9.4) fires once.
type ThreadTurn = {
  id: string;
  question: string;
  answer: string;
  citations: FusedCitation[];
  followUps: string[];
  usedLlm: boolean;
  pending: boolean;
};

// Citation source -> the mono designator word. The WORD carries the state
// (DESIGN.md §8.2 PREDICTED/MEASURED lexicon — color never carries it alone);
// both reuse the neutral designator tone, no new colors/pills/icons.
const SOURCE_LABEL: Record<CitationSource, string> = {
  measured: "MEASURED · REAL EXPERIMENT",
  predicted: "PREDICTED · SIDIRA SIM",
};

const UNTITLED_LABEL = "New conversation";

// The DOM id of a citation source card, scoped to its turn so the same prior id
// cited in two different turns never collides. The matching inline citation
// link (below) anchor-jumps here.
function citeAnchorId(turnId: string, citeId: string): string {
  return `mem-cite-${turnId}-${citeId.toLowerCase()}`;
}

// Inline citation links (#40): the composed answer prose repeats the short ids
// (e.g. `sim-ACEBE2BA`, `exp-0008`) the server already shortened. Rather than
// leaving them as cluttered plain text, we turn each occurrence that matches a
// real per-answer citation into a compact in-app citation link (Glean/Perplexity
// style) that scrolls to — and briefly highlights — its source card below.
//
// SAFETY: we NEVER inject markup. The text is tokenized into React nodes; the
// id pattern is a literal regex over plain text and each candidate is only
// linkified when it maps to an actual citation (case-insensitive), so we never
// mint a dead link or relabel anything.
type LinkifyNode = string | { token: string; citeId: string; key: string };

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Split `text` into a flat list of plain strings and citation tokens. We build the
// match set from the ACTUAL cited ids in `byId` (the real citations in THIS answer)
// rather than a fixed id-shape pattern, so any id form linkifies — `sim-ACEBE2BA`,
// `exp-0008`, AND multi-segment ids like `sim-cw-1` — and, by construction, only
// ids that resolve to a card here (never a dead link, never a relabel). Longest-
// first alternation so a longer id isn't pre-empted by a shorter prefix.
function tokenizeCitations(
  text: string,
  byId: Map<string, FusedCitation>,
): LinkifyNode[] {
  if (byId.size === 0) return text ? [text] : [];
  const ids = [...byId.keys()].sort((a, b) => b.length - a.length).map(escapeRegExp);
  const re = new RegExp(`\\b(${ids.join("|")})\\b`, "gi");
  const out: LinkifyNode[] = [];
  let last = 0;
  let occurrence = 0;
  for (let m = re.exec(text); m !== null; m = re.exec(text)) {
    const raw = m[1];
    const cite = byId.get(raw.toLowerCase());
    if (!cite) continue; // defensive — should always resolve by construction
    if (m.index > last) out.push(text.slice(last, m.index));
    out.push({
      token: raw,
      citeId: cite.id,
      key: `${cite.id.toLowerCase()}-${occurrence++}`,
    });
    last = m.index + raw.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

// The answer prose with its short ids rendered as in-app citation links. When no
// id resolves to a card, this is just the plain answer text (one string node).
function AnswerProse({
  turnId,
  text,
  citations,
  onJump,
}: {
  turnId: string;
  text: string;
  citations: FusedCitation[];
  onJump: (turnId: string, citeId: string) => void;
}) {
  const byId = new Map(citations.map((c) => [c.id.toLowerCase(), c]));
  const nodes = tokenizeCitations(text, byId);
  return (
    <p className="v2-mem-answer">
      {nodes.map((n, i) =>
        typeof n === "string" ? (
          <Fragment key={`t-${i}`}>{n}</Fragment>
        ) : (
          <button
            key={n.key}
            type="button"
            className="v2-mem-citelink v2-mono"
            // The link points at a per-turn card anchor; aria spells out the
            // jump for SR users (the visible text is just the short id).
            aria-label={`Jump to cited source ${n.token.toUpperCase()} below`}
            onClick={() => onJump(turnId, n.citeId)}
          >
            {n.token}
          </button>
        ),
      )}
    </p>
  );
}

// A fused citation (#31): distinguishes MEASURED (real experiment) from
// PREDICTED (Sidira sim). The source word + the pre-formatted effect label both
// carry the state; tone stays neutral (DESIGN.md §8.2 / §4.3). The card carries
// a per-turn anchor id (#40) so the inline citation link can scroll to it.
function FusedCitationRow({ turnId, c }: { turnId: string; c: FusedCitation }) {
  return (
    <li id={citeAnchorId(turnId, c.id)} className="v2-mem-cite">
      <span className="v2-mem-cite-head">
        <span className="v2-mem-cite-id v2-mono">{c.id.toUpperCase()}</span>
        <span className="v2-mem-cite-src v2-mono">{SOURCE_LABEL[c.source]}</span>
      </span>
      <span className="v2-mem-cite-desc">{c.change_description}</span>
      <span className="v2-mem-cite-res v2-mono v2-tnum">{c.effect_label}</span>
    </li>
  );
}

function threadTitle(t: ConversationSummary): string {
  return t.title?.trim() || UNTITLED_LABEL;
}

// ── thread-list rail (#41) ──────────────────────────────────────────────────
// The switcher: New conversation control + the tenant's threads (newest-touched
// first). Clicking a row loads its history; double-click / the rename control
// edits the title inline; delete is a quiet two-step confirm (no modal). Dark
// Console archetype, tokens only — no emoji / icon libs (§7.10).
function ThreadRail({
  threads,
  activeId,
  busy,
  onNew,
  onSelect,
  onRename,
  onDelete,
}: {
  threads: ConversationSummary[];
  activeId: string | null;
  busy: boolean;
  onNew: () => void;
  onSelect: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const beginRename = (t: ConversationSummary) => {
    setConfirmId(null);
    setEditingId(t.id);
    setDraft(t.title ?? "");
  };

  const commitRename = (id: string) => {
    const next = draft.trim();
    setEditingId(null);
    if (next) onRename(id, next);
  };

  return (
    <aside className="v2-mem-rail" aria-label="Conversations">
      <div className="v2-mem-rail-head">
        <span className="v2-mem-rail-title v2-mono">CONVERSATIONS</span>
        <button
          type="button"
          className="v2-mem-rail-new v2-mono"
          onClick={onNew}
          disabled={busy}
        >
          + New
        </button>
      </div>
      {threads.length === 0 ? (
        <p className="v2-mem-rail-empty">
          No conversations yet. Ask the archive a question to start one.
        </p>
      ) : (
        <ul className="v2-mem-rail-list">
          {threads.map((t) => {
            const isActive = t.id === activeId;
            const isEditing = t.id === editingId;
            const isConfirming = t.id === confirmId;
            return (
              <li key={t.id} className="v2-mem-rail-itemwrap">
                {isEditing ? (
                  <input
                    className="v2-mem-rail-rename"
                    value={draft}
                    autoFocus
                    aria-label="Rename conversation"
                    maxLength={256}
                    onChange={(e) => setDraft(e.target.value)}
                    onBlur={() => commitRename(t.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") commitRename(t.id);
                      if (e.key === "Escape") setEditingId(null);
                    }}
                  />
                ) : (
                  <div
                    className={
                      "v2-mem-rail-item" + (isActive ? " v2-mem-rail-item--active" : "")
                    }
                  >
                    <button
                      type="button"
                      className="v2-mem-rail-pick"
                      aria-current={isActive ? "true" : undefined}
                      title={threadTitle(t)}
                      onClick={() => onSelect(t.id)}
                      onDoubleClick={() => beginRename(t)}
                    >
                      <span
                        className={
                          "v2-mem-rail-name" +
                          (t.title ? "" : " v2-mem-rail-name--untitled")
                        }
                      >
                        {threadTitle(t)}
                      </span>
                    </button>
                    <div className="v2-mem-rail-actions">
                      <button
                        type="button"
                        className="v2-mem-rail-act v2-mono"
                        aria-label={`Rename ${threadTitle(t)}`}
                        onClick={() => beginRename(t)}
                      >
                        Rename
                      </button>
                      {isConfirming ? (
                        <button
                          type="button"
                          className="v2-mem-rail-act v2-mem-rail-act--danger v2-mono"
                          aria-label={`Confirm delete ${threadTitle(t)}`}
                          onClick={() => {
                            setConfirmId(null);
                            onDelete(t.id);
                          }}
                          onBlur={() => setConfirmId(null)}
                        >
                          Confirm
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="v2-mem-rail-act v2-mono"
                          aria-label={`Delete ${threadTitle(t)}`}
                          onClick={() => setConfirmId(t.id)}
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </aside>
  );
}

export default function MemoryConsoleV2() {
  // ── thread + conversation state (#41: persistent, multi-thread) ──
  const [threads, setThreads] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [thread, setThread] = useState<ThreadTurn[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const threadEndRef = useRef<HTMLDivElement | null>(null);
  // Monotonic token so only the MOST RECENT loadThread() applies its result:
  // rapidly selecting thread A then B must never let a slow A response overwrite
  // B's history (latest-wins request sequencing).
  const loadTokenRef = useRef(0);
  // Synchronous double-submit guard. React state (chatLoading) updates async, so
  // two near-simultaneous submits can both observe chatLoading === false AND
  // activeId === null, mint TWO threads, and duplicate the first turn. This ref
  // flips synchronously inside ask() so the second submit bails immediately.
  // (Same gate class as the simulation submit guard.)
  const askInFlightRef = useRef(false);

  // Keep the latest turn in view as the thread grows (reading order, §7.5).
  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ block: "nearest" });
  }, [thread.length]);

  // Load one thread's persisted history into the visible conversation.
  // Latest-wins: each call claims a token; a slower earlier load is ignored once
  // a newer load has started, so selecting A then B never lets A's late response
  // clobber B.
  const loadThread = useCallback(async (id: string) => {
    const token = ++loadTokenRef.current;
    const isStale = () => token !== loadTokenRef.current;
    setLoadingHistory(true);
    setChatError(null);
    try {
      const detail = await getConversation(id);
      if (isStale()) return; // a newer selection superseded this load
      setThread(
        detail.turns.map((t) => ({
          id: t.id,
          question: t.question,
          answer: t.answer,
          citations: t.citations,
          followUps: [], // suggestions are recomputed on the live turn only
          usedLlm: t.used_llm,
          pending: false,
        })),
      );
      setActiveId(id);
      writeLastThreadId(id);
    } catch (e) {
      if (isStale()) return; // a newer selection owns the view now
      // A vanished thread (deleted in another tab) → drop back to no-thread.
      if (e instanceof ApiError && e.status === 404) {
        writeLastThreadId(null);
        setActiveId(null);
        setThread([]);
      } else {
        setChatError((e as Error)?.message ?? "Could not load conversation");
      }
    } finally {
      // Only the most recent load may clear the loading flag — otherwise a slow
      // superseded load would prematurely hide the newer load's spinner.
      if (!isStale()) setLoadingHistory(false);
    }
  }, []);

  // On mount: load the customer's threads and restore the last-active (or the
  // most-recent) so a reload / tab-switch does NOT lose the conversation.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await listConversations();
        if (cancelled) return;
        setThreads(list);
        const last = readLastThreadId();
        const restore =
          (last && list.find((t) => t.id === last)?.id) || list[0]?.id || null;
        if (restore) await loadThread(restore);
      } catch {
        // Keyless/offline or a transient failure — start with an empty rail; the
        // first question lazily creates a thread.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadThread]);

  const refreshThreads = useCallback(async () => {
    try {
      setThreads(await listConversations());
    } catch {
      /* non-fatal — the rail just keeps its last-known list */
    }
  }, []);

  // "New conversation" — clear the visible thread; the actual row is minted
  // lazily on the first question (so we never leave empty husks if the PM clicks
  // New repeatedly without asking anything).
  const startNewThread = useCallback(() => {
    setActiveId(null);
    setThread([]);
    setQuestion("");
    setChatError(null);
    writeLastThreadId(null);
  }, []);

  const selectThread = useCallback(
    (id: string) => {
      if (id === activeId || chatLoading) return;
      void loadThread(id);
    },
    [activeId, chatLoading, loadThread],
  );

  const renameThread = useCallback(
    async (id: string, title: string) => {
      // Optimistic: update the rail immediately, then persist.
      setThreads((prev) =>
        prev.map((t) => (t.id === id ? { ...t, title } : t)),
      );
      try {
        await renameConversation(id, title);
      } catch {
        void refreshThreads(); // reconcile on failure
      }
    },
    [refreshThreads],
  );

  const removeThread = useCallback(
    async (id: string) => {
      setThreads((prev) => prev.filter((t) => t.id !== id));
      if (id === activeId) startNewThread();
      try {
        await deleteConversation(id);
      } catch {
        void refreshThreads();
      }
    },
    [activeId, startNewThread, refreshThreads],
  );

  // Inline citation link → its source card (#40). Scroll the matching per-turn
  // card into view and pulse a brief highlight so the eye lands on the evidence.
  // The pulse is a self-removing class; under prefers-reduced-motion the CSS
  // drops the animation but still tints the card briefly, so the affordance
  // never depends on motion. smooth scroll degrades to a jump for reduced-motion.
  const jumpToCitation = useCallback((turnId: string, citeId: string) => {
    if (typeof document === "undefined") return;
    const el = document.getElementById(citeAnchorId(turnId, citeId));
    if (!el) return;
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    el.scrollIntoView({
      behavior: reduce ? "auto" : "smooth",
      block: "nearest",
    });
    // Restart the pulse if it's already running (rapid re-clicks).
    el.classList.remove("v2-mem-cite--flash");
    void el.offsetWidth; // reflow so the class re-add re-triggers the animation
    el.classList.add("v2-mem-cite--flash");
    window.setTimeout(() => el.classList.remove("v2-mem-cite--flash"), 1400);
  }, []);

  // Ask one conversation turn. `text` lets a follow-up chip submit directly.
  // The turn is persisted server-side: a thread is lazily created on the first
  // question, then each turn POSTs to /conversations/{id}/turns which generates
  // the fused answer (same logic as the ephemeral path) AND persists Q + A +
  // citations — so the conversation survives navigation / reload.
  const ask = async (text: string) => {
    const q = text.trim();
    // Synchronous guard FIRST: a second click/Enter in the same tick bails here
    // before any thread is minted, so we never create two threads / duplicate the
    // first turn. chatLoading (async state) is the visual gate; this ref is the
    // race-proof one.
    if (!q || askInFlightRef.current || chatLoading) return;
    // Don't submit against a thread that's still loading — activeId may be stale
    // (mid-switch). Wait for the load to settle; the user can resubmit.
    if (loadingHistory) return;
    askInFlightRef.current = true;
    setChatError(null);
    setChatLoading(true);
    setQuestion("");

    // Optimistic user turn (no answer yet) so the question shows immediately.
    const optimisticId = `pending-${Date.now()}`;
    setThread((prev) => [
      ...prev,
      {
        id: optimisticId,
        question: q,
        answer: "",
        citations: [],
        followUps: [],
        usedLlm: false,
        pending: true,
      },
    ]);

    const runTurn = async (threadId: string) =>
      appendConversationTurn(threadId, q, 6);

    try {
      // Lazily mint the thread on the first question of a fresh conversation.
      let threadId = activeId;
      let createdNew = false;
      if (!threadId) {
        const created = await createConversation();
        threadId = created.id;
        createdNew = true;
        setActiveId(threadId);
        writeLastThreadId(threadId);
      }

      let res: Awaited<ReturnType<typeof appendConversationTurn>>;
      try {
        res = await runTurn(threadId);
      } catch (e) {
        // A 401 here almost always means the session token lapsed in an idle
        // tab. Refresh it once and retry before giving up — the user is still
        // signed in (this is a protected route), the cookie just went stale.
        if (isAuthError(e) && (await refreshClerkSession())) {
          res = await runTurn(threadId);
        } else {
          throw e;
        }
      }

      // Replace the optimistic turn with the persisted answer.
      setThread((prev) =>
        prev.map((t) =>
          t.id === optimisticId
            ? {
                id: res.turn.id,
                question: res.turn.question,
                answer: res.turn.answer,
                citations: res.turn.citations,
                followUps: res.follow_ups,
                usedLlm: res.turn.used_llm,
                pending: true,
              }
            : t,
        ),
      );
      // Reading choreography (§9.4): the just-arrived turn is "pending" for one
      // frame so its enter animation fires once, then settles. Reduced-motion
      // users get the settled frame immediately (the CSS handles that).
      requestAnimationFrame(() =>
        setThread((prev) =>
          prev.map((t) => (t.id === res.turn.id ? { ...t, pending: false } : t)),
        ),
      );

      // Reflect the (possibly newly auto-titled) thread in the rail, newest-first.
      setThreads((prev) => {
        const without = prev.filter((t) => t.id !== res.conversation.id);
        return [res.conversation, ...without];
      });
      if (createdNew) void refreshThreads();
    } catch (e) {
      // Roll the optimistic question back out so it doesn't strand answer-less.
      setThread((prev) => prev.filter((t) => t.id !== optimisticId));
      setQuestion(q);
      setChatError(
        isAuthError(e)
          ? "Your session expired. Refresh the page or sign in again to continue."
          : (e as Error)?.message ?? "Conversation failed",
      );
    } finally {
      askInFlightRef.current = false;
      setChatLoading(false);
    }
  };

  return (
    <AppShellV2
      activeNav="memory"
      title="Experiment memory"
      provenance={{ label: "RETRIEVAL · MEASURED + PREDICTED", calibrated: false, live: false }}
      actions={
        <Button as="a" variant="secondary" href="/memory/connect">
          Connect a source →
        </Button>
      }
    >
      <div className="v2-mem v2-mem--threaded">
        <p className="v2-mem-law v2-mono">
          RETRIEVAL OVER MEASURED EXPERIMENTS + SIDIRA PREDICTIONS · MEASURED = REAL RECORDED OUTCOME · PREDICTED = UNCALIBRATED SIMULATION, NEVER A MEASURED RESULT
        </p>

        <div className="v2-mem-layout">
          <ThreadRail
            threads={threads}
            activeId={activeId}
            busy={chatLoading}
            onNew={startNewThread}
            onSelect={selectThread}
            onRename={renameThread}
            onDelete={removeThread}
          />

          {/* ── Conversation over the fused archive (#31 + #32 + #41) ──────── */}
          <section className="v2-mem-section" aria-labelledby="v2-mem-chat-h">
            <h2 id="v2-mem-chat-h" className="v2-mem-section-title">
              Ask the archive
            </h2>
            <p className="v2-mem-section-sub">
              A grounded conversation across two kinds of evidence: real{" "}
              <span className="v2-mem-inline-src v2-mono">MEASURED</span> A/B
              experiments and Sidira&rsquo;s own{" "}
              <span className="v2-mem-inline-src v2-mono">PREDICTED</span>{" "}
              simulations. Ask a follow-up and it carries the thread&rsquo;s context
              — every conversation is saved, so you can keep several and pick up
              where you left off.
            </p>

            {thread.length > 0 && (
              <div
                className="v2-mem-thread"
                role="log"
                aria-label="Conversation with the archive"
                aria-live="polite"
              >
                {thread.map((t) => (
                  <div key={t.id} className="v2-mem-turn">
                    {/* user turn — right-offset, distinct surface, mono speaker */}
                    <div className="v2-mem-msg v2-mem-msg--you">
                      <span className="v2-mem-msg-who v2-mono">YOU</span>
                      <div className="v2-mem-bubble v2-mem-bubble--you">
                        <p className="v2-mem-ask">{t.question}</p>
                      </div>
                    </div>
                    {/* archive turn — left-offset, panel surface carries all evidence */}
                    {(t.answer || !t.pending) && (
                      <div className="v2-mem-msg v2-mem-msg--archive">
                        <span className="v2-mem-msg-who v2-mono">ARCHIVE</span>
                        <Panel
                          className={
                            "v2-mem-result v2-mem-bubble v2-mem-bubble--archive" +
                            (t.pending ? " v2-mem-result--arriving" : "")
                          }
                        >
                          <AnswerProse
                            turnId={t.id}
                            text={t.answer}
                            citations={t.citations}
                            onJump={jumpToCitation}
                          />
                          <div className="v2-mem-prov v2-mono">
                            {t.usedLlm ? "COMPOSED FROM ARCHIVE" : "EXTRACTIVE · NO LLM"}{" "}
                            · GROUNDED IN {t.citations.length}{" "}
                            {t.citations.length === 1 ? "SOURCE" : "SOURCES"}
                          </div>
                          {t.citations.length > 0 && (
                            <ul className="v2-mem-cites">
                              {t.citations.map((c) => (
                                <FusedCitationRow
                                  key={`${t.id}-${c.id}`}
                                  turnId={t.id}
                                  c={c}
                                />
                              ))}
                            </ul>
                          )}
                          {t.followUps.length > 0 && (
                            <div
                              className="v2-mem-followups"
                              aria-label="Suggested follow-up questions"
                            >
                              {t.followUps.map((f) => (
                                <button
                                  key={f}
                                  type="button"
                                  className="v2-mem-chip v2-mono"
                                  onClick={() => ask(f)}
                                  disabled={chatLoading || loadingHistory}
                                >
                                  {f}
                                </button>
                              ))}
                            </div>
                          )}
                        </Panel>
                      </div>
                    )}
                  </div>
                ))}
                <div ref={threadEndRef} />
              </div>
            )}

            {thread.length === 0 && loadingHistory && (
              <p className="v2-mem-section-sub v2-mono">Loading conversation…</p>
            )}

            <form
              className="v2-mem-form"
              onSubmit={(ev) => {
                ev.preventDefault();
                ask(question);
              }}
            >
              <textarea
                className="v2-mem-input"
                rows={2}
                placeholder={
                  thread.length === 0
                    ? "e.g. What did we predict vs measure on pricing? Which urgency tests backfired?"
                    : "Ask a follow-up…"
                }
                value={question}
                onChange={(ev) => setQuestion(ev.target.value)}
                aria-label="Question for the archive"
              />
              <div className="v2-mem-form-actions">
                <Button
                  variant="primary"
                  // Disable while a turn is in flight or history is loading so a
                  // second submit can't race in and create a duplicate thread/turn
                  // (the askInFlightRef is the synchronous backstop). type stays
                  // "button" (the form's onSubmit handles Enter) so a click fires
                  // ask() exactly once, not also via form submission.
                  disabled={chatLoading || loadingHistory || !question.trim()}
                  onClick={() => ask(question)}
                >
                  {chatLoading
                    ? "Reading…"
                    : thread.length === 0
                      ? "Ask →"
                      : "Send →"}
                </Button>
              </div>
            </form>

            {chatError && (
              <div role="alert" className="v2-mem-alert">
                Could not answer: {chatError}
              </div>
            )}
          </section>
        </div>
      </div>
    </AppShellV2>
  );
}
