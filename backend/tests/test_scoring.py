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

from pythia_simulator.schemas.scoring import (
    AgentAnalysis,
    ScoringConfig,
    Sentiment,
    SentimentClassification,
    WeaknessClassification,
)
from pythia_simulator.schemas.simulation import Hypothesis
from pythia_simulator.services.scoring import AgentReaction, ScoringService


def _analysis(
    agent_id: str,
    sentiment: Sentiment,
    categories: list[str] | None = None,
    confidence: float = 0.8,
    persona_id: str = "p",
    persona_name: str = "P",
) -> AgentAnalysis:
    return AgentAnalysis(
        agent_id=agent_id,
        persona_id=persona_id,
        persona_name=persona_name,
        weakness=WeaknessClassification(categories=categories or []),
        sentiment=SentimentClassification(
            sentiment=sentiment, confidence=confidence, one_line_summary=""
        ),
    )


# Disable the underpowered gate for formula-focused tests so we read the raw
# behavior. min_sample_size=1 means the gate never fires for N≥1.
_FORMULA_CFG = ScoringConfig(min_sample_size=1)


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


def test_scoring_config_is_tunable_without_code_changes() -> None:
    """Sanity: changing weights changes the score predictably."""
    analyses = [_analysis(f"a{i}", Sentiment.POSITIVE) for i in range(5)]
    cfg_heavy_sentiment = ScoringConfig(sentiment_weight=1.0, weakness_weight=0.0, min_sample_size=1)
    cfg_heavy_weakness = ScoringConfig(sentiment_weight=0.0, weakness_weight=1.0, min_sample_size=1)
    r_sent = ScoringService.aggregate(analyses, cfg_heavy_sentiment)
    r_weak = ScoringService.aggregate(analyses, cfg_heavy_weakness)
    # heavy-sentiment: 100 * sentiment_score = 100 * 0.9 = 90
    assert r_sent.confidence_score == 90.0
    # heavy-weakness: 100 * weakness_signal = 100 * 1.0 = 100
    assert r_weak.confidence_score == 100.0


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
