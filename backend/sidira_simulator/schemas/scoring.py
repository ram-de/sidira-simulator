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

from sidira_simulator.schemas.simulation import Weakness


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
    """Per-agent analysis bundle returned by the scoring service.

    `weakness_failed` / `sentiment_failed` mark which classifications fell
    back to the neutral default because the underlying LLM call raised
    (timeout, JSON parse error, etc.). `aggregate()` uses these to drive
    the Phase 2.5 #8 degradation guard: if >50% of classifications across
    the run failed, the aggregate score is discounted and an
    `underpowered_design` weakness is prepended.
    """

    agent_id: str
    persona_id: str
    persona_name: str
    weakness: WeaknessClassification
    sentiment: SentimentClassification
    weakness_failed: bool = False
    sentiment_failed: bool = False
    weakness_attempted: bool = True
    """Whether the weakness classifier ran for this agent. Phase 4.6 #90
    (codex R3-P2a): control-arm agents skip weakness classification
    entirely because the 6 categories describe experiment-design
    weaknesses in the proposed change, undefined for the status-quo
    arm. `aggregate()`'s degradation gate divides failures by
    *attempted* classifications, not by 2N — otherwise a fully-failed
    control sentiment run would show 50% failure rate (N/2N) and miss
    the strict `>` threshold. Treatment + single-arm callers keep the
    default True."""
    sample_index: int = 0
    """Per-persona draw index. Phase 4.6 #90 pairs treatment/control by
    (persona_id, sample_index); default 0 keeps single-arm callers
    backwards-compatible."""


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
    degradation_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "Phase 2.5 #8 degradation guard: if more than this fraction of "
            "LLM classifications (weakness + sentiment, counted independently) "
            "failed during the run, aggregate() discounts the confidence_score "
            "by `degradation_discount` and prepends an underpowered_design "
            "weakness so PMs see the silent-failure state."
        ),
    )
    degradation_discount: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "Multiplicative discount applied to the confidence_score (and its "
            "bootstrap CI) when the degradation threshold is exceeded. 0.3 "
            "means the reported score is 70% of the raw score."
        ),
    )


# ── A/B lift result (Phase 4.6 #90) ───────────────────────────────────


class ABLiftResult(BaseModel):
    """Paired-bootstrap lift between treatment and control arms.

    Returned by `services.scoring.aggregate_ab` alongside the per-arm
    SimulationResults; the route layer composes it onto the unified
    SimulationResult via the `lift*` fields.

    `lift` is in confidence_score units (range [-100, +100]) so it's
    directly comparable to a confidence_score delta. `lift_ci` is in the
    same units, derived by scaling the per-agent-delta bootstrap CI by
    `sentiment_weight × 100`. `paired_n` is the count of matched pairs
    that actually fed the bootstrap; the three drop counters surface
    what was excluded so PMs see partial-failure runs honestly instead
    of a silently shrunken N.
    """

    lift: float | None = None
    lift_ci: tuple[float, float] | None = None
    paired_n: int = 0
    unpaired_treatment: int = 0
    unpaired_control: int = 0
    sentiment_failure_drops: int = 0


# ── Conversion lift result (agent-behavior-spec §3a / #221) ────────────


class ConversionLiftResult(BaseModel):
    """Paired conversion-lift between treatment and control arms (§3a).

    Returned by `services.scoring.aggregate_conversion_lift`. `lift_pp` is the
    paired treatment−control delta in p_conv expressed in PERCENTAGE POINTS
    ([-100, +100]); `lift_ci_pp` is the paired-bootstrap CI in the same units,
    computed off the SAME statistic so it brackets the point by construction.
    `paired_n` is the matched-pair count that fed the bootstrap; the drop
    counters surface what was excluded (no twin, or a per-agent conversion
    elicitation failure on either side) so a partial run reads honestly.
    """

    lift_pp: float | None = None
    lift_ci_pp: tuple[float, float] | None = None
    paired_n: int = 0
    unpaired_treatment: int = 0
    unpaired_control: int = 0
    elicitation_failure_drops: int = 0
    # #221 §3b: True when at least one treatment contributor's conversion metric
    # ran on the UNBLINDED fallback prompt (no faithful standalone view —
    # removal / pure-mechanic / prose-only change). The treatment side was then
    # exposed to change framing, which can inflate p_conv and does NOT cancel in
    # the delta, so the lift is low-confidence; `conversion_lift_honesty` flags it.
    unblinded_fallback: bool = False
    # #221 §3e: True when at least one contributor (in a usable pair) had its
    # conversion propensity (p_conv) move materially across the K question
    # paraphrases — its answer was prompt-driven, not behavior-driven. Set from
    # EITHER arm. The paired delta then reflects wording noise, so the lift is
    # low-confidence; `conversion_lift_honesty` flags it.
    paraphrase_unstable: bool = False
    # #221 shrinkage layer: True once a FITTED calibrator (services.
    # conversion_calibrator) has mapped the raw `lift_pp` onto the real-world
    # effect-size scale. The default `IdentityCalibrator` leaves this False, so
    # pre-#222 runs keep the "uncalibrated — read as rank/direction, not effect
    # size" caveat (`conversion_lift_honesty`). An uncalibrated magnitude is
    # therefore never presented as calibrated. The fit itself is #222-gated.
    calibrated: bool = False


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
