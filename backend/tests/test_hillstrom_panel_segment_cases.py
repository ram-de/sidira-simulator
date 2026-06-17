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


def _row(
    segment: str,
    *,
    mens: int,
    womens: int,
    conversion: int,
    history_segment: str = "1) $0 - $100",
):
    return HillstromRow(
        recency=1,
        history_segment=history_segment,
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


_HIGH = "6) $750 - $1,000"  # high spend tier (rank >= 5) → high_spender
_MID = "3) $200 - $350"  # mid spend tier (rank < 5) → mid_tier


def _frame() -> list[HillstromRow]:
    """All four persona-aligned strata (mens_buyer / womens_buyer / high_spender /
    mid_tier) across all three arms — the partition the committed 4-persona pack
    clusters and the by-segment endpoint conditions on."""
    rows: list[HillstromRow] = []
    # mens_buyer (mens=1, womens=0)
    rows += [_row("No E-Mail", mens=1, womens=0, conversion=c) for c in (0, 0)]
    rows += [_row("Mens E-Mail", mens=1, womens=0, conversion=c) for c in (1, 1)]
    rows += [_row("Womens E-Mail", mens=1, womens=0, conversion=c) for c in (0, 1)]
    # womens_buyer (mens=0, womens=1)
    rows += [_row("No E-Mail", mens=0, womens=1, conversion=c) for c in (0, 0)]
    rows += [_row("Mens E-Mail", mens=0, womens=1, conversion=c) for c in (0, 0)]
    rows += [_row("Womens E-Mail", mens=0, womens=1, conversion=c) for c in (1, 1)]
    # high_spender (mens=1, womens=1, high history tier)
    rows += [
        _row("No E-Mail", mens=1, womens=1, conversion=c, history_segment=_HIGH) for c in (0, 1)
    ]
    rows += [
        _row("Mens E-Mail", mens=1, womens=1, conversion=c, history_segment=_HIGH) for c in (1, 1)
    ]
    rows += [
        _row("Womens E-Mail", mens=1, womens=1, conversion=c, history_segment=_HIGH) for c in (0, 1)
    ]
    # mid_tier (mens=1, womens=1, low/mid history tier)
    rows += [
        _row("No E-Mail", mens=1, womens=1, conversion=c, history_segment=_MID) for c in (0, 0)
    ]
    rows += [
        _row("Mens E-Mail", mens=1, womens=1, conversion=c, history_segment=_MID) for c in (1, 0)
    ]
    rows += [
        _row("Womens E-Mail", mens=1, womens=1, conversion=c, history_segment=_MID) for c in (1, 0)
    ]
    return rows


def test_segment_cases_enumerate_arm_by_segment() -> None:
    cases = hillstrom_segment_cases(_frame(), metric_name="conversion", n_resamples=50)
    ids = {c.case_id for c in cases}
    # 2 arms × 4 persona-aligned strata = 8 cases, each with a 4-component case_id.
    # 8 clears the null-integrity certificate's _MIN_EXPERIMENTS floor.
    assert ids == {
        "hillstrom:mens_email:conversion:mens_buyer",
        "hillstrom:mens_email:conversion:womens_buyer",
        "hillstrom:mens_email:conversion:high_spender",
        "hillstrom:mens_email:conversion:mid_tier",
        "hillstrom:womens_email:conversion:mens_buyer",
        "hillstrom:womens_email:conversion:womens_buyer",
        "hillstrom:womens_email:conversion:high_spender",
        "hillstrom:womens_email:conversion:mid_tier",
    }
    assert len(cases) == 8
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
    case = cases["hillstrom:mens_email:conversion:mens_buyer"]
    assert case.ground_truth.observed_lift == pytest.approx(segs["mens_buyer"].observed_lift)


def test_segment_case_stimulus_matches_arm_case() -> None:
    """The rendered change (capability + hypothesis) is identical between a
    segment case and its arm-level case — only ground truth / case_id differ, so
    the predictor cannot read the stratum off the stimulus (structural blindness)."""
    rows = _frame()
    arm_case = build_hillstrom_case(rows, "Mens E-Mail", metric_name="conversion", n_resamples=50)
    seg_case = next(
        c
        for c in hillstrom_segment_cases(rows, metric_name="conversion", n_resamples=50)
        if c.case_id == "hillstrom:mens_email:conversion:mens_buyer"
    )
    assert seg_case.capability == arm_case.capability
    assert seg_case.hypothesis == arm_case.hypothesis


def test_empty_rows_raises() -> None:
    with pytest.raises(ValueError):
        hillstrom_segment_cases([])
