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

import os
from typing import Literal

from pythia_simulator.schemas.persona import PersonaPack

WeightScheme = Literal["head_count", "order_weighted", "revenue_weighted"]

_DEFAULT_MAX_AGENTS = 50


def _resolve_max_agents(arg: int | None) -> int:
    if arg is not None:
        return max(1, arg)
    raw = os.environ.get("PYTHIA_MAX_AGENTS")
    if raw is None:
        return _DEFAULT_MAX_AGENTS
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_MAX_AGENTS


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
    cap = _resolve_max_agents(max_agents)
    n = min(max(0, population_size), cap)

    weights = _resolve_weights(pack, weight_scheme)
    # Walk in persona_id order for deterministic tie-breaking.
    persona_ids = sorted(p.id for p in pack.personas)

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
