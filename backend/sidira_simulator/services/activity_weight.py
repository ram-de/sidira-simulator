"""#5 Activity weighting (MiroFish-borrow) — the simulator's CONSUMER side.

The producer (sidira-personas) emits a RAW measured activity magnitude per
cohort on `Persona.activity_signal` (e.g. mean sessions/week). This module turns
a run's raw signals into per-agent scorer weights, conservatively, so the score
can't be quietly distorted by a noisy or partially-present signal:

  1. Sanitize — keep only finite, non-negative values; everything else is missing.
  2. Coverage gate — if fewer than COVERAGE_FLOOR of the agents carry a real
     signal, return all-1.0 (uniform). A half-weighted run would look more
     precise than it is; better to abstain from weighting entirely.
  3. Transform — log1p, because activity counts/frequencies are heavy-tailed; a
     2× more active cohort should not get 2× the scorer mass.
  4. Normalize — divide by the mean so the weights average 1.0 and the overall
     score scale is preserved (only the RELATIVE cohort pull shifts). Missing
     values are imputed to the center ⇒ weight ≈ 1.0.
  5. Clamp — bound to [CLAMP_LO, CLAMP_HI] so one runaway cohort can't dominate.

Pure and deterministic. Design consulted with codex (gpt-5.5), 2026-06-19:
honest uniform weighting beats a plausible-but-uncalibrated guess, so the
simulator never infers the signal — it only tames what the producer measured.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

# At least this fraction of agents must carry a real signal, else go uniform.
COVERAGE_FLOOR = 0.8
# Post-normalization bounds on any single agent's weight.
CLAMP_LO = 0.5
CLAMP_HI = 2.0


def _valid(x: float | None) -> bool:
    return x is not None and math.isfinite(x) and x >= 0.0


def normalize_activity_weights(raw_signals: Sequence[float | None]) -> list[float]:
    """Map a run's raw `Persona.activity_signal` values to scorer weights.

    Returns a list aligned 1:1 with `raw_signals`, each in [CLAMP_LO, CLAMP_HI]
    and averaging ~1.0. Returns all-1.0 (uniform, byte-identical to no weighting)
    when there is no usable signal — empty input, coverage below the floor, or a
    degenerate transform (all zeros).
    """
    n = len(raw_signals)
    if n == 0:
        return []

    valid_idx = [i for i, x in enumerate(raw_signals) if _valid(x)]
    if len(valid_idx) / n < COVERAGE_FLOOR:
        return [1.0] * n

    # log1p the present signals; impute the (few) missing ones to the valid mean
    # so they normalize to ~1.0 rather than dragging the distribution.
    transformed = {i: math.log1p(float(raw_signals[i])) for i in valid_idx}  # type: ignore[arg-type]
    valid_mean_t = sum(transformed.values()) / len(valid_idx)

    full = [transformed.get(i, valid_mean_t) for i in range(n)]
    mean_t = sum(full) / n
    if mean_t <= 0.0:
        # Degenerate (e.g. every signal is 0.0) — nothing to separate cohorts by.
        return [1.0] * n

    weights = [t / mean_t for t in full]
    return [min(CLAMP_HI, max(CLAMP_LO, w)) for w in weights]
