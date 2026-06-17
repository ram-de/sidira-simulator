"""Tests for the per-engagement-segment Cookie Cats case enumeration.

`cookiecats_segment_cases` builds one BenchmarkCase per engagement octile, each
carrying the per-stratum uplift as ground truth and a 4-component case_id
(`cookiecats:gate40_vs_gate30:<metric>:<segment>`) the `by_engagement` honesty
stratifier reads. The stimulus (capability + hypothesis gate delta) is IDENTICAL
to the population-level case — only ground truth + case_id differ — so the
predictor stays structurally blind to the stratum. Eight octiles ≥ the null-cert's
8-experiment floor.

Uses the committed synthetic fixture CSV (tests/data/cookiecats_sample.csv) so the
≥8 octiles are populated from a realistic engagement spread without depending on
the real (uncommitted) download.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sidira_simulator.services.cookiecats_adapter import (
    build_cookiecats_case,
    compute_segment_uplift,
    cookiecats_segment_cases,
)
from sidira_simulator.services.cookiecats_archive import load_cookiecats_csv

_FIXTURE = Path(__file__).parent / "data" / "cookiecats_sample.csv"


def _rows():
    rows, summary = load_cookiecats_csv(_FIXTURE)
    assert summary.rows_kept > 0
    return rows


def test_fixture_clears_eight_case_floor() -> None:
    """The fixture populates >=8 engagement octiles → >=8 by-segment cases, which
    clears the null-integrity certificate's 8-experiment floor."""
    cases = cookiecats_segment_cases(_rows(), metric_name="retention_7", n_resamples=50)
    assert len(cases) >= 8
    assert all(c.source == "cookiecats" for c in cases)
    assert all(len(c.case_id.split(":")) == 4 for c in cases)
    # Every stratum key is a distinct engagement octile.
    segs = {c.case_id.split(":")[3] for c in cases}
    assert len(segs) == len(cases)
    assert all(s.startswith("eng_o") for s in segs)


def test_segment_case_ground_truth_matches_segment_uplift() -> None:
    rows = _rows()
    segs = {
        s.segment: s
        for s in compute_segment_uplift(rows, metric_name="retention_7", n_resamples=50)
    }
    cases = {
        c.case_id.split(":")[3]: c
        for c in cookiecats_segment_cases(rows, metric_name="retention_7", n_resamples=50)
    }
    for seg_key, case in cases.items():
        assert case.ground_truth.observed_lift == pytest.approx(segs[seg_key].observed_lift)


def test_segment_case_stimulus_matches_population_case() -> None:
    """The rendered change is identical between a segment case and the population
    case — only ground truth / case_id differ (structural blindness)."""
    rows = _rows()
    pop_case = build_cookiecats_case(rows, metric_name="retention_7", n_resamples=50)
    seg_case = cookiecats_segment_cases(rows, metric_name="retention_7", n_resamples=50)[0]
    assert seg_case.capability == pop_case.capability
    assert seg_case.hypothesis == pop_case.hypothesis


def test_fixture_overall_direction_is_counter_intuitive() -> None:
    """Sanity-check the fixture encodes the real RCT's counter-intuitive sign:
    moving the gate later (gate_40) LOWERS 7-day retention vs gate_30 overall."""
    case = build_cookiecats_case(_rows(), metric_name="retention_7", n_resamples=50)
    assert case.ground_truth.observed_lift < 0
    assert case.ground_truth.winner == "control"


def test_empty_rows_raises() -> None:
    with pytest.raises(ValueError):
        cookiecats_segment_cases([])
