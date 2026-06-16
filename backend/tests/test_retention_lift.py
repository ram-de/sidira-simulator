"""Tests for the §275 retention-lift aggregation + score_ab wiring (Decision B).

Mirrors test_conversion_lift.py for the retention metric, which rides the shared
`aggregate_metric_lift` core:
- `aggregate_retention_lift` paired-delta math (retention-rate pp), drop counters,
  CI brackets point, degenerate honesty,
- the retention `metric_lift_honesty` wording (retains higher/lower; native unit),
- `score_ab` grafting the GENERIC metric_* fields with metric_name="retention".
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.scoring import (
    MetricLiftResult,
    ScoringConfig,
    Sentiment,
    SentimentClassification,
    WeaknessClassification,
)
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.metric_elicitor_core import _MetricAllocation
from sidira_simulator.services.metric_registry import get_metric
from sidira_simulator.services.scoring import (
    AgentReaction,
    ScoringService,
    aggregate_retention_lift,
)

_NO_CI_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=0)
_CI_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=500)


def _r(
    *,
    persona_id,
    arm,
    metric_p,
    sample_index=0,
    metric_unblinded=False,
    metric_paraphrase_unstable=False,
):
    return AgentReaction(
        agent_id=f"{arm}-{persona_id}-{sample_index}",
        persona_id=persona_id,
        persona_name=persona_id,
        reaction_text="r",
        sample_index=sample_index,
        arm=arm,
        metric_p=metric_p,
        metric_unblinded=metric_unblinded,
        metric_paraphrase_unstable=metric_paraphrase_unstable,
    )


# ── aggregate_retention_lift ──────────────────────────────────────────────────


def test_positive_retention_lift_in_pp() -> None:
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.6) for i in range(4)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.4) for i in range(4)]
    res = aggregate_retention_lift(treatment, control, _CI_CFG, run_seed=42)
    assert isinstance(res, MetricLiftResult)
    assert res.paired_n == 4
    # (0.6 - 0.4) * 100 = 20.0 pp retention-rate lift
    assert res.lift_pp == pytest.approx(20.0)
    assert res.lift_ci_pp is not None
    assert res.lift_ci_pp[0] <= res.lift_pp <= res.lift_ci_pp[1]


def test_negative_retention_lift() -> None:
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.2) for i in range(3)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.5) for i in range(3)]
    res = aggregate_retention_lift(treatment, control, _NO_CI_CFG)
    assert res.lift_pp == pytest.approx(-30.0)


def test_elicitation_failure_drops_unpaired_and_failed() -> None:
    treatment = [
        _r(persona_id="p0", arm="treatment", metric_p=0.6),
        _r(persona_id="p1", arm="treatment", metric_p=None),  # failed
        _r(persona_id="p2", arm="treatment", metric_p=0.6),  # no control twin
    ]
    control = [
        _r(persona_id="p0", arm="control", metric_p=0.4),
        _r(persona_id="p1", arm="control", metric_p=0.4),
    ]
    res = aggregate_retention_lift(treatment, control, _NO_CI_CFG)
    assert res.paired_n == 1  # only p0 usable
    assert res.elicitation_failure_drops == 1  # p1
    assert res.unpaired_treatment == 1  # p2
    assert res.lift_pp == pytest.approx(20.0)


def test_no_usable_pairs_returns_none_lift() -> None:
    treatment = [_r(persona_id="p0", arm="treatment", metric_p=None)]
    control = [_r(persona_id="p0", arm="control", metric_p=None)]
    res = aggregate_retention_lift(treatment, control, _CI_CFG, run_seed=42)
    assert res.lift_pp is None
    assert res.paired_n == 0
    assert res.elicitation_failure_drops == 1


def test_unblinded_and_paraphrase_flags() -> None:
    treatment = [
        _r(persona_id="p0", arm="treatment", metric_p=0.6, metric_unblinded=True),
        _r(persona_id="p1", arm="treatment", metric_p=0.6, metric_paraphrase_unstable=True),
    ]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.4) for i in range(2)]
    res = aggregate_retention_lift(treatment, control, _NO_CI_CFG)
    assert res.unblinded_fallback is True
    assert res.paraphrase_unstable is True


# ── retention honesty wording (registry hook) ────────────────────────────────


def test_retention_honesty_uses_native_unit_wording() -> None:
    descriptor = get_metric("retention")
    res = MetricLiftResult(lift_pp=12.0, lift_ci_pp=(3.0, 21.0), paired_n=5)
    regime, relative = descriptor.honesty(res)
    assert regime == "weak_behavioral"
    assert "retains directionally higher" in relative
    assert "Synthetic retention" in relative
    assert "rank/direction" in relative


def test_retention_honesty_none_when_uncomputable() -> None:
    descriptor = get_metric("retention")
    regime, relative = descriptor.honesty(MetricLiftResult())
    assert regime == "weak_behavioral"
    assert relative is None


# ── score_ab wiring (generic metric_* fields, discriminator set) ──────────────


class _ScriptedChat:
    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        if schema is WeaknessClassification:
            return WeaknessClassification(categories=[], primary_reason="ok")
        if schema is _MetricAllocation:  # pragma: no cover
            return _MetricAllocation(action_counts={"return next week": 5, "stop": 5})
        user_msg = next(m["content"] for m in messages if m["role"] == "user")
        if "TREATMENT_REACTION" in user_msg:
            return SentimentClassification(
                sentiment=Sentiment.POSITIVE, confidence=1.0, one_line_summary=""
            )
        return SentimentClassification(
            sentiment=Sentiment.NEGATIVE, confidence=1.0, one_line_summary=""
        )

    def chat(self, *a, **k):  # pragma: no cover
        raise NotImplementedError


def _retention_hypothesis() -> Hypothesis:
    return Hypothesis(
        capability_name="feed",
        prose="test",
        metric_name="retention",
        decision_point="you've just finished tonight's session",
    )


@pytest.mark.asyncio
async def test_score_ab_grafts_metric_fields_for_retention() -> None:
    svc = ScoringService(chat_client=_ScriptedChat())
    treatment = [
        AgentReaction(
            agent_id=f"t{i}",
            persona_id=f"p{i}",
            persona_name=f"P{i}",
            reaction_text="TREATMENT_REACTION",
            sample_index=0,
            arm="treatment",
            metric_p=0.6,
        )
        for i in range(5)
    ]
    control = [
        AgentReaction(
            agent_id=f"c{i}",
            persona_id=f"p{i}",
            persona_name=f"P{i}",
            reaction_text="CONTROL_REACTION",
            sample_index=0,
            arm="control",
            metric_p=0.4,
        )
        for i in range(5)
    ]
    result, _ = await svc.score_ab(
        _retention_hypothesis(), treatment, control, run_seed=42, config=_CI_CFG
    )
    # discriminator set to the native metric
    assert result.metric_name == "retention"
    assert result.metric_lift_pp == pytest.approx(20.0)
    assert result.metric_lift_paired_n == 5
    assert result.metric_regime == "weak_behavioral"
    assert "retains directionally higher" in result.metric_lift_relative


@pytest.mark.asyncio
async def test_score_ab_missing_arm_retention_marks_uncomputable() -> None:
    svc = ScoringService(chat_client=object())  # short-circuits
    result, analyses = await svc.score_ab(
        _retention_hypothesis(),
        treatment_reactions=[],
        control_reactions=[
            AgentReaction(
                agent_id="c0",
                persona_id="p0",
                persona_name="P0",
                reaction_text="r",
                sample_index=0,
                arm="control",
                metric_p=0.5,
            )
        ],
    )
    assert analyses == []
    assert result.metric_name == "retention"
    assert result.metric_lift_paired_n == 0  # NOT None
    assert result.metric_regime == "weak_behavioral"
    assert result.metric_lift_relative is None
    assert result.metric_lift_pp is None
