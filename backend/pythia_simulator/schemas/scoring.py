"""Scoring + refinement schemas.

Per-agent: weakness classification + sentiment classification (two LLM calls
each, in parallel). Aggregation is a pure function over the per-agent results.
Refinement is a single LLM call over the aggregated state.

The 6 weakness categories live on `Weakness.category` in `schemas/simulation.py`;
we reuse them here so the scorer's output flows directly into `SimulationResult`.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from pythia_simulator.schemas.simulation import Weakness


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class WeaknessClassification(BaseModel):
    """One agent's reaction → diagnosed experimental-design weaknesses.

    `categories` may be empty (the reaction reveals no design weakness).
    """

    categories: list[
        # mirrors Weakness.category Literal in schemas/simulation.py
        str
    ] = Field(default_factory=list)
    primary_reason: str = Field(default="", description="One-sentence reason.")


class SentimentClassification(BaseModel):
    """One agent's reception of the proposed change."""

    sentiment: Sentiment
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    one_line_summary: str = Field(default="")


class AgentAnalysis(BaseModel):
    """Per-agent analysis bundle returned by the scoring service."""

    agent_id: str
    persona_id: str
    persona_name: str
    weakness: WeaknessClassification
    sentiment: SentimentClassification


# ── Scoring configuration ─────────────────────────────────────────────


class ScoringConfig(BaseModel):
    """Tunable knobs for the aggregation formula.

    Locked starting priors per Wave 0 + Wave 4 (`/codex` consult). All values
    are intended targets for Layer-3 calibration once outcome data arrives.

    Formula:
        sentiment_score  = (Σ conf_i × value_i + prior_k × 0.5)
                           / (Σ conf_i + prior_k)
        any_flag_share   = (# agents flagging ≥1 weakness) / N    # deduped per agent
        weakness_signal  = 1 − any_flag_share
        confidence_score = (sentiment_weight × sentiment_score
                            + weakness_weight × weakness_signal) × 100
    """

    sentiment_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    weakness_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    sentiment_prior_k: float = Field(
        default=1.0,
        ge=0.0,
        description="Pseudo-observations of neutral sentiment. Shrinks small-N scores toward 50.",
    )
    use_sentiment_confidence: bool = Field(
        default=True,
        description="Weight each agent's sentiment by its classification confidence.",
    )
    min_sample_size: int = Field(
        default=3,
        ge=1,
        description="Below this N, surface underpowered_design as the top weakness.",
    )
    top_k_weaknesses: int = Field(default=3, ge=1, le=10)
    confidence_rounding: int = Field(default=1, ge=0, le=2)
    bootstrap_resamples: int = Field(
        default=1000,
        ge=0,
        le=10_000,
        description=(
            "Percentile-bootstrap resample count for the confidence_score CI. "
            "Set to 0 to skip the bootstrap entirely and leave confidence_score_ci=None."
        ),
    )


# ── Refinement ────────────────────────────────────────────────────────


class RefinementInput(BaseModel):
    """Self-documenting input contract for the refinement agent.

    Explicit per Wave 0 review finding: the refinement prompt composer needs a
    typed input so its tests can be deterministic without driving a real LLM
    through the full simulation path.
    """

    hypothesis_prose: str
    capability_name: str
    confidence_score: float = Field(ge=0.0, le=100.0)
    top_weaknesses: list[Weakness]
    sample_reactions: list[str] = Field(default_factory=list)


class RefinementOutput(BaseModel):
    """1–3 concrete refinement suggestions."""

    suggestions: list[str] = Field(min_length=0, max_length=5)
