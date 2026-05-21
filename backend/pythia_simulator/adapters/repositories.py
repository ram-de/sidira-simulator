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
from sqlalchemy.ext.asyncio import AsyncSession

from pythia_simulator.adapters.db_models import (
    AgentFeedback,
    AgentInstance,
    Customer,
    Simulation,
)


# ──────────────────────────────────────────────────────────────────────
# Customer
# ──────────────────────────────────────────────────────────────────────


class CustomerRepo(Protocol):
    async def ensure_exists(self, customer_id: str, name: str | None = None) -> None: ...


class PostgresCustomerRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_exists(self, customer_id: str, name: str | None = None) -> None:
        existing = await self._session.get(Customer, customer_id)
        if existing is None:
            self._session.add(Customer(id=customer_id, name=name or customer_id))
            await self._session.commit()


class InMemoryCustomerRepo:
    def __init__(self) -> None:
        self._customers: dict[str, dict[str, Any]] = {}

    async def ensure_exists(self, customer_id: str, name: str | None = None) -> None:
        self._customers.setdefault(
            customer_id, {"id": customer_id, "name": name or customer_id}
        )


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
    ) -> None:
        row = Simulation(
            id=sim_id,
            customer_id=customer_id,
            status="pending",
            persona_pack_version=persona_pack_version,
            feature_pack_version=feature_pack_version,
            hypothesis_json=hypothesis_json,
            parent_simulation_id=parent_simulation_id,
        )
        self._session.add(row)
        await self._session.commit()

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
        await self._session.commit()

    async def get(self, sim_id: str, customer_id: str) -> dict[str, Any] | None:
        row = await self._session.get(Simulation, sim_id)
        if row is None or row.customer_id != customer_id:
            return None
        return _simulation_to_dict(row)


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
        await self._session.commit()

    async def list_for_simulation(
        self, sim_id: str, customer_id: str
    ) -> list[dict[str, Any]]:
        stmt = select(AgentInstance).where(
            AgentInstance.simulation_id == sim_id,
            AgentInstance.customer_id == customer_id,
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_agent_to_dict(r) for r in rows]

    async def get(self, agent_id: str, customer_id: str) -> dict[str, Any] | None:
        row = await self._session.get(AgentInstance, agent_id)
        if row is None or row.customer_id != customer_id:
            return None
        return _agent_to_dict(row)

    async def touch(self, agent_id: str, customer_id: str) -> None:
        row = await self._session.get(AgentInstance, agent_id)
        if row is None or row.customer_id != customer_id:
            raise KeyError(f"Agent {agent_id!r} not found for customer {customer_id!r}")
        row.last_active_at = datetime.now(timezone.utc)
        row.message_count = (row.message_count or 0) + 1
        await self._session.commit()


class InMemoryAgentInstanceRepo:
    def __init__(self) -> None:
        self._agents: dict[str, dict[str, Any]] = {}

    async def create(self, metadata: dict[str, Any]) -> None:
        self._agents[metadata["id"]] = dict(metadata)

    async def list_for_simulation(
        self, sim_id: str, customer_id: str
    ) -> list[dict[str, Any]]:
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
        await self._session.commit()


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
