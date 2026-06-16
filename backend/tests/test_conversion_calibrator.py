"""Tests for the #221 conversion-lift calibration seam (shrinkage layer).

Covers:
- `IdentityCalibrator` is a true no-op (output == input, `calibrated=False`,
  never the same instance — honors the no-mutation contract),
- `resolve_conversion_calibrator` defaults to identity and fails OPEN to
  identity on an unknown env value (so a bad env can't silently transform or
  mark a number calibrated),
- `aggregate_conversion_lift` routes through the calibrator (default identity →
  byte-identical magnitude + `calibrated=False`; an injected fitted calibrator
  reaches the returned result),
- the `calibrated` flag threads through `score_ab` end-to-end, and
- `conversion_lift_honesty` softens the magnitude caveat only when calibrated.
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.scoring import (
    ConversionLiftResult,
    ScoringConfig,
)
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.conversion_calibrator import (
    ConversionCalibrator,
    IdentityCalibrator,
    resolve_conversion_calibrator,
)
from sidira_simulator.services.scoring import (
    AgentReaction,
    ScoringService,
    aggregate_conversion_lift,
    conversion_lift_honesty,
)

_NO_CI_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=0)


def _r(
    *,
    persona_id: str,
    arm: str,
    metric_p: float | None,
    sample_index: int = 0,
) -> AgentReaction:
    return AgentReaction(
        agent_id=f"{arm}-{persona_id}-{sample_index}",
        persona_id=persona_id,
        persona_name=persona_id,
        reaction_text="r",
        sample_index=sample_index,
        arm=arm,
        metric_p=metric_p,
    )


class _DoublingCalibrator:
    """A stand-in FITTED calibrator: doubles the lift and flags calibrated.

    Used only in tests to prove the aggregation actually routes through the
    seam; no fitted calibrator ships pre-#222.
    """

    def calibrate(self, result: ConversionLiftResult) -> ConversionLiftResult:
        new_pp = None if result.lift_pp is None else result.lift_pp * 2
        return result.model_copy(update={"lift_pp": new_pp, "calibrated": True})


# ── IdentityCalibrator ────────────────────────────────────────────────────────


def test_identity_calibrator_is_a_noop() -> None:
    raw = ConversionLiftResult(lift_pp=12.5, lift_ci_pp=(5.0, 20.0), paired_n=8)
    out = IdentityCalibrator().calibrate(raw)

    assert out == raw  # values byte-identical
    assert out.calibrated is False  # never claims calibration
    assert out is not raw  # returns a copy — no mutation of the input


def test_identity_calibrator_preserves_none_lift() -> None:
    raw = ConversionLiftResult()  # degenerate / no usable pairs
    out = IdentityCalibrator().calibrate(raw)

    assert out.lift_pp is None
    assert out.calibrated is False


def test_identity_calibrator_satisfies_protocol() -> None:
    assert isinstance(IdentityCalibrator(), ConversionCalibrator)


# ── resolve_conversion_calibrator ─────────────────────────────────────────────


def test_factory_defaults_to_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIDIRA_CONVERSION_CALIBRATOR", raising=False)
    monkeypatch.delenv("PYTHIA_CONVERSION_CALIBRATOR", raising=False)
    assert isinstance(resolve_conversion_calibrator(), IdentityCalibrator)


def test_factory_explicit_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIDIRA_CONVERSION_CALIBRATOR", "identity")
    assert isinstance(resolve_conversion_calibrator(), IdentityCalibrator)


def test_factory_unknown_value_fails_open_to_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIDIRA_CONVERSION_CALIBRATOR", "some-unfit-shrinkage")
    # Unknown name (no fitted calibrator exists pre-#222) → identity, never a
    # guessed transform and never `calibrated=True`.
    cal = resolve_conversion_calibrator()
    assert isinstance(cal, IdentityCalibrator)
    out = cal.calibrate(ConversionLiftResult(lift_pp=9.0))
    assert out.lift_pp == 9.0
    assert out.calibrated is False


# ── aggregate_conversion_lift routing ─────────────────────────────────────────


def test_aggregate_default_calibrator_is_identity() -> None:
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.5) for i in range(4)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.2) for i in range(4)]
    res = aggregate_conversion_lift(treatment, control, _NO_CI_CFG)

    # (0.5 - 0.2) * 100 = 30.0 pp, magnitude untouched, not marked calibrated.
    assert res.lift_pp == pytest.approx(30.0)
    assert res.calibrated is False


def test_aggregate_routes_through_injected_calibrator() -> None:
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.5) for i in range(4)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.2) for i in range(4)]
    res = aggregate_conversion_lift(
        treatment, control, _NO_CI_CFG, calibrator=_DoublingCalibrator()
    )

    # The fitted stand-in doubled the raw 30.0 pp and flagged calibration.
    assert res.lift_pp == pytest.approx(60.0)
    assert res.calibrated is True


def test_aggregate_no_pairs_still_calibrates_without_inventing_a_lift() -> None:
    # No matched pairs → lift not computable; identity leaves it None + uncalibrated.
    treatment = [_r(persona_id="p0", arm="treatment", metric_p=0.5)]
    control = [_r(persona_id="p9", arm="control", metric_p=0.2)]
    res = aggregate_conversion_lift(treatment, control, _NO_CI_CFG)

    assert res.paired_n == 0
    assert res.lift_pp is None
    assert res.calibrated is False


# ── score_ab end-to-end flag threading ────────────────────────────────────────


@pytest.mark.asyncio
async def test_score_ab_threads_calibrated_false_on_conversion_run() -> None:
    # Reuse the §3a conversion scaffolding (scripted chat + conversion hypothesis).
    from tests.test_conversion_lift import _conversion_hypothesis, _ScriptedChat

    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=0.5) for i in range(3)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=0.2) for i in range(3)]

    service = ScoringService(chat_client=_ScriptedChat())
    result, _ = await service.score_ab(
        _conversion_hypothesis(), treatment, control, run_seed=7, config=_NO_CI_CFG
    )

    # Default identity calibrator → flag present and False (never silently absent).
    assert result.metric_lift_calibrated is False
    assert result.metric_lift_pp is not None


@pytest.mark.asyncio
async def test_score_ab_no_metric_leaves_calibrated_flag_default() -> None:
    # Non-conversion run: the flag stays at its schema default (backwards-compat).
    from tests.test_conversion_lift import _ScriptedChat

    hypothesis = Hypothesis(capability_name="reorder", prose="test")  # no metric
    treatment = [_r(persona_id=f"p{i}", arm="treatment", metric_p=None) for i in range(3)]
    control = [_r(persona_id=f"p{i}", arm="control", metric_p=None) for i in range(3)]

    service = ScoringService(chat_client=_ScriptedChat())
    result, _ = await service.score_ab(
        hypothesis, treatment, control, run_seed=7, config=_NO_CI_CFG
    )

    assert result.metric_lift_calibrated is False
    assert result.metric_lift_pp is None


# ── conversion_lift_honesty caveat gating ─────────────────────────────────────


def test_honesty_uncalibrated_caveat_when_not_calibrated() -> None:
    raw = ConversionLiftResult(lift_pp=10.0, paired_n=5, calibrated=False)
    _regime, relative = conversion_lift_honesty(raw)
    assert relative is not None
    assert "not as a calibrated effect size" in relative
    assert "shrinkage layer" not in relative


def test_honesty_softens_caveat_when_calibrated() -> None:
    calibrated = ConversionLiftResult(lift_pp=10.0, paired_n=5, calibrated=True)
    _regime, relative = conversion_lift_honesty(calibrated)
    assert relative is not None
    assert "Magnitude calibrated" in relative
    assert "not as a calibrated effect size" not in relative
