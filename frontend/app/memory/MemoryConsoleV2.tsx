"use client";

// ───────────────────────────────────────────────────────────────────────────
// /memory — Experiment Memory (#28, #29), v2 Console reskin.
//
// Two retrieval surfaces over the past-experiment archive — NO prediction:
//   1. Pre-gate dedup: type a NEW hypothesis -> trust-ordered verdict
//      (already-tested · similar · novel) + similar past experiments with their
//      REAL recorded results. The "similar != guaranteed same effect" caveat is
//      shown verbatim on a SIMILAR verdict (honesty law, never smoothed).
//   2. Chat: ask the archive a question -> a grounded answer that cites the
//      real experiments it drew from.
//
// Token-driven only; all layout lives in styles/v2-theme.css (.v2-mem-*), so
// this island ships no inline <style> (no hydration risk). The whole subtree
// sits under AppShellV2 -> ConsoleShell's `.v2-console`.
// ───────────────────────────────────────────────────────────────────────────

import { useEffect, useRef, useState } from "react";

import {
  converseExperiments,
  searchSimilarExperiments,
  type CitationSource,
  type ConversationTurn,
  type ExperimentResult,
  type FusedCitation,
  type SearchSimilarResponse,
  type SimilarMatch,
  type Verdict,
} from "@/lib/api";
import AppShellV2 from "@/components/v2/AppShellV2";
import { Button, Panel, StatusBadge } from "@/components/v2";

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

// Verdict -> badge kind + the honest label string. `similar` borrows the `hold`
// badge (amber edge) as a "proceed with care" cue; tested/novel are neutral.
const VERDICT_META: Record<
  Verdict,
  { kind: "neutral" | "hold"; label: string }
> = {
  already_tested: { kind: "neutral", label: "ALREADY TESTED" },
  similar: { kind: "hold", label: "SIMILAR PRIOR" },
  novel: { kind: "neutral", label: "NOVEL · NO PRIOR" },
};

const RESULT_LABEL: Record<ExperimentResult, string> = {
  win: "WON",
  loss: "LOST",
  flat: "FLAT",
};

function pct(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function MatchRow({ match }: { match: SimilarMatch }) {
  const e = match.experiment;
  return (
    <div className="v2-mem-match" role="row">
      <div className="v2-mem-match-head">
        <span className="v2-mem-match-id v2-mono v2-tnum" title={e.id}>
          {e.id.toUpperCase()}
        </span>
        <span className="v2-mem-match-cat v2-mono">{e.category}</span>
        <span className="v2-mem-match-sim v2-mono v2-tnum" title="Cosine similarity to your hypothesis">
          {Math.round(match.similarity * 100)}% match
        </span>
      </div>
      <p className="v2-mem-match-desc">{e.change_description}</p>
      <div className="v2-mem-match-result">
        <span className="v2-mem-result-word v2-mono">
          {RESULT_LABEL[e.result]}
        </span>
        <span className="v2-mem-result-detail v2-mono v2-tnum">
          {pct(e.effect_size_pct)} on {e.primary_metric} · n={e.n.toLocaleString()} · {e.date}
        </span>
      </div>
    </div>
  );
}

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
  // ── dedup state ──
  const [hypothesis, setHypothesis] = useState("");
  const [dedup, setDedup] = useState<SearchSimilarResponse | null>(null);
  const [dedupLoading, setDedupLoading] = useState(false);
  const [dedupError, setDedupError] = useState<string | null>(null);

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

  const runDedup = async () => {
    const h = hypothesis.trim();
    if (!h) return;
    setDedupError(null);
    setDedupLoading(true);
    try {
      setDedup(await searchSimilarExperiments(h, 5));
    } catch (e) {
      setDedupError((e as Error)?.message ?? "Search failed");
    } finally {
      setDedupLoading(false);
    }
  };

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
      const res = await converseExperiments(q, history, 6);
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
      setChatError((e as Error)?.message ?? "Conversation failed");
    } finally {
      setChatLoading(false);
    }
  };

  const verdictMeta = dedup ? VERDICT_META[dedup.verdict] : null;

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

        {/* ── Pre-gate hypothesis dedup ─────────────────────────────────── */}
        <section className="v2-mem-section" aria-labelledby="v2-mem-dedup-h">
          <h2 id="v2-mem-dedup-h" className="v2-mem-section-title">
            Check a new hypothesis
          </h2>
          <p className="v2-mem-section-sub">
            Before you test, see whether the archive already answers it. Results
            are trust-ordered: already-tested shows the real result; similar is
            an analogical prior only; novel means there is nothing to lean on.
          </p>

          <form
            className="v2-mem-form"
            onSubmit={(ev) => {
              ev.preventDefault();
              runDedup();
            }}
          >
            <textarea
              className="v2-mem-input"
              rows={3}
              placeholder="e.g. Add an urgency countdown timer to the checkout page"
              value={hypothesis}
              onChange={(ev) => setHypothesis(ev.target.value)}
              aria-label="New hypothesis"
            />
            <div className="v2-mem-form-actions">
              <Button variant="primary" onClick={runDedup}>
                {dedupLoading ? "Checking…" : "Check the archive →"}
              </Button>
            </div>
          </form>

          {dedupError && (
            <div role="alert" className="v2-mem-alert">
              Could not check the archive: {dedupError}
            </div>
          )}

          {dedup && verdictMeta && (
            <Panel className="v2-mem-result">
              <div className="v2-mem-verdict">
                <StatusBadge kind={verdictMeta.kind}>{verdictMeta.label}</StatusBadge>
                <p className="v2-mem-headline">{dedup.headline}</p>
              </div>

              {dedup.caveat && (
                <p className="v2-mem-caveat" role="note">
                  {dedup.caveat}
                </p>
              )}

              {dedup.matches.length > 0 && (
                <div className="v2-mem-matches" role="table" aria-label="Similar past experiments">
                  {dedup.matches.map((m) => (
                    <MatchRow key={m.experiment.id} match={m} />
                  ))}
                </div>
              )}
            </Panel>
          )}
        </section>

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
            simulations. Ask a follow-up and it carries the thread&rsquo;s context.
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
                  <p className="v2-mem-ask">
                    <span className="v2-mem-ask-label v2-mono">YOU</span>
                    {t.question}
                  </p>
                  <Panel
                    className={
                      "v2-mem-result" + (t.pending ? " v2-mem-result--arriving" : "")
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
