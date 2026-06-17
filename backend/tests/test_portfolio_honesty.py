"""Tests for the portfolio per-experiment honesty stratifier.

Mirrors `test_cookiecats_honesty`. Pins that `by_portfolio_case` reads the
structured `portfolio:<id>` case_id to report ONE row per whole experiment (the
portfolio's unit of evidence), and that a non-portfolio case_id falls into an
explicit, REPORTED "case unknown" bucket rather than being dropped/mislabeled.
"""

from __future__ import annotations

from sidira_simulator.schemas.scoring import (
    BenchmarkCaseResult,
    BenchmarkRunResult,
    NullIntegrityCertificate,
)
from sidira_simulator.services.benchmark_honesty import (
    _BY_PORTFOLIO_CASE_UNKNOWN,
    by_portfolio_case,
    render,
    stratify,
)


def _cr(case_id: str, *, observed: float, prediction: float) -> BenchmarkCaseResult:
    return BenchmarkCaseResult(
        case_id=case_id, source="portfolio", observed_lift=observed, prediction=prediction
    )


def test_by_portfolio_case_reads_experiment_id() -> None:
    cr = _cr("portfolio:cookiecats_gate_move", observed=-1.0, prediction=-0.5)
    assert by_portfolio_case(cr) == "case=cookiecats_gate_move"


def test_non_portfolio_case_id_is_reported_not_dropped() -> None:
    cr = _cr("hillstrom:mens:conversion", observed=1.0, prediction=0.2)
    assert by_portfolio_case(cr) == _BY_PORTFOLIO_CASE_UNKNOWN


def test_stratify_reports_one_row_per_experiment() -> None:
    case_results = [
        _cr("portfolio:a", observed=1.0, prediction=0.3),  # correct
        _cr("portfolio:b", observed=-1.0, prediction=0.4),  # wrong sign
    ]
    cert = NullIntegrityCertificate(
        n_experiments=2,
        passed=True,
        certifying=True,
        n_permutations=10,
        seed=0,
        integrity_hash="dead",
    )
    run = BenchmarkRunResult(
        rank_rho=0.0,
        direction_accuracy=0.5,
        certificate=cert,
        n_cases=2,
        case_results=case_results,
        seed=0,
    )
    table = stratify(run, by_portfolio_case, stratifier_name="portfolio case")
    keys = {s.key for s in table.strata}
    assert keys == {"case=a", "case=b"}
    # The rendering emits every cell (report-every-cell rule).
    out = render(table)
    assert "case=a" in out and "case=b" in out
    assert "by portfolio case" in out
