"""Pure-Python statistical helpers used by the scoring service.

Two helpers, both dependency-free (no scipy, no numpy):

- `wilson_interval(k, n)` — closed-form 95% Wilson score interval for a
  Binomial proportion. Used to bracket each `Weakness.frequency` with
  `ci_low` / `ci_high`.

- `bootstrap_percentile_ci(data, statistic, ...)` — generic
  percentile-bootstrap CI. Used to bracket `SimulationResult.confidence_score`
  by resampling per-agent contributions and recomputing the aggregate.

Why pure Python: keeps the runtime deploy tree small (no scipy in deps —
weights ~50MB) and keeps the math auditable from the code alone. The
hand-computed values in `test_statistics.py` pin correctness against
known-good outputs.
"""

from __future__ import annotations

import math
import random
from typing import Callable, Sequence, TypeVar

T = TypeVar("T")


def wilson_interval(k: int, n: int, *, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a Binomial proportion p̂ = k/n.

    Closed-form, well-behaved at k=0 and k=n (unlike Wald, which collapses
    to a zero-width interval at the boundaries). z=1.96 → two-sided 95%.

    Raises ValueError on n <= 0 or k outside [0, n].
    """
    if n <= 0:
        raise ValueError(f"wilson_interval requires n > 0, got n={n}")
    if k < 0 or k > n:
        raise ValueError(f"wilson_interval requires 0 <= k <= n, got k={k}, n={n}")

    p_hat = k / n
    denom = 1.0 + (z * z) / n
    center = (p_hat + (z * z) / (2.0 * n)) / denom
    spread = (
        z * math.sqrt(p_hat * (1.0 - p_hat) / n + (z * z) / (4.0 * n * n))
    ) / denom

    ci_low = max(0.0, center - spread)
    ci_high = min(1.0, center + spread)
    return ci_low, ci_high


def bootstrap_percentile_ci(
    data: Sequence[T],
    statistic: Callable[[Sequence[T]], float],
    *,
    n_resamples: int = 1000,
    confidence: float = 0.95,
    rng: random.Random,
) -> tuple[float, float]:
    """Generic percentile-bootstrap CI. Caller owns the RNG.

    Resamples `data` with replacement `n_resamples` times, applies
    `statistic` to each resample, and returns the (lower, upper)
    percentile bounds of the resulting distribution.

    NOTE: percentile bootstrap is biased at small N (n<10). Acceptable
    for Phase 2.5 — the bias is small relative to upstream LLM
    classification noise. Layer-3 calibration TODO: revisit with BCa
    (bias-corrected accelerated bootstrap).

    Raises ValueError on empty `data` or `n_resamples < 1` or
    `confidence` outside (0, 1).
    """
    if not data:
        raise ValueError("bootstrap_percentile_ci requires non-empty data")
    if n_resamples < 1:
        raise ValueError(f"n_resamples must be >= 1, got {n_resamples}")
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence must be in (0, 1), got {confidence}")

    n = len(data)
    samples = [statistic(rng.choices(data, k=n)) for _ in range(n_resamples)]
    samples.sort()

    # Nearest-rank percentile (symmetric): index k_p = ceil(p * B) - 1.
    # Earlier draft used floor on the lower side and ceil on the upper, which
    # biased the CI slightly inward on the lower end (codex P2 fix).
    alpha = (1.0 - confidence) / 2.0
    lo_idx = max(0, int(math.ceil(alpha * n_resamples)) - 1)
    hi_idx = min(n_resamples - 1, int(math.ceil((1.0 - alpha) * n_resamples)) - 1)
    return samples[lo_idx], samples[hi_idx]
