"""#5 Activity weighting — normalizer tests (consumer side).

Covers the conservative recipe: coverage gate, log1p transform, mean-1.0
normalization with imputation, and clamping. The scorer-mechanism tests live in
test_scoring.py; these pin the pure data transform.
"""

from __future__ import annotations

import math

import pytest

from sidira_simulator.services.activity_weight import (
    CLAMP_HI,
    CLAMP_LO,
    COVERAGE_FLOOR,
    normalize_activity_weights,
)


def test_empty_input_returns_empty() -> None:
    assert normalize_activity_weights([]) == []


def test_all_missing_is_uniform() -> None:
    assert normalize_activity_weights([None, None, None]) == [1.0, 1.0, 1.0]


def test_equal_signals_are_uniform() -> None:
    out = normalize_activity_weights([5.0, 5.0, 5.0, 5.0])
    assert all(w == pytest.approx(1.0) for w in out)


def test_all_zero_signal_is_uniform() -> None:
    # log1p(0)=0 ⇒ degenerate mean ⇒ abstain from weighting.
    assert normalize_activity_weights([0.0, 0.0]) == [1.0, 1.0]


def test_mean_is_approximately_one_when_unclamped() -> None:
    # Spread small enough that log1p keeps every weight inside the clamp, so the
    # mean-1.0 property is observable exactly.
    out = normalize_activity_weights([4.0, 6.0, 8.0, 10.0])
    assert sum(out) / len(out) == pytest.approx(1.0)
    assert all(CLAMP_LO <= w <= CLAMP_HI for w in out)


def test_more_active_cohort_gets_more_weight() -> None:
    out = normalize_activity_weights([1.0, 100.0])
    assert out[1] > out[0]
    # log1p tames it: a 100× raw gap is nowhere near a 100× weight gap.
    assert out[1] / out[0] < 100.0


def test_coverage_gate_below_floor_goes_uniform() -> None:
    # 1 of 5 present = 20% < 80% floor ⇒ uniform, even though the one signal is huge.
    raw = [1000.0, None, None, None, None]
    assert len(raw) == 5 and (1 / 5) < COVERAGE_FLOOR
    assert normalize_activity_weights(raw) == [1.0] * 5


def test_coverage_gate_at_or_above_floor_weights() -> None:
    # 4 of 5 present = 80% ⇒ at the floor ⇒ weighting applies (not all 1.0).
    raw = [2.0, 20.0, 50.0, 80.0, None]
    out = normalize_activity_weights(raw)
    assert out != [1.0] * 5
    # The imputed (missing) member sits near the center.
    assert CLAMP_LO <= out[4] <= CLAMP_HI


def test_extreme_outlier_is_clamped() -> None:
    out = normalize_activity_weights([1.0, 1.0, 1.0, 1.0, 10_000_000.0])
    assert max(out) == pytest.approx(CLAMP_HI)
    assert min(out) >= CLAMP_LO


def test_negative_and_nan_treated_as_missing() -> None:
    # Negatives / NaN are invalid; here only 1 of 3 is valid ⇒ coverage gate ⇒ uniform.
    assert normalize_activity_weights([-5.0, float("nan"), 3.0]) == [1.0, 1.0, 1.0]
