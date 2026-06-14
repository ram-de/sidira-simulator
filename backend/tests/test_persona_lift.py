"""Tests for `services.scoring.aggregate_persona_lift` — #221 §4.1 persona-lift.

The persona-lift baseline pairs the persona arm against a no-persona shadow
panel (the base LLM with persona conditioning stripped) and reports
`persona_lift = persona − no_persona` sentiment delta. It reuses the SAME
matched-pair bootstrap (`_paired_lift`) as the A/B aggregator, so the formula
and CI-bracketing guarantees carry over; these tests pin the persona-specific
contract:

- sign convention (persona − no_persona),
- the standalone no-persona SimulationResult is returned,
- a CI that straddles zero is the falsification signal,
- the drop counters map onto persona / no_persona,
- extraction parity: `aggregate_ab`'s lift block is byte-equivalent to the
  shared `_paired_lift` helper.
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.scoring import (
    ABLiftResult,
    AgentAnalysis,
    ScoringConfig,
    Sentiment,
    SentimentClassification,
    WeaknessClassification,
)
from sidira_simulator.schemas.simulation import SimulationResult
from sidira_simulator.services.scoring import (
    aggregate_ab,
    aggregate_persona_lift,
)


def _a(
    *,
    agent_id: str,
    persona_id: str,
    sample_index: int,
    sentiment: Sentiment,
    confidence: float = 1.0,
    sentiment_failed: bool = False,
) -> AgentAnalysis:
    return AgentAnalysis(
        agent_id=agent_id,
        persona_id=persona_id,
        persona_name=persona_id,
        sample_index=sample_index,
        weakness=WeaknessClassification(categories=[]),
        sentiment=SentimentClassification(
            sentiment=sentiment, confidence=confidence, one_line_summary=""
        ),
        sentiment_failed=sentiment_failed,
    )


def _matched(
    n: int,
    *,
    persona_sentiment: Sentiment,
    no_persona_sentiment: Sentiment,
    confidence: float = 1.0,
) -> tuple[list[AgentAnalysis], list[AgentAnalysis]]:
    persona = [
        _a(
            agent_id=f"pa{i}",
            persona_id=f"p{i}",
            sample_index=0,
            sentiment=persona_sentiment,
            confidence=confidence,
        )
        for i in range(n)
    ]
    no_persona = [
        _a(
            agent_id=f"np{i}",
            persona_id=f"p{i}",
            sample_index=0,
            sentiment=no_persona_sentiment,
            confidence=confidence,
        )
        for i in range(n)
    ]
    return persona, no_persona


_NO_CI_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=0)
_CI_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=500)


def test_returns_no_persona_result_and_lift() -> None:
    persona, no_persona = _matched(
        6, persona_sentiment=Sentiment.NEUTRAL, no_persona_sentiment=Sentiment.NEUTRAL
    )
    no_persona_result, lift = aggregate_persona_lift(persona, no_persona, _CI_CFG, run_seed=42)
    assert isinstance(no_persona_result, SimulationResult)
    assert isinstance(lift, ABLiftResult)
    assert lift.paired_n == 6
    assert lift.lift == pytest.approx(0.0, abs=1e-6)


def test_positive_lift_means_personas_add_optimism() -> None:
    """persona positive vs no_persona negative → positive lift (persona − base)."""
    persona, no_persona = _matched(
        8, persona_sentiment=Sentiment.POSITIVE, no_persona_sentiment=Sentiment.NEGATIVE
    )
    _np_result, lift = aggregate_persona_lift(persona, no_persona, _CI_CFG, run_seed=42)
    assert lift.lift is not None and lift.lift > 0
    assert lift.lift_ci is not None
    # CI excludes zero → personas genuinely move the needle.
    assert lift.lift_ci[0] > 0


def test_negative_lift_means_personas_dampen() -> None:
    persona, no_persona = _matched(
        8, persona_sentiment=Sentiment.NEGATIVE, no_persona_sentiment=Sentiment.POSITIVE
    )
    _np_result, lift = aggregate_persona_lift(persona, no_persona, _CI_CFG, run_seed=42)
    assert lift.lift is not None and lift.lift < 0
    assert lift.lift_ci is not None and lift.lift_ci[1] < 0


def test_funhouse_mirror_ci_straddles_zero_when_arms_agree() -> None:
    """The falsification signal: when persona and no-persona react identically,
    the lift is ~0 and its CI brackets zero — the personas add no signal over
    the base model."""
    persona, no_persona = _matched(
        10, persona_sentiment=Sentiment.POSITIVE, no_persona_sentiment=Sentiment.POSITIVE
    )
    _np_result, lift = aggregate_persona_lift(persona, no_persona, _CI_CFG, run_seed=42)
    assert lift.lift == pytest.approx(0.0, abs=1e-6)
    assert lift.lift_ci is not None
    assert lift.lift_ci[0] <= 0.0 <= lift.lift_ci[1]


def test_no_persona_score_reflects_no_persona_arm() -> None:
    """The returned SimulationResult is the no-persona arm's own score, not the
    persona arm's — so the route can show base-LLM sentiment next to persona."""
    # All no-persona negative → low no_persona_score.
    persona, no_persona = _matched(
        5, persona_sentiment=Sentiment.POSITIVE, no_persona_sentiment=Sentiment.NEGATIVE
    )
    no_persona_result, _lift = aggregate_persona_lift(persona, no_persona, _CI_CFG, run_seed=42)
    # A no-persona arm that's uniformly negative should score well below neutral.
    assert no_persona_result.confidence_score < 50.0


def test_drop_counters_map_to_persona_and_no_persona() -> None:
    """Unpaired persona agents (no matching shadow) and unpaired shadows surface
    via the _paired_lift treatment/control counters, which the runner maps onto
    persona / no_persona."""
    persona = [
        _a(agent_id="pa0", persona_id="p0", sample_index=0, sentiment=Sentiment.POSITIVE),
        _a(agent_id="pa1", persona_id="p1", sample_index=0, sentiment=Sentiment.POSITIVE),
        # extra persona agent with no shadow
        _a(agent_id="pa2", persona_id="p2", sample_index=0, sentiment=Sentiment.POSITIVE),
    ]
    no_persona = [
        _a(agent_id="np0", persona_id="p0", sample_index=0, sentiment=Sentiment.NEUTRAL),
        _a(agent_id="np1", persona_id="p1", sample_index=0, sentiment=Sentiment.NEUTRAL),
        # extra shadow with no persona twin
        _a(agent_id="np9", persona_id="p9", sample_index=0, sentiment=Sentiment.NEUTRAL),
    ]
    _np_result, lift = aggregate_persona_lift(persona, no_persona, _NO_CI_CFG, run_seed=42)
    assert lift.paired_n == 2
    # treatment-side unpaired == persona-side unpaired (p2)
    assert lift.unpaired_treatment == 1
    # control-side unpaired == no_persona-side unpaired (p9)
    assert lift.unpaired_control == 1


def test_sentiment_failure_drops_excluded_from_pairing() -> None:
    persona = [
        _a(agent_id="pa0", persona_id="p0", sample_index=0, sentiment=Sentiment.POSITIVE),
        _a(
            agent_id="pa1",
            persona_id="p1",
            sample_index=0,
            sentiment=Sentiment.NEUTRAL,
            sentiment_failed=True,
        ),
    ]
    no_persona = [
        _a(agent_id="np0", persona_id="p0", sample_index=0, sentiment=Sentiment.NEUTRAL),
        _a(agent_id="np1", persona_id="p1", sample_index=0, sentiment=Sentiment.NEUTRAL),
    ]
    _np_result, lift = aggregate_persona_lift(persona, no_persona, _NO_CI_CFG, run_seed=42)
    assert lift.paired_n == 1
    assert lift.sentiment_failure_drops == 1


def test_zero_usable_pairs_returns_none_lift() -> None:
    persona = [
        _a(agent_id="pa0", persona_id="p0", sample_index=0, sentiment=Sentiment.POSITIVE),
    ]
    no_persona = [
        _a(agent_id="np9", persona_id="p9", sample_index=0, sentiment=Sentiment.NEUTRAL),
    ]
    _np_result, lift = aggregate_persona_lift(persona, no_persona, _CI_CFG, run_seed=42)
    assert lift.paired_n == 0
    assert lift.lift is None
    assert lift.lift_ci is None


def test_deterministic_with_run_seed() -> None:
    persona, no_persona = _matched(
        6, persona_sentiment=Sentiment.POSITIVE, no_persona_sentiment=Sentiment.NEUTRAL
    )
    _r1, lift1 = aggregate_persona_lift(persona, no_persona, _CI_CFG, run_seed=7)
    _r2, lift2 = aggregate_persona_lift(persona, no_persona, _CI_CFG, run_seed=7)
    assert lift1.lift == lift2.lift
    assert lift1.lift_ci == lift2.lift_ci


def test_paired_lift_extraction_matches_aggregate_ab() -> None:
    """Refactor-safety: `aggregate_ab`'s lift output must be byte-identical to
    the persona-lift's `_paired_lift` core for the same analyses + seed, proving
    the extraction didn't change A/B behavior."""
    persona, no_persona = _matched(
        9, persona_sentiment=Sentiment.POSITIVE, no_persona_sentiment=Sentiment.NEGATIVE
    )
    _t, _c, ab_lift = aggregate_ab(persona, no_persona, _CI_CFG, run_seed=123)
    _np_result, persona_lift = aggregate_persona_lift(persona, no_persona, _CI_CFG, run_seed=123)
    assert ab_lift.lift == persona_lift.lift
    assert ab_lift.lift_ci == persona_lift.lift_ci
    assert ab_lift.paired_n == persona_lift.paired_n
