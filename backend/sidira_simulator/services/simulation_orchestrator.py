"""Simulation orchestrator — the seam between the API route and SimulationRunner.

Owns: ID assignment, customer scoping, repo persistence, background task fire,
and the bridge between SimulationRunner's in-memory return value and the DB row.

Why this exists:
- SimulationRunner is producer-of-AgentInstances (knows R2 + LLM, doesn't know DB).
- API route is HTTP-shaped (knows requests + responses, doesn't know LLM).
- This class glues them so neither needs to know about the other.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import AsyncContextManager

import structlog

from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.repositories import (
    AgentInstanceRepo,
    CustomerRepo,
    SimulationRepo,
)
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.simulation_runner import SimulationRunner

log = structlog.get_logger()

BackgroundOrchestratorFactory = Callable[[], AsyncContextManager["SimulationOrchestrator"]]


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
        background_orchestrator_factory: BackgroundOrchestratorFactory | None = None,
    ) -> None:
        self._customers = customer_repo
        self._simulations = simulation_repo
        self._agents = agent_repo
        self._personas = persona_loader or PersonaPackLoader()
        self._features = feature_pack_loader or FeaturePackLoader()
        self._runner = runner or SimulationRunner()
        self._background_orchestrator_factory = background_orchestrator_factory

    async def prepare(
        self,
        *,
        customer_id: str,
        hypothesis: Hypothesis,
        population_size: int | None = None,
        sampled_agent_count: int | None = None,
        run_seed: int | None = None,
        treatment_fraction: float | None = None,
        selected_personas: list[str] | None = None,
        model_id: str | None = None,
        sample_size: int = 10,
        include_no_persona_control: bool = False,
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

        # Phase 5 #101: eager validation of selected_personas against the
        # active pack. Catches unknown persona_ids at submit time with a
        # clean 400 (POST handler maps ValueError -> 400) instead of failing
        # the background run after the sim row is already persisted. The
        # allocator does the same check defensively, but doing it here means
        # the sim row never even gets created for a bad request.
        if selected_personas is not None:
            pack_ids = {p.id for p in persona_pack.personas}
            unknown = sorted(set(selected_personas) - pack_ids)
            if unknown:
                raise ValueError(
                    f"selected_personas references persona_ids not present "
                    f"in the active Persona Pack ({persona_pack.version}): "
                    f"{unknown}. Known ids: {sorted(pack_ids)}"
                )

        # Phase 2.5 (#5): the runner now does its own allocate()-based stratification
        # over population_size, so we just thread it (plus run_seed for identity
        # reproducibility) through. Legacy `sample_size` is no longer consulted by
        # the runner but kept on this signature as a defaulted no-op so older direct
        # callers don't break at import time.
        effective_population_size = population_size if population_size is not None else sample_size
        # Resolve run_seed BEFORE persisting so the DB row matches the seed the
        # runner will actually use. If we let the runner mint its own default, the
        # row stores NULL while the simulation uses a time-derived seed -- and the
        # caller can never replay it. (codex review P1)
        # Use a 53-bit range so the JSON-encoded value round-trips losslessly
        # through JavaScript clients (Number.MAX_SAFE_INTEGER = 2**53 - 1). A
        # browser reading back time.time_ns() (~1.7e18) and resubmitting it for
        # replay would round the value and hash a different RNG seed. (codex P2)
        resolved_run_seed = run_seed if run_seed is not None else secrets.randbits(53)

        sim_id = str(uuid.uuid4())
        await self._simulations.create(
            sim_id=sim_id,
            customer_id=customer_id,
            persona_pack_version=persona_pack.version,
            feature_pack_version=feature_pack_version,
            hypothesis_json=hypothesis.model_dump(mode="json"),
            population_size=population_size,
            sampled_agent_count=sampled_agent_count,
            run_seed=resolved_run_seed,
            treatment_fraction=treatment_fraction,
            selected_personas=selected_personas,
            model_id=model_id,
        )

        async def run() -> None:
            background_orchestrator = self
            if self._background_orchestrator_factory is not None:
                async with self._background_orchestrator_factory() as orchestrator:
                    await orchestrator._run_in_background(
                        sim_id=sim_id,
                        customer_id=customer_id,
                        hypothesis=hypothesis,
                        population_size=effective_population_size,
                        run_seed=resolved_run_seed,
                        # Pass the API-derived cap so allocate() uses the same number
                        # the row recorded. Otherwise SIDIRA_MAX_AGENTS=0 makes the API
                        # clamp to 1 while allocate() falls back to default 50. (codex P2)
                        max_agents=sampled_agent_count,
                        treatment_fraction=treatment_fraction,
                        selected_personas=selected_personas,
                        model_id=model_id,
                        include_no_persona_control=include_no_persona_control,
                    )
                return

            await background_orchestrator._run_in_background(
                sim_id=sim_id,
                customer_id=customer_id,
                hypothesis=hypothesis,
                population_size=effective_population_size,
                run_seed=resolved_run_seed,
                # Pass the API-derived cap so allocate() uses the same number
                # the row recorded. Otherwise SIDIRA_MAX_AGENTS=0 makes the API
                # clamp to 1 while allocate() falls back to default 50. (codex P2)
                max_agents=sampled_agent_count,
                treatment_fraction=treatment_fraction,
                selected_personas=selected_personas,
                model_id=model_id,
                include_no_persona_control=include_no_persona_control,
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

    async def list_recent(self, customer_id: str, limit: int = 50) -> list[dict]:
        return await self._simulations.list_recent(customer_id, limit)

    async def _run_in_background(
        self,
        *,
        sim_id: str,
        customer_id: str,
        hypothesis: Hypothesis,
        population_size: int,
        run_seed: int | None,
        max_agents: int | None = None,
        treatment_fraction: float | None = None,
        selected_personas: list[str] | None = None,
        model_id: str | None = None,
        include_no_persona_control: bool = False,
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
                population_size=population_size,
                run_seed=run_seed,
                max_agents=max_agents,
                treatment_fraction=treatment_fraction,
                selected_personas=selected_personas,
                model_id=model_id,
                include_no_persona_control=include_no_persona_control,
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
        population_size: int,
        run_seed: int | None,
        max_agents: int | None = None,
        treatment_fraction: float | None = None,
        selected_personas: list[str] | None = None,
        model_id: str | None = None,
        include_no_persona_control: bool = False,
    ) -> None:
        """Call SimulationRunner with a pre-assigned sim_id; persist agents + result."""
        simulation = await self._runner.run(
            customer_id=customer_id,
            persona_pack=persona_pack,
            capability=capability,
            feature_pack_version=feature_pack_version,
            hypothesis=hypothesis,
            population_size=population_size,
            run_seed=run_seed,
            max_agents=max_agents,
            sim_id=sim_id,
            treatment_fraction=treatment_fraction,
            selected_personas=selected_personas,
            model_id=model_id,
            include_no_persona_control=include_no_persona_control,
        )

        # Persist agent_instances rows using the records the runner exposed.
        for materialization_index, record in enumerate(
            getattr(self._runner, "_last_run_agent_records", [])
        ):
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
                    "materialization_index": materialization_index,
                    "arm": record.arm,
                }
            )

        await self._simulations.update_status(
            sim_id,
            customer_id,
            simulation.status.value,
            result_json=simulation.result.model_dump(mode="json") if simulation.result else None,
            completed_at=datetime.now(timezone.utc),
        )
