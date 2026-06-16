"""Tests for the Hillstrom RCT → BenchmarkCase adapter (#222 directional uplift).

Mirrors `test_benchmark_upworthy`. Pins:
- the difference-in-means ground-truth math on a small synthetic frame with a
  KNOWN answer (PLAN §2),
- the adapter producing well-formed `BenchmarkCase`s with the correct
  `GroundTruth` (control = No E-Mail, treatment = the campaign arm, copy delta),
- per-arm + per-segment uplift with reproducible bootstrap CIs,
- the `visit` metric path (the second registered v1 metric),
- `spend` (and any other metric) being rejected (out of scope, no elicitor).
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.benchmark import BenchmarkCase, GroundTruth
from sidira_simulator.services.hillstrom_archive import HillstromRow
from sidira_simulator.services.hillstrom_adapter import (
    EMAIL_BODY_COMPONENT_ID,
    build_hillstrom_case,
    compute_arm_uplift,
    compute_segment_uplift,
    hillstrom_rows_to_cases,
)


def _row(segment: str, *, conversion: int, visit: int = 0, mens: int = 1, womens: int = 0):
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
        visit=visit,
        conversion=conversion,
        spend=0.0,
    )


def _known_frame() -> list[HillstromRow]:
    """A frame with hand-computable rates.

    No E-Mail:   conversion in 1 of 4 → control rate 0.25
    Mens E-Mail: conversion in 3 of 4 → treatment rate 0.75 → uplift +0.50
    Womens E-Mail: conversion in 1 of 4 → treatment rate 0.25 → uplift  0.00
    """
    rows: list[HillstromRow] = []
    rows += [_row("No E-Mail", conversion=c) for c in (1, 0, 0, 0)]
    rows += [_row("Mens E-Mail", conversion=c) for c in (1, 1, 1, 0)]
    rows += [_row("Womens E-Mail", conversion=c) for c in (1, 0, 0, 0)]
    return rows


# ── GROUND-TRUTH MATH (known answer) ───────────────────────────────────────────


def test_arm_uplift_difference_in_means_known_answer() -> None:
    rows = _known_frame()
    mens = compute_arm_uplift(rows, "Mens E-Mail", metric_name="conversion", n_resamples=200)
    assert mens.control_rate == pytest.approx(0.25)
    assert mens.treatment_rate == pytest.approx(0.75)
    assert mens.observed_lift == pytest.approx(0.50)
    assert mens.n_control == 4 and mens.n_treatment == 4
    # The bootstrap CI brackets the point estimate.
    lo, hi = mens.ci
    assert lo <= mens.observed_lift <= hi

    womens = compute_arm_uplift(rows, "Womens E-Mail", metric_name="conversion", n_resamples=200)
    assert womens.observed_lift == pytest.approx(0.0)


def test_arm_uplift_is_deterministic_for_a_fixed_seed() -> None:
    rows = _known_frame()
    a = compute_arm_uplift(rows, "Mens E-Mail", seed=7, n_resamples=200)
    b = compute_arm_uplift(rows, "Mens E-Mail", seed=7, n_resamples=200)
    assert a.ci == b.ci


def test_unknown_arm_raises() -> None:
    with pytest.raises(ValueError, match="unknown treatment arm"):
        compute_arm_uplift(_known_frame(), "No E-Mail")


def test_unsupported_metric_raises() -> None:
    with pytest.raises(ValueError, match="spend is continuous"):
        compute_arm_uplift(_known_frame(), "Mens E-Mail", metric_name="spend")


# ── PER-SEGMENT HETEROGENEITY ──────────────────────────────────────────────────


def test_segment_uplift_strata_are_matched_and_sorted() -> None:
    rows: list[HillstromRow] = []
    # mens-history stratum: control 0/2, treatment 2/2 → +1.0
    rows += [_row("No E-Mail", conversion=0, mens=1, womens=0) for _ in range(2)]
    rows += [_row("Mens E-Mail", conversion=1, mens=1, womens=0) for _ in range(2)]
    # womens-history stratum: control 1/2, treatment 1/2 → 0.0
    rows += [_row("No E-Mail", conversion=c, mens=0, womens=1) for c in (1, 0)]
    rows += [_row("Mens E-Mail", conversion=c, mens=0, womens=1) for c in (1, 0)]

    segs = compute_segment_uplift(rows, "Mens E-Mail", n_resamples=100)
    by_seg = {s.segment: s for s in segs}
    assert by_seg["mens_history"].observed_lift == pytest.approx(1.0)
    assert by_seg["womens_history"].observed_lift == pytest.approx(0.0)
    # stable sorted order so the pre-registration hash is reproducible
    assert [s.segment for s in segs] == sorted(s.segment for s in segs)


# ── BENCHMARK CASE SHAPE ───────────────────────────────────────────────────────


def test_build_case_is_well_formed_with_correct_ground_truth() -> None:
    rows = _known_frame()
    case = build_hillstrom_case(rows, "Mens E-Mail", metric_name="conversion", n_resamples=100)
    assert isinstance(case, BenchmarkCase)
    assert case.source == "hillstrom"
    assert case.case_id == "hillstrom:mens_email:conversion"
    assert isinstance(case.ground_truth, GroundTruth)
    assert case.ground_truth.metric_name == "conversion"
    assert case.ground_truth.control_metric == pytest.approx(0.25)
    assert case.ground_truth.treatment_metric == pytest.approx(0.75)
    assert case.ground_truth.observed_lift == pytest.approx(0.50)
    assert case.ground_truth.winner == "treatment"


def test_treatment_state_adds_exactly_the_email_body_copy_delta() -> None:
    """Control = no campaign e-mail; treatment = the SAME inbox plus an e-mail body
    component carrying the campaign copy — exactly one CHANGED copy delta."""
    case = build_hillstrom_case(_known_frame(), "Mens E-Mail", n_resamples=10)
    control_screens = {s.id for s in case.capability.reverse_figma.screens}
    treatment_screens = {s.id for s in case.hypothesis.proposed_figma.screens}
    # The treatment adds the promo e-mail screen on top of the unchanged inbox.
    assert "inbox" in control_screens
    assert treatment_screens - control_screens == {"promo_email"}
    # The added e-mail body component carries the campaign copy.
    email_screen = next(s for s in case.hypothesis.proposed_figma.screens if s.id == "promo_email")
    body = next(c for c in email_screen.components if c.id == EMAIL_BODY_COMPONENT_ID)
    assert body.text and "men's merchandise" in body.text


def test_rows_to_cases_enumerates_both_arms() -> None:
    cases = hillstrom_rows_to_cases(_known_frame(), metric_name="conversion", n_resamples=50)
    assert {c.case_id for c in cases} == {
        "hillstrom:mens_email:conversion",
        "hillstrom:womens_email:conversion",
    }


def test_visit_metric_path() -> None:
    """`visit` (the second registered v1 metric) flows through the same adapter."""
    rows: list[HillstromRow] = []
    rows += [_row("No E-Mail", conversion=0, visit=v) for v in (1, 0, 0, 0)]  # control 0.25
    rows += [_row("Mens E-Mail", conversion=0, visit=v) for v in (1, 1, 1, 1)]  # treat 1.0
    case = build_hillstrom_case(rows, "Mens E-Mail", metric_name="visit", n_resamples=100)
    assert case.case_id == "hillstrom:mens_email:visit"
    assert case.ground_truth.metric_name == "visit"
    assert case.ground_truth.observed_lift == pytest.approx(0.75)


def test_empty_rows_raises() -> None:
    with pytest.raises(ValueError, match="at least one row"):
        hillstrom_rows_to_cases([])
