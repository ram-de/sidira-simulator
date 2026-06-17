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
    metric_lift_honesty,
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
    behavioral_seeds_fallback=False,
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
        behavioral_seeds_fallback=behavioral_seeds_fallback,
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


# ── variance-collapse honesty flag (v1.0-pack identity-seed fallback) ─────────

_VARIANCE_NOTE_FRAGMENT = "cross-persona variance is degraded"


def test_variance_collapsed_flag_set_and_persona_count() -> None:
    # Collapse afflicts BOTH arms; flag fires if EITHER side carries the bit.
    treatment = [
        _r(persona_id="p0", arm="treatment", metric_p=0.6, behavioral_seeds_fallback=True),
        _r(persona_id="p1", arm="treatment", metric_p=0.6),  # treatment-side clean
    ]
    control = [
        _r(persona_id="p0", arm="control", metric_p=0.4, behavioral_seeds_fallback=True),
        # p1 collapse only shows up on the control arm — still must count.
        _r(persona_id="p1", arm="control", metric_p=0.4, behavioral_seeds_fallback=True),
    ]
    res = aggregate_retention_lift(treatment, control, _NO_CI_CFG)
    assert res.variance_collapsed is True
    # Distinct personas across both arms (p0, p1) — not reaction count.
    assert res.variance_collapsed_persona_count == 2
    # Purely additive: the point estimate is untouched.
    assert res.lift_pp == pytest.approx(20.0)


def test_variance_collapsed_persona_count_dedupes_across_samples() -> None:
    # Same persona sampled twice + flagged on both arms counts ONCE.
    treatment = [
        _r(
            persona_id="p0",
            arm="treatment",
            metric_p=0.6,
            sample_index=i,
            behavioral_seeds_fallback=True,
        )
        for i in range(2)
    ]
    control = [
        _r(
            persona_id="p0",
            arm="control",
            metric_p=0.4,
            sample_index=i,
            behavioral_seeds_fallback=True,
        )
        for i in range(2)
    ]
    res = aggregate_retention_lift(treatment, control, _NO_CI_CFG)
    assert res.variance_collapsed is True
    assert res.variance_collapsed_persona_count == 1


def test_no_variance_collapse_when_all_seeds_present() -> None:
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.6) for i in range(3)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.4) for i in range(3)]
    res = aggregate_retention_lift(treatment, control, _NO_CI_CFG)
    assert res.variance_collapsed is False
    assert res.variance_collapsed_persona_count == 0
    # And the honesty caveat must NOT carry the variance note.
    _regime, relative = metric_lift_honesty(res)
    assert relative is not None
    assert _VARIANCE_NOTE_FRAGMENT not in relative


def test_variance_collapse_honesty_note_appended_when_flagged() -> None:
    # A genuinely flat metric (lift_pp == 0, CI straddles zero) under collapse:
    # the note must explain it may be an artifact, not a true null.
    res = MetricLiftResult(
        lift_pp=0.0,
        lift_ci_pp=(-5.0, 5.0),
        paired_n=8,
        variance_collapsed=True,
        variance_collapsed_persona_count=8,
    )
    _regime, relative = metric_lift_honesty(res)
    assert relative is not None
    assert _VARIANCE_NOTE_FRAGMENT in relative
    assert "v1.1" in relative  # the de-attenuate remediation


def test_variance_collapse_note_absent_when_flag_false() -> None:
    res = MetricLiftResult(lift_pp=0.0, lift_ci_pp=(-5.0, 5.0), paired_n=8)
    _regime, relative = metric_lift_honesty(res)
    assert relative is not None
    assert _VARIANCE_NOTE_FRAGMENT not in relative


# ── underpowered honesty flag (small paired-n, non-separable = inconclusive) ──

_UNDERPOWERED_NOTE_FRAGMENT = "INCONCLUSIVE"


def _pairs(n: int, *, t_p: float, c_p: float):
    # n matched pairs across distinct personas → paired_n == n. The pair delta is
    # constant (t_p - c_p), so with bootstrap_resamples=0 the CI stays None
    # (non-separable) — exactly the inconclusive small-n regime.
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=t_p) for i in range(n)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=c_p) for i in range(n)]
    return treatment, control


def test_underpowered_small_n_non_separable_is_inconclusive() -> None:
    # 16 paired identities (the streamly case), CI absent / straddles zero → the
    # flag fires and the honesty note calls it INCONCLUSIVE, not a null.
    treatment, control = _pairs(16, t_p=0.5, c_p=0.5)  # flat lift, n below floor
    res = aggregate_retention_lift(treatment, control, _NO_CI_CFG)
    assert res.paired_n == 16
    assert res.lift_pp == pytest.approx(0.0)
    assert res.lift_ci_pp is None  # non-separable (no interval)
    assert res.underpowered is True
    _regime, relative = metric_lift_honesty(res)
    assert relative is not None
    assert _UNDERPOWERED_NOTE_FRAGMENT in relative
    assert "16 paired identities" in relative


def test_underpowered_false_at_or_above_floor() -> None:
    # n == floor (30), still non-separable → NOT underpowered (enough power), and
    # the note must be absent.
    treatment, control = _pairs(30, t_p=0.5, c_p=0.5)
    res = aggregate_retention_lift(treatment, control, _NO_CI_CFG)
    assert res.paired_n == 30
    assert res.underpowered is False
    _regime, relative = metric_lift_honesty(res)
    assert relative is not None
    assert _UNDERPOWERED_NOTE_FRAGMENT not in relative


def test_underpowered_false_when_separable_despite_small_n() -> None:
    # Small n but the CI EXCLUDES zero → the run DID detect the effect, so it is
    # NOT underpowered and no note is appended.
    res = aggregate_retention_lift(
        # Exercise the real predicate via the aggregator: a strong, consistent
        # delta with bootstrap gives a CI that excludes zero.
        [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.9) for i in range(8)],
        [_r(persona_id=f"p{i}", arm="control", metric_p=0.1) for i in range(8)],
        _CI_CFG,
    )
    assert res.paired_n == 8
    assert res.lift_ci_pp is not None
    assert res.lift_ci_pp[0] > 0  # excludes zero (separable)
    assert res.underpowered is False
    _regime, relative = metric_lift_honesty(res)
    assert relative is not None
    assert _UNDERPOWERED_NOTE_FRAGMENT not in relative


def test_underpowered_false_when_lift_uncomputable() -> None:
    # No usable pairs → lift_pp is None → nothing to qualify, flag stays False.
    treatment = [_r(persona_id="p0", arm="treatment", metric_p=None)]
    control = [_r(persona_id="p0", arm="control", metric_p=None)]
    res = aggregate_retention_lift(treatment, control, _NO_CI_CFG)
    assert res.lift_pp is None
    assert res.underpowered is False
    _regime, relative = metric_lift_honesty(res)
    assert relative is None  # no computable lift → blank PM line


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
