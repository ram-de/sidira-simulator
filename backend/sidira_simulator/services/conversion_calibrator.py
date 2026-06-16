"""Conversion-lift calibration seam (agent-behavior-spec #221 / shrinkage layer).

The §3a/§3e conversion pass produces a RAW paired lift in percentage points
(`ConversionLiftResult.lift_pp`). That number is honest as a rank/direction
signal, but its MAGNITUDE is uncalibrated — synthetic conversion is a weak
behavioral regime, and LLM agents systematically inflate stated propensities
(the Hewitt inflation). The fix is a learned shrinkage layer that maps the raw
synthetic lift onto the real-world effect-size scale, FIT against the
benchmark's predicted-vs-actual outcome pairs.

That fit is #222-gated: it needs the Tier-0 benchmark's outcome data, which does
not exist yet. This module ships only the SEAM — a typed calibrator interface
plus a default no-op `IdentityCalibrator` — so the conversion-lift aggregation
already routes its result through a calibrator. When #222 produces a fitted
shrinkage, it drops in here behind `resolve_conversion_calibrator()` WITHOUT
touching the elicitation or scoring call sites.

Honesty contract: a calibrator MUST set `ConversionLiftResult.calibrated` to
True only when it has applied a real, fitted transform. The identity calibrator
leaves it False, so `conversion_lift_honesty` keeps the "uncalibrated — read as
rank/direction, not effect size" caveat. An uncalibrated number is therefore
never presented as calibrated.

This is deliberately NOT the unrelated `scoring.py` sentiment shrinkage (the
Bayesian-toward-0.5 confidence shrink); this seam calibrates the conversion-lift
magnitude only.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import structlog

from sidira_simulator.schemas.scoring import MetricLiftResult
from sidira_simulator.services.runtime_config import resolve_sidira_env

log = structlog.get_logger()

# The only calibrator implemented today. #222 registers fitted calibrators here.
IDENTITY_CALIBRATOR = "identity"


@runtime_checkable
class MetricCalibrator(Protocol):
    """Maps a RAW metric-lift result onto the calibrated effect-size scale (#275).

    Metric-agnostic (#275): the same protocol calibrates conversion, retention,
    and future metrics — each resolves its own calibrator by name. Implementations
    MUST be pure (no I/O, deterministic) and MUST NOT mutate the input — return a
    new `MetricLiftResult`. A real fitted calibrator sets `calibrated=True` on its
    output; the identity no-op leaves it False so the raw magnitude keeps its
    uncalibrated caveat.
    """

    def calibrate(self, result: MetricLiftResult) -> MetricLiftResult: ...


# Backwards-compatible alias: the conversion-specific protocol name still imported
# by some call sites/tests. Identical — #275 made the protocol metric-agnostic.
ConversionCalibrator = MetricCalibrator


class IdentityCalibrator:
    """No-op calibrator: the raw lift IS the output, `calibrated` stays False.

    The wired default for EVERY metric until #222 fits a shrinkage layer, so
    production metric-lift numbers are byte-identical to the pre-seam path.
    Returns a copy (never the same instance) to honor the no-mutation contract,
    and never sets `calibrated=True`.
    """

    def calibrate(self, result: MetricLiftResult) -> MetricLiftResult:
        return result.model_copy()


def resolve_metric_calibrator(metric_name: str) -> MetricCalibrator:
    """Select the lift calibrator for `metric_name` (default: identity no-op; #275).

    Reads `SIDIRA_<METRIC>_CALIBRATOR` (legacy `PYTHIA_` fallback), e.g.
    `SIDIRA_CONVERSION_CALIBRATOR` / `SIDIRA_RETENTION_CALIBRATOR`. Today the only
    registered calibrator is ``identity`` (every metric defaults to it). #222 will
    register fitted shrinkage calibrators by name in the dispatch seam below. An
    unset, blank, or UNKNOWN value fails OPEN to the identity no-op (and logs), so
    a bad deployment env can never silently apply an unintended transform — or,
    worse, mark an uncalibrated number as calibrated. A fitted calibrator must be
    an explicit, named, shipped artifact.
    """
    env_suffix = f"{metric_name.upper()}_CALIBRATOR"
    name = (
        (resolve_sidira_env(env_suffix, IDENTITY_CALIBRATOR) or IDENTITY_CALIBRATOR).strip().lower()
    )
    if name != IDENTITY_CALIBRATOR:
        # #222 seam: register fitted calibrators in a dispatch table here. Until
        # one exists, an unknown name is a misconfiguration — fail open to the
        # identity no-op rather than guess at a transform.
        log.warning(
            "unknown_metric_calibrator_failing_open_to_identity",
            metric=metric_name,
            requested=name,
        )
    return IdentityCalibrator()


def resolve_conversion_calibrator() -> MetricCalibrator:
    """Back-compat: the conversion metric's calibrator (#275 → resolve_metric_calibrator)."""
    return resolve_metric_calibrator("conversion")
