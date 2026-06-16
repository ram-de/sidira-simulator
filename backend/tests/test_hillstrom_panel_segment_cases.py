"""Tests for the per-segment Hillstrom case enumeration (#222 PR-B, endpoint #3).

`hillstrom_segment_cases` builds one BenchmarkCase per (arm × purchase-history
segment), each carrying the per-stratum uplift as ground truth and a 4-component
case_id (`hillstrom:<arm>:<metric>:<segment>`) the `by_segment` honesty
stratifier reads. The stimulus (capability + hypothesis copy delta) is IDENTICAL
to the arm-level case for that arm — only ground truth + case_id differ — so the
predictor stays structurally blind to the stratum.
"""

from __future__ import annotations

import pytest

from sidira_simulator.services.hillstrom_adapter import (
    build_hillstrom_case,
    compute_segment_uplift,
    hillstrom_segment_cases,
)
from sidira_simulator.services.hillstrom_archive import HillstromRow


def _row(segment: str, *, mens: int, womens: int, conversion: int):
    return HillstromRow(
        recency=1,
        history_segment="1) $0 - $100",
        history=100.0,
        mens=mens,
        womens=womens,
        zip_code="Urban",
        newbie=0,
        channel="Web",
        segment=segment,
        visit=0,
        conversion=conversion,
        spend=0.0,
    )


def _frame() -> list[HillstromRow]:
    """Two purchase-history strata (mens_history / womens_history) across all arms."""
    rows: list[HillstromRow] = []
    # mens_history customers
    rows += [_row("No E-Mail", mens=1, womens=0, conversion=c) for c in (0, 0)]
    rows += [_row("Mens E-Mail", mens=1, womens=0, conversion=c) for c in (1, 1)]
    rows += [_row("Womens E-Mail", mens=1, womens=0, conversion=c) for c in (0, 1)]
    # womens_history customers
    rows += [_row("No E-Mail", mens=0, womens=1, conversion=c) for c in (0, 0)]
    rows += [_row("Mens E-Mail", mens=0, womens=1, conversion=c) for c in (0, 0)]
    rows += [_row("Womens E-Mail", mens=0, womens=1, conversion=c) for c in (1, 1)]
    return rows


def test_segment_cases_enumerate_arm_by_segment() -> None:
    cases = hillstrom_segment_cases(_frame(), metric_name="conversion", n_resamples=50)
    ids = {c.case_id for c in cases}
    # 2 arms × 2 strata = 4 cases, each with a 4-component case_id.
    assert ids == {
        "hillstrom:mens_email:conversion:mens_history",
        "hillstrom:mens_email:conversion:womens_history",
        "hillstrom:womens_email:conversion:mens_history",
        "hillstrom:womens_email:conversion:womens_history",
    }
    assert all(len(c.case_id.split(":")) == 4 for c in cases)
    assert all(c.source == "hillstrom" for c in cases)


def test_segment_case_ground_truth_matches_segment_uplift() -> None:
    """The per-segment case's ground-truth lift equals the matched-stratum
    compute_segment_uplift point estimate (no re-derivation drift)."""
    rows = _frame()
    segs = {
        s.segment: s
        for s in compute_segment_uplift(
            rows, "Mens E-Mail", metric_name="conversion", n_resamples=50
        )
    }
    cases = {
        c.case_id: c
        for c in hillstrom_segment_cases(rows, metric_name="conversion", n_resamples=50)
    }
    case = cases["hillstrom:mens_email:conversion:mens_history"]
    assert case.ground_truth.observed_lift == pytest.approx(segs["mens_history"].observed_lift)


def test_segment_case_stimulus_matches_arm_case() -> None:
    """The rendered change (capability + hypothesis) is identical between a
    segment case and its arm-level case — only ground truth / case_id differ, so
    the predictor cannot read the stratum off the stimulus (structural blindness)."""
    rows = _frame()
    arm_case = build_hillstrom_case(rows, "Mens E-Mail", metric_name="conversion", n_resamples=50)
    seg_case = next(
        c
        for c in hillstrom_segment_cases(rows, metric_name="conversion", n_resamples=50)
        if c.case_id == "hillstrom:mens_email:conversion:mens_history"
    )
    assert seg_case.capability == arm_case.capability
    assert seg_case.hypothesis == arm_case.hypothesis


def test_empty_rows_raises() -> None:
    with pytest.raises(ValueError):
        hillstrom_segment_cases([])
