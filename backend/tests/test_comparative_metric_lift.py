"""#342 comparative-delta lift: aggregate_metric_lift delegates to the comparative
aggregator when treatment reactions carry metric_comparative_delta; otherwise the
historical two-pass subtraction is unchanged."""
from __future__ import annotations

from sidira_simulator.services.scoring import (
    AgentReaction, aggregate_metric_lift, aggregate_comparative_metric_lift,
)


def _t(i, delta=None, p=None):
    return AgentReaction(agent_id=f"t{i}", persona_id=f"p{i}", persona_name="x",
                         reaction_text="", sample_index=0, arm="treatment",
                         metric_p=p, metric_comparative_delta=delta)


def _c(i, p):
    return AgentReaction(agent_id=f"c{i}", persona_id=f"p{i}", persona_name="x",
                         reaction_text="", sample_index=0, arm="control", metric_p=p)


def test_delegates_to_comparative_when_deltas_present() -> None:
    tr = [_t(i, delta=d) for i, d in enumerate([0.05, 0.07, 0.09])]
    res = aggregate_metric_lift(tr, [], metric_name="visit")
    assert res.lift_pp == 7.0          # mean(5,7,9)pp
    assert res.paired_n == 3
    assert res.elicitation_failure_drops == 0


def test_comparative_counts_none_deltas_as_failures_never_zero() -> None:
    tr = [_t(0, delta=0.05), _t(1, delta=0.07), _t(2, delta=None)]
    res = aggregate_comparative_metric_lift(tr, metric_name="visit")
    assert res.lift_pp == 6.0          # mean(5,7)pp — the None is dropped, not 0
    assert res.paired_n == 2
    assert res.elicitation_failure_drops == 1


def test_no_deltas_uses_historical_subtraction_unchanged() -> None:
    # treatment 0.6 vs control 0.5 → +10pp via the paired subtraction path
    res = aggregate_metric_lift([_t(0, p=0.6)], [_c(0, 0.5)], metric_name="visit")
    assert res.lift_pp == 10.0
    assert res.paired_n == 1


def test_empty_comparative_yields_none_lift() -> None:
    res = aggregate_comparative_metric_lift([_t(0, delta=None)], metric_name="visit")
    assert res.lift_pp is None
    assert res.paired_n == 0
    assert res.elicitation_failure_drops == 1
