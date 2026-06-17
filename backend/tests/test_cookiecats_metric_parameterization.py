"""Tests for the Cookie Cats metric routing through the parameterized eval core.

The gate-move benchmark scores the IN-SCOPE deliberative `retention` metric. The
two data outcomes (retention_7 / retention_1) both map to the engine's single
`retention` metric_name; the `--metric` flag only selects which outcome anchors
ground truth and how the post-experience moment is phrased. These tests pin:

- the `_cookiecats_hypothesis_builder` forces metric_name="retention" with the
  retention-required template fields (decision_point), and the day window shows up
  in the decision_point,
- an injected retention metric + builder flows end-to-end through `eval_engine_blind`
  (the same parameterized core the Hillstrom/Upworthy benchmarks reuse),
- `retention` is registered with the right required fields.

No live LLM — a fake `CaseRunner` is injected.
"""

from __future__ import annotations

import pytest

from sidira_simulator.cli import _cookiecats_hypothesis_builder
from sidira_simulator.schemas.simulation import Hypothesis, SimulationResult
from sidira_simulator.services.benchmark_runner import eval_engine_blind
from sidira_simulator.services.cookiecats_adapter import build_cookiecats_case
from sidira_simulator.services.cookiecats_archive import CookieCatsRow
from sidira_simulator.services.metric_registry import get_metric, is_registered


def _frame():
    rows = [
        CookieCatsRow(userid=i, version="gate_30", sum_gamerounds=10, retention_1=1, retention_7=1)
        for i in range(4)
    ]
    rows += [
        CookieCatsRow(userid=i, version="gate_40", sum_gamerounds=10, retention_1=0, retention_7=0)
        for i in range(4, 8)
    ]
    return rows


class FakeRunner:
    def __init__(self, *, metric_name: str, lift_pp: float = -2.5):
        self.metric_name = metric_name
        self.lift_pp = lift_pp
        self.calls: list[dict] = []

    def __call__(self, **kwargs) -> SimulationResult:
        self.calls.append(kwargs)
        return SimulationResult(
            confidence_score=0.0, metric_name=self.metric_name, metric_lift_pp=self.lift_pp
        )


def test_retention_is_registered_with_decision_point() -> None:
    assert is_registered("retention")
    d = get_metric("retention")
    assert d.name == "retention"
    assert d.required_template_fields == ("decision_point",)


def test_builder_forces_retention_metric_with_day_window() -> None:
    case = build_cookiecats_case(_frame(), metric_name="retention_7", n_resamples=10)
    hyp = _cookiecats_hypothesis_builder("retention_7")(case)
    assert isinstance(hyp, Hypothesis)
    # The engine metric is `retention`, NOT the data-layer `retention_7`.
    assert hyp.metric_name == "retention"
    assert hyp.decision_point
    assert "7 days" in hyp.decision_point
    # retention_1 phrases the shorter horizon.
    hyp1 = _cookiecats_hypothesis_builder("retention_1")(case)
    assert "day after" in hyp1.decision_point


def test_builder_does_not_read_ground_truth() -> None:
    """The builder is structurally blind — it reads only case.hypothesis."""
    case = build_cookiecats_case(_frame(), metric_name="retention_7", n_resamples=10)
    # Mutating the ground truth must not change the forced hypothesis.
    h1 = _cookiecats_hypothesis_builder("retention_7")(case)
    mutated = case.model_copy(
        update={"ground_truth": case.ground_truth.model_copy(update={"observed_lift": 99.0})}
    )
    h2 = _cookiecats_hypothesis_builder("retention_7")(mutated)
    assert h1 == h2


def test_injected_retention_builder_flows_end_to_end() -> None:
    case = build_cookiecats_case(_frame(), metric_name="retention_7", n_resamples=10)
    runner = FakeRunner(metric_name="retention", lift_pp=-2.5)
    result = eval_engine_blind(
        [case],
        runner=runner,
        customer_id="b",
        model_id=None,
        population_size=2,
        max_agents=None,
        seed=1,
        n_permutations=10,
        metric_name="retention",
        hypothesis_builder=_cookiecats_hypothesis_builder("retention_7"),
    )
    assert runner.calls
    for call in runner.calls:
        assert call["hypothesis"].metric_name == "retention"
    assert result.n_cases == 1
    assert result.n_dropped == 0
    # -2.5 pp → -0.025 raw probability delta.
    pred = result.case_results[0].prediction
    assert pred == pytest.approx(-0.025)


def test_mismatched_engine_metric_drops() -> None:
    """If the engine returns a non-retention metric the case DROPS (never zero-filled)."""
    case = build_cookiecats_case(_frame(), metric_name="retention_7", n_resamples=10)
    runner = FakeRunner(metric_name="ctr")  # wrong metric
    result = eval_engine_blind(
        [case],
        runner=runner,
        customer_id="b",
        model_id=None,
        population_size=2,
        max_agents=None,
        seed=1,
        n_permutations=10,
        metric_name="retention",
        hypothesis_builder=_cookiecats_hypothesis_builder("retention_7"),
    )
    assert result.n_cases == 0
    assert result.n_dropped == 1
