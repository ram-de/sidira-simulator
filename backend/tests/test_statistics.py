"""Tests for services/statistics.py — Wilson + bootstrap helpers.

Hand-computed Wilson values are the source of truth (no scipy dep).
Each value was computed against the closed-form formula and verified
against known scipy outputs once during plan authoring — preserved
here as constants so the test suite remains scipy-free.
"""

from __future__ import annotations

import math
import random

import pytest

from pythia_simulator.services.statistics import (
    bootstrap_percentile_ci,
    wilson_interval,
)


# ── Wilson interval ─────────────────────────────────────────────────────


def test_wilson_matches_known_values() -> None:
    """Three hand-computed cases pinned to 4 decimal places."""
    # p̂ = 0.5, symmetric interval
    lo, hi = wilson_interval(5, 10)
    assert lo == pytest.approx(0.2366, abs=1e-4)
    assert hi == pytest.approx(0.7634, abs=1e-4)

    # k=0: lower bound hits 0
    lo, hi = wilson_interval(0, 10)
    assert lo == pytest.approx(0.0000, abs=1e-4)
    assert hi == pytest.approx(0.2775, abs=1e-4)

    # k=n: upper bound hits 1
    lo, hi = wilson_interval(10, 10)
    assert lo == pytest.approx(0.7225, abs=1e-4)
    assert hi == pytest.approx(1.0000, abs=1e-4)


def test_wilson_clamps_to_unit_interval() -> None:
    """Boundary cases must stay inside [0, 1] — no negative, no >1."""
    for k, n in [(0, 1), (1, 1), (0, 100), (100, 100), (1, 2)]:
        lo, hi = wilson_interval(k, n)
        assert 0.0 <= lo <= hi <= 1.0, f"out-of-range CI for k={k}, n={n}: ({lo}, {hi})"


def test_wilson_n1_extreme_intervals() -> None:
    """n=1 produces very wide but valid intervals (locked from /plan-eng-review T1a)."""
    lo, hi = wilson_interval(0, 1)
    assert lo == pytest.approx(0.0000, abs=1e-4)
    assert hi == pytest.approx(0.7935, abs=1e-4)
    assert hi - lo > 0.5  # genuinely wide

    lo, hi = wilson_interval(1, 1)
    assert lo == pytest.approx(0.2065, abs=1e-4)
    assert hi == pytest.approx(1.0000, abs=1e-4)
    assert hi - lo > 0.5


def test_wilson_rejects_invalid_inputs() -> None:
    """Defensive: n<=0 and k outside [0, n] raise rather than silently corrupting."""
    with pytest.raises(ValueError):
        wilson_interval(0, 0)
    with pytest.raises(ValueError):
        wilson_interval(-1, 10)
    with pytest.raises(ValueError):
        wilson_interval(11, 10)


# ── Bootstrap percentile CI ─────────────────────────────────────────────


def _mean(xs):
    return sum(xs) / len(xs)


def test_bootstrap_deterministic_given_rng() -> None:
    """Two calls with separately-constructed Random(42) rngs produce identical CIs."""
    data = [0.1, 0.4, 0.5, 0.6, 0.9, 0.3, 0.7, 0.2, 0.8, 0.5]
    ci_a = bootstrap_percentile_ci(
        data, _mean, n_resamples=500, rng=random.Random(42)
    )
    ci_b = bootstrap_percentile_ci(
        data, _mean, n_resamples=500, rng=random.Random(42)
    )
    assert ci_a == ci_b


def test_bootstrap_50_narrower_than_6() -> None:
    """The calibration promise: more agents → tighter CI.

    Construct a 50-element sample with mean ≈ 0.5 and a 6-element sample
    with the same mean. Bootstrap CI on n=50 must be strictly narrower
    than on n=6.
    """
    big = [0.0, 1.0] * 25  # 50 elements, mean 0.5
    small = [0.0, 1.0] * 3  # 6 elements, mean 0.5
    ci_big = bootstrap_percentile_ci(
        big, _mean, n_resamples=1000, rng=random.Random(7)
    )
    ci_small = bootstrap_percentile_ci(
        small, _mean, n_resamples=1000, rng=random.Random(7)
    )
    width_big = ci_big[1] - ci_big[0]
    width_small = ci_small[1] - ci_small[0]
    assert width_big < width_small, (
        f"n=50 CI width {width_big} should be strictly narrower than "
        f"n=6 CI width {width_small}"
    )


def test_bootstrap_n1_returns_degenerate_ci() -> None:
    """Single-element input: every resample picks the same element, so CI collapses
    to a point. Locked from /plan-eng-review T1b."""
    ci = bootstrap_percentile_ci(
        [0.42], _mean, n_resamples=100, rng=random.Random(0)
    )
    assert ci == (0.42, 0.42)


def test_bootstrap_rejects_invalid_inputs() -> None:
    """Defensive: empty data, zero resamples, bad confidence."""
    rng = random.Random(0)
    with pytest.raises(ValueError):
        bootstrap_percentile_ci([], _mean, rng=rng)
    with pytest.raises(ValueError):
        bootstrap_percentile_ci([1.0], _mean, n_resamples=0, rng=rng)
    with pytest.raises(ValueError):
        bootstrap_percentile_ci([1.0], _mean, confidence=0.0, rng=rng)
    with pytest.raises(ValueError):
        bootstrap_percentile_ci([1.0], _mean, confidence=1.0, rng=rng)


def test_bootstrap_ci_brackets_sample_mean_under_iid() -> None:
    """For a roughly symmetric data set, the CI should bracket the sample mean
    in the vast majority of runs. Sanity check that we're not off by orders
    of magnitude or returning the wrong percentiles."""
    rng = random.Random(123)
    data = [rng.gauss(0.5, 0.1) for _ in range(40)]
    sample_mean = _mean(data)
    ci = bootstrap_percentile_ci(
        data, _mean, n_resamples=1000, rng=random.Random(123)
    )
    assert ci[0] <= sample_mean <= ci[1]
    # And the CI should be much narrower than the data range
    assert (ci[1] - ci[0]) < 0.2
