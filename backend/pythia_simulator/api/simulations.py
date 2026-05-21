"""Simulation routes — submit a hypothesis, fetch a simulation, poll live state."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from pythia_simulator.adapters.base import ArtifactNotFound
from pythia_simulator.adapters.r2 import get_store
from pythia_simulator.api.deps import (
    current_customer_id,
    get_orchestrator,
)
from pythia_simulator.schemas.simulation import (
    Simulation,
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
)
from pythia_simulator.services.run_state import RunStateStore, SimulationRunState
from pythia_simulator.services.simulation_orchestrator import SimulationOrchestrator

router = APIRouter(prefix="/simulations", tags=["simulations"])


class CreateSimulationResponse(BaseModel):
    id: str
    status: SimulationStatus
    poll_url: str


class SimulationListItem(BaseModel):
    id: str
    status: SimulationStatus
    created_at: datetime
    completed_at: datetime | None = None
    hypothesis_prose: str
    capability_name: str
    confidence_score: float | None = None


@router.get("", response_model=list[SimulationListItem])
async def list_simulations(
    customer_id: str = Depends(current_customer_id),
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
    limit: int = 50,
) -> list[SimulationListItem]:
    """Recent simulations for the current customer, newest first."""
    rows = await orchestrator.list_recent(customer_id, limit=limit)
    items: list[SimulationListItem] = []
    for row in rows:
        hyp = row.get("hypothesis_json") or {}
        result = row.get("result_json") or {}
        items.append(
            SimulationListItem(
                id=row["id"],
                status=SimulationStatus(row["status"]) if row.get("status") else SimulationStatus.PENDING,
                created_at=row.get("created_at") or datetime.utcnow(),
                completed_at=row.get("completed_at"),
                hypothesis_prose=hyp.get("prose", ""),
                capability_name=hyp.get("capability_name", ""),
                confidence_score=result.get("confidence_score"),
            )
        )
    return items


@router.post(
    "",
    response_model=CreateSimulationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_simulation(
    payload: SimulationRequest,
    background_tasks: BackgroundTasks,
    customer_id: str = Depends(current_customer_id),
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
) -> CreateSimulationResponse:
    """Accepts a hypothesis. Returns 202 + simulation_id; runs after the response is sent."""
    try:
        sim_id, run = await orchestrator.prepare(
            customer_id=customer_id,
            hypothesis=payload.hypothesis,
            sample_size=payload.persona_sample_size,
        )
    except ArtifactNotFound as exc:
        # No persona pack or feature pack for this customer yet.
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    background_tasks.add_task(run)
    return CreateSimulationResponse(
        id=sim_id,
        status=SimulationStatus.PENDING,
        poll_url=f"/simulations/{sim_id}/state",
    )


@router.get("/{simulation_id}", response_model=Simulation)
async def get_simulation(
    simulation_id: str,
    customer_id: str = Depends(current_customer_id),
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
) -> Simulation:
    row = await orchestrator.get(simulation_id, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")

    return Simulation(
        id=row["id"],
        customer_id=row["customer_id"],
        created_at=row["created_at"] or datetime.utcnow(),
        status=SimulationStatus(row["status"]) if row["status"] else SimulationStatus.PENDING,
        persona_pack_version=row["persona_pack_version"],
        feature_pack_version=row["feature_pack_version"],
        hypothesis=row["hypothesis_json"],
        agent_instance_ids=row.get("agent_instance_ids", []),
        result=SimulationResult(**row["result_json"]) if row.get("result_json") else None,
    )


@router.get("/{simulation_id}/state", response_model=SimulationRunState)
async def get_simulation_state(
    simulation_id: str,
    customer_id: str = Depends(current_customer_id),
) -> SimulationRunState:
    """Live progress state. Frontend polls this every 5s until phase=complete."""
    store = get_store()
    rs = RunStateStore(store)
    try:
        return rs.read_state(customer_id, simulation_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No state recorded yet for simulation {simulation_id}",
        )
