"""Scoring service tests.

`aggregate()` is a pure function — test the locked 0.6/0.4 formula directly.
`analyze()` + `score()` are LLM-driven — test with a stub.
"""

from __future__ import annotations

import pytest

from pythia_simulator.schemas.scoring import (
    AgentAnalysis,
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
    persona_id: str = "p",
    persona_name: str = "P",
) -> AgentAnalysis:
    return AgentAnalysis(
        agent_id=agent_id,
        persona_id=persona_id,
        persona_name=persona_name,
        weakness=WeaknessClassification(categories=categories or []),
        sentiment=SentimentClassification(sentiment=sentiment, confidence=0.8, one_line_summary=""),
    )


# ── Aggregation formula ───────────────────────────────────────────────


def test_aggregate_zero_agents_returns_zero_confidence() -> None:
    result = ScoringService.aggregate([])
    assert result.confidence_score == 0.0
    assert result.weaknesses == []


def test_aggregate_all_positive_no_weaknesses_caps_at_100() -> None:
    analyses = [_analysis(f"a{i}", Sentiment.POSITIVE) for i in range(5)]
    result = ScoringService.aggregate(analyses)
    # sentiment = 1.0, concentration = 0.0 → 0.6 + 0.4 = 1.0 → 100
    assert result.confidence_score == 100.0
    assert result.weaknesses == []


def test_aggregate_all_negative_with_unanimous_weakness_floors_at_zero() -> None:
    analyses = [
        _analysis(f"a{i}", Sentiment.NEGATIVE, categories=["wrong_metric"]) for i in range(5)
    ]
    result = ScoringService.aggregate(analyses)
    # sentiment = 0.0, concentration = 1.0 → 0.0 + 0.0 = 0.0
    assert result.confidence_score == 0.0
    assert len(result.weaknesses) == 1
    assert result.weaknesses[0].category == "wrong_metric"


def test_aggregate_mixed_sentiment_neutral_baseline() -> None:
    analyses = [
        _analysis("a", Sentiment.POSITIVE),
        _analysis("b", Sentiment.NEUTRAL),
        _analysis("c", Sentiment.NEGATIVE),
    ]
    result = ScoringService.aggregate(analyses)
    # sentiment = (1 + 0.5 + 0) / 3 = 0.5, concentration = 0.0 → 0.3 + 0.4 = 0.7 → 70
    assert result.confidence_score == 70.0


def test_aggregate_concentration_uses_max_category_share() -> None:
    """5 agents: 4 flag wrong_cohort, 1 flags wrong_metric.
    Concentration = max(4/5, 1/5) = 0.8."""
    analyses = [
        _analysis("a", Sentiment.POSITIVE, categories=["wrong_cohort"]),
        _analysis("b", Sentiment.POSITIVE, categories=["wrong_cohort"]),
        _analysis("c", Sentiment.POSITIVE, categories=["wrong_cohort"]),
        _analysis("d", Sentiment.POSITIVE, categories=["wrong_cohort"]),
        _analysis("e", Sentiment.POSITIVE, categories=["wrong_metric"]),
    ]
    result = ScoringService.aggregate(analyses)
    # sentiment = 1.0, concentration = 0.8 → 0.6 + 0.4 * 0.2 = 0.68 → 68.0
    assert result.confidence_score == 68.0
    # wrong_cohort is the top weakness
    assert result.weaknesses[0].category == "wrong_cohort"


def test_aggregate_top_3_weaknesses_by_frequency() -> None:
    """6 categories surfaced — only top 3 returned."""
    analyses = [
        _analysis(f"a{i}", Sentiment.NEUTRAL, categories=["wrong_metric"]) for i in range(4)
    ] + [
        _analysis(f"b{i}", Sentiment.NEUTRAL, categories=["wrong_cohort"]) for i in range(3)
    ] + [
        _analysis(f"c{i}", Sentiment.NEUTRAL, categories=["broken_mechanism"]) for i in range(2)
    ] + [
        _analysis(f"d{i}", Sentiment.NEUTRAL, categories=["underpowered_design"]) for i in range(1)
    ]
    result = ScoringService.aggregate(analyses)
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
    result = ScoringService.aggregate(analyses)
    assert len(result.weaknesses[0].supporting_agent_ids) == 5


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
