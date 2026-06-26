"""Offline semantic similarity + trust-ordering for the experiment archive (#29).

No external embedding service and no new dependency: similarity is a pure-Python
TF-IDF vector space with cosine similarity, so search-similar runs fully offline
(and deterministically) in the test suite and in a keyless local demo. If a real
embedding client is wired in later, only ``ExperimentIndex`` changes — the
trust-ordering in :func:`classify` is independent of how similarity is computed.

Trust-ordering (#29): a NEW hypothesis is classified against its best match by
cosine similarity into ALREADY_TESTED (effectively the same test — show the real
result), SIMILAR (an analogical prior, shown honestly with the
"similar != guaranteed same effect" caveat), or NOVEL (no prior to lean on).
The thresholds are tuned against the seed archive and are easy to revisit.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from sidira_simulator.schemas.experiment_memory import (
    Experiment,
    SearchSimilarResponse,
    SimilarMatch,
    Verdict,
)

# Cosine-similarity thresholds for the trust verdict. Tuned against the seed
# archive: a near-restatement of an existing change clears ALREADY_TESTED; a
# change that shares topic/metric vocabulary clears SIMILAR; below that there is
# no honest prior to show.
ALREADY_TESTED_THRESHOLD = 0.62
SIMILAR_THRESHOLD = 0.28

_SIMILAR_CAVEAT = (
    "Similar != guaranteed same effect. These past experiments rhyme with your "
    "hypothesis but tested a different change, audience, or surface — treat the "
    "result as an analogical prior, not a prediction for your test."
)

# Lightweight English stopword list — enough to stop function words from
# dominating the TF-IDF vectors without pulling in a dependency.
_STOPWORDS = frozenset("""
    a an the and or but if then else of to in on at by for with from into onto over
    under as is are was were be been being do does did has have had this that these
    those it its their our your his her my we you they he she them us i not no yes
    new instead than versus vs per up down out off about above below
    """.split())

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokens with stopwords dropped.

    A trailing-'s' plural is folded to its singular ('timers' -> 'timer') so a
    hypothesis and a past experiment match on the same concept regardless of
    number. Crude but dependency-free and good enough for the seed archive.
    """
    tokens: list[str] = []
    for raw in _TOKEN_RE.findall(text.lower()):
        if raw in _STOPWORDS:
            continue
        if len(raw) > 3 and raw.endswith("s") and not raw.endswith("ss"):
            raw = raw[:-1]
        tokens.append(raw)
    return tokens


def _experiment_text(exp: Experiment) -> str:
    """The INPUT-side text an experiment is indexed on.

    Two-table firewall: this deliberately excludes the outcome fields (winner /
    result / effect_size). Retrieval ranks on what the experiment *changed* and
    *measured*, never on how it turned out, so an outcome can never leak into the
    features that drive a match.
    """
    return " ".join([exp.change_description, exp.primary_metric, *exp.variants])


@dataclass(frozen=True)
class _Doc:
    experiment: Experiment
    tf: dict[str, float]  # L2-normalized tf-idf weights


class ExperimentIndex:
    """An in-memory TF-IDF index over an experiment archive.

    Built once per request from the seed archive (cheap at this size). Cosine
    similarity between L2-normalized tf-idf vectors reduces to a dot product over
    shared terms.
    """

    def __init__(self, experiments: list[Experiment]) -> None:
        self._experiments = experiments
        token_lists = [_tokenize(_experiment_text(e)) for e in experiments]

        n_docs = len(experiments)
        df: Counter[str] = Counter()
        for tokens in token_lists:
            df.update(set(tokens))
        # Smoothed idf so a term in every doc still carries a small positive
        # weight and an unseen term is simply absent rather than dividing by zero.
        self._idf = {term: math.log((1 + n_docs) / (1 + count)) + 1.0 for term, count in df.items()}

        self._docs = [
            _Doc(experiment=exp, tf=self._vectorize(tokens))
            for exp, tokens in zip(experiments, token_lists)
        ]

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        if not tokens:
            return {}
        counts = Counter(tokens)
        total = float(len(tokens))
        weights = {
            term: (count / total) * self._idf.get(term, 0.0) for term, count in counts.items()
        }
        norm = math.sqrt(sum(w * w for w in weights.values()))
        if norm == 0.0:
            return {}
        return {term: w / norm for term, w in weights.items()}

    def rank(self, query: str, top_k: int) -> list[SimilarMatch]:
        """Top-k archive experiments by cosine similarity to ``query``.

        Stable ordering: ties break by experiment id so results are
        deterministic for tests and for repeated UI calls.
        """
        qvec = self._vectorize(_tokenize(query))
        scored: list[tuple[float, Experiment]] = []
        for doc in self._docs:
            # Dot product over shared terms == cosine (both vectors L2-normalized).
            shorter, longer = (qvec, doc.tf) if len(qvec) <= len(doc.tf) else (doc.tf, qvec)
            sim = sum(w * longer.get(term, 0.0) for term, w in shorter.items())
            scored.append((sim, doc.experiment))

        scored.sort(key=lambda pair: (-pair[0], pair[1].id))
        return [
            SimilarMatch(experiment=exp, similarity=round(max(0.0, min(1.0, sim)), 4))
            for sim, exp in scored[:top_k]
        ]


def classify(best_similarity: float) -> Verdict:
    """Map the best-match similarity to a trust-ordered verdict (#29)."""
    if best_similarity >= ALREADY_TESTED_THRESHOLD:
        return Verdict.ALREADY_TESTED
    if best_similarity >= SIMILAR_THRESHOLD:
        return Verdict.SIMILAR
    return Verdict.NOVEL


def _headline(verdict: Verdict, match: SimilarMatch | None) -> str:
    if verdict is Verdict.ALREADY_TESTED and match is not None:
        exp = match.experiment
        direction = {
            "win": "the change won",
            "loss": "the change lost",
            "flat": "the change was flat",
        }[exp.result.value]
        return (
            f"You've effectively run this before ({exp.id}): {direction} on "
            f"{exp.primary_metric} ({exp.effect_size_pct:+.1f}%, n={exp.n:,}). "
            "Showing the real result instead of a fresh prediction."
        )
    if verdict is Verdict.SIMILAR and match is not None:
        return (
            "No exact prior, but related experiments exist. Showing them as "
            "analogical references, ordered by closeness."
        )
    return (
        "No prior match in the archive — this looks novel and is a candidate for "
        "testing. There's no past result to lean on."
    )


def search_similar(
    hypothesis: str,
    experiments: list[Experiment],
    top_k: int,
) -> SearchSimilarResponse:
    """Run the full pre-gate dedup: rank, classify, and build an honest response."""
    index = ExperimentIndex(experiments)
    matches = index.rank(hypothesis, top_k)
    best = matches[0] if matches else None
    verdict = classify(best.similarity if best is not None else 0.0)

    # NOVEL surfaces no matches: showing weakly-related experiments under a
    # "novel" headline would undercut the honest "no prior to lean on" message.
    shown = [] if verdict is Verdict.NOVEL else matches

    return SearchSimilarResponse(
        hypothesis=hypothesis,
        verdict=verdict,
        headline=_headline(verdict, best),
        caveat=_SIMILAR_CAVEAT if verdict is Verdict.SIMILAR else None,
        matches=shown,
    )
