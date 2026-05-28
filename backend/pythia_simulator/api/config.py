"""Runtime configuration endpoints for frontend truth-from-backend UI."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from pythia_simulator.services.runtime_config import resolve_max_agents_per_simulation

router = APIRouter(prefix="/config", tags=["config"])


class SimulationLimitsResponse(BaseModel):
    """Limits that affect simulation cost previews and request shaping."""

    max_agents_per_simulation: int
    max_agents_per_arm: int


@router.get("/limits", response_model=SimulationLimitsResponse)
def get_limits() -> SimulationLimitsResponse:
    """Return effective caps for this backend process.

    A/B v1 treats `population_size` as a per-arm target, so the same resolved
    cap applies both to single-arm runs and to each arm in A/B mode.
    """
    cap = resolve_max_agents_per_simulation()
    return SimulationLimitsResponse(
        max_agents_per_simulation=cap,
        max_agents_per_arm=cap,
    )
