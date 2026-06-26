"""Tests for the live-simulation → SimulatedHypothesis adapter (#33).

The /memory fused conversation reads the customer's OWN completed simulations via
this adapter instead of the synthetic demo seed. These cover the projection: field
mapping, direction derivation from the signed delta, and the skip rules that keep a
non-citable row (pending / result-less / agreement-less) out of retrieval.
"""

from __future__ import annotations

from datetime import datetime

from sidira_simulator.schemas.experiment_memory import ExperimentCategory
from sidira_simulator.schemas.simulation_archive import PredictedDirection
from sidira_simulator.services.live_simulations import to_simulated_hypotheses


def _row(
    *,
    sim_id: str = "sim-live-1",
    status: str = "completed",
    prose: str = "Add a 'Continue Watching' rail to the home screen",
    metric_name: str | None = "retention",
    capability_name: str = "home_screen",
    confidence: float | None = 65.0,
    metric_lift_pp: float | None = 1.4,
    lift: float | None = None,
    completed_at: object | None = "2026-06-24T10:00:00+00:00",
    created_at: object | None = "2026-06-23T09:00:00+00:00",
) -> dict:
    hyp = {"prose": prose, "capability_name": capability_name}
    if metric_name is not None:
        hyp["metric_name"] = metric_name
    result: dict | None = None
    if confidence is not None or metric_lift_pp is not None or lift is not None:
        result = {}
        if confidence is not None:
            result["confidence_score"] = confidence
        if metric_lift_pp is not None:
            result["metric_lift_pp"] = metric_lift_pp
        if lift is not None:
            result["lift"] = lift
    return {
        "id": sim_id,
        "status": status,
        "hypothesis_json": hyp,
        "result_json": result,
        "completed_at": completed_at,
        "created_at": created_at,
    }


def test_maps_completed_row_to_simulated_hypothesis() -> None:
    [sim] = to_simulated_hypotheses([_row()])
    assert sim.id == "sim-live-1"
    assert sim.change_description == "Add a 'Continue Watching' rail to the home screen"
    assert sim.primary_metric == "retention"
    assert sim.confidence_score == 65.0
    assert sim.predicted_metric_lift_pp == 1.4
    assert sim.predicted_direction is PredictedDirection.UP
    assert sim.sim_date == "2026-06-24"
    assert sim.paired_experiment_id is None
    # Live rows carry no firewall category — the neutral default, never ranked on.
    assert sim.category is ExperimentCategory.UI


def test_direction_from_signed_metric_delta() -> None:
    up = to_simulated_hypotheses([_row(metric_lift_pp=2.0)])[0]
    down = to_simulated_hypotheses([_row(metric_lift_pp=-2.0)])[0]
    assert up.predicted_direction is PredictedDirection.UP
    assert down.predicted_direction is PredictedDirection.DOWN


def test_direction_falls_back_to_headline_lift_without_fabricating_pp() -> None:
    # No metric_lift_pp, but a negative headline lift → direction DOWN, yet the
    # metric-lift figure stays None (never fabricated as 0.0, which would contradict
    # the direction in the rendered citation — DESIGN.md §8.3).
    sim = to_simulated_hypotheses([_row(metric_lift_pp=None, lift=-3.1)])[0]
    assert sim.predicted_direction is PredictedDirection.DOWN
    assert sim.predicted_metric_lift_pp is None


def test_flat_when_no_signal_or_inside_band() -> None:
    no_signal = to_simulated_hypotheses([_row(metric_lift_pp=None, lift=None)])[0]
    inside_band = to_simulated_hypotheses([_row(metric_lift_pp=0.01)])[0]
    assert no_signal.predicted_direction is PredictedDirection.FLAT
    assert inside_band.predicted_direction is PredictedDirection.FLAT


def test_sim_date_accepts_datetime_and_falls_back_to_created() -> None:
    dt_row = _row(completed_at=datetime(2026, 6, 24, 10, 0, 0), created_at=None)
    assert to_simulated_hypotheses([dt_row])[0].sim_date == "2026-06-24"
    no_completed = _row(completed_at=None)
    assert to_simulated_hypotheses([no_completed])[0].sim_date == "2026-06-23"


def test_skips_non_citable_rows() -> None:
    rows = [
        _row(sim_id="running", status="running"),
        _row(sim_id="failed", status="failed"),
        _row(sim_id="no-result", confidence=None, metric_lift_pp=None, lift=None),
        _row(sim_id="no-prose", prose="   "),
        _row(sim_id="no-confidence", confidence=None, metric_lift_pp=1.0),
        _row(sim_id="ok"),
    ]
    out = to_simulated_hypotheses(rows)
    assert [s.id for s in out] == ["ok"]


def test_primary_metric_falls_back_to_capability_then_default() -> None:
    cap = to_simulated_hypotheses([_row(metric_name=None)])[0]
    assert cap.primary_metric == "home_screen"
    none_either = to_simulated_hypotheses([_row(metric_name=None, capability_name="")])[0]
    assert none_either.primary_metric == "the primary metric"
