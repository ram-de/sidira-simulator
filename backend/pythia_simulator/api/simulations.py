"""Simulation routes — submit a hypothesis, fetch a simulation result."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from pythia_simulator.schemas.simulation import Simulation, SimulationRequest

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("", response_model=Simulation)
async def create_simulation(payload: SimulationRequest) -> Simulation:
    """Submit a hypothesis and run a simulation against the customer's latest packs."""
    raise HTTPException(
        status_code=501,
        detail="create_simulation — wires SimulationRunner once persona_loader is in",
    )


@router.get("/{simulation_id}", response_model=Simulation)
async def get_simulation(simulation_id: str) -> Simulation:
    """Fetch a completed simulation including the list of agent_instance_ids."""
    raise HTTPException(
        status_code=501, detail="get_simulation — implement once Postgres layer lands"
    )
