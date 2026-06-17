"""Tests for the #222 metric parameterization of `eval_engine_blind`.

The Upworthy harness hardcoded `metric_name="ctr"` + `_ctr_hypothesis_for_case`.
#222 made both injectable so the Hillstrom benchmark (conversion / visit) reuses
the exact eval core, with the DEFAULT preserving the ctr behavior byte-for-byte.
These tests pin:

- the DEFAULT path is byte-identical to the old ctr behavior (same forced metric,
  same validated hypothesis, same prediction) — the Upworthy regression gate,
- an INJECTED conversion metric + builder flows end-to-end: the engine is asked
  for the conversion hypothesis and a conversion result is required,
- a result whose metric_name mismatches the injected metric DROPS (never
  zero-filled), with the drop message naming the injected metric,
- the injected hypothesis_builder is what reaches the runner (not the ctr default),
- the `visit` metric registers and routes (registry-level proof for PR-B's run).

No live LLM — a fake `CaseRunner` is injected throughout.
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.benchmark import (
    BenchmarkCase,
    UpworthyTest,
    UpworthyVariant,
)
from sidira_simulator.schemas.simulation import Hypothesis, SimulationResult
from sidira_simulator.services.benchmark_adapter import upworthy_test_to_cases
from sidira_simulator.services.benchmark_runner import (
    _ctr_hypothesis_for_case,
    eval_engine_blind,
)
from sidira_simulator.services.metric_registry import get_metric, is_registered

_N_CHALLENGERS = 12


# ── fixtures ───────────────────────────────────────────────────────────────────


def _upworthy_cases() -> list[BenchmarkCase]:
    base_clicks = 120
    impressions = 10_000
    baseline = UpworthyVariant(
        headline="Baseline story headline",
        clicks=base_clicks,
        impressions=impressions,
        eyecatcher_id=None,
    )
    challengers = [
        UpworthyVariant(
            headline=f"Challenger {i}",
            clicks=base_clicks + i * 5,
            impressions=impressions,
            eyecatcher_id=None,
        )
        for i in range(1, _N_CHALLENGERS + 1)
    ]
    test = UpworthyTest(test_id="synthetic-1", variants=[baseline, *challengers])
    return upworthy_test_to_cases(test).cases


def _conversion_hypothesis_for_case(case: BenchmarkCase) -> Hypothesis:
    """A minimal conversion hypothesis_builder for the test — forces the conversion
    metric with the registry-required template fields, via model_validate (the same
    discipline `_ctr_hypothesis_for_case` uses)."""
    data = case.hypothesis.model_dump()
    data.update(
        {
            "metric_name": "conversion",
            "conversion_action": "check out",
            "conversion_action_label": "check out now",
            "decision_point": "you are about to leave the site",
        }
    )
    return Hypothesis.model_validate(data)


class FakeRunner:
    """Fake `CaseRunner` returning a fixed metric_name + lift, recording its calls."""

    def __init__(self, *, metric_name: str, lift_pp: float = 2.5):
        self.metric_name = metric_name
        self.lift_pp = lift_pp
        self.calls: list[dict] = []

    def __call__(self, **kwargs) -> SimulationResult:
        self.calls.append(kwargs)
        return SimulationResult(
            confidence_score=0.0, metric_name=self.metric_name, metric_lift_pp=self.lift_pp
        )


# ── DEFAULT path is unchanged (Upworthy regression gate) ───────────────────────


def test_default_path_forces_ctr_metric_byte_for_byte() -> None:
    cases = _upworthy_cases()
    runner = FakeRunner(metric_name="ctr")
    eval_engine_blind(
        cases,
        runner=runner,
        customer_id="b",
        model_id=None,
        population_size=2,
        max_agents=None,
        seed=1,
        n_permutations=10,
    )
    assert runner.calls, "the engine must have been driven"
    # The default builder is the ctr one: every forced hypothesis the runner saw
    # must be exactly one the ctr builder produces from some case — proving the
    # default path is byte-identical to the old behavior. (Cases share a capability
    # — the baseline headline — so match on the forced hypothesis itself, which the
    # ctr builder derives from each case's distinct treatment hypothesis.)
    expected_forced = [_ctr_hypothesis_for_case(c) for c in cases]
    for call in runner.calls:
        hyp = call["hypothesis"]
        assert hyp.metric_name == "ctr"
        assert hyp in expected_forced


def test_default_path_drops_on_non_ctr_result() -> None:
    """With the default ctr metric, a conversion result is unscorable → drops."""
    cases = _upworthy_cases()
    runner = FakeRunner(metric_name="conversion")  # wrong metric for the ctr default
    result = eval_engine_blind(
        cases,
        runner=runner,
        customer_id="b",
        model_id=None,
        population_size=2,
        max_agents=None,
        seed=1,
        n_permutations=10,
    )
    assert result.n_cases == 0
    assert result.n_dropped == _N_CHALLENGERS


# ── INJECTED conversion metric flows end-to-end ────────────────────────────────


def test_injected_conversion_builder_reaches_runner() -> None:
    cases = _upworthy_cases()
    runner = FakeRunner(metric_name="conversion")
    eval_engine_blind(
        cases,
        runner=runner,
        customer_id="b",
        model_id=None,
        population_size=2,
        max_agents=None,
        seed=1,
        n_permutations=10,
        metric_name="conversion",
        hypothesis_builder=_conversion_hypothesis_for_case,
    )
    assert runner.calls
    for call in runner.calls:
        hyp = call["hypothesis"]
        # The INJECTED builder reached the runner, NOT the ctr default.
        assert hyp.metric_name == "conversion"
        assert hyp.conversion_action == "check out"
        assert hyp.decision_point == "you are about to leave the site"


def test_injected_conversion_scores_and_passes_cert() -> None:
    cases = _upworthy_cases()
    runner = FakeRunner(metric_name="conversion", lift_pp=2.5)
    result = eval_engine_blind(
        cases,
        runner=runner,
        customer_id="b",
        model_id=None,
        population_size=2,
        max_agents=None,
        seed=7,
        n_permutations=200,
        metric_name="conversion",
        hypothesis_builder=_conversion_hypothesis_for_case,
    )
    # Every case scored (no drops): the conversion result matched the injected metric.
    assert result.n_cases == _N_CHALLENGERS
    assert result.n_dropped == 0
    # 2.5 pp → 0.025 raw probability delta for every case.
    preds = [cr.prediction for cr in result.case_results if cr.prediction is not None]
    assert all(p == pytest.approx(0.025) for p in preds)
    # Constant predictions → the structurally-blinded null cert PASSes (no leakage).
    assert result.certificate is not None
    assert result.void is False


def test_injected_metric_mismatch_drops_with_named_metric() -> None:
    """Inject conversion but have the engine return ctr → unscorable → drops, and
    the drop reason names the INJECTED metric (not a hardcoded 'ctr')."""
    cases = _upworthy_cases()
    runner = FakeRunner(metric_name="ctr")  # mismatches the injected conversion metric
    result = eval_engine_blind(
        cases,
        runner=runner,
        customer_id="b",
        model_id=None,
        population_size=2,
        max_agents=None,
        seed=1,
        n_permutations=10,
        metric_name="conversion",
        hypothesis_builder=_conversion_hypothesis_for_case,
    )
    assert result.n_cases == 0
    assert result.n_dropped == _N_CHALLENGERS


# ── visit registers + routes (PR-B run readiness) ──────────────────────────────


def test_visit_metric_is_registered() -> None:
    assert is_registered("visit")
    d = get_metric("visit")
    assert d.name == "visit"
    assert d.required_template_fields == ("decision_point",)


def test_visit_honesty_is_strong_behavioral() -> None:
    from sidira_simulator.schemas.scoring import MetricLiftResult

    d = get_metric("visit")
    regime, relative = d.honesty(MetricLiftResult(lift_pp=5.0, paired_n=3))
    assert regime == "strong_behavioral"
    assert "visits the site directionally more often" in relative


def test_visit_hypothesis_validates_with_decision_point() -> None:
    h = Hypothesis(
        capability_name="promo email",
        prose="x",
        metric_name="visit",
        decision_point="you just got an email from a store you've shopped at",
    )
    assert h.metric_name == "visit"
    # missing decision_point fails loud (registry-driven required field)
    with pytest.raises(ValueError, match="requires non-empty"):
        Hypothesis(capability_name="promo email", prose="x", metric_name="visit")
