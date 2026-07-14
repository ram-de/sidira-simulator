"""Tests for the train-then-serve direction calibrator (pivot Rewire-A).

Pure: no LLM, no R2. Covers the Platt fit/predict, the deadzone sign, and the
safety-first pre-partner default (no calibrator => never kill-eligible).
"""

from __future__ import annotations

import pytest

from sidira_simulator.services.calibration import (
    CalibratedDirection,
    PlattCalibrator,
    direction_confidence,
)

# Synthetic history where the panel signal genuinely tracks the real lift:
# positive signals really won, negative signals really lost.
_SIGNALS = [-0.9, -0.7, -0.5, -0.3, 0.3, 0.5, 0.7, 0.9]
_LIFTS = [-0.08, -0.05, -0.04, -0.02, 0.02, 0.04, 0.05, 0.08]


def _fit() -> PlattCalibrator:
    return PlattCalibrator.fit(_SIGNALS, _LIFTS)


# ── the calibrator learns the sign mapping ────────────────────────────────────


def test_fit_then_predict_tracks_sign():
    cal = _fit()
    hi_pos = cal.predict(0.9)
    hi_neg = cal.predict(-0.9)
    # a strong positive signal is confidently P(pos); a strong negative, P(neg)
    assert hi_pos.p_pos > hi_pos.p_neg
    assert hi_neg.p_neg > hi_neg.p_pos
    # probabilities are well-formed
    for p in (hi_pos, hi_neg):
        assert 0.0 <= p.p_pos <= 1.0 and 0.0 <= p.p_neg <= 1.0
        assert abs(p.p_pos + p.p_neg + p.p_flat - 1.0) < 1e-9


def test_confidence_is_monotone_in_signal():
    cal = _fit()
    # more-positive signal => at least as confident it's a positive (winner)
    weak = cal.predict(0.3).p_pos
    strong = cal.predict(0.9).p_pos
    assert strong >= weak


def test_fit_length_mismatch_raises():
    with pytest.raises(ValueError):
        PlattCalibrator.fit([0.1, 0.2], [0.01])


def test_empty_fit_degrades_not_raises():
    cal = PlattCalibrator.fit([], [])
    # identity coefficients => bare sigmoid, no crash
    probs = cal.predict(0.5)
    assert 0.0 <= probs.p_pos <= 1.0


def test_degenerate_constant_signal_predicts_prevalence():
    """codex P2: all-identical signals => intercept-only fit predicts the base
    rate, NOT the uninformative 0.5. Here 2/3 of the history is a positive win."""
    cal = PlattCalibrator.fit([0.0, 0.0, 0.0], [0.02, 0.03, -0.01])  # +, +, -
    probs = cal.predict(0.0)
    assert abs(probs.p_pos - 2.0 / 3.0) < 0.02
    assert abs(probs.p_neg - 1.0 / 3.0) < 0.02


# ── direction_confidence + the safety-first default ───────────────────────────


def test_uncalibrated_is_never_kill_eligible():
    """Pre-partner: no calibrator => is_calibrated False, no confidence."""
    r = direction_confidence(-0.9, calibrator=None)
    assert isinstance(r, CalibratedDirection)
    assert r.direction == "negative"  # sign is still read
    assert r.confidence is None  # but no calibrated confidence
    assert r.is_calibrated is False  # => the screen must not KILL


def test_deadzone_yields_no_direction():
    cal = _fit()
    r = direction_confidence(0.0, calibrator=cal, deadzone=0.05)
    assert r.direction is None  # in-band => abstain
    assert r.confidence is None


def test_calibrated_negative_carries_p_neg():
    cal = _fit()
    r = direction_confidence(-0.9, calibrator=cal)
    assert r.direction == "negative"
    assert r.is_calibrated is True
    assert r.confidence is not None
    # the negative-direction confidence IS P(neg)
    assert abs(r.confidence - cal.predict(-0.9).p_neg) < 1e-12


def test_calibrated_positive_carries_p_pos():
    cal = _fit()
    r = direction_confidence(0.9, calibrator=cal)
    assert r.direction == "positive"
    assert abs(r.confidence - cal.predict(0.9).p_pos) < 1e-12
