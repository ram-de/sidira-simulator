"""Tests for `services.scoring.aggregate_current_state_delta` — #221 §3.3.1 delta-mode.

The delta-mode baseline pairs the proposed-change arm (the headline single-arm
panel) against a current-state shadow panel (the SAME personas reacting to the
product as it works TODAY — the existing A/B control framing applied 1:1) and
reports `current_state_delta = treatment − current_state` sentiment delta. It
reuses the SAME matched-pair bootstrap (`_paired_lift`) as the A/B aggregator
and the persona-lift baseline, so the formula and CI-bracketing guarantees carry
over; these tests pin the delta-specific contract:

- sign convention (treatment − current_state),
- the standalone current-state SimulationResult is returned,
- a CI that straddles zero is the falsification signal (the change moves no
  sentiment over the status quo),
- the drop counters map onto persona / current_state,
- byte-equivalence with the shared `_paired_lift` core (via aggregate_ab).
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
    aggregate_current_state_delta,
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
    treatment_sentiment: Sentiment,
    current_state_sentiment: Sentiment,
    confidence: float = 1.0,
) -> tuple[list[AgentAnalysis], list[AgentAnalysis]]:
    treatment = [
        _a(
            agent_id=f"tx{i}",
            persona_id=f"p{i}",
            sample_index=0,
            sentiment=treatment_sentiment,
            confidence=confidence,
        )
        for i in range(n)
    ]
    current_state = [
        _a(
            agent_id=f"cs{i}",
            persona_id=f"p{i}",
            sample_index=0,
            sentiment=current_state_sentiment,
            confidence=confidence,
        )
        for i in range(n)
    ]
    return treatment, current_state


_NO_CI_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=0)
_CI_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=500)


def test_returns_current_state_result_and_delta() -> None:
    treatment, current_state = _matched(
        6, treatment_sentiment=Sentiment.NEUTRAL, current_state_sentiment=Sentiment.NEUTRAL
    )
    cs_result, delta = aggregate_current_state_delta(treatment, current_state, _CI_CFG, run_seed=42)
    assert isinstance(cs_result, SimulationResult)
    assert isinstance(delta, ABLiftResult)
    assert delta.paired_n == 6
    assert delta.lift == pytest.approx(0.0, abs=1e-6)


def test_positive_delta_means_change_improves_on_status_quo() -> None:
    """treatment positive vs current_state negative → positive delta
    (treatment − current_state)."""
    treatment, current_state = _matched(
        8, treatment_sentiment=Sentiment.POSITIVE, current_state_sentiment=Sentiment.NEGATIVE
    )
    _cs, delta = aggregate_current_state_delta(treatment, current_state, _CI_CFG, run_seed=42)
    assert delta.lift is not None and delta.lift > 0
    assert delta.lift_ci is not None
    # CI excludes zero → the change genuinely moves sentiment over the status quo.
    assert delta.lift_ci[0] > 0


def test_negative_delta_means_change_regresses() -> None:
    treatment, current_state = _matched(
        8, treatment_sentiment=Sentiment.NEGATIVE, current_state_sentiment=Sentiment.POSITIVE
    )
    _cs, delta = aggregate_current_state_delta(treatment, current_state, _CI_CFG, run_seed=42)
    assert delta.lift is not None and delta.lift < 0
    assert delta.lift_ci is not None and delta.lift_ci[1] < 0


def test_ci_straddles_zero_when_change_moves_nothing() -> None:
    """The falsification signal: when the proposed change and the current state
    are received identically, the delta is ~0 and its CI brackets zero — the
    change adds no sentiment over leaving the product as-is."""
    treatment, current_state = _matched(
        10, treatment_sentiment=Sentiment.POSITIVE, current_state_sentiment=Sentiment.POSITIVE
    )
    _cs, delta = aggregate_current_state_delta(treatment, current_state, _CI_CFG, run_seed=42)
    assert delta.lift == pytest.approx(0.0, abs=1e-6)
    assert delta.lift_ci is not None
    assert delta.lift_ci[0] <= 0.0 <= delta.lift_ci[1]


def test_current_state_score_reflects_current_state_arm() -> None:
    """The returned SimulationResult is the current-state arm's own score, not
    the headline arm's — so the route can show status-quo sentiment next to the
    proposed change."""
    # All current-state negative → low current_state_score.
    treatment, current_state = _matched(
        5, treatment_sentiment=Sentiment.POSITIVE, current_state_sentiment=Sentiment.NEGATIVE
    )
    cs_result, _delta = aggregate_current_state_delta(
        treatment, current_state, _CI_CFG, run_seed=42
    )
    # A current-state arm that's uniformly negative should score well below neutral.
    assert cs_result.confidence_score < 50.0


def test_drop_counters_map_to_persona_and_current_state() -> None:
    """Unpaired persona agents (no matching shadow) and unpaired shadows surface
    via the _paired_lift treatment/control counters, which the runner maps onto
    persona / current_state."""
    treatment = [
        _a(agent_id="tx0", persona_id="p0", sample_index=0, sentiment=Sentiment.POSITIVE),
        _a(agent_id="tx1", persona_id="p1", sample_index=0, sentiment=Sentiment.POSITIVE),
        # extra persona agent with no shadow
        _a(agent_id="tx2", persona_id="p2", sample_index=0, sentiment=Sentiment.POSITIVE),
    ]
    current_state = [
        _a(agent_id="cs0", persona_id="p0", sample_index=0, sentiment=Sentiment.NEUTRAL),
        _a(agent_id="cs1", persona_id="p1", sample_index=0, sentiment=Sentiment.NEUTRAL),
        # extra shadow with no persona twin
        _a(agent_id="cs9", persona_id="p9", sample_index=0, sentiment=Sentiment.NEUTRAL),
    ]
    _cs, delta = aggregate_current_state_delta(treatment, current_state, _NO_CI_CFG, run_seed=42)
    assert delta.paired_n == 2
    # treatment-side unpaired == persona-side unpaired (p2)
    assert delta.unpaired_treatment == 1
    # control-side unpaired == current_state-side unpaired (p9)
    assert delta.unpaired_control == 1


def test_sentiment_failure_drops_excluded_from_pairing() -> None:
    treatment = [
        _a(agent_id="tx0", persona_id="p0", sample_index=0, sentiment=Sentiment.POSITIVE),
        _a(
            agent_id="tx1",
            persona_id="p1",
            sample_index=0,
            sentiment=Sentiment.NEUTRAL,
            sentiment_failed=True,
        ),
    ]
    current_state = [
        _a(agent_id="cs0", persona_id="p0", sample_index=0, sentiment=Sentiment.NEUTRAL),
        _a(agent_id="cs1", persona_id="p1", sample_index=0, sentiment=Sentiment.NEUTRAL),
    ]
    _cs, delta = aggregate_current_state_delta(treatment, current_state, _NO_CI_CFG, run_seed=42)
    assert delta.paired_n == 1
    assert delta.sentiment_failure_drops == 1


def test_zero_usable_pairs_returns_none_delta() -> None:
    treatment = [
        _a(agent_id="tx0", persona_id="p0", sample_index=0, sentiment=Sentiment.POSITIVE),
    ]
    current_state = [
        _a(agent_id="cs9", persona_id="p9", sample_index=0, sentiment=Sentiment.NEUTRAL),
    ]
    _cs, delta = aggregate_current_state_delta(treatment, current_state, _CI_CFG, run_seed=42)
    assert delta.paired_n == 0
    assert delta.lift is None
    assert delta.lift_ci is None


def test_deterministic_with_run_seed() -> None:
    treatment, current_state = _matched(
        6, treatment_sentiment=Sentiment.POSITIVE, current_state_sentiment=Sentiment.NEUTRAL
    )
    _r1, delta1 = aggregate_current_state_delta(treatment, current_state, _CI_CFG, run_seed=7)
    _r2, delta2 = aggregate_current_state_delta(treatment, current_state, _CI_CFG, run_seed=7)
    assert delta1.lift == delta2.lift
    assert delta1.lift_ci == delta2.lift_ci


def test_paired_delta_extraction_matches_aggregate_ab() -> None:
    """Refactor-safety: `aggregate_ab`'s lift output must be byte-identical to
    the delta-mode `_paired_lift` core for the same analyses + seed, proving the
    delta-mode aggregator reuses the locked paired statistic unchanged."""
    treatment, current_state = _matched(
        9, treatment_sentiment=Sentiment.POSITIVE, current_state_sentiment=Sentiment.NEGATIVE
    )
    _t, _c, ab_lift = aggregate_ab(treatment, current_state, _CI_CFG, run_seed=123)
    _cs, delta = aggregate_current_state_delta(treatment, current_state, _CI_CFG, run_seed=123)
    assert ab_lift.lift == delta.lift
    assert ab_lift.lift_ci == delta.lift_ci
    assert ab_lift.paired_n == delta.paired_n
