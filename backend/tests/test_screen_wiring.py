"""Rewire-C: the screen verdict is stamped onto the live result, flag-gated.

Regression: the eng-review required proof the live path emits a verdict when on,
and stays byte-identical (None) when off.
"""

from __future__ import annotations

from sidira_simulator.schemas.simulation import InputFlags, SimulationResult
from sidira_simulator.services.simulation_runner import (
    _stamp_screen_verdict,
    screen_v2_enabled,
)


def _result(**kw) -> SimulationResult:
    return SimulationResult(confidence_score=50.0, **kw)


def test_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("SIDIRA_SCREEN_V2", raising=False)
    assert screen_v2_enabled() is False


def test_flag_off_is_byte_identical(monkeypatch):
    monkeypatch.delenv("SIDIRA_SCREEN_V2", raising=False)
    r = _result(lift=-0.05)
    out = _stamp_screen_verdict(r)
    assert out is r  # unchanged object
    assert out.decision_verdict is None


def test_flag_on_emits_pass_for_a_lift_pre_partner(monkeypatch):
    monkeypatch.setenv("SIDIRA_SCREEN_V2", "1")
    out = _stamp_screen_verdict(_result(lift=-0.05))
    assert out.decision_verdict is not None
    # no calibrator pre-partner ⇒ a strong loser still cannot KILL
    assert out.decision_verdict.screen_action == "PASS"
    assert out.decision_verdict.source == "calibrated"


def test_flag_on_out_of_scope_abstains(monkeypatch):
    monkeypatch.setenv("SIDIRA_SCREEN_V2", "on")
    out = _stamp_screen_verdict(_result(lift=-0.05, instrument_scope="out_of_scope"))
    assert out.decision_verdict.screen_action == "ABSTAIN"


def test_flag_on_no_lift_abstains(monkeypatch):
    monkeypatch.setenv("SIDIRA_SCREEN_V2", "yes")
    out = _stamp_screen_verdict(_result(lift=None))  # single-arm run
    assert out.decision_verdict.screen_action == "ABSTAIN"


def test_flag_on_input_abstain_abstains(monkeypatch):
    monkeypatch.setenv("SIDIRA_SCREEN_V2", "1")
    flags = InputFlags(
        state="abstain",
        reasons=["under-specified"],
        reason_codes=["x"],
        fixes=[],
        paraphrase_unstable=False,
    )
    out = _stamp_screen_verdict(_result(lift=-0.05, input_flags=flags))
    assert out.decision_verdict.screen_action == "ABSTAIN"
