"""Repository pattern over the SQLAlchemy models.

Two implementations satisfy each Protocol:
- Postgres-backed (async SQLAlchemy) for production
- In-memory dict for dev without Postgres + for unit tests

Every read/write is scoped by `customer_id`. The middleware that extracts
customer_id from auth (Phase 5) injects it into the request context; until
then, the simulator hardcodes `customer_id="demo"`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from sidira_simulator.adapters.db_models import (
    AgentFeedback,
    AgentInstance,
    Customer,
    Simulation,
)


async def _commit(session: AsyncSession) -> None:
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def _release_read_transaction(session: AsyncSession) -> None:
    if session.in_transaction() and not (session.new or session.dirty or session.deleted):
        await session.rollback()


# ──────────────────────────────────────────────────────────────────────
# Customer
# ──────────────────────────────────────────────────────────────────────


class CustomerRepo(Protocol):
    async def ensure_exists(
        self, customer_id: str, name: str | None = None, clerk_org_id: str | None = None
    ) -> None: ...


class PostgresCustomerRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_exists(
        self, customer_id: str, name: str | None = None, clerk_org_id: str | None = None
    ) -> None:
        insert = pg_insert(Customer).values(
            id=customer_id, name=name or customer_id, clerk_org_id=clerk_org_id
        )
        # Only the Clerk webhook carries a clerk_org_id; the simulation path never
        # does. Use that as the discriminator: webhook deliveries backfill the
        # org name + clerk_org_id onto a row a prior simulation may have created
        # with placeholder values (the signup-then-act race), while the
        # orchestrator's bare ensure_exists keeps plain DO NOTHING semantics.
        if clerk_org_id is not None:
            stmt = insert.on_conflict_do_update(
                index_elements=[Customer.id],
                set_={
                    "name": insert.excluded.name,
                    "clerk_org_id": insert.excluded.clerk_org_id,
                },
            )
        else:
            stmt = insert.on_conflict_do_nothing(index_elements=[Customer.id])
        await self._session.execute(stmt)
        await _commit(self._session)


class InMemoryCustomerRepo:
    def __init__(self) -> None:
        self._customers: dict[str, dict[str, Any]] = {}

    async def ensure_exists(
        self, customer_id: str, name: str | None = None, clerk_org_id: str | None = None
    ) -> None:
        existing = self._customers.get(customer_id)
        if existing is None:
            self._customers[customer_id] = {
                "id": customer_id,
                "name": name or customer_id,
                "clerk_org_id": clerk_org_id,
            }
        elif clerk_org_id is not None:
            # Webhook delivery backfills profile fields onto a row a prior
            # simulation created with placeholders; mirrors the Postgres
            # on_conflict_do_update path above.
            existing["name"] = name or customer_id
            existing["clerk_org_id"] = clerk_org_id


# ──────────────────────────────────────────────────────────────────────
# Simulation
# ──────────────────────────────────────────────────────────────────────


class SimulationRepo(Protocol):
    async def create(
        self,
        *,
        sim_id: str,
        customer_id: str,
        persona_pack_version: str,
        feature_pack_version: str,
        hypothesis_json: dict[str, Any],
        parent_simulation_id: str | None = None,
        population_size: int | None = None,
        sampled_agent_count: int | None = None,
        run_seed: int | None = None,
        treatment_fraction: float | None = None,
        selected_personas: list[str] | None = None,
        model_id: str | None = None,
    ) -> None: ...

    async def update_status(
        self,
        sim_id: str,
        customer_id: str,
        status: str,
        *,
        result_json: dict[str, Any] | None = None,
        error: str | None = None,
        completed_at: datetime | None = None,
    ) -> None: ...

    async def get(self, sim_id: str, customer_id: str) -> dict[str, Any] | None: ...

    async def list_recent(self, customer_id: str, limit: int = 50) -> list[dict[str, Any]]: ...


class PostgresSimulationRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        sim_id: str,
        customer_id: str,
        persona_pack_version: str,
        feature_pack_version: str,
        hypothesis_json: dict[str, Any],
        parent_simulation_id: str | None = None,
        population_size: int | None = None,
        sampled_agent_count: int | None = None,
        run_seed: int | None = None,
        treatment_fraction: float | None = None,
        selected_personas: list[str] | None = None,
        model_id: str | None = None,
    ) -> None:
        row = Simulation(
            id=sim_id,
            customer_id=customer_id,
            status="pending",
            persona_pack_version=persona_pack_version,
            feature_pack_version=feature_pack_version,
            hypothesis_json=hypothesis_json,
            parent_simulation_id=parent_simulation_id,
            population_size=population_size,
            sampled_agent_count=sampled_agent_count,
            run_seed=run_seed,
            treatment_fraction=treatment_fraction,
            selected_personas=selected_personas,
            model_id=model_id,
        )
        self._session.add(row)
        await _commit(self._session)

    async def update_status(
        self,
        sim_id: str,
        customer_id: str,
        status: str,
        *,
        result_json: dict[str, Any] | None = None,
        error: str | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        row = await self._session.get(Simulation, sim_id)
        if row is None or row.customer_id != customer_id:
            raise KeyError(f"Simulation {sim_id!r} not found for customer {customer_id!r}")
        row.status = status
        if result_json is not None:
            row.result_json = result_json
        if error is not None:
            row.error = error
        if completed_at is not None:
            row.completed_at = completed_at
        await _commit(self._session)

    async def get(self, sim_id: str, customer_id: str) -> dict[str, Any] | None:
        row = await self._session.get(Simulation, sim_id)
        if row is None or row.customer_id != customer_id:
            await _release_read_transaction(self._session)
            return None
        result = _simulation_to_dict(row)
        await _release_read_transaction(self._session)
        return result

    async def list_recent(self, customer_id: str, limit: int = 50) -> list[dict[str, Any]]:
        stmt = (
            select(Simulation)
            .where(Simulation.customer_id == customer_id)
            .order_by(Simulation.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        result = [_simulation_to_dict(r) for r in rows]
        await _release_read_transaction(self._session)
        return result


class InMemorySimulationRepo:
    def __init__(self) -> None:
        self._sims: dict[str, dict[str, Any]] = {}

    async def create(
        self,
        *,
        sim_id: str,
        customer_id: str,
        persona_pack_version: str,
        feature_pack_version: str,
        hypothesis_json: dict[str, Any],
        parent_simulation_id: str | None = None,
        population_size: int | None = None,
        sampled_agent_count: int | None = None,
        run_seed: int | None = None,
        treatment_fraction: float | None = None,
        selected_personas: list[str] | None = None,
        model_id: str | None = None,
    ) -> None:
        self._sims[sim_id] = {
            "id": sim_id,
            "customer_id": customer_id,
            "status": "pending",
            "persona_pack_version": persona_pack_version,
            "feature_pack_version": feature_pack_version,
            "hypothesis_json": hypothesis_json,
            "result_json": None,
            "parent_simulation_id": parent_simulation_id,
            "error": None,
            "created_at": datetime.now(timezone.utc),
            "completed_at": None,
            "population_size": population_size,
            "sampled_agent_count": sampled_agent_count,
            "run_seed": run_seed,
            "treatment_fraction": treatment_fraction,
            "selected_personas": selected_personas,
            "model_id": model_id,
        }

    async def update_status(
        self,
        sim_id: str,
        customer_id: str,
        status: str,
        *,
        result_json: dict[str, Any] | None = None,
        error: str | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        sim = self._sims.get(sim_id)
        if sim is None or sim["customer_id"] != customer_id:
            raise KeyError(f"Simulation {sim_id!r} not found for customer {customer_id!r}")
        sim["status"] = status
        if result_json is not None:
            sim["result_json"] = result_json
        if error is not None:
            sim["error"] = error
        if completed_at is not None:
            sim["completed_at"] = completed_at

    async def get(self, sim_id: str, customer_id: str) -> dict[str, Any] | None:
        sim = self._sims.get(sim_id)
        if sim is None or sim["customer_id"] != customer_id:
            return None
        return dict(sim)

    async def list_recent(self, customer_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = [dict(s) for s in self._sims.values() if s["customer_id"] == customer_id]
        rows.sort(
            key=lambda r: r.get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return rows[:limit]


# ──────────────────────────────────────────────────────────────────────
# AgentInstance
# ──────────────────────────────────────────────────────────────────────


class AgentInstanceRepo(Protocol):
    async def create(self, metadata: dict[str, Any]) -> None: ...
    async def list_for_simulation(self, sim_id: str, customer_id: str) -> list[dict[str, Any]]: ...
    async def get(self, agent_id: str, customer_id: str) -> dict[str, Any] | None: ...
    async def touch(self, agent_id: str, customer_id: str) -> None: ...


class PostgresAgentInstanceRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, metadata: dict[str, Any]) -> None:
        row = AgentInstance(**metadata)
        self._session.add(row)
        await _commit(self._session)

    async def list_for_simulation(self, sim_id: str, customer_id: str) -> list[dict[str, Any]]:
        stmt = (
            select(AgentInstance)
            .where(
                AgentInstance.simulation_id == sim_id,
                AgentInstance.customer_id == customer_id,
            )
            .order_by(
                AgentInstance.materialization_index.asc().nulls_last(),
                AgentInstance.created_at.asc(),
                AgentInstance.id.asc(),
            )
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        result = [_agent_to_dict(r) for r in rows]
        await _release_read_transaction(self._session)
        return result

    async def get(self, agent_id: str, customer_id: str) -> dict[str, Any] | None:
        row = await self._session.get(AgentInstance, agent_id)
        if row is None or row.customer_id != customer_id:
            await _release_read_transaction(self._session)
            return None
        result = _agent_to_dict(row)
        await _release_read_transaction(self._session)
        return result

    async def touch(self, agent_id: str, customer_id: str) -> None:
        row = await self._session.get(AgentInstance, agent_id)
        if row is None or row.customer_id != customer_id:
            raise KeyError(f"Agent {agent_id!r} not found for customer {customer_id!r}")
        row.last_active_at = datetime.now(timezone.utc)
        row.message_count = (row.message_count or 0) + 1
        await _commit(self._session)


class InMemoryAgentInstanceRepo:
    def __init__(self) -> None:
        self._agents: dict[str, dict[str, Any]] = {}

    async def create(self, metadata: dict[str, Any]) -> None:
        self._agents[metadata["id"]] = dict(metadata)

    async def list_for_simulation(self, sim_id: str, customer_id: str) -> list[dict[str, Any]]:
        return [
            dict(a)
            for a in self._agents.values()
            if a["simulation_id"] == sim_id and a["customer_id"] == customer_id
        ]

    async def get(self, agent_id: str, customer_id: str) -> dict[str, Any] | None:
        a = self._agents.get(agent_id)
        if a is None or a["customer_id"] != customer_id:
            return None
        return dict(a)

    async def touch(self, agent_id: str, customer_id: str) -> None:
        a = self._agents.get(agent_id)
        if a is None or a["customer_id"] != customer_id:
            raise KeyError(f"Agent {agent_id!r} not found for customer {customer_id!r}")
        a["last_active_at"] = datetime.now(timezone.utc)
        a["message_count"] = a.get("message_count", 0) + 1


# ──────────────────────────────────────────────────────────────────────
# AgentFeedback
# ──────────────────────────────────────────────────────────────────────


class AgentFeedbackRepo(Protocol):
    async def record(
        self,
        *,
        feedback_id: str,
        customer_id: str,
        agent_id: str,
        turn_index: int,
        realistic_flag: bool,
    ) -> None: ...


class PostgresAgentFeedbackRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        feedback_id: str,
        customer_id: str,
        agent_id: str,
        turn_index: int,
        realistic_flag: bool,
    ) -> None:
        row = AgentFeedback(
            id=feedback_id,
            customer_id=customer_id,
            agent_id=agent_id,
            turn_index=turn_index,
            realistic_flag=realistic_flag,
        )
        self._session.add(row)
        await _commit(self._session)


class InMemoryAgentFeedbackRepo:
    def __init__(self) -> None:
        self._feedback: list[dict[str, Any]] = []

    async def record(
        self,
        *,
        feedback_id: str,
        customer_id: str,
        agent_id: str,
        turn_index: int,
        realistic_flag: bool,
    ) -> None:
        self._feedback.append(
            {
                "id": feedback_id,
                "customer_id": customer_id,
                "agent_id": agent_id,
                "turn_index": turn_index,
                "realistic_flag": realistic_flag,
                "created_at": datetime.now(timezone.utc),
            }
        )


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────


def _simulation_to_dict(row: Simulation) -> dict[str, Any]:
    return {
        "id": row.id,
        "customer_id": row.customer_id,
        "status": row.status,
        "persona_pack_version": row.persona_pack_version,
        "feature_pack_version": row.feature_pack_version,
        "hypothesis_json": row.hypothesis_json,
        "result_json": row.result_json,
        "parent_simulation_id": row.parent_simulation_id,
        "error": row.error,
        "created_at": row.created_at,
        "completed_at": row.completed_at,
        "population_size": row.population_size,
        "sampled_agent_count": row.sampled_agent_count,
        "run_seed": row.run_seed,
        "treatment_fraction": row.treatment_fraction,
        "selected_personas": row.selected_personas,
        "model_id": row.model_id,
    }


def _agent_to_dict(row: AgentInstance) -> dict[str, Any]:
    return {
        "id": row.id,
        "customer_id": row.customer_id,
        "simulation_id": row.simulation_id,
        "persona_id": row.persona_id,
        "persona_pack_version": row.persona_pack_version,
        "persona_name": row.persona_name,
        "created_at": row.created_at,
        "last_active_at": row.last_active_at,
        "message_count": row.message_count,
        "materialization_index": row.materialization_index,
        "arm": row.arm,
    }


# ──────────────────────────────────────────────────────────────────────
# Module-level singletons for the in-memory variant (used when DATABASE_URL is unset)
# ──────────────────────────────────────────────────────────────────────

_in_memory_customers: InMemoryCustomerRepo | None = None
_in_memory_simulations: InMemorySimulationRepo | None = None
_in_memory_agents: InMemoryAgentInstanceRepo | None = None
_in_memory_feedback: InMemoryAgentFeedbackRepo | None = None


def get_in_memory_repos() -> tuple[
    InMemoryCustomerRepo,
    InMemorySimulationRepo,
    InMemoryAgentInstanceRepo,
    InMemoryAgentFeedbackRepo,
]:
    """Process-wide in-memory repos. State persists for the lifetime of the process."""
    global _in_memory_customers, _in_memory_simulations, _in_memory_agents, _in_memory_feedback
    if _in_memory_customers is None:
        _in_memory_customers = InMemoryCustomerRepo()
        _in_memory_simulations = InMemorySimulationRepo()
        _in_memory_agents = InMemoryAgentInstanceRepo()
        _in_memory_feedback = InMemoryAgentFeedbackRepo()
    return (
        _in_memory_customers,
        _in_memory_simulations,
        _in_memory_agents,
        _in_memory_feedback,
    )
