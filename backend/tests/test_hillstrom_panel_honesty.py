"""Tests for the Hillstrom by_arm / by_segment honesty stratifiers (#222 PR-B).

These stratifiers read the structured Hillstrom case_id
(`hillstrom:<arm>:<metric>[:<segment>]`) so a blind-eval can be reported PER ARM
(endpoint #1/#2) and PER heterogeneity SEGMENT (endpoint #3 — the only
non-trivially-guessable claim). The report-every-cell rule (§4) means a case_id
that lacks the expected component lands in an explicit "unknown" stratum, never
dropped or mislabeled.
"""

from __future__ import annotations

from sidira_simulator.schemas.scoring import BenchmarkCaseResult, BenchmarkRunResult
from sidira_simulator.services.benchmark_honesty import by_arm, by_segment, stratify


def _case(
    case_id: str, *, observed: float = 0.01, prediction: float | None = 0.01
) -> BenchmarkCaseResult:
    return BenchmarkCaseResult(
        case_id=case_id,
        source="hillstrom",
        observed_lift=observed,
        prediction=prediction,
        dropped=prediction is None,
    )


def test_by_arm_reads_arm_slug() -> None:
    assert by_arm(_case("hillstrom:mens_email:conversion")) == "arm=mens_email"
    assert by_arm(_case("hillstrom:womens_email:visit")) == "arm=womens_email"
    # A segment case still stratifies by its arm (4-component id).
    assert by_arm(_case("hillstrom:mens_email:conversion:mens_buyer")) == "arm=mens_email"


def test_by_arm_unknown_bucket_for_non_hillstrom() -> None:
    # A non-hillstrom / malformed case_id falls into a reported "unknown" bucket,
    # never mislabeled into a real arm.
    key = by_arm(_case("upworthy:t1:0"))
    assert "unknown" in key
    assert by_arm(_case("hillstrom")) == by_arm(_case("nope"))  # both unknown


def test_by_segment_reads_segment_component() -> None:
    assert by_segment(_case("hillstrom:mens_email:conversion:mens_buyer")) == "segment=mens_buyer"
    assert (
        by_segment(_case("hillstrom:womens_email:conversion:womens_buyer"))
        == "segment=womens_buyer"
    )


def test_by_segment_unknown_when_no_segment_component() -> None:
    # An ARM-level case (3 components) has no segment → reported "unknown" bucket,
    # not a fabricated stratum.
    key = by_segment(_case("hillstrom:mens_email:conversion"))
    assert "unknown" in key


def test_stratify_by_arm_reports_each_arm_as_a_row() -> None:
    """Two arm cases → two arm rows; the runner-level totals carry through."""
    results = [
        _case("hillstrom:mens_email:conversion", observed=0.02, prediction=0.03),
        _case("hillstrom:womens_email:conversion", observed=0.01, prediction=-0.01),
    ]
    run = BenchmarkRunResult(
        rank_rho=0.0, direction_accuracy=0.5, n_cases=2, case_results=results, seed=0
    )
    table = stratify(run, by_arm, stratifier_name="arm")
    keys = {s.key for s in table.strata}
    assert keys == {"arm=mens_email", "arm=womens_email"}
    # Every stratum is reported (report-every-cell), each with its one case.
    assert all(s.n_cases == 1 for s in table.strata)


def test_stratify_by_segment_reports_each_stratum() -> None:
    results = [
        _case("hillstrom:mens_email:conversion:mens_buyer", observed=0.03, prediction=0.04),
        _case("hillstrom:mens_email:conversion:womens_buyer", observed=0.00, prediction=0.01),
        _case("hillstrom:womens_email:conversion:mens_buyer", observed=0.01, prediction=0.00),
        _case("hillstrom:womens_email:conversion:womens_buyer", observed=0.04, prediction=0.05),
    ]
    run = BenchmarkRunResult(
        rank_rho=0.0, direction_accuracy=0.5, n_cases=4, case_results=results, seed=0
    )
    table = stratify(run, by_segment, stratifier_name="segment")
    keys = {s.key for s in table.strata}
    assert keys == {"segment=mens_buyer", "segment=womens_buyer"}
    # Both strata reported, no cell dropped.
    assert sum(s.n_cases for s in table.strata) == 4
