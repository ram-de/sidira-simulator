"""The screen producer — turns a finished A/B panel into KILL / PASS / ABSTAIN.

This is the pivot's live verdict path (replacing the deleted grounded shadow
flow). It is a PURE function of the panel's signed ``lift`` plus the structural
abstain signals; the caller (the runner, Rewire-C) extracts those from the
``SimulationResult`` and persists the returned verdict into ``result_json``.

    lift + abstain-signals ──▶ direction_confidence ──▶ DirectionVerdict
                                     (calibrator)          (screen_action:
                                                            KILL/PASS/ABSTAIN)

Decision order (structural abstains first, then the calibrated KILL gate):

    out_of_scope / input_abstain / no A/B lift / in-deadzone  ──▶ ABSTAIN
    negative sign, CALIBRATED, confidence ≥ kill_threshold    ──▶ KILL
    everything else (predicted winner, or unconfident loser)  ──▶ PASS

SAFETY-FIRST (FN ceiling before coverage): a KILL requires ALL of a negative
sign, a *fitted* calibrator (``is_calibrated``), a configured ``kill_threshold``,
and calibrated confidence ≥ that threshold. Pre-partner (no calibrator / no
threshold) NOTHING kills — the screen only PASS/ABSTAINs. So this is safe to ship
before a design partner exists.
"""

from __future__ import annotations

from sidira_simulator.schemas.verdict import DirectionVerdict
from sidira_simulator.services.calibration import PlattCalibrator, direction_confidence


def _abstain(reason: str) -> DirectionVerdict:
    return DirectionVerdict(
        direction=None,
        caution="hard",
        confidence="low",
        label=reason,
        source="calibrated",
    )


def screen_verdict(
    *,
    lift: float | None,
    out_of_scope: bool = False,
    input_abstain: bool = False,
    calibrator: PlattCalibrator | None = None,
    deadzone: float = 0.0,
    kill_threshold: float | None = None,
) -> DirectionVerdict:
    """Map a finished A/B panel to a KILL / PASS / ABSTAIN ``DirectionVerdict``.

    Args:
        lift: the panel's signed treatment-vs-control lift. ``None`` for a
            single-arm run (no comparison) → ABSTAIN.
        out_of_scope: the instrument-fit gate said this OEC is not answerable by
            a first-exposure panel → ABSTAIN.
        input_abstain: the input lint said the hypothesis is too under-specified
            to judge → ABSTAIN.
        calibrator: the client's fitted calibrator, or ``None`` pre-partner.
        deadzone: |lift| within this band ⇒ no direction ⇒ ABSTAIN (a no-op change).
        kill_threshold: the operating-point τ chosen on held-out winners (#609).
            ``None`` ⇒ KILL disabled (no confident-kill without a chosen point).
    """
    # ── structural abstains: we can't judge → run the real test ──
    if out_of_scope:
        return _abstain("not answerable by this instrument — run the test")
    if input_abstain:
        return _abstain("hypothesis under-specified — run the test")
    if lift is None:
        return _abstain("no A/B comparison — run the test")

    cd = direction_confidence(lift, calibrator, deadzone=deadzone)
    if cd.direction is None:
        return _abstain("no meaningful difference — run the test")

    # ── the calibrated KILL gate: confident the treatment will NOT win ──
    if (
        cd.direction == "negative"
        and cd.is_calibrated
        and kill_threshold is not None
        and cd.confidence is not None
        and cd.confidence >= kill_threshold
    ):
        return DirectionVerdict(
            direction="negative",
            caution="none",
            confidence="high",
            label="don't run — this variant is likely to lose",
            source="calibrated",
        )

    # ── PASS: a predicted winner, or a not-confident-enough loser → run it ──
    return DirectionVerdict(
        direction=cd.direction,
        caution="moderate",
        confidence="low",
        label="run the test",
        source="calibrated",
    )


__all__ = ["screen_verdict"]
