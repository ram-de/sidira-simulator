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

import { useState } from "react";

import {
  chatExperiments,
  searchSimilarExperiments,
  type ChatCitation,
  type ExperimentChatResponse,
  type ExperimentResult,
  type SearchSimilarResponse,
  type SimilarMatch,
  type Verdict,
} from "@/lib/api";
import AppShellV2 from "@/components/v2/AppShellV2";
import { Button, Panel, StatusBadge } from "@/components/v2";

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

function CitationRow({ c }: { c: ChatCitation }) {
  return (
    <li className="v2-mem-cite">
      <span className="v2-mem-cite-id v2-mono">{c.id.toUpperCase()}</span>
      <span className="v2-mem-cite-desc">{c.change_description}</span>
      <span className="v2-mem-cite-res v2-mono v2-tnum">
        {RESULT_LABEL[c.result]} · {pct(c.effect_size_pct)}
      </span>
    </li>
  );
}

export default function MemoryConsoleV2() {
  // ── dedup state ──
  const [hypothesis, setHypothesis] = useState("");
  const [dedup, setDedup] = useState<SearchSimilarResponse | null>(null);
  const [dedupLoading, setDedupLoading] = useState(false);
  const [dedupError, setDedupError] = useState<string | null>(null);

  // ── chat state ──
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState<ExperimentChatResponse | null>(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

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

  const runChat = async () => {
    const q = question.trim();
    if (!q) return;
    setChatError(null);
    setChatLoading(true);
    try {
      setChat(await chatExperiments(q, 6));
    } catch (e) {
      setChatError((e as Error)?.message ?? "Chat failed");
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

        {/* ── Chat over the archive ─────────────────────────────────────── */}
        <section className="v2-mem-section" aria-labelledby="v2-mem-chat-h">
          <h2 id="v2-mem-chat-h" className="v2-mem-section-title">
            Ask the archive
          </h2>
          <p className="v2-mem-section-sub">
            Ask what the team has learned. Answers are grounded in — and cite —
            real past experiments.
          </p>

          <form
            className="v2-mem-form"
            onSubmit={(ev) => {
              ev.preventDefault();
              runChat();
            }}
          >
            <textarea
              className="v2-mem-input"
              rows={2}
              placeholder="e.g. What have we learned about urgency framing? Which pricing tests won?"
              value={question}
              onChange={(ev) => setQuestion(ev.target.value)}
              aria-label="Question for the archive"
            />
            <div className="v2-mem-form-actions">
              <Button variant="primary" onClick={runChat}>
                {chatLoading ? "Reading…" : "Ask →"}
              </Button>
            </div>
          </form>

          {chatError && (
            <div role="alert" className="v2-mem-alert">
              Could not answer: {chatError}
            </div>
          )}

          {chat && (
            <Panel className="v2-mem-result">
              <p className="v2-mem-answer">{chat.answer}</p>
              <div className="v2-mem-prov v2-mono">
                {chat.used_llm ? "COMPOSED FROM ARCHIVE" : "EXTRACTIVE · NO LLM"} ·
                GROUNDED IN {chat.citations.length}{" "}
                {chat.citations.length === 1 ? "EXPERIMENT" : "EXPERIMENTS"}
              </div>
              {chat.citations.length > 0 && (
                <ul className="v2-mem-cites">
                  {chat.citations.map((c) => (
                    <CitationRow key={c.id} c={c} />
                  ))}
                </ul>
              )}
            </Panel>
          )}
        </section>
      </div>
    </AppShellV2>
  );
}
