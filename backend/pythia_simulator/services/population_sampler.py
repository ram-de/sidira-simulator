"""Hamilton largest-remainder allocation over a PersonaPack's weight scheme.

Phase 2.5, issue #58. Replaces simulation_runner._top_personas_by_weight,
which truncated rather than stratified. The math:

  N           = min(population_size, max_agents)              # effective cap
  exact_i     = weight_i × N                                  # fractional
  floor_i     = ⌊exact_i⌋
  remainder   = N − Σ floor_i
  → hand out the remainder one-by-one to the personas with the largest
    fractional parts. Ties broken by persona_id sort for determinism.

Pure function — no I/O, no LLM calls. Caller (the runner) is responsible
for actually instantiating that many agents.
"""

from __future__ import annotations

import math
import os
from typing import Literal

from pythia_simulator.schemas.persona import PersonaPack

WeightScheme = Literal["head_count", "order_weighted", "revenue_weighted"]

_DEFAULT_MAX_AGENTS = 50
# Producers (pythia-personas, hand-authored fixtures) emit weights as floats,
# so allow a small drift around 1.0. Anything beyond this is a real producer bug.
_WEIGHT_SUM_TOLERANCE = 1e-3


def _resolve_max_agents(arg: int | None) -> int:
    """Resolve max_agents from explicit arg, env, or default.

    Explicit `arg <= 0` raises (caller error). Bad env values fall back to the
    default -- matches the fail-open posture of api/simulations.py so a
    misconfigured deployment env doesn't 500 every POST.
    """
    if arg is not None:
        if arg <= 0:
            raise ValueError(f"max_agents must be >= 1, got {arg!r}")
        return arg
    raw = os.environ.get("PYTHIA_MAX_AGENTS")
    if raw is None:
        return _DEFAULT_MAX_AGENTS
    try:
        parsed = int(raw)
    except ValueError:
        return _DEFAULT_MAX_AGENTS
    if parsed <= 0:
        return _DEFAULT_MAX_AGENTS
    return parsed


def _resolve_weights(pack: PersonaPack, scheme: str) -> dict[str, float]:
    if scheme == "head_count":
        return pack.weights.head_count
    if scheme == "order_weighted":
        w = pack.weights.order_weighted
        if w is None:
            raise ValueError(f"PersonaPack does not carry {scheme!r} weights")
        return w
    if scheme == "revenue_weighted":
        w = pack.weights.revenue_weighted
        if w is None:
            raise ValueError(f"PersonaPack does not carry {scheme!r} weights")
        return w
    raise ValueError(
        f"Unknown weight scheme {scheme!r}. Expected one of: head_count, "
        f"order_weighted, revenue_weighted."
    )


def _validate_weights(weights: dict[str, float], persona_ids: list[str], scheme: str) -> None:
    """Reject inputs that would silently miscount or crash the allocation.

    The docstring promises counts sum to the effective sample size. That
    invariant only holds for a complete, finite, non-negative weight vector
    that sums to 1. Producer bugs (negative, NaN, missing personas, partial
    sums) should surface loudly rather than under/over-allocating in silence.
    """
    pack_ids = set(persona_ids)
    weight_ids = set(weights)
    missing = pack_ids - weight_ids
    if missing:
        raise ValueError(
            f"{scheme!r} weights are missing personas present in the pack: "
            f"{sorted(missing)}"
        )
    extra = weight_ids - pack_ids
    if extra:
        raise ValueError(
            f"{scheme!r} weights carry personas absent from the pack: {sorted(extra)}"
        )
    for pid, w in weights.items():
        if not isinstance(w, (int, float)) or isinstance(w, bool):
            raise ValueError(f"{scheme!r} weight for {pid!r} is not numeric: {w!r}")
        if not math.isfinite(w):
            raise ValueError(f"{scheme!r} weight for {pid!r} is not finite: {w!r}")
        if w < 0:
            raise ValueError(f"{scheme!r} weight for {pid!r} is negative: {w!r}")
    total = sum(weights.values())
    if abs(total - 1.0) > _WEIGHT_SUM_TOLERANCE:
        raise ValueError(
            f"{scheme!r} weights must sum to ~1.0 (within {_WEIGHT_SUM_TOLERANCE}), "
            f"got {total!r}"
        )


def allocate(
    pack: PersonaPack,
    population_size: int,
    *,
    weight_scheme: str = "head_count",
    max_agents: int | None = None,
) -> list[tuple[str, int]]:
    """Allocate `min(population_size, max_agents)` agents across the pack's personas.

    Returns a list of `(persona_id, agent_count)` tuples in persona_id sort
    order. Counts sum to the effective sample size.
    """
    if population_size < 0:
        raise ValueError(f"population_size must be >= 0, got {population_size!r}")
    cap = _resolve_max_agents(max_agents)
    n = min(population_size, cap)

    weights = _resolve_weights(pack, weight_scheme)
    # Walk in persona_id order for deterministic tie-breaking.
    persona_ids = sorted(p.id for p in pack.personas)
    _validate_weights(weights, persona_ids, weight_scheme)

    # Step 1+2: exact share and integer floor.
    exact = {pid: weights.get(pid, 0.0) * n for pid in persona_ids}
    floors = {pid: int(exact[pid]) for pid in persona_ids}
    remainder = n - sum(floors.values())

    # Step 3: hand out the remainder one-by-one to largest fractional parts.
    # Sort by (-fractional, persona_id) so ties go to lex-smallest id.
    if remainder > 0:
        fractional = [(pid, exact[pid] - floors[pid]) for pid in persona_ids]
        fractional.sort(key=lambda x: (-x[1], x[0]))
        for pid, _ in fractional[:remainder]:
            floors[pid] += 1

    return [(pid, floors[pid]) for pid in persona_ids]
