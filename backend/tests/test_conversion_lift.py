"""Tests for the §3a conversion-lift aggregation + score_ab wiring (#221).

Covers:
- `aggregate_conversion_lift` paired-delta math, drop counters, CI brackets
  point, and degenerate (no-pairs) honesty,
- `conversion_lift_honesty` direction/rank statement (never a bare-pp truth),
- `score_ab` grafting the conversion_* fields onto the composed result ONLY
  when the Hypothesis carried a conversion metric (backwards-compat otherwise).
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.scoring import (
    ConversionLiftResult,
    ScoringConfig,
    Sentiment,
    SentimentClassification,
    WeaknessClassification,
)
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.conversion_elicitor import _ConversionAllocation
from sidira_simulator.services.scoring import (
    AgentReaction,
    ScoringService,
    aggregate_conversion_lift,
    conversion_lift_honesty,
)

_NO_CI_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=0)
_CI_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=500)


def _r(
    *,
    persona_id: str,
    sample_index: int = 0,
    arm: str,
    metric_p: float | None,
    metric_unblinded: bool = False,
    metric_paraphrase_unstable: bool = False,
) -> AgentReaction:
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


# ── aggregate_conversion_lift ─────────────────────────────────────────────────


def test_affordance_gate_does_not_affect_paired_lift(monkeypatch) -> None:
    """#221/#222: the affordance clause is added symmetrically to BOTH arms'
    rendered states, so it cancels in the paired delta. `aggregate_metric_lift`
    (which `aggregate_conversion_lift` rides) operates on the elicited `metric_p`
    scalars — never on the prompt — so flipping the gate yields the IDENTICAL lift."""
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.5) for i in range(4)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.2) for i in range(4)]

    monkeypatch.delenv("SIDIRA_STIMULUS_AFFORDANCE", raising=False)
    monkeypatch.delenv("PYTHIA_STIMULUS_AFFORDANCE", raising=False)
    off = aggregate_conversion_lift(treatment, control, _CI_CFG, run_seed=42)
    monkeypatch.setenv("SIDIRA_STIMULUS_AFFORDANCE", "1")
    on = aggregate_conversion_lift(treatment, control, _CI_CFG, run_seed=42)
    assert on.lift_pp == off.lift_pp == pytest.approx(30.0)
    assert on.lift_ci_pp == off.lift_ci_pp


def test_positive_paired_lift_in_percentage_points() -> None:
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.5) for i in range(4)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.2) for i in range(4)]
    res = aggregate_conversion_lift(treatment, control, _CI_CFG, run_seed=42)

    assert isinstance(res, ConversionLiftResult)
    assert res.paired_n == 4
    # (0.5 - 0.2) * 100 = 30.0 pp
    assert res.lift_pp == pytest.approx(30.0)
    assert res.lift_ci_pp is not None
    # all pairs identical → tight CI bracketing the point
    assert res.lift_ci_pp[0] <= res.lift_pp <= res.lift_ci_pp[1]
    assert res.unpaired_treatment == 0
    assert res.unpaired_control == 0
    assert res.elicitation_failure_drops == 0


def test_negative_lift() -> None:
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.1) for i in range(3)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.4) for i in range(3)]
    res = aggregate_conversion_lift(treatment, control, _NO_CI_CFG)
    assert res.lift_pp == pytest.approx(-30.0)


def test_unpaired_arms_counted_and_excluded() -> None:
    treatment = [
        _r(persona_id="p0", arm="treatment", metric_p=0.5),
        _r(persona_id="p1", arm="treatment", metric_p=0.5),  # no control twin
    ]
    control = [
        _r(persona_id="p0", arm="control", metric_p=0.2),
        _r(persona_id="p2", arm="control", metric_p=0.2),  # no treatment twin
    ]
    res = aggregate_conversion_lift(treatment, control, _NO_CI_CFG)
    assert res.paired_n == 1  # only p0 matched
    assert res.unpaired_treatment == 1  # p1
    assert res.unpaired_control == 1  # p2
    assert res.lift_pp == pytest.approx(30.0)


def test_elicitation_failure_drops_pairs_where_either_side_is_none() -> None:
    treatment = [
        _r(persona_id="p0", arm="treatment", metric_p=0.5),
        _r(persona_id="p1", arm="treatment", metric_p=None),  # failed treatment
        _r(persona_id="p2", arm="treatment", metric_p=0.5),
    ]
    control = [
        _r(persona_id="p0", arm="control", metric_p=0.2),
        _r(persona_id="p1", arm="control", metric_p=0.2),
        _r(persona_id="p2", arm="control", metric_p=None),  # failed control
    ]
    res = aggregate_conversion_lift(treatment, control, _NO_CI_CFG)
    assert res.paired_n == 1  # only p0 usable
    assert res.elicitation_failure_drops == 2  # p1 + p2
    assert res.lift_pp == pytest.approx(30.0)


def test_no_usable_pairs_returns_none_lift() -> None:
    treatment = [_r(persona_id="p0", arm="treatment", metric_p=None)]
    control = [_r(persona_id="p0", arm="control", metric_p=None)]
    res = aggregate_conversion_lift(treatment, control, _CI_CFG, run_seed=42)
    assert res.lift_pp is None
    assert res.lift_ci_pp is None
    assert res.paired_n == 0
    assert res.elicitation_failure_drops == 1


def test_single_pair_ci_brackets_point() -> None:
    treatment = [_r(persona_id="p0", arm="treatment", metric_p=0.7)]
    control = [_r(persona_id="p0", arm="control", metric_p=0.3)]
    res = aggregate_conversion_lift(treatment, control, _CI_CFG, run_seed=7)
    assert res.lift_pp == pytest.approx(40.0)
    assert res.lift_ci_pp == (res.lift_pp, res.lift_pp)


def test_deterministic_for_same_seed() -> None:
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.1 * i) for i in range(6)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.05 * i) for i in range(6)]
    a = aggregate_conversion_lift(treatment, control, _CI_CFG, run_seed=99)
    b = aggregate_conversion_lift(treatment, control, _CI_CFG, run_seed=99)
    assert a.lift_pp == b.lift_pp
    assert a.lift_ci_pp == b.lift_ci_pp


# ── §3b unblinded-fallback flag ───────────────────────────────────────────────


def test_unblinded_fallback_false_when_all_treatment_blinded() -> None:
    """Default posture: every treatment agent ran blinded → the run's lift is
    NOT flagged."""
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.5) for i in range(3)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.2) for i in range(3)]
    res = aggregate_conversion_lift(treatment, control, _NO_CI_CFG)
    assert res.unblinded_fallback is False


def test_unblinded_fallback_set_when_any_treatment_agent_unblinded() -> None:
    """A single treatment agent forced onto the unblinded fallback prompt taints
    the whole run's lift as low-confidence (control is always blinded, so only
    the treatment side carries the flag)."""
    treatment = [
        _r(persona_id="p0", arm="treatment", metric_p=0.5),
        _r(persona_id="p1", arm="treatment", metric_p=0.5, metric_unblinded=True),
    ]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.2) for i in range(2)]
    res = aggregate_conversion_lift(treatment, control, _NO_CI_CFG)
    assert res.unblinded_fallback is True


# ── conversion_lift_honesty (§5) ──────────────────────────────────────────────


def test_honesty_returns_weak_regime_and_no_statement_when_uncomputable() -> None:
    regime, relative = conversion_lift_honesty(ConversionLiftResult())
    assert regime == "weak_behavioral"
    assert relative is None


def test_honesty_positive_direction_and_ci_excludes_zero() -> None:
    res = ConversionLiftResult(lift_pp=12.0, lift_ci_pp=(3.0, 21.0), paired_n=5)
    regime, relative = conversion_lift_honesty(res)
    assert regime == "weak_behavioral"
    assert relative is not None
    assert "higher" in relative
    assert "excludes zero" in relative
    # never asserts the bare pp as a calibrated truth
    assert "rank/direction" in relative


def test_honesty_straddling_ci_is_not_separable() -> None:
    res = ConversionLiftResult(lift_pp=2.0, lift_ci_pp=(-5.0, 9.0), paired_n=5)
    _regime, relative = conversion_lift_honesty(res)
    assert "straddles zero" in relative


def test_honesty_negative_direction() -> None:
    res = ConversionLiftResult(lift_pp=-8.0, lift_ci_pp=(-15.0, -1.0), paired_n=5)
    _regime, relative = conversion_lift_honesty(res)
    assert "lower" in relative


def test_honesty_appends_unblinded_caveat_when_flagged() -> None:
    """§3b: an unblinded-fallback run gets an explicit low-confidence caveat in
    the PM-facing relative statement, so a lift that ran unblinded is never read
    as if it were a clean blinded delta."""
    res = ConversionLiftResult(
        lift_pp=12.0, lift_ci_pp=(3.0, 21.0), paired_n=5, unblinded_fallback=True
    )
    _regime, relative = conversion_lift_honesty(res)
    assert "UNBLINDED" in relative
    assert "low-confidence" in relative


def test_honesty_no_unblinded_caveat_when_blinded() -> None:
    res = ConversionLiftResult(lift_pp=12.0, lift_ci_pp=(3.0, 21.0), paired_n=5)
    _regime, relative = conversion_lift_honesty(res)
    assert "UNBLINDED" not in relative


# ── §3e paraphrase-instability flag ───────────────────────────────────────────


def test_aggregate_flags_paraphrase_instability_from_treatment() -> None:
    treatment = [
        _r(persona_id="p0", arm="treatment", metric_p=0.5, metric_paraphrase_unstable=True),
        _r(persona_id="p1", arm="treatment", metric_p=0.5),
    ]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.2) for i in range(2)]
    res = aggregate_conversion_lift(treatment, control, _NO_CI_CFG)
    assert res.paraphrase_unstable is True


def test_aggregate_flags_paraphrase_instability_from_control() -> None:
    """Unlike unblinding (treatment-only), a CONTROL agent's flip also taints the
    pair's delta, so instability is collected from either arm."""
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.5) for i in range(2)]
    control = [
        _r(persona_id="p0", arm="control", metric_p=0.2, metric_paraphrase_unstable=True),
        _r(persona_id="p1", arm="control", metric_p=0.2),
    ]
    res = aggregate_conversion_lift(treatment, control, _NO_CI_CFG)
    assert res.paraphrase_unstable is True


def test_aggregate_paraphrase_stable_when_no_flips() -> None:
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.5) for i in range(2)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.2) for i in range(2)]
    res = aggregate_conversion_lift(treatment, control, _NO_CI_CFG)
    assert res.paraphrase_unstable is False


def test_aggregate_ignores_paraphrase_flip_on_unpaired_agent() -> None:
    """codex P2: a flagged agent with no twin never enters the delta, so it must
    NOT taint the lift caveat."""
    treatment = [
        _r(persona_id="p0", arm="treatment", metric_p=0.5),  # paired, stable
        # p9 has no control twin → unpaired; its flip is irrelevant to the delta.
        _r(persona_id="p9", arm="treatment", metric_p=0.5, metric_paraphrase_unstable=True),
    ]
    control = [_r(persona_id="p0", arm="control", metric_p=0.2)]
    res = aggregate_conversion_lift(treatment, control, _NO_CI_CFG)
    assert res.paired_n == 1
    assert res.unpaired_treatment == 1
    assert res.paraphrase_unstable is False


def test_aggregate_ignores_paraphrase_flip_on_dropped_pair() -> None:
    """codex P2: a flagged agent whose pair is DROPPED (the other side has no
    usable p_conv) never enters the delta, so it must NOT taint the lift caveat."""
    treatment = [
        _r(persona_id="p0", arm="treatment", metric_p=0.5),  # paired, stable
        _r(persona_id="p1", arm="treatment", metric_p=0.5, metric_paraphrase_unstable=True),
    ]
    control = [
        _r(persona_id="p0", arm="control", metric_p=0.2),
        _r(persona_id="p1", arm="control", metric_p=None),  # drops the p1 pair
    ]
    res = aggregate_conversion_lift(treatment, control, _NO_CI_CFG)
    assert res.paired_n == 1
    assert res.elicitation_failure_drops == 1
    assert res.paraphrase_unstable is False


def test_honesty_appends_paraphrase_caveat_when_flagged() -> None:
    res = ConversionLiftResult(
        lift_pp=12.0, lift_ci_pp=(3.0, 21.0), paired_n=5, paraphrase_unstable=True
    )
    _regime, relative = conversion_lift_honesty(res)
    assert "paraphrase" in relative
    assert "low-confidence" in relative


def test_honesty_no_paraphrase_caveat_when_stable() -> None:
    res = ConversionLiftResult(lift_pp=12.0, lift_ci_pp=(3.0, 21.0), paired_n=5)
    _regime, relative = conversion_lift_honesty(res)
    assert "paraphrase" not in relative


# ── score_ab wiring ───────────────────────────────────────────────────────────


class _ScriptedChat:
    """Positive sentiment on treatment, negative on control; canned conversion
    allocations keyed by the conversion label so score_ab's grafting is stable.
    """

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        if schema is WeaknessClassification:
            return WeaknessClassification(categories=[], primary_reason="ok")
        if schema is _ConversionAllocation:  # pragma: no cover - score_ab path
            return _ConversionAllocation(action_counts={"buy": 5, "leave": 5})
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


def _conversion_hypothesis() -> Hypothesis:
    return Hypothesis(
        capability_name="reorder",
        prose="test",
        metric_name="conversion",
        conversion_action="complete checkout",
        conversion_action_label="check out now",
        decision_point="cart has 2 items",
    )


@pytest.mark.asyncio
async def test_score_ab_grafts_conversion_fields_when_metric_set() -> None:
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
            metric_p=0.2,
        )
        for i in range(5)
    ]
    result, _ = await svc.score_ab(
        _conversion_hypothesis(), treatment, control, run_seed=42, config=_CI_CFG
    )
    # sentiment headline still present and unchanged in spirit
    assert result.confidence_score == pytest.approx(result.treatment_score)
    # conversion fields grafted on
    assert result.metric_lift_pp == pytest.approx(40.0)
    assert result.metric_lift_paired_n == 5
    assert result.metric_lift_ci_pp is not None
    assert result.metric_regime == "weak_behavioral"
    assert result.metric_lift_relative is not None
    assert "higher" in result.metric_lift_relative
    # §3e: no agent flagged → the run is paraphrase-stable
    assert result.metric_lift_paraphrase_unstable is False


@pytest.mark.asyncio
async def test_score_ab_grafts_paraphrase_instability_flag() -> None:
    """§3e: a flagged contributor surfaces on the result + its caveat in the
    PM-facing relative statement."""
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
            metric_paraphrase_unstable=(i == 0),
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
            metric_p=0.2,
        )
        for i in range(5)
    ]
    result, _ = await svc.score_ab(
        _conversion_hypothesis(), treatment, control, run_seed=42, config=_CI_CFG
    )
    assert result.metric_lift_paraphrase_unstable is True
    assert "paraphrase" in result.metric_lift_relative


@pytest.mark.asyncio
async def test_score_ab_no_metric_leaves_conversion_fields_default() -> None:
    """Backwards-compat: a non-conversion A/B run never touches the conversion
    fields — they stay at their schema defaults, byte-identical to today."""
    svc = ScoringService(chat_client=_ScriptedChat())
    hypothesis = Hypothesis(capability_name="reorder", prose="test")  # no metric
    treatment = [
        AgentReaction(
            agent_id=f"t{i}",
            persona_id=f"p{i}",
            persona_name=f"P{i}",
            reaction_text="TREATMENT_REACTION",
            sample_index=0,
            arm="treatment",
        )
        for i in range(3)
    ]
    control = [
        AgentReaction(
            agent_id=f"c{i}",
            persona_id=f"p{i}",
            persona_name=f"P{i}",
            reaction_text="CONTROL_REACTION",
            sample_index=0,
            arm="control",
        )
        for i in range(3)
    ]
    result, _ = await svc.score_ab(hypothesis, treatment, control, run_seed=42, config=_CI_CFG)
    assert result.metric_lift_pp is None
    assert result.metric_lift_ci_pp is None
    assert result.metric_lift_paired_n is None
    assert result.metric_regime is None
    assert result.metric_lift_relative is None
    # the sentiment lift path is unaffected
    assert result.lift is not None


@pytest.mark.asyncio
async def test_score_ab_missing_arm_conversion_run_marks_uncomputable() -> None:
    """A conversion-metric A/B run with one empty arm hits the early-return
    missing-arm branch; it must still mark the conversion fields as honestly
    uncomputable (paired_n=0 + weak regime), not leave them at the None default
    that would make it look like a non-conversion run (codex P2)."""
    svc = ScoringService(chat_client=object())  # short-circuits, never called
    result, analyses = await svc.score_ab(
        _conversion_hypothesis(),
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
    assert result.lift_paired_n == 0
    assert result.metric_lift_paired_n == 0  # NOT None
    assert result.metric_regime == "weak_behavioral"
    # no direction is computable with zero usable pairs
    assert result.metric_lift_relative is None
    assert result.metric_lift_pp is None
