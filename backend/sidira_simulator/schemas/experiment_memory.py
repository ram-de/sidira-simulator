"""Experiment-memory schemas (#28, #29).

The experiment-memory feature is pure RETRIEVAL over an archive of PAST,
already-resolved A/B experiments. There is NO model prediction here — every
number a caller sees is a real recorded outcome — so it is valuable regardless
of the simulation engine's accuracy.

Two-table firewall note: the `Experiment` model keeps the *input* side of an
experiment (``change_description``, ``variants``, ``category``) cleanly separate
from the *outcome* side (``winner``, ``result``, ``effect_size_pct``, ``n``).
Similarity search reads ONLY the input side (plus the hypothesis text the caller
types, which carries no outcome). The outcome fields are attached to a match
only AFTER ranking, never used to rank. So the feature surfaces known past
outcomes without inventing a leakage path from outcome back into the "features"
that drive retrieval.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ExperimentCategory(str, Enum):
    """The kind of product change an experiment tested."""

    COPY = "copy"
    PRICING = "pricing"
    UI = "ui"
    FLOW = "flow"


class ExperimentResult(str, Enum):
    """The recorded outcome of a resolved experiment.

    ``WIN``/``LOSS`` are relative to the treatment (the proposed change): a
    treatment that beat control on the primary metric is a WIN, one that lost is
    a LOSS, and one whose effect was not distinguishable from zero is ``FLAT``.
    """

    WIN = "win"
    LOSS = "loss"
    FLAT = "flat"


class Experiment(BaseModel):
    """One resolved past A/B experiment in the archive.

    INPUT side (drives retrieval): id, change_description, variants,
    primary_metric, category.
    OUTCOME side (attached after ranking, never ranks): winner, result,
    effect_size_pct, n, date.
    """

    id: str
    change_description: str = Field(
        description="What the experiment changed — the testable hypothesis, input side."
    )
    variants: list[str] = Field(
        description="The arms tested; index 0 is the control by convention."
    )
    primary_metric: str = Field(description="The metric the experiment was decided on.")
    category: ExperimentCategory
    # ── outcome side ──────────────────────────────────────────────────────
    winner: str = Field(description="Which variant won, or 'control' / 'no winner'.")
    result: ExperimentResult
    effect_size_pct: float = Field(
        description=(
            "Relative effect of the treatment on the primary metric, in percent. "
            "Positive = treatment beat control. Real recorded number, not a prediction."
        )
    )
    n: int = Field(gt=0, description="Total sample size across arms.")
    date: str = Field(description="ISO date the experiment concluded (YYYY-MM-DD).")


class Verdict(str, Enum):
    """Trust-ordered classification of a NEW hypothesis against the archive.

    Ordered by how much the past evidence can be trusted to speak to the new
    hypothesis:

    - ``ALREADY_TESTED``: a past experiment is close enough that it is, for
      practical purposes, the SAME test — show its real result.
    - ``SIMILAR``: a past experiment rhymes with the new one — shown HONESTLY as
      an analogical prior, never as a guarantee ("similar != guaranteed same
      effect").
    - ``NOVEL``: nothing in the archive is close — a genuine candidate for
      testing, no prior to lean on.
    """

    ALREADY_TESTED = "already_tested"
    SIMILAR = "similar"
    NOVEL = "novel"


class SimilarMatch(BaseModel):
    """A past experiment surfaced for a hypothesis, with its similarity score."""

    experiment: Experiment
    similarity: float = Field(
        ge=0.0, le=1.0, description="Cosine similarity of the hypothesis to this experiment."
    )


class SearchSimilarRequest(BaseModel):
    hypothesis: str = Field(
        min_length=1,
        description="The NEW change the PM is considering. Carries no outcome.",
    )
    top_k: int = Field(default=5, ge=1, le=25)


class SearchSimilarResponse(BaseModel):
    """Trust-ordered dedup result for a new hypothesis."""

    hypothesis: str
    verdict: Verdict
    headline: str = Field(
        description="One honest sentence stating what the archive does/doesn't say."
    )
    caveat: str | None = Field(
        default=None,
        description=(
            "Present for SIMILAR verdicts — the 'similar != guaranteed same "
            "effect' honesty label. None for ALREADY_TESTED / NOVEL."
        ),
    )
    matches: list[SimilarMatch]


class ExperimentChatRequest(BaseModel):
    message: str = Field(min_length=1, description="A question about the experiment archive.")
    top_k: int = Field(default=6, ge=1, le=25)


class ChatCitation(BaseModel):
    """A past experiment cited in a chat answer."""

    id: str
    change_description: str
    result: ExperimentResult
    effect_size_pct: float
    primary_metric: str


class ExperimentChatResponse(BaseModel):
    """A grounded answer over the archive plus the experiments it cited."""

    answer: str
    citations: list[ChatCitation]
    grounded: bool = Field(
        description=(
            "True when the answer was produced from retrieved archive experiments "
            "(always — the feature never answers ungrounded). The flag is kept so "
            "the UI can show provenance and a future ungrounded path stays honest."
        )
    )
    used_llm: bool = Field(
        description="True if an LLM composed the prose; False for the offline extractive fallback."
    )
