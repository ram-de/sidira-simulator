"""Tests for the KILL / PASS / ABSTAIN screen producer (pivot Rewire-B).

Pure: no LLM, no R2. Exercises the decision order and the safety-first KILL gate.
"""

from __future__ import annotations

import pytest

from sidira_simulator.services.calibration import PlattCalibrator
from sidira_simulator.services.screen import screen_verdict


def _cal() -> PlattCalibrator:
    # Panel lift IS the signal; the real observed outcome is the label. Cleanly
    # separated: negative lifts really lost, positive really won.
    sigs = [-0.09, -0.07, -0.05, -0.03, 0.03, 0.05, 0.07, 0.09]
    obs = [-0.10, -0.08, -0.06, -0.02, 0.02, 0.06, 0.08, 0.10]
    return PlattCalibrator.fit(sigs, obs)


# ── ABSTAIN: every "can't judge" path ────────────────────────────────────────


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(lift=-0.08, out_of_scope=True),  # instrument-fit gate
        dict(lift=-0.08, input_abstain=True),  # input lint
        dict(lift=None),  # single-arm, no comparison
        dict(lift=0.0, deadzone=0.05),  # in-deadzone no-op
    ],
)
def test_abstain_paths(kwargs):
    v = screen_verdict(calibrator=_cal(), kill_threshold=0.4, **kwargs)
    assert v.screen_action == "ABSTAIN"
    assert v.direction is None


# ── KILL: only a confident, calibrated loser ─────────────────────────────────


def test_kill_on_confident_calibrated_loser():
    v = screen_verdict(lift=-0.09, calibrator=_cal(), kill_threshold=0.4)
    assert v.screen_action == "KILL"
    assert v.direction == "negative"
    assert v.source == "calibrated"


def test_predicted_winner_passes():
    v = screen_verdict(lift=0.09, calibrator=_cal(), kill_threshold=0.4)
    assert v.screen_action == "PASS"
    assert v.direction == "positive"


# ── the safety-first guards: nothing kills without calibration + threshold ───


def test_uncalibrated_negative_never_kills():
    v = screen_verdict(lift=-0.09, calibrator=None, kill_threshold=0.4)
    assert v.screen_action == "PASS"  # strong loser, but uncalibrated


def test_no_threshold_never_kills():
    v = screen_verdict(lift=-0.09, calibrator=_cal(), kill_threshold=None)
    assert v.screen_action == "PASS"  # KILL disabled until an operating point is set


def test_threshold_boundary_is_exactly_the_gate():
    """Probe the `>=` gate at the achieved confidence: just above ⇒ PASS,
    just below ⇒ KILL. Robust to the fit (no hard-coded confidence)."""
    from sidira_simulator.services.calibration import direction_confidence

    cal = _cal()
    lift = -0.05
    conf = direction_confidence(lift, cal).confidence
    assert conf is not None
    above = screen_verdict(lift=lift, calibrator=cal, kill_threshold=conf + 0.01)
    below = screen_verdict(lift=lift, calibrator=cal, kill_threshold=conf - 0.01)
    assert above.screen_action == "PASS"  # threshold above achieved confidence
    assert below.screen_action == "KILL"  # threshold below it
