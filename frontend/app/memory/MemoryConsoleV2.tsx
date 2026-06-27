"use client";

// ───────────────────────────────────────────────────────────────────────────
// /memory — Experiment Memory (#28, #31, #32), v2 Console reskin.
//
// ONE archive front-door: "Ask the archive" — a grounded, multi-turn conversation
// across two kinds of evidence (real MEASURED A/B experiments and Sidira's own
// PREDICTED simulations). Each answer cites the items it drew from, labeled
// MEASURED or PREDICTED (DESIGN.md §8.2/§8.3).
//
// The standalone "Check a new hypothesis" dedup box was REMOVED (#38d): that
// pre-gate check now fires at submit in the run wizard (POST
// /experiments/search-similar → the advisory submit gate), so a duplicate
// proactive box on /memory was dead weight. The archive keeps a single front
// door; a PM who wants to check a change can still ask the archive directly.
//
// Token-driven only; all layout lives in styles/v2-theme.css (.v2-mem-*), so
// this island ships no inline <style> (no hydration risk). The whole subtree
// sits under AppShellV2 -> ConsoleShell's `.v2-console`.
// ───────────────────────────────────────────────────────────────────────────

import { useEffect, useRef, useState } from "react";

import {
  ApiError,
  converseExperiments,
  type CitationSource,
  type ConversationTurn,
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

// One rendered exchange in the conversation thread (#32). Carries the user's
// question, the grounded answer, its per-answer citations, suggested follow-ups,
// and provenance (extractive vs composed). `pending` marks the turn whose answer
// is still streaming in — its reading choreography (DESIGN.md §9.4) fires once.
type ThreadTurn = {
  id: number;
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

// A fused citation (#31): distinguishes MEASURED (real experiment) from
// PREDICTED (Sidira sim). The source word + the pre-formatted effect label both
// carry the state; tone stays neutral (DESIGN.md §8.2 / §4.3).
function FusedCitationRow({ c }: { c: FusedCitation }) {
  return (
    <li className="v2-mem-cite">
      <span className="v2-mem-cite-head">
        <span className="v2-mem-cite-id v2-mono">{c.id.toUpperCase()}</span>
        <span className="v2-mem-cite-src v2-mono">{SOURCE_LABEL[c.source]}</span>
      </span>
      <span className="v2-mem-cite-desc">{c.change_description}</span>
      <span className="v2-mem-cite-res v2-mono v2-tnum">{c.effect_label}</span>
    </li>
  );
}

export default function MemoryConsoleV2() {
  // ── conversation state (#32: threaded, multi-turn) ──
  const [question, setQuestion] = useState("");
  const [thread, setThread] = useState<ThreadTurn[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const turnSeq = useRef(0);
  const threadEndRef = useRef<HTMLDivElement | null>(null);

  // Keep the latest turn in view as the thread grows (reading order, §7.5).
  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ block: "nearest" });
  }, [thread.length]);

  // Ask one conversation turn. `text` lets a follow-up chip submit directly.
  const ask = async (text: string) => {
    const q = text.trim();
    if (!q || chatLoading) return;
    setChatError(null);
    setChatLoading(true);
    setQuestion("");
    // Carry the prior turns as context so a follow-up resolves against them.
    const history: ConversationTurn[] = thread.map((t) => ({
      question: t.question,
      answer: t.answer,
    }));
    try {
      let res: Awaited<ReturnType<typeof converseExperiments>>;
      try {
        res = await converseExperiments(q, history, 6);
      } catch (e) {
        // A 401 here almost always means the session token lapsed in an idle
        // tab. Refresh it once and retry before giving up — the user is still
        // signed in (this is a protected route), the cookie just went stale.
        if (isAuthError(e) && (await refreshClerkSession())) {
          res = await converseExperiments(q, history, 6);
        } else {
          throw e;
        }
      }
      const id = ++turnSeq.current;
      setThread((prev) => [
        ...prev,
        {
          id,
          question: q,
          answer: res.answer,
          citations: res.citations,
          followUps: res.follow_ups,
          usedLlm: res.used_llm,
          pending: true,
        },
      ]);
      // Reading choreography (§9.4): the just-arrived turn is "pending" for one
      // frame so its enter animation fires once, then settles. Reduced-motion
      // users get the settled frame immediately (the CSS handles that).
      requestAnimationFrame(() =>
        setThread((prev) =>
          prev.map((t) => (t.id === id ? { ...t, pending: false } : t)),
        ),
      );
    } catch (e) {
      setChatError(
        isAuthError(e)
          ? "Your session expired. Refresh the page or sign in again to continue."
          : (e as Error)?.message ?? "Conversation failed",
      );
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <AppShellV2
      activeNav="memory"
      title="Experiment memory"
      provenance={{ label: "RETRIEVAL · REAL OUTCOMES", calibrated: false, live: false }}
      actions={
        <Button as="a" variant="secondary" href="/memory/connect">
          Connect a source →
        </Button>
      }
    >
      <div className="v2-mem">
        <p className="v2-mem-law v2-mono">
          RETRIEVAL OVER PAST EXPERIMENTS · EVERY FIGURE IS A REAL RECORDED OUTCOME · NO PREDICTION
        </p>

        {/* ── Conversation over the fused archive (#31 + #32) ───────────── */}
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
            — or check whether a change you&rsquo;re weighing has been tested or
            predicted before.
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
                  <div className="v2-mem-msg v2-mem-msg--archive">
                    <span className="v2-mem-msg-who v2-mono">ARCHIVE</span>
                    <Panel
                      className={
                        "v2-mem-result v2-mem-bubble v2-mem-bubble--archive" +
                        (t.pending ? " v2-mem-result--arriving" : "")
                      }
                    >
                    <p className="v2-mem-answer">{t.answer}</p>
                    <div className="v2-mem-prov v2-mono">
                      {t.usedLlm ? "COMPOSED FROM ARCHIVE" : "EXTRACTIVE · NO LLM"}{" "}
                      · GROUNDED IN {t.citations.length}{" "}
                      {t.citations.length === 1 ? "SOURCE" : "SOURCES"}
                    </div>
                    {t.citations.length > 0 && (
                      <ul className="v2-mem-cites">
                        {t.citations.map((c) => (
                          <FusedCitationRow key={`${t.id}-${c.id}`} c={c} />
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
                            disabled={chatLoading}
                          >
                            {f}
                          </button>
                        ))}
                      </div>
                    )}
                    </Panel>
                  </div>
                </div>
              ))}
              <div ref={threadEndRef} />
            </div>
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
              <Button variant="primary" onClick={() => ask(question)}>
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
    </AppShellV2>
  );
}
