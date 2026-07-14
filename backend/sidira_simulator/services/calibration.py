"""Calibrated direction confidence — the pivot's one sanctioned complexity.

The screen derives a *direction* from ``sign(lift)`` (the A/B panel's
treatment-vs-control lean). Raw signal is a proven-unusable confidence (the
engine's most-confident calls were its biggest misses), so a KILL is gated on a
**calibrated** probability instead: the calibrator is fit on a client's real
``(panel_signal, observed_lift)`` history and then *serves* a calibrated
``P(sign)`` for a new signal. The KILL gate reads ``P(negative)``; PASS/ABSTAIN
never need it.

SAFETY-FIRST DEFAULT (FN ceiling before coverage):
    With NO fitted calibrator (the pre-partner reality), ``direction_confidence``
    returns ``is_calibrated=False`` and no probability. The screen MUST NOT KILL
    on that — it PASS/ABSTAINs. KILL turns on only once a calibrator is fit on
    real outcomes and an operating-point threshold is chosen (#609). So shipping
    this before a design partner exists is safe by construction: nothing kills.

Harvested from ``directional_gate``'s Platt cross-fit, which is EVAL-shaped
(cross-fit on records to compute honest ECE/tail-recall). This is the
TRAIN-then-SERVE shape the runtime needs: fit once on all training data, store
the coefficients, apply to new points.

NOTE (DRY): ``_platt_fit`` / ``_sigmoid`` are duplicated from ``directional_gate``
for now. ``directional_gate`` is an orphan slated for trimming (Rewire-D); at
that point its eval metrics import the Platt primitives from HERE (the survivor)
and the duplication is removed. Deferred, not forgotten.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence

Direction = Literal["positive", "negative"]


def _sign_dead(x: float, delta: float) -> int:
    """Deadzone sign: +1 above ``delta``, -1 below ``-delta``, 0 within the band.

    The deadzone keeps a near-zero lift (no meaningful effect) out of the KILL
    path — a treatment that neither clearly wins nor clearly loses has no sign,
    so the screen ABSTAINs rather than calling it.
    """
    if x > delta:
        return 1
    if x < -delta:
        return -1
    return 0


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def _platt_fit(
    signals: Sequence[float], labels: Sequence[int], iters: int = 100
) -> tuple[float, float]:
    """1-D logistic ``P(label=1) = sigmoid(a*x + b)`` via Newton's method.

    ``labels`` in {0,1}; pure stdlib (no sklearn). Returns ``(a, b)``. On empty
    input returns the identity ``(1.0, 0.0)`` so ``predict`` degrades to a bare
    sigmoid of the raw signal rather than raising.
    """
    a, b = 1.0, 0.0
    n = len(signals)
    if n == 0:
        return a, b
    # If the signal carries no variance (all identical, or n == 1) the slope is
    # unidentifiable — no line separates the labels. Fit INTERCEPT-ONLY to the
    # label prevalence (a=0, b=logit(mean)) instead of returning the uninformative
    # identity, which would serve 0.5 for a clearly-skewed history (e.g.
    # [0,0,0] -> [1,1,0] should predict ~2/3, not 0.5). (codex P2)
    if all(abs(s - signals[0]) < 1e-12 for s in signals):
        p_mean = min(max(sum(labels) / n, 1e-6), 1.0 - 1e-6)
        return 0.0, math.log(p_mean / (1.0 - p_mean))
    for _ in range(iters):
        g_a = g_b = h_aa = h_ab = h_bb = 0.0
        for x, y in zip(signals, labels):
            p = _sigmoid(a * x + b)
            w = max(p * (1 - p), 1e-9)
            err = p - y
            g_a += err * x
            g_b += err
            h_aa += w * x * x
            h_ab += w * x
            h_bb += w
        det = h_aa * h_bb - h_ab * h_ab
        if abs(det) < 1e-12:
            break  # weights saturated after convergence: keep the current (a, b)
        da = (g_a * h_bb - g_b * h_ab) / det
        db = (h_aa * g_b - h_ab * g_a) / det
        a -= da
        b -= db
        if abs(da) < 1e-8 and abs(db) < 1e-8:
            break
    return a, b


@dataclass(frozen=True)
class DirectionProbabilities:
    """Calibrated one-vs-rest sign probabilities. ``p_flat`` is the residual."""

    p_pos: float
    p_neg: float
    p_flat: float


@dataclass(frozen=True)
class PlattCalibrator:
    """Two one-vs-rest Platt logistics: P(sign=+1) and P(sign=-1).

    Fit on a client's real ``(signal, observed_lift)`` history; ``P(flat)`` is the
    renormalised residual. Frozen + serialisable (four floats) so a fitted
    calibrator can be persisted per client and reloaded to serve KILL decisions.
    """

    a_pos: float
    b_pos: float
    a_neg: float
    b_neg: float

    @classmethod
    def fit(
        cls,
        signals: Sequence[float],
        observed_lifts: Sequence[float],
        *,
        deadzone: float = 0.0,
    ) -> "PlattCalibrator":
        """Fit on paired ``(panel signal, real observed lift)``.

        The real lift is reduced to a class label via the same deadzone the screen
        uses, so the calibrator learns ``P(this signal really won / really lost)``.
        """
        if len(signals) != len(observed_lifts):
            raise ValueError("signals and observed_lifts must be the same length")
        signs = [_sign_dead(o, deadzone) for o in observed_lifts]
        a_p, b_p = _platt_fit(signals, [int(s == 1) for s in signs])
        a_n, b_n = _platt_fit(signals, [int(s == -1) for s in signs])
        return cls(a_p, b_p, a_n, b_n)

    def predict(self, signal: float) -> DirectionProbabilities:
        pp = _sigmoid(self.a_pos * signal + self.b_pos)
        pn = _sigmoid(self.a_neg * signal + self.b_neg)
        s = pp + pn
        if s > 1.0:  # renormalise the two OvR heads so they leave room for flat
            pp, pn = pp / s, pn / s
        return DirectionProbabilities(pp, pn, max(0.0, 1.0 - pp - pn))


@dataclass(frozen=True)
class CalibratedDirection:
    """The screen's direction read for one variant.

    - ``direction``: ``sign(signal)`` via the deadzone, or None (in-band ⇒ abstain).
    - ``confidence``: calibrated ``P(direction)``; None when uncalibrated OR no
      direction. A KILL requires ``is_calibrated and direction == "negative" and
      confidence >= threshold`` — the caller enforces the threshold.
    - ``is_calibrated``: whether a fitted calibrator was applied. False ⇒ the
      screen must NOT kill (safety-first).
    """

    direction: Direction | None
    confidence: float | None
    is_calibrated: bool


def direction_confidence(
    signal: float,
    calibrator: PlattCalibrator | None,
    *,
    deadzone: float = 0.0,
) -> CalibratedDirection:
    """Map a raw panel signal to a (direction, calibrated confidence) read.

    With ``calibrator is None`` (pre-partner) the result carries
    ``is_calibrated=False`` and ``confidence=None`` — the screen cannot KILL, by
    design. A signal inside the deadzone has ``direction=None`` (abstain).
    """
    s = _sign_dead(signal, deadzone)
    direction: Direction | None = (
        "positive" if s == 1 else "negative" if s == -1 else None
    )
    if calibrator is None or direction is None:
        return CalibratedDirection(
            direction=direction,
            confidence=None,
            is_calibrated=calibrator is not None,
        )
    probs = calibrator.predict(signal)
    confidence = probs.p_pos if direction == "positive" else probs.p_neg
    return CalibratedDirection(
        direction=direction, confidence=confidence, is_calibrated=True
    )


__all__ = [
    "Direction",
    "DirectionProbabilities",
    "PlattCalibrator",
    "CalibratedDirection",
    "direction_confidence",
]
