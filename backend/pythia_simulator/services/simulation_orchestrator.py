"""Simulation orchestrator — the seam between the API route and SimulationRunner.

Owns: ID assignment, customer scoping, repo persistence, background task fire,
and the bridge between SimulationRunner's in-memory return value and the DB row.

Why this exists:
- SimulationRunner is producer-of-AgentInstances (knows R2 + LLM, doesn't know DB).
- API route is HTTP-shaped (knows requests + responses, doesn't know LLM).
- This class glues them so neither needs to know about the other.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import structlog

from pythia_simulator.adapters.feature_pack_loader import FeaturePackLoader
from pythia_simulator.adapters.persona_loader import PersonaPackLoader
from pythia_simulator.adapters.repositories import (
    AgentInstanceRepo,
    CustomerRepo,
    SimulationRepo,
)
from pythia_simulator.schemas.simulation import Hypothesis, Simulation, SimulationStatus
from pythia_simulator.services.simulation_runner import SimulationRunner

log = structlog.get_logger()


class SimulationOrchestrator:
    def __init__(
        self,
        *,
        customer_repo: CustomerRepo,
        simulation_repo: SimulationRepo,
        agent_repo: AgentInstanceRepo,
        persona_loader: PersonaPackLoader | None = None,
        feature_pack_loader: FeaturePackLoader | None = None,
        runner: SimulationRunner | None = None,
    ) -> None:
        self._customers = customer_repo
        self._simulations = simulation_repo
        self._agents = agent_repo
        self._personas = persona_loader or PersonaPackLoader()
        self._features = feature_pack_loader or FeaturePackLoader()
        self._runner = runner or SimulationRunner()

    async def prepare(
        self,
        *,
        customer_id: str,
        hypothesis: Hypothesis,
        sample_size: int = 10,
    ):
        """Persist a pending simulation row. Returns sim_id and the run-coroutine.

        The HTTP route is responsible for scheduling the coroutine — via
        FastAPI's BackgroundTasks or asyncio.create_task. Keeping scheduling
        out of the orchestrator means this class stays HTTP-agnostic and is
        trivially testable without TestClient event-loop choreography.
        """
        await self._customers.ensure_exists(customer_id, name=customer_id)

        persona_pack = self._personas.load_latest(customer_id)
        feature_pack_version = self._features.resolve_latest_version(customer_id)

        sim_id = str(uuid.uuid4())
        await self._simulations.create(
            sim_id=sim_id,
            customer_id=customer_id,
            persona_pack_version=persona_pack.version,
            feature_pack_version=feature_pack_version,
            hypothesis_json=hypothesis.model_dump(mode="json"),
        )

        async def run() -> None:
            await self._run_in_background(
                sim_id=sim_id,
                customer_id=customer_id,
                hypothesis=hypothesis,
                sample_size=sample_size,
            )

        return sim_id, run

    async def get(self, sim_id: str, customer_id: str) -> dict | None:
        """Return the simulation row plus the list of agent_instance_ids."""
        sim = await self._simulations.get(sim_id, customer_id)
        if sim is None:
            return None
        agents = await self._agents.list_for_simulation(sim_id, customer_id)
        sim["agent_instance_ids"] = [a["id"] for a in agents]
        return sim

    async def _run_in_background(
        self,
        *,
        sim_id: str,
        customer_id: str,
        hypothesis: Hypothesis,
        sample_size: int,
    ) -> None:
        try:
            await self._simulations.update_status(sim_id, customer_id, "running")

            persona_pack = self._personas.load_latest(customer_id)
            feature_pack_version = self._features.resolve_latest_version(customer_id)
            capability = self._features.load_capability(
                customer_id, feature_pack_version, hypothesis.capability_name
            )

            # SimulationRunner already mints its own sim_id; we override here so the DB
            # row, agent_instances rows, and R2 paths all share the same id.
            await self._run_with_id(
                sim_id=sim_id,
                customer_id=customer_id,
                persona_pack=persona_pack,
                capability=capability,
                feature_pack_version=feature_pack_version,
                hypothesis=hypothesis,
                sample_size=sample_size,
            )

        except Exception as exc:
            log.exception("simulation.failed", sim_id=sim_id, error=str(exc))
            await self._simulations.update_status(
                sim_id,
                customer_id,
                "failed",
                error=str(exc)[:1000],
                completed_at=datetime.now(timezone.utc),
            )

    async def _run_with_id(
        self,
        *,
        sim_id: str,
        customer_id: str,
        persona_pack,
        capability,
        feature_pack_version: str,
        hypothesis: Hypothesis,
        sample_size: int,
    ) -> None:
        """Call SimulationRunner with a pre-assigned sim_id; persist agents + result."""
        simulation = await self._runner.run(
            customer_id=customer_id,
            persona_pack=persona_pack,
            capability=capability,
            feature_pack_version=feature_pack_version,
            hypothesis=hypothesis,
            sample_size=sample_size,
            sim_id=sim_id,
        )

        # Persist agent_instances rows using the records the runner exposed.
        for record in getattr(self._runner, "_last_run_agent_records", []):
            await self._agents.create(
                {
                    "id": record.agent_id,
                    "customer_id": customer_id,
                    "simulation_id": sim_id,
                    "persona_id": record.persona_id,
                    "persona_pack_version": persona_pack.version,
                    "persona_name": record.persona_name,
                    "created_at": record.created_at,
                    "last_active_at": record.created_at,
                    "message_count": 0,
                }
            )

        await self._simulations.update_status(
            sim_id,
            customer_id,
            simulation.status.value,
            result_json=simulation.result.model_dump(mode="json") if simulation.result else None,
            completed_at=datetime.now(timezone.utc),
        )
