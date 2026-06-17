"""Tests for the Cookie Cats A/B → BenchmarkCase adapter (product-change benchmark).

Mirrors `test_hillstrom_adapter`. Pins:
- the difference-in-means ground-truth math on a small synthetic frame with a
  KNOWN answer (including the COUNTER-INTUITIVE negative retention_7 lift),
- the adapter producing well-formed `BenchmarkCase`s with the correct
  `GroundTruth` (control = gate_30, treatment = gate_40, gate-level delta),
- the engagement-octile stratification + per-segment uplift,
- the `retention_1` metric path (the second scorable v1 outcome),
- an unsupported metric being rejected.
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.benchmark import BenchmarkCase, GroundTruth
from sidira_simulator.services.cookiecats_adapter import (
    GATE_COMPONENT_ID,
    build_cookiecats_case,
    compute_gate_uplift,
    compute_segment_uplift,
    cookiecats_rows_to_cases,
    engagement_octile_edges,
)
from sidira_simulator.services.cookiecats_archive import CookieCatsRow


def _row(version: str, *, retention_7: int, retention_1: int = 0, sum_gamerounds: int = 10):
    return CookieCatsRow(
        userid=0,
        version=version,
        sum_gamerounds=sum_gamerounds,
        retention_1=retention_1,
        retention_7=retention_7,
    )


def _known_frame() -> list[CookieCatsRow]:
    """A frame with hand-computable rates (the COUNTER-INTUITIVE direction).

    gate_30 (control):   retention_7 in 3 of 4 → control rate 0.75
    gate_40 (treatment): retention_7 in 1 of 4 → treatment rate 0.25 → lift −0.50
    (gate_30 OUTPERFORMS gate_40, exactly the real RCT's counter-intuitive sign.)
    """
    rows: list[CookieCatsRow] = []
    rows += [_row("gate_30", retention_7=r) for r in (1, 1, 1, 0)]
    rows += [_row("gate_40", retention_7=r) for r in (1, 0, 0, 0)]
    return rows


# ── GROUND-TRUTH MATH (known answer) ───────────────────────────────────────────


def test_gate_uplift_difference_in_means_known_answer() -> None:
    rows = _known_frame()
    up = compute_gate_uplift(rows, metric_name="retention_7", n_resamples=200)
    assert up.control_rate == pytest.approx(0.75)
    assert up.treatment_rate == pytest.approx(0.25)
    # The counter-intuitive result: moving the gate LATER LOWERS retention.
    assert up.observed_lift == pytest.approx(-0.50)
    assert up.n_control == 4 and up.n_treatment == 4
    lo, hi = up.ci
    assert lo <= up.observed_lift <= hi


def test_gate_uplift_is_deterministic_for_a_fixed_seed() -> None:
    rows = _known_frame()
    a = compute_gate_uplift(rows, seed=7, n_resamples=200)
    b = compute_gate_uplift(rows, seed=7, n_resamples=200)
    assert a.ci == b.ci


def test_unsupported_metric_raises() -> None:
    with pytest.raises(ValueError, match="unsupported Cookie Cats metric"):
        compute_gate_uplift(_known_frame(), metric_name="spend")


# ── ENGAGEMENT STRATIFICATION ──────────────────────────────────────────────────


def test_octile_edges_are_ascending_interior_cuts() -> None:
    rows = [_row("gate_30", retention_7=0, sum_gamerounds=g) for g in range(0, 80)]
    edges = engagement_octile_edges(rows, n_strata=8)
    assert len(edges) == 7  # n_strata - 1 interior edges
    assert edges == sorted(edges)


def test_segment_uplift_strata_are_matched_and_sorted() -> None:
    rows: list[CookieCatsRow] = []
    # Two engagement bands; within each, gate_30 retains better than gate_40.
    # low band (sum_gamerounds ~ 1): control 2/2, treatment 0/2 → −1.0
    rows += [_row("gate_30", retention_7=1, sum_gamerounds=1) for _ in range(2)]
    rows += [_row("gate_40", retention_7=0, sum_gamerounds=1) for _ in range(2)]
    # high band (sum_gamerounds ~ 100): control 1/2, treatment 1/2 → 0.0
    rows += [_row("gate_30", retention_7=c, sum_gamerounds=100) for c in (1, 0)]
    rows += [_row("gate_40", retention_7=c, sum_gamerounds=100) for c in (1, 0)]

    segs = compute_segment_uplift(rows, metric_name="retention_7", n_resamples=100, n_strata=2)
    # Stable sorted order (by octile number) so the pre-registration hash is stable.
    assert [s.segment for s in segs] == sorted(
        (s.segment for s in segs), key=lambda k: int(k.split("_o")[1])
    )
    # The low band carries the strong negative lift.
    assert min(s.observed_lift for s in segs) == pytest.approx(-1.0)


# ── BENCHMARK CASE SHAPE ───────────────────────────────────────────────────────


def test_build_case_is_well_formed_with_correct_ground_truth() -> None:
    rows = _known_frame()
    case = build_cookiecats_case(rows, metric_name="retention_7", n_resamples=100)
    assert isinstance(case, BenchmarkCase)
    assert case.source == "cookiecats"
    assert case.case_id == "cookiecats:gate40_vs_gate30:retention_7"
    assert isinstance(case.ground_truth, GroundTruth)
    assert case.ground_truth.metric_name == "retention_7"
    assert case.ground_truth.control_metric == pytest.approx(0.75)
    assert case.ground_truth.treatment_metric == pytest.approx(0.25)
    assert case.ground_truth.observed_lift == pytest.approx(-0.50)
    # The winner is the CONTROL (gate_30) — the earlier gate is better.
    assert case.ground_truth.winner == "control"


def test_treatment_state_moves_only_the_gate_level() -> None:
    """Control = gate at level 30; treatment = the SAME screen with the gate moved
    to level 40 — exactly one CHANGED value delta (no new screen)."""
    case = build_cookiecats_case(_known_frame(), n_resamples=10)
    control_screens = {s.id for s in case.capability.reverse_figma.screens}
    treatment_screens = {s.id for s in case.hypothesis.proposed_figma.screens}
    # No screen added/removed — same single progress screen, only the gate moves.
    assert control_screens == treatment_screens == {"level_progress"}
    control_body = next(
        c
        for s in case.capability.reverse_figma.screens
        for c in s.components
        if c.id == GATE_COMPONENT_ID
    )
    treatment_body = next(
        c
        for s in case.hypothesis.proposed_figma.screens
        for c in s.components
        if c.id == GATE_COMPONENT_ID
    )
    assert "level 30" in control_body.text
    assert "level 40" in treatment_body.text


def test_rows_to_cases_yields_single_ab_case() -> None:
    cases = cookiecats_rows_to_cases(_known_frame(), metric_name="retention_7", n_resamples=50)
    assert {c.case_id for c in cases} == {"cookiecats:gate40_vs_gate30:retention_7"}


def test_retention_1_metric_path() -> None:
    """`retention_1` (the second scorable v1 outcome) flows through the adapter."""
    rows: list[CookieCatsRow] = []
    rows += [_row("gate_30", retention_7=0, retention_1=r) for r in (1, 1, 1, 1)]  # control 1.0
    rows += [_row("gate_40", retention_7=0, retention_1=r) for r in (1, 0, 0, 0)]  # treat 0.25
    case = build_cookiecats_case(rows, metric_name="retention_1", n_resamples=100)
    assert case.case_id == "cookiecats:gate40_vs_gate30:retention_1"
    assert case.ground_truth.metric_name == "retention_1"
    assert case.ground_truth.observed_lift == pytest.approx(-0.75)


def test_empty_rows_raises() -> None:
    with pytest.raises(ValueError, match="at least one row"):
        cookiecats_rows_to_cases([])
