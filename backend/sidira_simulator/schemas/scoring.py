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


# ── Metric lift result (agent-behavior-spec §3a / #221; generalized #275) ──


class MetricLiftResult(BaseModel):
    """Paired metric-lift between treatment and control arms (§3a; generic #275).

    Returned by every per-metric paired-lift aggregator (`aggregate_conversion_lift`,
    `aggregate_retention_lift`, …). `lift_pp` is the paired treatment−control delta
    in p_metric expressed in PERCENTAGE POINTS ([-100, +100]); `lift_ci_pp` is the
    paired-bootstrap CI in the same units, computed off the SAME statistic so it
    brackets the point by construction. `paired_n` is the matched-pair count that
    fed the bootstrap; the drop counters surface what was excluded (no twin, or a
    per-agent metric elicitation failure on either side) so a partial run reads
    honestly.

    #275: this is the SHARED result type for all per-metric lifts (one
    `metric_name` is set per simulation), so a single generic class — not parallel
    per-metric ones — carries the lift. The calibrator protocol is keyed on it too.
    """

    lift_pp: float | None = None
    lift_ci_pp: tuple[float, float] | None = None
    paired_n: int = 0
    unpaired_treatment: int = 0
    unpaired_control: int = 0
    elicitation_failure_drops: int = 0
    # #221 §3b: True when at least one treatment contributor's metric pass ran on
    # the UNBLINDED fallback prompt (no faithful standalone view — removal /
    # pure-mechanic / prose-only change). The treatment side was then exposed to
    # change framing, which can inflate p_metric and does NOT cancel in the delta,
    # so the lift is low-confidence; `metric_lift_honesty` flags it.
    unblinded_fallback: bool = False
    # #221 §3e: True when at least one contributor (in a usable pair) had its
    # metric propensity (p_metric) move materially across the K question
    # paraphrases — its answer was prompt-driven, not behavior-driven. Set from
    # EITHER arm. The paired delta then reflects wording noise, so the lift is
    # low-confidence; `metric_lift_honesty` flags it.
    paraphrase_unstable: bool = False
    # #221 shrinkage layer: True once a FITTED calibrator (services.
    # conversion_calibrator) has mapped the raw `lift_pp` onto the real-world
    # effect-size scale. The default `IdentityCalibrator` leaves this False, so
    # pre-#222 runs keep the "uncalibrated — read as rank/direction, not effect
    # size" caveat (`metric_lift_honesty`). An uncalibrated magnitude is therefore
    # never presented as calibrated. The fit itself is #222-gated.
    calibrated: bool = False
    # Variance-collapse honesty flag: True when at least one contributor (EITHER
    # arm) reacted on a persona that lacks per-persona v1.1 `behavioral_seeds` and
    # therefore fell back to the shared default identity seed (see
    # `services.identity_seed.draw_identity_seed`). When that happens, cross-agent
    # identity variance collapses and the paired blinded metric flattens toward
    # 0.0 / "non-separable" even for a genuinely large effect — so a flat metric
    # here may reflect collapsed agent variance, not a true null. Mirrors
    # `unblinded_fallback`: a property of the inputs, surfaced by
    # `metric_lift_honesty`; changes no numeric output. Rebuild the pack to v1.1
    # to de-attenuate.
    variance_collapsed: bool = False
    # Cheap diagnostic: the number of DISTINCT persona_ids across both arms whose
    # reactions carried the variance-collapse fallback bit. 0 when the flag is
    # False; counts personas (not reactions), so a persona sampled K times counts
    # once.
    variance_collapsed_persona_count: int = 0


# Backwards-compatible alias: the conversion-specific name some call sites and
# tests still import. Identical type — #275 made the result generic across metrics.
ConversionLiftResult = MetricLiftResult


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


class BenchmarkCaseResult(BaseModel):
    """One case's outcome within a blind-eval run — the per-case record.

    Carried on `BenchmarkRunResult.case_results` so the stratified honesty table
    (and any other reporting layer) can break the run down by case WITHOUT
    re-running the predictor — which for a stochastic / LLM-backed predictor
    would produce DIFFERENT predictions and drops than the certified run. These
    are the exact predictions the certificate was computed over.

    A `dropped` case carries no `prediction` (the predictor failed or it had no
    scorable label) but DOES carry its `source` + `stratum`-able fields, so a
    stratum where every case was dropped is still reported as an empty/dropped
    cell rather than silently vanishing (no silent truncation, §4 line 71).
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str
    source: str = Field(description="The case's source dataset label (for source-stratification).")
    observed_lift: float | None = Field(
        default=None,
        description="The case's ground-truth signed lift (the scoring actual). None if unscorable.",
    )
    prediction: float | None = Field(
        default=None,
        description="The blind predicted signed effect. None when the case was dropped.",
    )
    dropped: bool = Field(
        default=False,
        description="True when the predictor failed / the case had no scorable label.",
    )


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

    # ── Per-case records (for downstream reporting without a second pass) ──
    case_results: list[BenchmarkCaseResult] = Field(
        default_factory=list,
        description=(
            "Per-case outcome (prediction + actual + dropped flag) in input order, "
            "scored AND dropped. Lets a reporting layer (the stratified honesty "
            "table) break the run down without re-running a stochastic predictor — "
            "these are the exact predictions the certificate was computed over."
        ),
    )

    seed: int = Field(
        description="Seed driving the bootstrap + null permutation RNGs (reproducible)."
    )


# ── Stratified honesty table (ablation-protocol §4 / §5, ticket #222) ──


class StratumResult(BaseModel):
    """Per-stratum slice of a blind-eval, reported honestly (no cell dropped).

    One row of the `StratifiedHonestyTable`: the same direction/rank reads the
    runner computes globally, restricted to the cases in this stratum, plus the
    per-stratum always-flat + random-rank baselines so a stratum's gain is read
    against ITS OWN floor (a stratum of all-positive actuals has a very different
    flat baseline than a sign-balanced one). Reported for EVERY stratum the
    stratifier produces — including ones with poor/negative ρ or tiny n, which
    are FLAGGED `underpowered`, never hidden (ablation-protocol §4 line 71, the
    silent-truncation rule).

    The confidence is `regime`: pre-calibration the trustworthy reads are rank
    and direction (#221 shrinkage is still identity), so a stratum is labelled
    "rank/direction-only" and a bare effect size is never presented as truth.
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(description="The stratum's label (the stratifier's value for these cases).")
    n_cases: int = Field(ge=0, description="Cases SCORED in this stratum (predictor succeeded).")
    n_dropped: int = Field(
        default=0,
        ge=0,
        description=(
            "Cases in this stratum the runner DROPPED (predictor failed / no label). "
            "A stratum where every case was dropped is still reported (n_cases=0, "
            "n_dropped>0) so source-specific failures are never silently hidden (§4)."
        ),
    )
    direction_accuracy: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fraction of stratum cases where sign(predicted) == sign(observed).",
    )
    rank_rho: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="PRIMARY (§5): Spearman rank-ρ of predicted vs observed within the stratum.",
    )
    baselines: list[BenchmarkBaseline] = Field(
        default_factory=list,
        description="Always-flat + random-rank baselines computed on THIS stratum's actuals.",
    )
    underpowered: bool = Field(
        default=False,
        description=(
            "True when n_cases is below the certification floor — the stratum's "
            "reads are too noisy to certify. The cell is STILL reported (no silent "
            "truncation, §4 line 71); `caveat` explains the small-N limit."
        ),
    )
    regime: str = Field(
        description=(
            "Confidence/regime label. Pre-calibration this is rank/direction-only "
            "(never a bare effect-size-as-truth) — weak behavioral regime per "
            "oec-scoring §6. Underpowered strata carry the small-N qualifier too."
        ),
    )
    caveat: str | None = Field(
        default=None,
        description="Human-readable per-stratum caveat (small-N, degenerate ρ, single-sign).",
    )


class StratifiedHonestyTable(BaseModel):
    """Per-stratum breakdown of a blind-eval, presented honestly (#222 reporting).

    Built by `services.benchmark_honesty.stratify` over a `BenchmarkRunResult`
    and its cases + per-case predictions, partitioned by an injected stratifier
    (by source dataset, by effect-magnitude bucket, …). EVERY stratum is a row in
    `strata` — including poor/negative-ρ or tiny-n ones, flagged `underpowered`,
    never dropped (ablation-protocol §4 line 71).

    `void` mirrors the run's null-integrity gate: if the run's certificate did
    NOT PASS, the WHOLE table is void/untrustworthy — the per-stratum scores are
    leakage-suspect and must not be trusted (§4). The `caveat` block summarizes
    the global honesty frame: primary endpoint is rank-ρ, magnitude is
    uncalibrated until the #222 shrinkage layer, total n, and runner-level drops.
    """

    model_config = ConfigDict(extra="forbid")

    stratifier_name: str = Field(
        description="Which stratifier produced these rows (e.g. 'source', 'effect_magnitude')."
    )
    strata: list[StratumResult] = Field(
        default_factory=list,
        description="One row PER stratum — every cell reported, none dropped (§4 line 71).",
    )

    # ── Global honesty frame (carried through from the run) ──
    void: bool = Field(
        default=False,
        description=(
            "True when the run's null-integrity certificate did NOT PASS — the "
            "whole table is leakage-suspect and untrustworthy (§4)."
        ),
    )
    void_reason: str | None = Field(
        default=None, description="Why the table is void (mirrors the run's void_reason)."
    )
    total_n_scored: int = Field(
        ge=0, description="Total cases scored across all strata (the runner's n_cases)."
    )
    n_dropped_at_runner: int = Field(
        default=0,
        ge=0,
        description="Cases the RUNNER dropped (predictor failed / no label), carried through.",
    )
    dropped_case_ids: list[str] = Field(
        default_factory=list,
        description="Runner-level dropped case ids, carried through so nothing is silently lost.",
    )
    caveat: str = Field(
        description=(
            "Global honesty caveat: primary endpoint is rank-ρ; magnitude is "
            "uncalibrated until #222 calibration; total n; runner-level drops; and "
            "the void status if the null-integrity certificate did not pass."
        )
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
