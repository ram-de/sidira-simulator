"""Scoring service tests.

Aggregation is a pure function — formula assertions live here.
Codex review (Wave 4) reshaped the formula:
- Confidence-weighted sentiment with Bayesian shrinkage toward neutral
- any_flag_share replaces max_category_share as the primary weakness penalty
- min_sample_size gate surfaces underpowered_design below threshold
- Categories deduped per agent before counting
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.scoring import (
    AgentAnalysis,
    ScoringConfig,
    Sentiment,
    SentimentClassification,
    WeaknessClassification,
)
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.scoring import AgentReaction, ScoringService


def _analysis(
    agent_id: str,
    sentiment: Sentiment,
    categories: list[str] | None = None,
    confidence: float = 0.8,
    persona_id: str = "p",
    persona_name: str = "P",
    weakness_failed: bool = False,
    sentiment_failed: bool = False,
) -> AgentAnalysis:
    return AgentAnalysis(
        agent_id=agent_id,
        persona_id=persona_id,
        persona_name=persona_name,
        weakness=WeaknessClassification(categories=categories or []),
        sentiment=SentimentClassification(
            sentiment=sentiment, confidence=confidence, one_line_summary=""
        ),
        weakness_failed=weakness_failed,
        sentiment_failed=sentiment_failed,
    )


# Disable the underpowered gate AND the bootstrap CI for formula-focused
# tests so we read the raw behavior fast.
# - min_sample_size=1 → gate never fires for N≥1.
# - bootstrap_resamples=0 → confidence_score_ci stays None; CI-aware tests
#   below opt in explicitly with their own config.
_FORMULA_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=0)


# ── Aggregation formula ───────────────────────────────────────────────


def test_aggregate_zero_agents_returns_zero_confidence() -> None:
    result = ScoringService.aggregate([])
    assert result.confidence_score == 0.0
    assert result.weaknesses == []


def test_aggregate_all_positive_no_weaknesses_shrinks_below_100() -> None:
    """Shrinkage prior keeps small-N runs from claiming a perfect score.

    5 positive agents at confidence 0.8 + prior_k=1.0 of neutral:
      numerator = 5*0.8*1.0 + 1.0*0.5 = 4.5
      denominator = 5*0.8 + 1.0 = 5.0
      sentiment_score = 0.9
      score = 100 * (0.6*0.9 + 0.4*1.0) = 94.0
    """
    analyses = [_analysis(f"a{i}", Sentiment.POSITIVE) for i in range(5)]
    result = ScoringService.aggregate(analyses, _FORMULA_CFG)
    assert result.confidence_score == 94.0
    assert result.weaknesses == []


def test_aggregate_all_negative_unanimous_weakness_floors_near_zero() -> None:
    """Mirror image of the above: shrinkage prevents an absolute zero.

    5 negative agents at confidence 0.8, all flagging wrong_metric:
      numerator = 5*0.8*0.0 + 0.5 = 0.5
      denominator = 5*0.8 + 1.0 = 5.0
      sentiment_score = 0.1
      any_flag_share = 1.0 → weakness_signal = 0.0
      score = 100 * (0.6*0.1 + 0.4*0) = 6.0
    """
    analyses = [
        _analysis(f"a{i}", Sentiment.NEGATIVE, categories=["wrong_metric"]) for i in range(5)
    ]
    result = ScoringService.aggregate(analyses, _FORMULA_CFG)
    assert result.confidence_score == 6.0
    assert result.weaknesses[0].category == "wrong_metric"


def test_aggregate_mixed_sentiment_neutral_baseline() -> None:
    """Symmetric pos/neutral/neg keeps the mean at 0.5 under shrinkage.

    3 agents (pos, neutral, neg), confidence 0.8, no weaknesses:
      numerator = 0.8*1.0 + 0.8*0.5 + 0.8*0.0 + 1.0*0.5 = 1.7
      denominator = 0.8*3 + 1.0 = 3.4
      sentiment_score = 0.5
      weakness_signal = 1.0
      score = 100 * (0.6*0.5 + 0.4*1.0) = 70.0
    """
    analyses = [
        _analysis("a", Sentiment.POSITIVE),
        _analysis("b", Sentiment.NEUTRAL),
        _analysis("c", Sentiment.NEGATIVE),
    ]
    result = ScoringService.aggregate(analyses, _FORMULA_CFG)
    assert result.confidence_score == 70.0


def test_aggregate_diffuse_weaknesses_penalize_score() -> None:
    """Codex P2 finding: 5 agents each flag a different category.

    OLD formula: max_category_share = 1/5 = 0.2 → score looked fine.
    NEW formula: any_flag_share = 5/5 = 1.0 → score collapses appropriately.

    5 positive agents, each flagging a different unique category:
      sentiment_score = (5*0.8*1.0 + 0.5) / 5.0 = 0.9
      any_flag_share = 1.0; weakness_signal = 0.0
      score = 100 * (0.6*0.9 + 0.4*0.0) = 54.0
    """
    cats = [
        "wrong_metric",
        "wrong_cohort",
        "broken_mechanism",
        "untestable_hypothesis",
        "hidden_guardrail_risk",
    ]
    analyses = [_analysis(f"a{i}", Sentiment.POSITIVE, categories=[c]) for i, c in enumerate(cats)]
    result = ScoringService.aggregate(analyses, _FORMULA_CFG)
    assert result.confidence_score == 54.0
    # Five distinct categories surfaced; top_k=3 caps the list
    assert len(result.weaknesses) == 3


def test_aggregate_dedupes_categories_within_an_agent() -> None:
    """Codex finding: a malformed LLM response with duplicate categories must
    not inflate the count above the agent's true contribution."""
    analyses = [
        _analysis("a", Sentiment.NEUTRAL, categories=["wrong_cohort", "wrong_cohort"]),
        _analysis("b", Sentiment.NEUTRAL, categories=["wrong_cohort"]),
    ]
    result = ScoringService.aggregate(analyses, _FORMULA_CFG)
    # 2/2 agents flagged wrong_cohort, not 3/2
    assert result.weaknesses[0].category == "wrong_cohort"
    assert "2/2 agents" in result.weaknesses[0].summary


def test_aggregate_sentiment_confidence_dampens_low_confidence_dissenter() -> None:
    """A low-confidence negative shouldn't swing as hard as a high-confidence one."""
    # 4 positive at confidence 0.9, 1 negative at confidence 0.1
    high_conf = [_analysis(f"a{i}", Sentiment.POSITIVE, confidence=0.9) for i in range(4)]
    low_conf_neg = [_analysis("b", Sentiment.NEGATIVE, confidence=0.1)]
    result_dampened = ScoringService.aggregate(high_conf + low_conf_neg, _FORMULA_CFG)

    # Same agents but with the negative at high confidence
    high_conf_neg = [_analysis("b", Sentiment.NEGATIVE, confidence=0.9)]
    result_full = ScoringService.aggregate(high_conf + high_conf_neg, _FORMULA_CFG)

    # The low-confidence dissenter should pull the score down LESS than the high-confidence one
    assert result_dampened.confidence_score > result_full.confidence_score


def test_aggregate_below_min_sample_size_surfaces_underpowered_design() -> None:
    """Codex P2 finding: N below threshold must surface the underpowered warning."""
    cfg = ScoringConfig(min_sample_size=3)
    analyses = [_analysis("a", Sentiment.POSITIVE), _analysis("b", Sentiment.POSITIVE)]
    result = ScoringService.aggregate(analyses, cfg)
    # Underpowered weakness is the top entry
    assert result.weaknesses[0].category == "underpowered_design"
    assert "Only 2 agents" in result.weaknesses[0].summary
    assert "provisional" in result.weaknesses[0].summary


def test_aggregate_at_min_sample_size_does_not_surface_underpowered() -> None:
    cfg = ScoringConfig(min_sample_size=3)
    analyses = [_analysis(f"a{i}", Sentiment.POSITIVE) for i in range(3)]
    result = ScoringService.aggregate(analyses, cfg)
    assert all(w.category != "underpowered_design" for w in result.weaknesses)


def test_aggregate_top_k_weaknesses_by_frequency() -> None:
    """top_k cap enforced. 4 categories surfaced — only top 3 returned."""
    analyses = (
        [_analysis(f"a{i}", Sentiment.NEUTRAL, categories=["wrong_metric"]) for i in range(4)]
        + [_analysis(f"b{i}", Sentiment.NEUTRAL, categories=["wrong_cohort"]) for i in range(3)]
        + [_analysis(f"c{i}", Sentiment.NEUTRAL, categories=["broken_mechanism"]) for i in range(2)]
        + [_analysis("d0", Sentiment.NEUTRAL, categories=["underpowered_design"])]
    )
    result = ScoringService.aggregate(analyses, _FORMULA_CFG)
    assert len(result.weaknesses) == 3
    assert [w.category for w in result.weaknesses] == [
        "wrong_metric",
        "wrong_cohort",
        "broken_mechanism",
    ]


def test_aggregate_supporting_agent_ids_capped_at_five() -> None:
    analyses = [
        _analysis(f"a{i}", Sentiment.NEUTRAL, categories=["wrong_cohort"]) for i in range(8)
    ]
    result = ScoringService.aggregate(analyses, _FORMULA_CFG)
    assert len(result.weaknesses[0].supporting_agent_ids) == 5


def test_aggregate_parity_snapshot() -> None:
    """Pins the `_compute_score()` extraction (T2 + /plan-eng-review C1).

    Fixed 6-agent input (3 positive @ conf 0.8, 2 neutral @ 0.5, 1 negative
    @ 0.9 with one `wrong_metric` flag). If the extraction silently shifts a
    constant or a shrinkage term, this snapshot fails before the rest of
    the suite can rationalize it.

    Snapshot value (71.8 rounded, 71.8238... raw) was captured against the
    pre-extraction implementation on `main` at 2026-05-22.
    """
    analyses = [
        _analysis("a1", Sentiment.POSITIVE, confidence=0.8),
        _analysis("a2", Sentiment.POSITIVE, confidence=0.8),
        _analysis("a3", Sentiment.POSITIVE, confidence=0.8),
        _analysis("a4", Sentiment.NEUTRAL, confidence=0.5),
        _analysis("a5", Sentiment.NEUTRAL, confidence=0.5),
        _analysis("a6", Sentiment.NEGATIVE, categories=["wrong_metric"], confidence=0.9),
    ]
    result = ScoringService.aggregate(analyses, _FORMULA_CFG)
    # Rounded score (display-facing)
    assert result.confidence_score == 71.8
    # Raw _compute_score values (pre-rounding) — pins both sub-statistics
    confidence_raw, sentiment_score, weakness_signal = ScoringService._compute_score(
        analyses, _FORMULA_CFG
    )
    assert confidence_raw == pytest.approx(71.82389937106919, abs=1e-9)
    assert sentiment_score == pytest.approx(0.6415094339622641, abs=1e-9)
    assert weakness_signal == pytest.approx(0.8333333333333334, abs=1e-9)
    # Weakness surface preserved
    assert [(w.category, len(w.supporting_agent_ids)) for w in result.weaknesses] == [
        ("wrong_metric", 1)
    ]


# ── Wilson CIs on weakness rows (T3) ──────────────────────────────────


def test_weakness_frequency_and_wilson_populated() -> None:
    """N=20 with 5 agents flagging `wrong_metric` → frequency=0.25 with a
    Wilson CI that brackets the point estimate inside [0, 1]."""
    flagged = [_analysis(f"f{i}", Sentiment.NEUTRAL, categories=["wrong_metric"]) for i in range(5)]
    clean = [_analysis(f"c{i}", Sentiment.NEUTRAL) for i in range(15)]
    result = ScoringService.aggregate(flagged + clean, _FORMULA_CFG)
    w = next(x for x in result.weaknesses if x.category == "wrong_metric")
    assert w.frequency == pytest.approx(0.25, abs=1e-9)
    assert w.ci_low is not None and w.ci_high is not None
    assert 0.0 <= w.ci_low < 0.25 < w.ci_high <= 1.0


def test_underpowered_gate_weakness_has_no_ci() -> None:
    """The prepended `underpowered_design` is a structural flag, not an
    observed frequency — frequency/ci_low/ci_high stay None."""
    cfg = ScoringConfig(min_sample_size=5)
    analyses = [_analysis(f"a{i}", Sentiment.NEUTRAL) for i in range(2)]
    result = ScoringService.aggregate(analyses, cfg)
    underpowered = result.weaknesses[0]
    assert underpowered.category == "underpowered_design"
    assert underpowered.frequency is None
    assert underpowered.ci_low is None
    assert underpowered.ci_high is None


def test_weakness_summary_shape_unchanged() -> None:
    """Existing summary text format ("X/N agents flagged this — …") must not
    drift — anything reading it as a string would break silently otherwise."""
    analyses = [
        _analysis(f"a{i}", Sentiment.NEUTRAL, categories=["wrong_cohort"]) for i in range(3)
    ] + [_analysis(f"b{i}", Sentiment.NEUTRAL) for i in range(7)]
    result = ScoringService.aggregate(analyses, _FORMULA_CFG)
    w = next(x for x in result.weaknesses if x.category == "wrong_cohort")
    assert w.summary == "3/10 agents flagged this — wrong cohort."


def test_scoring_config_is_tunable_without_code_changes() -> None:
    """Sanity: changing weights changes the score predictably."""
    analyses = [_analysis(f"a{i}", Sentiment.POSITIVE) for i in range(5)]
    cfg_heavy_sentiment = ScoringConfig(
        sentiment_weight=1.0, weakness_weight=0.0, min_sample_size=1
    )
    cfg_heavy_weakness = ScoringConfig(sentiment_weight=0.0, weakness_weight=1.0, min_sample_size=1)
    r_sent = ScoringService.aggregate(analyses, cfg_heavy_sentiment)
    r_weak = ScoringService.aggregate(analyses, cfg_heavy_weakness)
    # heavy-sentiment: 100 * sentiment_score = 100 * 0.9 = 90
    assert r_sent.confidence_score == 90.0
    # heavy-weakness: 100 * weakness_signal = 100 * 1.0 = 100
    assert r_weak.confidence_score == 100.0


# ── Bootstrap CI on confidence_score (T4) ─────────────────────────────


# Bootstrap-enabled config: small B keeps tests fast while still exercising
# the percentile path.
_BOOT_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=200)


def test_confidence_ci_is_set_and_brackets_point_estimate() -> None:
    """N=20 with a mix of sentiments + flags → CI populated, brackets the
    point estimate."""
    analyses = (
        [_analysis(f"p{i}", Sentiment.POSITIVE) for i in range(10)]
        + [_analysis(f"n{i}", Sentiment.NEUTRAL) for i in range(5)]
        + [_analysis(f"x{i}", Sentiment.NEGATIVE, categories=["wrong_metric"]) for i in range(5)]
    )
    result = ScoringService.aggregate(analyses, _BOOT_CFG, run_seed=42)
    assert result.confidence_score_ci is not None
    ci_low, ci_high = result.confidence_score_ci
    assert ci_low <= result.confidence_score <= ci_high
    assert 0.0 <= ci_low <= ci_high <= 100.0


def test_confidence_ci_deterministic_with_run_seed() -> None:
    """Same analyses + same run_seed → byte-identical CI. Uses varied input
    so the CI has actual width to compare."""
    analyses = [_analysis(f"p{i}", Sentiment.POSITIVE) for i in range(10)] + [
        _analysis(f"n{i}", Sentiment.NEGATIVE, categories=["wrong_metric"]) for i in range(10)
    ]
    r1 = ScoringService.aggregate(analyses, _BOOT_CFG, run_seed=12345)
    r2 = ScoringService.aggregate(analyses, _BOOT_CFG, run_seed=12345)
    assert r1.confidence_score_ci == r2.confidence_score_ci
    # Also confirm it's a real interval, not a degenerate point
    assert r1.confidence_score_ci[1] > r1.confidence_score_ci[0]


def test_confidence_ci_changes_without_seed() -> None:
    """No run_seed → fresh entropy each call. Test 10 unseeded calls and
    assert at least 2 distinct CIs across the batch — robust to occasional
    rounded-tuple coincidence that the schema's `confidence_rounding<=2`
    cap makes possible on small binary inputs."""
    cfg = ScoringConfig(min_sample_size=1, bootstrap_resamples=1000, confidence_rounding=2)
    analyses = [_analysis(f"p{i}", Sentiment.POSITIVE) for i in range(10)] + [
        _analysis(f"n{i}", Sentiment.NEGATIVE, categories=["wrong_metric"]) for i in range(10)
    ]
    cis = {ScoringService.aggregate(analyses, cfg).confidence_score_ci for _ in range(10)}
    assert len(cis) >= 2, f"unseeded bootstrap should vary, got only {cis!r}"


def test_n50_ci_narrower_than_n6() -> None:
    """The calibration promise as an aggregate-level test: 50 agents with the
    same sentiment/weakness mix produces a strictly narrower CI than 6."""

    # 50% positive, 50% negative-with-weakness — same mix at both sizes
    def make(n: int) -> list:
        half = n // 2
        return [_analysis(f"p{i}", Sentiment.POSITIVE) for i in range(half)] + [
            _analysis(f"n{i}", Sentiment.NEGATIVE, categories=["wrong_metric"])
            for i in range(n - half)
        ]

    big = ScoringService.aggregate(make(50), _BOOT_CFG, run_seed=7)
    small = ScoringService.aggregate(make(6), _BOOT_CFG, run_seed=7)
    assert big.confidence_score_ci is not None
    assert small.confidence_score_ci is not None
    width_big = big.confidence_score_ci[1] - big.confidence_score_ci[0]
    width_small = small.confidence_score_ci[1] - small.confidence_score_ci[0]
    assert width_big < width_small


def test_confidence_ci_always_brackets_rounded_point_estimate() -> None:
    """Codex P2 (round-2): independent rounding of point estimate vs CI bounds
    can violate ci_low <= confidence_score <= ci_high at the edges. The clamp
    in aggregate() must guarantee the invariant for every input.

    Sweep 12 varied compositions to surface the edge case where a raw
    percentile bound sits within one rounding step of the raw point estimate."""
    cfg = ScoringConfig(min_sample_size=1, bootstrap_resamples=500)
    compositions = [
        # (n_pos, n_neg_with_flag, n_neutral, run_seed)
        (10, 0, 0, 1),
        (0, 10, 0, 2),
        (5, 5, 0, 3),
        (3, 3, 4, 4),
        (1, 9, 0, 5),
        (9, 1, 0, 6),
        (2, 2, 6, 7),
        (8, 1, 1, 8),
        (1, 8, 1, 9),
        (4, 4, 2, 10),
        (6, 3, 1, 11),
        (3, 6, 1, 12),
    ]
    for n_pos, n_neg, n_neutral, seed in compositions:
        analyses = (
            [_analysis(f"p{i}", Sentiment.POSITIVE) for i in range(n_pos)]
            + [
                _analysis(f"n{i}", Sentiment.NEGATIVE, categories=["wrong_metric"])
                for i in range(n_neg)
            ]
            + [_analysis(f"x{i}", Sentiment.NEUTRAL) for i in range(n_neutral)]
        )
        result = ScoringService.aggregate(analyses, cfg, run_seed=seed)
        assert result.confidence_score_ci is not None
        lo, hi = result.confidence_score_ci
        assert lo <= result.confidence_score <= hi, (
            f"CI {(lo, hi)} fails to bracket score {result.confidence_score} for "
            f"composition n_pos={n_pos} n_neg={n_neg} n_neutral={n_neutral}"
        )


# ── Degradation guard (#8) ────────────────────────────────────────────


# Bootstrap-off config so we can read aggregate scores deterministically
# without paying B × O(n) per assertion.
_DEGRADE_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=0)


def _failed_analysis(agent_id: str) -> AgentAnalysis:
    """An agent whose BOTH classifications fell back — what `analyze()` returns
    when both LLM calls raise."""
    return _analysis(
        agent_id,
        Sentiment.NEUTRAL,
        confidence=0.0,
        weakness_failed=True,
        sentiment_failed=True,
    )


def test_aggregate_all_failed_degrades_score_and_prepends_warning() -> None:
    """All-failed run: every classification fell back to neutral. Without the
    guard, score would be ~70 (neutral × shrinkage, no flags). With the
    guard, score must be <50 and an underpowered_design weakness must appear
    flagging the classification failure rate."""
    analyses = [_failed_analysis(f"a{i}") for i in range(10)]
    result = ScoringService.aggregate(analyses, _DEGRADE_CFG)
    assert result.confidence_score < 50.0
    # First weakness explains the degradation (not the low-N gate — N=10>1)
    assert result.weaknesses[0].category == "underpowered_design"
    assert "100% of LLM classifications failed" in result.weaknesses[0].summary
    assert "20/20" in result.weaknesses[0].summary


def test_aggregate_30_percent_failures_does_not_degrade() -> None:
    """30% failure rate is below the 50% threshold — score must be untouched.

    10 agents × 2 classifications = 20 total. 6 failed = 30%. Mix of pos/neg
    among the successful ones to keep the score recognizable."""
    successful = [_analysis(f"p{i}", Sentiment.POSITIVE) for i in range(5)] + [
        _analysis(f"n{i}", Sentiment.NEGATIVE, categories=["wrong_metric"]) for i in range(2)
    ]
    # 3 fully-failed agents = 6 failed classifications out of 20 = 30%
    failed = [_failed_analysis(f"f{i}") for i in range(3)]
    baseline = ScoringService.aggregate(successful + failed, _DEGRADE_CFG)
    # Same input but with the failure flags cleared — confirms degradation
    # gate is the ONLY difference, not some side-effect of the neutral fallbacks.
    no_flags = successful + [
        _analysis(f"f{i}", Sentiment.NEUTRAL, confidence=0.0) for i in range(3)
    ]
    control = ScoringService.aggregate(no_flags, _DEGRADE_CFG)
    assert baseline.confidence_score == control.confidence_score
    # And no degradation row prepended
    assert not any("LLM classifications failed" in w.summary for w in baseline.weaknesses)


def test_aggregate_at_exactly_50_percent_does_not_degrade() -> None:
    """Boundary: ticket says `> 0.5` not `>= 0.5`. Exactly 50% must NOT trigger.

    10 agents × 2 classifications = 20. 10 failed = exactly 50%."""
    successful = [_analysis(f"s{i}", Sentiment.POSITIVE) for i in range(5)]
    failed = [_failed_analysis(f"f{i}") for i in range(5)]
    result = ScoringService.aggregate(successful + failed, _DEGRADE_CFG)
    assert not any("LLM classifications failed" in w.summary for w in result.weaknesses)


def test_aggregate_just_above_50_percent_does_degrade() -> None:
    """Boundary: 11/20 = 55% > 50% must trigger.

    Composition: 10 agents (20 classifications total). 5 fully-failed
    (10 failed) + 1 sentiment-only-failed (1 failed) + 4 healthy
    = 11 failed of 20 = 55%."""
    healthy = [_analysis(f"h{i}", Sentiment.POSITIVE) for i in range(4)]
    sentiment_only_failed = [
        _analysis(
            "half",
            Sentiment.NEUTRAL,
            confidence=0.0,
            sentiment_failed=True,
        )
    ]
    fully_failed = [_failed_analysis(f"f{i}") for i in range(5)]
    analyses = healthy + sentiment_only_failed + fully_failed
    assert len(analyses) == 10  # sanity: agent count
    total_failed = sum(int(a.weakness_failed) + int(a.sentiment_failed) for a in analyses)
    assert total_failed == 11
    assert 2 * len(analyses) == 20
    assert total_failed / 20 > 0.5  # sanity: we crossed the threshold
    result = ScoringService.aggregate(analyses, _DEGRADE_CFG)
    assert result.weaknesses[0].category == "underpowered_design"
    assert "LLM classifications failed" in result.weaknesses[0].summary
    assert "11/20" in result.weaknesses[0].summary


def test_aggregate_both_gates_collapse_to_single_underpowered_row() -> None:
    """Codex P2: when both the low-N gate and the degradation gate fire,
    they share the `underpowered_design` category — API consumers that
    dedupe by category would see two duplicate-looking rows. Collapse
    into one row with both root causes joined by AND."""
    cfg = ScoringConfig(min_sample_size=5, bootstrap_resamples=0)
    # 2 agents (< min_sample_size=5) AND both fully failed (100% > 50%)
    analyses = [_failed_analysis("a1"), _failed_analysis("a2")]
    result = ScoringService.aggregate(analyses, cfg)
    underpowered_rows = [w for w in result.weaknesses if w.category == "underpowered_design"]
    assert len(underpowered_rows) == 1, (
        f"expected one merged row when both gates fire, got "
        f"{len(underpowered_rows)}: {[w.summary for w in underpowered_rows]}"
    )
    # Pin BEHAVIOR (both root causes mentioned), not the delimiter — copy
    # edits should be able to swap " AND " for "; " without breaking tests.
    summary = underpowered_rows[0].summary
    assert "Only 2 agents" in summary
    assert "100% of LLM classifications failed" in summary


def test_aggregate_degradation_discounts_bootstrap_ci_too() -> None:
    """When the guard fires, the bootstrap CI must shift down with the
    point estimate — otherwise the CI would bracket the raw score, not the
    displayed (discounted) one. Pin the invariant against the no-degradation
    path."""
    cfg = ScoringConfig(min_sample_size=1, bootstrap_resamples=200)
    # 10 failed agents → 100% failure → discount = 0.3 → score * 0.7
    failed = [_failed_analysis(f"a{i}") for i in range(10)]
    degraded = ScoringService.aggregate(failed, cfg, run_seed=42)
    # Same shape but flags cleared → no degradation, CI unaffected
    flags_off = [_analysis(f"a{i}", Sentiment.NEUTRAL, confidence=0.0) for i in range(10)]
    healthy = ScoringService.aggregate(flags_off, cfg, run_seed=42)
    # Score discounted by 30%
    assert degraded.confidence_score == pytest.approx(healthy.confidence_score * 0.7, abs=0.5)
    # CI bounds shifted in the same direction
    assert degraded.confidence_score_ci is not None
    assert healthy.confidence_score_ci is not None
    assert degraded.confidence_score_ci[0] <= healthy.confidence_score_ci[0]
    assert degraded.confidence_score_ci[1] <= healthy.confidence_score_ci[1]
    # And the bracket invariant still holds after the discount
    assert (
        degraded.confidence_score_ci[0]
        <= degraded.confidence_score
        <= degraded.confidence_score_ci[1]
    )


def test_aggregate_with_bootstrap_resamples_0_leaves_ci_none() -> None:
    """C3 (locked from /plan-eng-review): bootstrap_resamples=0 is a sentinel
    that skips the bootstrap entirely and leaves confidence_score_ci=None."""
    analyses = [_analysis(f"a{i}", Sentiment.POSITIVE) for i in range(10)]
    cfg = ScoringConfig(min_sample_size=1, bootstrap_resamples=0)
    result = ScoringService.aggregate(analyses, cfg, run_seed=42)
    assert result.confidence_score_ci is None


# ── Hallucinated category guard ───────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_drops_hallucinated_categories() -> None:
    """An LLM that returns a category outside the closed set should be filtered."""

    class _Hallucinator:
        def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
            if schema is WeaknessClassification:
                return WeaknessClassification(
                    categories=["wrong_cohort", "this_is_made_up"],
                    primary_reason="halluc",
                )
            return SentimentClassification(
                sentiment=Sentiment.POSITIVE, confidence=0.7, one_line_summary=""
            )

        def chat(self, *a, **k):  # pragma: no cover
            raise NotImplementedError

    svc = ScoringService(chat_client=_Hallucinator())
    analysis = await svc.analyze(
        Hypothesis(capability_name="reorder", prose="test"),
        AgentReaction(agent_id="a", persona_id="p", persona_name="P", reaction_text="r"),
    )
    assert analysis.weakness.categories == ["wrong_cohort"]
    assert "this_is_made_up" not in analysis.weakness.categories


# ── Classification-failure WARN visibility (#70) ──────────────────────


@pytest.mark.asyncio
async def test_analyze_warns_on_weakness_classification_failure() -> None:
    """#70: when the weakness classification raises, analyze() must emit a
    structlog WARN with the agent context AND fall back to a neutral
    classification. Without this test the WARN previously went to a
    handler-less stdlib logger and was silently dropped."""
    import structlog

    class _WeaknessRaiser:
        def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
            if schema is WeaknessClassification:
                raise RuntimeError("simulated upstream LLM failure")
            return SentimentClassification(
                sentiment=Sentiment.POSITIVE, confidence=0.7, one_line_summary=""
            )

        def chat(self, *a, **k):  # pragma: no cover
            raise NotImplementedError

    svc = ScoringService(chat_client=_WeaknessRaiser())
    with structlog.testing.capture_logs() as captured:
        analysis = await svc.analyze(
            Hypothesis(capability_name="reorder", prose="test"),
            AgentReaction(
                agent_id="agent-123", persona_id="p", persona_name="P", reaction_text="r"
            ),
        )
    # Fallback path
    assert analysis.weakness_failed is True
    assert analysis.weakness.categories == []
    assert analysis.sentiment_failed is False
    # WARN was emitted with the full structured context. Exact event-name
    # equality + all four kwargs pinned (codex P2: substring + partial-kwargs
    # let a future regression drop fields silently).
    warn_events = [
        e
        for e in captured
        if e.get("log_level") == "warning"
        and e.get("event") == "scoring.weakness_classification_failed"
    ]
    assert len(warn_events) == 1, f"expected 1 weakness-failure WARN, got {warn_events!r}"
    ev = warn_events[0]
    assert ev["agent_id"] == "agent-123"
    assert ev["persona_id"] == "p"
    assert "simulated upstream LLM failure" in ev["error"]
    assert ev["exc_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_analyze_warns_on_sentiment_classification_failure() -> None:
    """#70 mirror: sentiment-classification failure also emits a structlog WARN."""
    import structlog

    class _SentimentRaiser:
        def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
            if schema is SentimentClassification:
                raise RuntimeError("simulated sentiment failure")
            return WeaknessClassification(categories=[], primary_reason="")

        def chat(self, *a, **k):  # pragma: no cover
            raise NotImplementedError

    svc = ScoringService(chat_client=_SentimentRaiser())
    with structlog.testing.capture_logs() as captured:
        analysis = await svc.analyze(
            Hypothesis(capability_name="reorder", prose="test"),
            AgentReaction(
                agent_id="agent-xyz", persona_id="p", persona_name="P", reaction_text="r"
            ),
        )
    assert analysis.sentiment_failed is True
    assert analysis.sentiment.sentiment is Sentiment.NEUTRAL
    assert analysis.sentiment.confidence == 0.0
    assert analysis.weakness_failed is False
    # Same tightening as the weakness test: exact event-name + all four kwargs.
    warn_events = [
        e
        for e in captured
        if e.get("log_level") == "warning"
        and e.get("event") == "scoring.sentiment_classification_failed"
    ]
    assert len(warn_events) == 1, f"expected 1 sentiment-failure WARN, got {warn_events!r}"
    ev = warn_events[0]
    assert ev["agent_id"] == "agent-xyz"
    assert ev["persona_id"] == "p"
    assert "simulated sentiment failure" in ev["error"]
    assert ev["exc_type"] == "RuntimeError"


# ── Score + degenerate cases ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_score_with_no_reactions_returns_underpowered_design() -> None:
    svc = ScoringService(chat_client=object())  # won't be called
    result, analyses = await svc.score(
        Hypothesis(capability_name="reorder", prose="test"),
        reactions=[],
    )
    assert result.confidence_score == 0.0
    assert result.weaknesses[0].category == "underpowered_design"
    assert analyses == []
