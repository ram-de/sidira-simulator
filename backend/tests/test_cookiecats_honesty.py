"""Tests for the Cookie Cats by_engagement honesty stratifier.

The stratifier reads the structured Cookie Cats case_id
(`cookiecats:gate40_vs_gate30:<metric>[:<segment>]`) so a blind-eval can be
reported PER engagement octile (the heterogeneity endpoint). The report-every-cell
rule means a case_id that lacks the segment component lands in an explicit
"unknown" stratum, never dropped or mislabeled.
"""

from __future__ import annotations

from sidira_simulator.schemas.scoring import BenchmarkCaseResult, BenchmarkRunResult
from sidira_simulator.services.benchmark_honesty import by_engagement, stratify


def _case(
    case_id: str, *, observed: float = -0.01, prediction: float | None = -0.01
) -> BenchmarkCaseResult:
    return BenchmarkCaseResult(
        case_id=case_id,
        source="cookiecats",
        observed_lift=observed,
        prediction=prediction,
        dropped=prediction is None,
    )


def test_by_engagement_reads_segment_component() -> None:
    assert (
        by_engagement(_case("cookiecats:gate40_vs_gate30:retention_7:eng_o1"))
        == "engagement=eng_o1"
    )
    assert (
        by_engagement(_case("cookiecats:gate40_vs_gate30:retention_1:eng_o8"))
        == "engagement=eng_o8"
    )


def test_by_engagement_unknown_when_no_segment_component() -> None:
    # A population-level case (3 components) has no engagement stratum.
    key = by_engagement(_case("cookiecats:gate40_vs_gate30:retention_7"))
    assert "unknown" in key


def test_by_engagement_unknown_for_non_cookiecats() -> None:
    key = by_engagement(_case("hillstrom:mens_email:conversion:mens_buyer"))
    assert "unknown" in key


def test_stratify_by_engagement_reports_each_octile() -> None:
    results = [
        _case("cookiecats:gate40_vs_gate30:retention_7:eng_o1", observed=-0.03, prediction=-0.02),
        _case("cookiecats:gate40_vs_gate30:retention_7:eng_o2", observed=0.00, prediction=0.01),
        _case("cookiecats:gate40_vs_gate30:retention_7:eng_o3", observed=-0.01, prediction=0.00),
    ]
    run = BenchmarkRunResult(
        rank_rho=0.0, direction_accuracy=0.5, n_cases=3, case_results=results, seed=0
    )
    table = stratify(run, by_engagement, stratifier_name="engagement")
    keys = {s.key for s in table.strata}
    assert keys == {"engagement=eng_o1", "engagement=eng_o2", "engagement=eng_o3"}
    assert sum(s.n_cases for s in table.strata) == 3
