"""Scoring + refinement schemas.

Per-agent: weakness classification + sentiment classification (two LLM calls
each, in parallel). Aggregation is a pure function over the per-agent results.
Refinement is a single LLM call over the aggregated state.

The 6 weakness categories live on `Weakness.category` in `schemas/simulation.py`;
we reuse them here so the scorer's output flows directly into `SimulationResult`.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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


# ── Null-integrity certificate (ablation-protocol §4) ──────────────────


class NullIntegrityCertificate(BaseModel):
    """Engine-validation gate for a Tier-0 ablation cell (ablation-protocol §4).

    Scramble the experiment outcome labels and a CLEAN cell must score at
    chance on direction and ρ≈0 on rank. A cell that "predicts" scrambled
    outcomes is leaking signal from the label into the prediction; the whole
    run is VOID until it doesn't. This certificate is the shippable proof:
    `services.null_integrity.certify_null_integrity` produces it over a cell's
    paired `(predicted_effect, actual_effect)` arrays, and it is meant to be
    pre-registered (`integrity_hash`) and shipped alongside results.

    The PASS/VOID gate (`passed`) reads the NULL distribution, not the observed
    scores: a clean cell is one whose SCRAMBLED-label scores center at chance.
    The observed scores and the permutation p-values (`*_p_value`) are the
    SEPARATE "is the real result better than chance" read — they never relax
    the gate.
    """

    # ── 1. Observed scores (the real, unscrambled prediction) ──
    n_experiments: int = Field(
        ge=0, description="Paired experiments scored (len of predictions == actuals)."
    )
    observed_direction_accuracy: float | None = Field(
        default=None,
        description=(
            "Fraction of experiments where sign(pred) == sign(actual), over the "
            "real labels. None on a degenerate (empty / underpowered-void) cert."
        ),
    )
    observed_rank_rho: float | None = Field(
        default=None,
        description="Spearman rank-ρ of predictions vs actuals over the real labels.",
    )

    # ── 2. Null distribution (scrambled labels) ──
    null_direction_accuracy_mean: float | None = Field(
        default=None, description="Mean direction-accuracy across label permutations."
    )
    null_direction_accuracy_ci: tuple[float, float] | None = Field(
        default=None,
        description="Percentile CI of the null direction-accuracy distribution.",
    )
    null_rank_rho_mean: float | None = Field(
        default=None, description="Mean rank-ρ across label permutations."
    )
    null_rank_rho_ci: tuple[float, float] | None = Field(
        default=None, description="Percentile CI of the null rank-ρ distribution."
    )
    marginal_chance_accuracy: float | None = Field(
        default=None,
        description=(
            "Expected direction-accuracy under random relabeling, given THIS "
            "cell's sign marginals (Σ_s (n_pred_s/n)(n_actual_s/n)). The TRUE "
            "chance baseline the direction gate brackets — not a fixed 0.5 — so "
            "an imbalanced-but-honest sign distribution (e.g. all-positive "
            "actuals) is not falsely voided."
        ),
    )

    # ── 3. PASS/VOID gate (reads the NULL, per §4) ──
    certifying: bool = Field(
        default=False,
        description=(
            "True only when the faithful §4 rerun path was used (a `predict_fn` "
            "re-derived predictions from each scrambled label set). A diagnostic "
            "(fixed-prediction) certificate is NON-certifying and can never PASS, "
            "because it cannot rule out a cell that leaked labels at predict-time."
        ),
    )
    passed: bool = Field(
        description=(
            "True iff the certificate is `certifying` AND the null "
            "direction-accuracy CI brackets the marginal chance baseline AND the "
            "null rank-ρ CI brackets 0 (and the cell is not underpowered). False "
            "means non-certifying, underpowered, or the scrambled-label scores did "
            "NOT center at chance → leakage → the run is void until fixed."
        )
    )
    void_reason: str | None = Field(
        default=None,
        description="Why the cell is VOID (leakage / degenerate). None when passed.",
    )

    # ── 4. Significance read (SECONDARY — never relaxes the gate) ──
    direction_accuracy_p_value: float | None = Field(
        default=None,
        description=(
            "Permutation p-value: fraction of permutations whose direction-accuracy "
            ">= observed (+1/+1 add-one correction). The honest 'is the real "
            "direction signal better than chance' number. Separate from `passed`."
        ),
    )
    rank_rho_p_value: float | None = Field(
        default=None,
        description=(
            "Permutation p-value: fraction of permutations whose rank-ρ >= observed "
            "(+1/+1 add-one correction). Separate from `passed`."
        ),
    )

    # ── 5. Honesty guards ──
    underpowered: bool = Field(
        default=False,
        description=(
            "True when n_experiments is below the certification floor. An "
            "underpowered cell can never PASS (the null CI is too wide to certify); "
            "`passed` is forced False and `caveat` explains."
        ),
    )
    caveat: str | None = Field(
        default=None,
        description="Human-readable caveat (small-N, degenerate input, ties, etc.).",
    )

    # ── 6. Config + hash-commit integrity (§5) ──
    n_permutations: int = Field(ge=0, description="Label permutations drawn for the null.")
    seed: int = Field(description="Seed that drove the permutation RNG (reproducibility).")
    integrity_hash: str = Field(
        description=(
            "SHA-256 over the canonical-serialized inputs + config (predictions, "
            "actuals, n_permutations, seed, n_experiments). Lets a certificate be "
            "pre-registered and not retrofitted — any input/config change moves it."
        )
    )


# ── Blind-eval benchmark result (ablation-protocol §4 / §5, ticket #222) ──


class BenchmarkBaseline(BaseModel):
    """Direction-accuracy + rank-ρ of a trivial no-information predictor.

    Printed alongside the engine's score so a gain is read against the real
    floor, not zero (ablation-protocol §4 line 72). Two are reported:

    * the ALWAYS-FLAT baseline — predict 0 effect for every experiment, the
      "nothing moves" null. Its direction-accuracy is the share of experiments
      whose actual effect is itself flat (sign 0); its rank-ρ is 0.0 (a constant
      prediction has no rank variation).
    * the RANDOM-RANK baseline — the marginal-expected score under a random
      relabeling of the actuals, the same closed-form chance baseline the
      null-integrity certificate brackets. Its rank-ρ is 0.0 in expectation.
    """

    model_config = ConfigDict(extra="forbid")

    name: Literal["always_flat", "random_rank"]
    direction_accuracy: float = Field(ge=0.0, le=1.0)
    rank_rho: float = Field(ge=-1.0, le=1.0)


class BenchmarkRunResult(BaseModel):
    """Scored blind-eval of a predictor over a set of adapter-produced cases.

    The PRIMARY endpoint is `rank_rho` (ablation-protocol §5 line 79): the
    magnitude stays directional/relative pre-calibration (the #221 shrinkage
    layer is still identity), so `direction_accuracy` and `rank_rho` are the
    trustworthy reads and an effect size is never presented as calibrated truth.

    Honesty (no silent truncation): `n_cases` is the count actually scored;
    `n_dropped` + `dropped_case_ids` surface every case the predictor failed on
    or that carried no scorable label, so a partial run reads honestly rather
    than as a silently shrunken denominator.

    `certificate` is the null-integrity gate (§4). If it does NOT pass
    (`certificate.passed is False`), `void` is True and the run is reported as
    void — the scores are leakage-suspect and must not be trusted.
    """

    model_config = ConfigDict(extra="forbid")

    # ── Primary + secondary scores ──
    rank_rho: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="PRIMARY endpoint (§5): Spearman rank-ρ of predicted vs observed effect.",
    )
    direction_accuracy: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fraction of cases where sign(predicted) == sign(observed).",
    )

    # ── Paired-across-cases bootstrap CI on per-case direction deltas (§4 l.69) ──
    direction_delta_vs_flat: float | None = Field(
        default=None,
        description=(
            "Mean per-case (engine-correct − always-flat-correct) indicator, the "
            "paired direction-accuracy gain over the flat baseline."
        ),
    )
    direction_delta_ci: tuple[float, float] | None = Field(
        default=None,
        description=(
            "Paired percentile-bootstrap CI on the per-case direction-delta vs the "
            "always-flat baseline (ablation-protocol §4 line 69). None when the "
            "bootstrap is skipped or the run is degenerate."
        ),
    )

    # ── Baselines (the real floor — §4 line 72) ──
    baselines: list[BenchmarkBaseline] = Field(default_factory=list)

    # ── Null-integrity gate (§4) ──
    certificate: NullIntegrityCertificate | None = Field(
        default=None,
        description="The shipped null-integrity certificate. None only on an empty run.",
    )
    void: bool = Field(
        default=False,
        description=(
            "True when the run is VOID — the null-integrity certificate did not "
            "PASS, so the scores are leakage-suspect and must not be trusted (§4)."
        ),
    )
    void_reason: str | None = Field(
        default=None,
        description="Why the run is void (mirrors certificate.void_reason / caveat).",
    )

    # ── Honesty: denominator transparency ──
    n_cases: int = Field(
        ge=0, description="Cases actually scored (predictor succeeded, label present)."
    )
    n_dropped: int = Field(
        default=0,
        ge=0,
        description="Cases dropped (predictor failed or no scorable label). Never silently truncated.",
    )
    dropped_case_ids: list[str] = Field(
        default_factory=list,
        description="Case ids that were dropped, with no silent omission from the denominator.",
    )

    seed: int = Field(
        description="Seed driving the bootstrap + null permutation RNGs (reproducible)."
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
