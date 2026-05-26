"""Simulation routes — submit a hypothesis, fetch a simulation, poll live state."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from pythia_simulator.adapters.base import ArtifactNotFound
from pythia_simulator.adapters.r2 import get_store
from pythia_simulator.adapters.repositories import AgentInstanceRepo
from pythia_simulator.api.deps import (
    current_customer_id,
    get_agent_repo,
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
    # Phase 2.5: population_size is the modeled userbase. Until the
    # population_sampler ticket (#58) lands, derive the internal sample_size
    # as min(population, MAX_AGENTS_DEFAULT). The sampler PR will replace this.
    import os

    raw_max = os.environ.get("PYTHIA_MAX_AGENTS", "50")
    try:
        max_agents = int(raw_max)
    except ValueError:
        max_agents = 50  # fail-open on malformed env; default already proven safe
    if max_agents < 1:
        max_agents = 1
    derived_sample_size = max(1, min(payload.population_size, max_agents))

    try:
        sim_id, run = await orchestrator.prepare(
            customer_id=customer_id,
            hypothesis=payload.hypothesis,
            population_size=payload.population_size,
            sampled_agent_count=derived_sample_size,
            run_seed=payload.run_seed,
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
        population_size=row.get("population_size"),
        sampled_agent_count=row.get("sampled_agent_count"),
        run_seed=row.get("run_seed"),
        agent_instance_ids=row.get("agent_instance_ids", []),
        result=SimulationResult(**row["result_json"]) if row.get("result_json") else None,
    )


class AgentSummary(BaseModel):
    """Lightweight per-agent row for the simulation detail page.

    Just enough for the persona-grouped table (#51). Full agent state +
    conversation history lives behind GET /agents/{id}, which lands with
    Phase 4 chat. Pulling the summary directly off the metadata repo means
    the frontend makes one call instead of N=50.

    `sentiment` + `top_quote` join the metadata row against
    `simulation.result_json.per_agent_analyses`, which the runner populates
    at score time. Both are None for agents whose simulation hasn't
    completed yet, OR for sims that ran before #51 landed (the field is
    backwards-compatible — empty `per_agent_analyses` means "data not
    available", not "agent didn't react").
    """

    agent_id: str
    persona_id: str
    persona_name: str
    sentiment: Literal["positive", "neutral", "negative"] | None = None
    sentiment_confidence: float | None = None
    top_quote: str | None = None


@router.get("/{simulation_id}/agents", response_model=list[AgentSummary])
async def list_simulation_agents(
    simulation_id: str,
    customer_id: str = Depends(current_customer_id),
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
    agent_repo: AgentInstanceRepo = Depends(get_agent_repo),
) -> list[AgentSummary]:
    """Persona-grouped table feed (Phase 2.5 #51).

    Order matches the runner's materialization order (largest-remainder
    allocator → largest persona first), since `list_for_simulation`
    returns rows in insertion order in both the InMemory and Postgres
    implementations.
    """
    sim_row = await orchestrator.get(simulation_id, customer_id)
    if sim_row is None:
        raise HTTPException(
            status_code=404, detail=f"Simulation {simulation_id} not found"
        )
    rows = await agent_repo.list_for_simulation(simulation_id, customer_id)

    # Build a {agent_id -> AgentAnalysisSummary} map from the persisted
    # result so we can join in one pass without N R2 reads.
    analyses_by_id: dict[str, dict] = {}
    result_json = sim_row.get("result_json") or {}
    for entry in result_json.get("per_agent_analyses") or []:
        if isinstance(entry, dict) and "agent_id" in entry:
            analyses_by_id[entry["agent_id"]] = entry

    out: list[AgentSummary] = []
    for r in rows:
        analysis = analyses_by_id.get(r["id"])
        out.append(
            AgentSummary(
                agent_id=r["id"],
                persona_id=r["persona_id"],
                persona_name=r["persona_name"],
                sentiment=analysis.get("sentiment") if analysis else None,
                sentiment_confidence=(
                    analysis.get("sentiment_confidence") if analysis else None
                ),
                top_quote=analysis.get("top_quote") if analysis else None,
            )
        )
    return out


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
