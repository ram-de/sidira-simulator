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
