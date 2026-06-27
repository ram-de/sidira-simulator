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

from sqlalchemy import func, or_, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sidira_simulator.adapters.db_models import (
    AgentFeedback,
    AgentInstance,
    ArchivedFeaturePack,
    Conversation,
    ConversationTurn,
    CrawlConfig,
    CrawlRun,
    Customer,
    ExperimentConnection,
    ExperimentImportRun,
    FeatureStoreConnection,
    PersonaBuildRun,
    Simulation,
)

# Reserved setup id for the org's single/primary crawl target. Every existing
# endpoint (GET/PUT /crawl-setup, dispatch, the credential pull) operates on
# this setup; migration 015 backfilled the prior single crawl_configs row here,
# and migration 017 backfills every existing simulation here. Callers that pass
# only customer_id keep hitting it. Defined at module top so it is available as
# a default-parameter value for the SimulationRepo Protocol + impls below
# (#215/#245 PR 3a). Multi-setup CRUD landed in PR2 (#215).
DEFAULT_SETUP_ID = "default"


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
        setup_id: str = DEFAULT_SETUP_ID,
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
        setup_id: str = DEFAULT_SETUP_ID,
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
            setup_id=setup_id,
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
        setup_id: str = DEFAULT_SETUP_ID,
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
            "setup_id": setup_id,
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
# CrawlConfig (#171)
# ──────────────────────────────────────────────────────────────────────


# DEFAULT_SETUP_ID is defined at module top (it is a default-parameter value for
# the SimulationRepo Protocol above). The CrawlConfig repo helpers below import
# it from there.


class CrawlConfigRepo(Protocol):
    async def get(
        self, customer_id: str, setup_id: str = DEFAULT_SETUP_ID
    ) -> dict[str, Any] | None: ...

    async def upsert(
        self,
        customer_id: str,
        config_json: dict[str, Any],
        setup_id: str = DEFAULT_SETUP_ID,
        name: str | None = None,
    ) -> dict[str, Any]: ...

    async def list(self, customer_id: str) -> list[dict[str, Any]]: ...

    async def delete(self, customer_id: str, setup_id: str) -> bool: ...


class PostgresCrawlConfigRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, customer_id: str, setup_id: str = DEFAULT_SETUP_ID
    ) -> dict[str, Any] | None:
        row = await self._session.get(CrawlConfig, (customer_id, setup_id))
        result = _crawl_config_to_dict(row) if row is not None else None
        await _release_read_transaction(self._session)
        return result

    async def upsert(
        self,
        customer_id: str,
        config_json: dict[str, Any],
        setup_id: str = DEFAULT_SETUP_ID,
        name: str | None = None,
    ) -> dict[str, Any]:
        # name is only written on insert (and only when provided), so an upsert
        # of an existing setup never clobbers a label set by a later CRUD edit.
        insert_values: dict[str, Any] = {
            "customer_id": customer_id,
            "setup_id": setup_id,
            "config_json": config_json,
        }
        if name is not None:
            insert_values["name"] = name
        update_set: dict[str, Any] = {"config_json": config_json, "updated_at": func.now()}
        if name is not None:
            update_set["name"] = name
        stmt = (
            pg_insert(CrawlConfig)
            .values(**insert_values)
            .on_conflict_do_update(
                index_elements=[CrawlConfig.customer_id, CrawlConfig.setup_id],
                set_=update_set,
            )
        )
        await self._session.execute(stmt)
        await _commit(self._session)
        row = await self._session.get(CrawlConfig, (customer_id, setup_id))
        assert row is not None
        result = _crawl_config_to_dict(row)
        await _release_read_transaction(self._session)
        return result

    async def list(self, customer_id: str) -> list[dict[str, Any]]:
        stmt = (
            select(CrawlConfig)
            .where(CrawlConfig.customer_id == customer_id)
            .order_by(CrawlConfig.setup_id)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        result = [_crawl_config_to_dict(row) for row in rows]
        await _release_read_transaction(self._session)
        return result

    async def delete(self, customer_id: str, setup_id: str) -> bool:
        # Config-row delete ONLY — never touches R2 feature-pack objects, so a
        # historical sim that froze a pack from this setup still resolves
        # (#214 / #215 integrity invariant). Route-level guard refuses "default".
        stmt = sa_delete(CrawlConfig).where(
            CrawlConfig.customer_id == customer_id,
            CrawlConfig.setup_id == setup_id,
        )
        result = await self._session.execute(stmt)
        await _commit(self._session)
        return result.rowcount > 0


class InMemoryCrawlConfigRepo:
    def __init__(self) -> None:
        # Keyed by (customer_id, setup_id) to mirror the composite PK.
        self._configs: dict[tuple[str, str], dict[str, Any]] = {}

    async def get(
        self, customer_id: str, setup_id: str = DEFAULT_SETUP_ID
    ) -> dict[str, Any] | None:
        row = self._configs.get((customer_id, setup_id))
        return dict(row) if row is not None else None

    async def upsert(
        self,
        customer_id: str,
        config_json: dict[str, Any],
        setup_id: str = DEFAULT_SETUP_ID,
        name: str | None = None,
    ) -> dict[str, Any]:
        existing = self._configs.get((customer_id, setup_id))
        # Preserve a prior label on re-save unless a new one is supplied.
        resolved_name = name if name is not None else (existing or {}).get("name")
        row = {
            "customer_id": customer_id,
            "setup_id": setup_id,
            "name": resolved_name,
            "config_json": config_json,
            "updated_at": datetime.now(timezone.utc),
        }
        self._configs[(customer_id, setup_id)] = row
        return dict(row)

    async def list(self, customer_id: str) -> list[dict[str, Any]]:
        return [
            dict(row)
            for (cid, _sid), row in sorted(self._configs.items())
            if cid == customer_id
        ]

    async def delete(self, customer_id: str, setup_id: str) -> bool:
        # Config-only delete — no R2 side effects (integrity invariant).
        return self._configs.pop((customer_id, setup_id), None) is not None


# ──────────────────────────────────────────────────────────────────────
# CrawlRun (#193)
# ──────────────────────────────────────────────────────────────────────


class CrawlRunRepo(Protocol):
    async def insert(self, run: dict[str, Any]) -> dict[str, Any]: ...

    async def get(self, crawl_id: str) -> dict[str, Any] | None: ...

    async def update(self, crawl_id: str, fields: dict[str, Any]) -> dict[str, Any]: ...

    async def list_for_customer(self, customer_id: str, limit: int = 20) -> list[dict[str, Any]]: ...


class PostgresCrawlRunRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, run: dict[str, Any]) -> dict[str, Any]:
        row = CrawlRun(**run)
        self._session.add(row)
        await _commit(self._session)
        await self._session.refresh(row)
        result = _crawl_run_to_dict(row)
        await _release_read_transaction(self._session)
        return result

    async def get(self, crawl_id: str) -> dict[str, Any] | None:
        row = await self._session.get(CrawlRun, crawl_id)
        result = _crawl_run_to_dict(row) if row is not None else None
        await _release_read_transaction(self._session)
        return result

    async def update(self, crawl_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        row = await self._session.get(CrawlRun, crawl_id)
        if row is None:
            # Reachable: a customer delete cascades to crawl_runs mid-poll.
            raise LookupError(f"crawl run {crawl_id} vanished mid-update")
        for key, value in fields.items():
            setattr(row, key, value)
        await _commit(self._session)
        await self._session.refresh(row)
        result = _crawl_run_to_dict(row)
        await _release_read_transaction(self._session)
        return result

    async def list_for_customer(self, customer_id: str, limit: int = 20) -> list[dict[str, Any]]:
        stmt = (
            select(CrawlRun)
            .where(CrawlRun.customer_id == customer_id)
            .order_by(CrawlRun.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        result = [_crawl_run_to_dict(row) for row in rows]
        await _release_read_transaction(self._session)
        return result


class InMemoryCrawlRunRepo:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}

    async def insert(self, run: dict[str, Any]) -> dict[str, Any]:
        row = {
            "status": "pending",
            "run_id": None,
            "run_url": None,
            "snapshot_version": None,
            "error": None,
            "completed_at": None,
            **run,
            "created_at": datetime.now(timezone.utc),
        }
        self._runs[row["id"]] = row
        return dict(row)

    async def get(self, crawl_id: str) -> dict[str, Any] | None:
        row = self._runs.get(crawl_id)
        return dict(row) if row is not None else None

    async def update(self, crawl_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        row = self._runs[crawl_id]
        row.update(fields)
        return dict(row)

    async def list_for_customer(self, customer_id: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = [r for r in self._runs.values() if r["customer_id"] == customer_id]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return [dict(r) for r in rows[:limit]]


# ──────────────────────────────────────────────────────────────────────
# ArchivedFeaturePack (#214) — soft-delete / hide-from-Library marker
# ──────────────────────────────────────────────────────────────────────


class ArchivedFeaturePackRepo(Protocol):
    """Soft-delete markers for Feature Pack versions (#214).

    A marker HIDES a pack version from the Library; it never deletes R2 artifacts
    and is never consulted when resolving a pack to RUN a simulation, so a
    historical sim that froze an archived version still replays.
    """

    async def is_archived(self, customer_id: str, pack_version: str) -> bool: ...

    async def archive(self, customer_id: str, pack_version: str) -> None: ...

    async def unarchive(self, customer_id: str, pack_version: str) -> bool: ...

    async def list_versions(self, customer_id: str) -> list[str]: ...


class PostgresArchivedFeaturePackRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_archived(self, customer_id: str, pack_version: str) -> bool:
        row = await self._session.get(ArchivedFeaturePack, (customer_id, pack_version))
        await _release_read_transaction(self._session)
        return row is not None

    async def archive(self, customer_id: str, pack_version: str) -> None:
        """Idempotent: re-archiving an already-archived version is a no-op (the
        composite PK makes the upsert do-nothing)."""
        stmt = (
            pg_insert(ArchivedFeaturePack)
            .values(customer_id=customer_id, pack_version=pack_version)
            .on_conflict_do_nothing(
                index_elements=[
                    ArchivedFeaturePack.customer_id,
                    ArchivedFeaturePack.pack_version,
                ]
            )
        )
        await self._session.execute(stmt)
        await _commit(self._session)

    async def unarchive(self, customer_id: str, pack_version: str) -> bool:
        """Delete the marker (un-hide). Returns True if a marker was removed,
        False if the version was not archived for this customer."""
        row = await self._session.get(ArchivedFeaturePack, (customer_id, pack_version))
        if row is None:
            await _release_read_transaction(self._session)
            return False
        await self._session.delete(row)
        await _commit(self._session)
        return True

    async def list_versions(self, customer_id: str) -> list[str]:
        stmt = (
            select(ArchivedFeaturePack.pack_version)
            .where(ArchivedFeaturePack.customer_id == customer_id)
            .order_by(ArchivedFeaturePack.archived_at.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        await _release_read_transaction(self._session)
        return list(rows)


class InMemoryArchivedFeaturePackRepo:
    def __init__(self) -> None:
        # (customer_id, pack_version) -> archived_at
        self._archived: dict[tuple[str, str], datetime] = {}

    async def is_archived(self, customer_id: str, pack_version: str) -> bool:
        return (customer_id, pack_version) in self._archived

    async def archive(self, customer_id: str, pack_version: str) -> None:
        self._archived.setdefault((customer_id, pack_version), datetime.now(timezone.utc))

    async def unarchive(self, customer_id: str, pack_version: str) -> bool:
        return self._archived.pop((customer_id, pack_version), None) is not None

    async def list_versions(self, customer_id: str) -> list[str]:
        rows = [
            (version, at)
            for (cid, version), at in self._archived.items()
            if cid == customer_id
        ]
        rows.sort(key=lambda r: r[1], reverse=True)
        return [version for version, _ in rows]


# ──────────────────────────────────────────────────────────────────────
# FeatureStoreConnection (#22)
# ──────────────────────────────────────────────────────────────────────


class FeatureStoreConnectionRepo(Protocol):
    async def insert(self, connection: dict[str, Any]) -> dict[str, Any]: ...

    async def get(self, connection_id: str, customer_id: str) -> dict[str, Any] | None: ...

    async def list_for_customer(self, customer_id: str) -> list[dict[str, Any]]: ...

    async def name_exists(self, customer_id: str, name: str) -> bool: ...

    async def delete(self, connection_id: str, customer_id: str) -> bool: ...

    async def record_test_result(
        self,
        connection_id: str,
        customer_id: str,
        *,
        status: str,
        tested_at: datetime,
        error_kind: str | None,
        error_message: str | None,
    ) -> bool: ...


class PostgresFeatureStoreConnectionRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, connection: dict[str, Any]) -> dict[str, Any]:
        row = FeatureStoreConnection(**connection)
        self._session.add(row)
        await _commit(self._session)
        await self._session.refresh(row)
        result = _feature_store_connection_to_dict(row)
        await _release_read_transaction(self._session)
        return result

    async def get(self, connection_id: str, customer_id: str) -> dict[str, Any] | None:
        row = await self._session.get(FeatureStoreConnection, connection_id)
        # Scope by customer: never hand back another tenant's row even on a
        # correct id guess.
        result = (
            _feature_store_connection_to_dict(row)
            if row is not None and row.customer_id == customer_id
            else None
        )
        await _release_read_transaction(self._session)
        return result

    async def list_for_customer(self, customer_id: str) -> list[dict[str, Any]]:
        stmt = (
            select(FeatureStoreConnection)
            .where(FeatureStoreConnection.customer_id == customer_id)
            .order_by(FeatureStoreConnection.updated_at.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        result = [_feature_store_connection_to_dict(row) for row in rows]
        await _release_read_transaction(self._session)
        return result

    async def name_exists(self, customer_id: str, name: str) -> bool:
        """True if this customer already has a connection whose name matches
        `name` case-insensitively (after trim). App-level uniqueness guard for
        #327 — no DB unique constraint, so no Alembic migration. The compare is
        on the trimmed lowercased name; stored values are never mutated."""
        target = name.strip().lower()
        stmt = select(FeatureStoreConnection.id).where(
            FeatureStoreConnection.customer_id == customer_id,
            func.lower(func.trim(FeatureStoreConnection.name)) == target,
        )
        row = (await self._session.execute(stmt)).first()
        await _release_read_transaction(self._session)
        return row is not None

    async def delete(self, connection_id: str, customer_id: str) -> bool:
        """Customer-scoped delete. Returns True if a row owned by `customer_id`
        was deleted, False if the id is unknown OR belongs to another tenant —
        the route maps both to 404 so existence never leaks across customers
        (#327 security requirement)."""
        row = await self._session.get(FeatureStoreConnection, connection_id)
        if row is None or row.customer_id != customer_id:
            await _release_read_transaction(self._session)
            return False
        await self._session.delete(row)
        await _commit(self._session)
        return True

    async def record_test_result(
        self,
        connection_id: str,
        customer_id: str,
        *,
        status: str,
        tested_at: datetime,
        error_kind: str | None,
        error_message: str | None,
    ) -> bool:
        """Persist the outcome of a connectivity test (#328). Customer-scoped:
        only a row this customer OWNS is updated; an unknown id OR another
        tenant's id returns False and writes nothing (security requirement —
        never touch another tenant's health). On success the caller passes
        status='ok' with cleared error fields; on failure status='failed' with
        the classified ``error_kind`` and human-readable ``error_message``."""
        row = await self._session.get(FeatureStoreConnection, connection_id)
        if row is None or row.customer_id != customer_id:
            await _release_read_transaction(self._session)
            return False
        row.last_test_status = status
        row.last_tested_at = tested_at
        row.last_error_kind = error_kind
        row.last_error_message = error_message
        await _commit(self._session)
        return True


class InMemoryFeatureStoreConnectionRepo:
    def __init__(self) -> None:
        self._connections: dict[str, dict[str, Any]] = {}

    async def insert(self, connection: dict[str, Any]) -> dict[str, Any]:
        # Seed the health columns (#328) as None so a freshly-inserted row reads
        # as UNTESTED, matching the Postgres nullable columns. `connection` never
        # carries them on the create path; record_test_result fills them later.
        row = {
            "last_tested_at": None,
            "last_test_status": None,
            "last_error_kind": None,
            "last_error_message": None,
            **connection,
            "updated_at": datetime.now(timezone.utc),
        }
        self._connections[row["id"]] = row
        return dict(row)

    async def get(self, connection_id: str, customer_id: str) -> dict[str, Any] | None:
        row = self._connections.get(connection_id)
        if row is None or row["customer_id"] != customer_id:
            return None
        return dict(row)

    async def list_for_customer(self, customer_id: str) -> list[dict[str, Any]]:
        rows = [r for r in self._connections.values() if r["customer_id"] == customer_id]
        rows.sort(key=lambda r: r["updated_at"], reverse=True)
        return [dict(r) for r in rows]

    async def name_exists(self, customer_id: str, name: str) -> bool:
        """Mirror of the Postgres app-level uniqueness guard (#327): case-
        insensitive, trimmed name compare scoped to the customer. Stored values
        are never mutated — only the comparison is normalized."""
        target = name.strip().lower()
        return any(
            r["customer_id"] == customer_id and r["name"].strip().lower() == target
            for r in self._connections.values()
        )

    async def delete(self, connection_id: str, customer_id: str) -> bool:
        """Customer-scoped delete (#327). Returns True on a successful owned
        delete, False if the id is unknown or owned by another tenant — the
        route maps False to 404 so existence never leaks across customers."""
        row = self._connections.get(connection_id)
        if row is None or row["customer_id"] != customer_id:
            return False
        del self._connections[connection_id]
        return True

    async def record_test_result(
        self,
        connection_id: str,
        customer_id: str,
        *,
        status: str,
        tested_at: datetime,
        error_kind: str | None,
        error_message: str | None,
    ) -> bool:
        """Mirror of the Postgres test-result persistence (#328). Customer-
        scoped: an unknown id OR another tenant's id returns False and mutates
        nothing. Writes status/timestamp + (cleared on ok / set on failed) the
        error fields onto the owned row."""
        row = self._connections.get(connection_id)
        if row is None or row["customer_id"] != customer_id:
            return False
        row["last_test_status"] = status
        row["last_tested_at"] = tested_at
        row["last_error_kind"] = error_kind
        row["last_error_message"] = error_message
        return True


# ──────────────────────────────────────────────────────────────────────
# ExperimentConnection + ExperimentImportRun (#46)
# ──────────────────────────────────────────────────────────────────────


class ExperimentConnectionRepo(Protocol):
    async def insert(self, connection: dict[str, Any]) -> dict[str, Any]: ...

    async def get(self, connection_id: str, customer_id: str) -> dict[str, Any] | None: ...

    async def list_for_customer(self, customer_id: str) -> list[dict[str, Any]]: ...

    async def name_exists(self, customer_id: str, name: str) -> bool: ...

    async def delete(self, connection_id: str, customer_id: str) -> bool: ...

    async def mark_import(
        self,
        connection_id: str,
        customer_id: str,
        *,
        status: str,
        imported_at: datetime,
    ) -> bool: ...


class PostgresExperimentConnectionRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, connection: dict[str, Any]) -> dict[str, Any]:
        row = ExperimentConnection(**connection)
        self._session.add(row)
        await _commit(self._session)
        await self._session.refresh(row)
        result = _experiment_connection_to_dict(row)
        await _release_read_transaction(self._session)
        return result

    async def get(self, connection_id: str, customer_id: str) -> dict[str, Any] | None:
        row = await self._session.get(ExperimentConnection, connection_id)
        # Scope by customer: never hand back another tenant's row even on a
        # correct id guess (cross-tenant → 404 at the route).
        result = (
            _experiment_connection_to_dict(row)
            if row is not None and row.customer_id == customer_id
            else None
        )
        await _release_read_transaction(self._session)
        return result

    async def list_for_customer(self, customer_id: str) -> list[dict[str, Any]]:
        stmt = (
            select(ExperimentConnection)
            .where(ExperimentConnection.customer_id == customer_id)
            .order_by(ExperimentConnection.created_at.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        result = [_experiment_connection_to_dict(row) for row in rows]
        await _release_read_transaction(self._session)
        return result

    async def name_exists(self, customer_id: str, name: str) -> bool:
        """True if this customer already has a source whose name matches `name`
        case-insensitively (after trim). App-level uniqueness guard (mirrors the
        feature-store pattern) — no DB unique constraint, so no extra migration."""
        target = name.strip().lower()
        stmt = select(ExperimentConnection.id).where(
            ExperimentConnection.customer_id == customer_id,
            func.lower(func.trim(ExperimentConnection.name)) == target,
        )
        row = (await self._session.execute(stmt)).first()
        await _release_read_transaction(self._session)
        return row is not None

    async def delete(self, connection_id: str, customer_id: str) -> bool:
        """Customer-scoped delete. Returns True if a row owned by `customer_id`
        was deleted, False if the id is unknown OR belongs to another tenant —
        the route maps both to 404 so existence never leaks across customers. The
        FK ``ondelete=CASCADE`` removes the import-history rows; the cred blob is
        a column on the deleted row, so it goes with it."""
        row = await self._session.get(ExperimentConnection, connection_id)
        if row is None or row.customer_id != customer_id:
            await _release_read_transaction(self._session)
            return False
        await self._session.delete(row)
        await _commit(self._session)
        return True

    async def mark_import(
        self,
        connection_id: str,
        customer_id: str,
        *,
        status: str,
        imported_at: datetime,
    ) -> bool:
        """Stamp the connection's last-import time + status after a (re-)import.
        Customer-scoped: an unknown id OR another tenant's id returns False and
        writes nothing."""
        row = await self._session.get(ExperimentConnection, connection_id)
        if row is None or row.customer_id != customer_id:
            await _release_read_transaction(self._session)
            return False
        row.status = status
        row.last_import_at = imported_at
        await _commit(self._session)
        return True


class InMemoryExperimentConnectionRepo:
    def __init__(self) -> None:
        self._connections: dict[str, dict[str, Any]] = {}

    async def insert(self, connection: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        row = {
            "status": "connected",
            "created_by": None,
            "credentials_enc": None,
            "last_import_at": None,
            **connection,
            "created_at": now,
            "updated_at": now,
        }
        self._connections[row["id"]] = row
        return dict(row)

    async def get(self, connection_id: str, customer_id: str) -> dict[str, Any] | None:
        row = self._connections.get(connection_id)
        if row is None or row["customer_id"] != customer_id:
            return None
        return dict(row)

    async def list_for_customer(self, customer_id: str) -> list[dict[str, Any]]:
        rows = [r for r in self._connections.values() if r["customer_id"] == customer_id]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return [dict(r) for r in rows]

    async def name_exists(self, customer_id: str, name: str) -> bool:
        target = name.strip().lower()
        return any(
            r["customer_id"] == customer_id and r["name"].strip().lower() == target
            for r in self._connections.values()
        )

    async def delete(self, connection_id: str, customer_id: str) -> bool:
        row = self._connections.get(connection_id)
        if row is None or row["customer_id"] != customer_id:
            return False
        del self._connections[connection_id]
        return True

    async def mark_import(
        self,
        connection_id: str,
        customer_id: str,
        *,
        status: str,
        imported_at: datetime,
    ) -> bool:
        row = self._connections.get(connection_id)
        if row is None or row["customer_id"] != customer_id:
            return False
        row["status"] = status
        row["last_import_at"] = imported_at
        return True


class ExperimentImportRunRepo(Protocol):
    async def create(self, run: dict[str, Any]) -> dict[str, Any]: ...

    async def finish(
        self,
        run_id: str,
        customer_id: str,
        *,
        status: str,
        finished_at: datetime,
        imported_count: int,
        failed_count: int,
        error: str | None,
    ) -> bool: ...

    async def list_for_connection(
        self, connection_id: str, customer_id: str
    ) -> list[dict[str, Any]]: ...


class PostgresExperimentImportRunRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: dict[str, Any]) -> dict[str, Any]:
        row = ExperimentImportRun(**run)
        self._session.add(row)
        await _commit(self._session)
        await self._session.refresh(row)
        result = _experiment_import_run_to_dict(row)
        await _release_read_transaction(self._session)
        return result

    async def finish(
        self,
        run_id: str,
        customer_id: str,
        *,
        status: str,
        finished_at: datetime,
        imported_count: int,
        failed_count: int,
        error: str | None,
    ) -> bool:
        row = await self._session.get(ExperimentImportRun, run_id)
        if row is None or row.customer_id != customer_id:
            await _release_read_transaction(self._session)
            return False
        row.status = status
        row.finished_at = finished_at
        row.imported_count = imported_count
        row.failed_count = failed_count
        row.error = error
        await _commit(self._session)
        return True

    async def list_for_connection(
        self, connection_id: str, customer_id: str
    ) -> list[dict[str, Any]]:
        stmt = (
            select(ExperimentImportRun)
            .where(
                ExperimentImportRun.connection_id == connection_id,
                ExperimentImportRun.customer_id == customer_id,
            )
            .order_by(ExperimentImportRun.started_at.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        result = [_experiment_import_run_to_dict(row) for row in rows]
        await _release_read_transaction(self._session)
        return result


class InMemoryExperimentImportRunRepo:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}

    async def create(self, run: dict[str, Any]) -> dict[str, Any]:
        row = {
            "finished_at": None,
            "imported_count": 0,
            "failed_count": 0,
            "error": None,
            **run,
            "started_at": run.get("started_at") or datetime.now(timezone.utc),
        }
        self._runs[row["id"]] = row
        return dict(row)

    async def finish(
        self,
        run_id: str,
        customer_id: str,
        *,
        status: str,
        finished_at: datetime,
        imported_count: int,
        failed_count: int,
        error: str | None,
    ) -> bool:
        row = self._runs.get(run_id)
        if row is None or row["customer_id"] != customer_id:
            return False
        row["status"] = status
        row["finished_at"] = finished_at
        row["imported_count"] = imported_count
        row["failed_count"] = failed_count
        row["error"] = error
        return True

    async def list_for_connection(
        self, connection_id: str, customer_id: str
    ) -> list[dict[str, Any]]:
        rows = [
            r
            for r in self._runs.values()
            if r["connection_id"] == connection_id and r["customer_id"] == customer_id
        ]
        rows.sort(key=lambda r: r["started_at"], reverse=True)
        return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────────────
# PersonaBuildRun (#24)
# ──────────────────────────────────────────────────────────────────────


class PersonaBuildRepo(Protocol):
    async def create(
        self,
        *,
        build_id: str,
        customer_id: str,
        connection_id: str,
        config_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    async def claim_next_pending(self) -> dict[str, Any] | None: ...

    async def fail_orphaned_running(self, *, error: str) -> int: ...

    async def update_status(
        self,
        build_id: str,
        customer_id: str,
        status: str,
        *,
        pack_version: str | None = None,
        stability_score: float | None = None,
        persona_count: int | None = None,
        error: str | None = None,
        completed_at: datetime | None = None,
    ) -> dict[str, Any]: ...

    async def get(self, build_id: str, customer_id: str) -> dict[str, Any] | None: ...

    async def list_recent(self, customer_id: str, limit: int = 50) -> list[dict[str, Any]]: ...

    async def get_by_pack_version(
        self, customer_id: str, pack_version: str
    ) -> dict[str, Any] | None: ...


class PostgresPersonaBuildRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        build_id: str,
        customer_id: str,
        connection_id: str,
        config_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = PersonaBuildRun(
            id=build_id,
            customer_id=customer_id,
            connection_id=connection_id,
            status="pending",
            config_json=config_json,
        )
        self._session.add(row)
        await _commit(self._session)
        await self._session.refresh(row)
        result = _persona_build_to_dict(row)
        await _release_read_transaction(self._session)
        return result

    async def claim_next_pending(self) -> dict[str, Any] | None:
        """Atomically claim the oldest PENDING build across all tenants and flip
        it to RUNNING, returning its row dict. The worker (not customer-scoped)
        calls this to pull its next job. ``SELECT ... FOR UPDATE SKIP LOCKED``
        lets concurrent workers each grab a distinct row without blocking.
        Returns None when nothing is pending."""
        stmt = (
            select(PersonaBuildRun)
            .where(PersonaBuildRun.status == "pending")
            .order_by(PersonaBuildRun.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = (await self._session.execute(stmt)).scalars().first()
        if row is None:
            await _release_read_transaction(self._session)
            return None
        row.status = "running"
        await _commit(self._session)
        await self._session.refresh(row)
        result = _persona_build_to_dict(row)
        await _release_read_transaction(self._session)
        return result

    async def fail_orphaned_running(self, *, error: str) -> int:
        """Mark every RUNNING build FAILED. Called once at worker startup: the
        single worker is the only thing that sets a row RUNNING (in worker mode
        the API enqueues only), so any row still RUNNING when the worker boots is
        a job whose process died mid-build (deploy recreate, OOM, host restart).
        The claim query only looks at PENDING rows, so without this sweep those
        rows would hang RUNNING forever in the UI. Returns the count reaped.

        (Single-worker assumption: a future multi-worker fleet would need a
        per-row lease/heartbeat instead, so a live worker's job isn't reaped by a
        peer's startup.)"""
        now = datetime.now(timezone.utc)
        stmt = (
            sa_update(PersonaBuildRun)
            .where(PersonaBuildRun.status == "running")
            .values(status="failed", error=error, completed_at=now)
        )
        res = await self._session.execute(stmt)
        await _commit(self._session)
        await _release_read_transaction(self._session)
        return res.rowcount or 0

    async def update_status(
        self,
        build_id: str,
        customer_id: str,
        status: str,
        *,
        pack_version: str | None = None,
        stability_score: float | None = None,
        persona_count: int | None = None,
        error: str | None = None,
        completed_at: datetime | None = None,
    ) -> dict[str, Any]:
        row = await self._session.get(PersonaBuildRun, build_id)
        if row is None or row.customer_id != customer_id:
            raise KeyError(f"Persona build {build_id!r} not found for customer {customer_id!r}")
        row.status = status
        if pack_version is not None:
            row.pack_version = pack_version
        if stability_score is not None:
            row.stability_score = stability_score
        if persona_count is not None:
            row.persona_count = persona_count
        if error is not None:
            row.error = error
        if completed_at is not None:
            row.completed_at = completed_at
        await _commit(self._session)
        await self._session.refresh(row)
        result = _persona_build_to_dict(row)
        await _release_read_transaction(self._session)
        return result

    async def get(self, build_id: str, customer_id: str) -> dict[str, Any] | None:
        row = await self._session.get(PersonaBuildRun, build_id)
        result = (
            _persona_build_to_dict(row)
            if row is not None and row.customer_id == customer_id
            else None
        )
        await _release_read_transaction(self._session)
        return result

    async def list_recent(self, customer_id: str, limit: int = 50) -> list[dict[str, Any]]:
        stmt = (
            select(PersonaBuildRun)
            .where(PersonaBuildRun.customer_id == customer_id)
            .order_by(PersonaBuildRun.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        result = [_persona_build_to_dict(row) for row in rows]
        await _release_read_transaction(self._session)
        return result

    async def get_by_pack_version(
        self, customer_id: str, pack_version: str
    ) -> dict[str, Any] | None:
        """Resolve a COMPLETE build by its exact (customer, pack_version) with no
        row cap, so promoting/listing an older version still finds its metadata.
        Returns the newest match if (rarely) more than one build shares a
        version."""
        stmt = (
            select(PersonaBuildRun)
            .where(
                PersonaBuildRun.customer_id == customer_id,
                PersonaBuildRun.pack_version == pack_version,
                PersonaBuildRun.status == "complete",
            )
            .order_by(PersonaBuildRun.created_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalars().first()
        result = _persona_build_to_dict(row) if row is not None else None
        await _release_read_transaction(self._session)
        return result


class InMemoryPersonaBuildRepo:
    def __init__(self) -> None:
        self._builds: dict[str, dict[str, Any]] = {}

    async def create(
        self,
        *,
        build_id: str,
        customer_id: str,
        connection_id: str,
        config_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = {
            "id": build_id,
            "customer_id": customer_id,
            "connection_id": connection_id,
            "status": "pending",
            "pack_version": None,
            "stability_score": None,
            "persona_count": None,
            "error": None,
            "config_json": config_json,
            "created_at": datetime.now(timezone.utc),
            "completed_at": None,
        }
        self._builds[build_id] = row
        return dict(row)

    async def claim_next_pending(self) -> dict[str, Any] | None:
        """Pick the oldest PENDING build (any tenant), flip it to RUNNING, and
        return a copy. Mirrors the Postgres atomic claim for the in-memory path;
        None when nothing is pending."""
        pending = [r for r in self._builds.values() if r["status"] == "pending"]
        if not pending:
            return None
        pending.sort(
            key=lambda r: r.get("created_at") or datetime.min.replace(tzinfo=timezone.utc)
        )
        row = pending[0]
        row["status"] = "running"
        return dict(row)

    async def fail_orphaned_running(self, *, error: str) -> int:
        """In-memory mirror of the Postgres startup sweep: mark every RUNNING
        build FAILED and return the count reaped."""
        now = datetime.now(timezone.utc)
        reaped = 0
        for row in self._builds.values():
            if row["status"] == "running":
                row["status"] = "failed"
                row["error"] = error
                row["completed_at"] = now
                reaped += 1
        return reaped

    async def update_status(
        self,
        build_id: str,
        customer_id: str,
        status: str,
        *,
        pack_version: str | None = None,
        stability_score: float | None = None,
        persona_count: int | None = None,
        error: str | None = None,
        completed_at: datetime | None = None,
    ) -> dict[str, Any]:
        row = self._builds.get(build_id)
        if row is None or row["customer_id"] != customer_id:
            raise KeyError(f"Persona build {build_id!r} not found for customer {customer_id!r}")
        row["status"] = status
        if pack_version is not None:
            row["pack_version"] = pack_version
        if stability_score is not None:
            row["stability_score"] = stability_score
        if persona_count is not None:
            row["persona_count"] = persona_count
        if error is not None:
            row["error"] = error
        if completed_at is not None:
            row["completed_at"] = completed_at
        return dict(row)

    async def get(self, build_id: str, customer_id: str) -> dict[str, Any] | None:
        row = self._builds.get(build_id)
        if row is None or row["customer_id"] != customer_id:
            return None
        return dict(row)

    async def list_recent(self, customer_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = [dict(r) for r in self._builds.values() if r["customer_id"] == customer_id]
        rows.sort(
            key=lambda r: r.get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return rows[:limit]

    async def get_by_pack_version(
        self, customer_id: str, pack_version: str
    ) -> dict[str, Any] | None:
        matches = [
            dict(r)
            for r in self._builds.values()
            if r["customer_id"] == customer_id
            and r.get("pack_version") == pack_version
            and r.get("status") == "complete"
        ]
        matches.sort(
            key=lambda r: r.get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return matches[0] if matches else None


# ──────────────────────────────────────────────────────────────────────
# Conversation (#41) — persistent, multi-thread "Ask the archive"
# ──────────────────────────────────────────────────────────────────────


class ConversationRepo(Protocol):
    """Persistent multi-thread conversations over the fused archive (#41, #42).

    Every method is scoped by BOTH the tenant (``customer_id`` — the Clerk org,
    the outer boundary) AND the end user (``user_id`` — the Clerk session sub,
    the inner PRIVATE boundary, #42). A thread is visible to / mutable by its
    owning ``(customer_id, user_id)`` ONLY: a user can never see or touch another
    user's thread even within the same org. An unknown id, a cross-tenant id, OR
    a same-tenant-but-other-user id all read as None / return False — the route
    maps that to 404 so a thread's existence never leaks across users OR tenants.

    BACK-COMPAT: ``user_id`` is nullable for legacy rows created before #42 (a
    pre-existing demo thread). A legacy NULL-user row is treated as ORG-VISIBLE —
    visible to / editable by ANY user in the owning tenant — so it is not
    orphaned. Encoded as the predicate ``user_id == current OR user_id IS NULL``;
    every NEW thread always stamps a concrete ``user_id``, so this only ever
    matches the legacy rows. ``customer_id`` stays the hard outer boundary
    regardless. ``append_turn`` auto-titles the thread from the first question
    when it is still untitled (Claude-style default).
    """

    async def create(
        self,
        *,
        conversation_id: str,
        customer_id: str,
        user_id: str,
        title: str | None = None,
    ) -> dict[str, Any]: ...

    async def list_for_user(
        self, customer_id: str, user_id: str, limit: int = 100
    ) -> list[dict[str, Any]]: ...

    async def get(
        self, conversation_id: str, customer_id: str, user_id: str
    ) -> dict[str, Any] | None: ...

    async def get_with_turns(
        self, conversation_id: str, customer_id: str, user_id: str
    ) -> dict[str, Any] | None: ...

    async def rename(
        self, conversation_id: str, customer_id: str, user_id: str, title: str
    ) -> dict[str, Any] | None: ...

    async def delete(
        self, conversation_id: str, customer_id: str, user_id: str
    ) -> bool: ...

    async def append_turn(
        self,
        *,
        turn_id: str,
        conversation_id: str,
        customer_id: str,
        user_id: str,
        question: str,
        answer: str,
        citations: list[Any],
        used_llm: bool,
    ) -> dict[str, Any] | None: ...


# Claude-style default title: a trimmed first question. Kept here (shared by both
# repo impls) so the in-memory and Postgres paths derive byte-identical titles.
_AUTO_TITLE_MAX = 80

# Bounded retries when a concurrent append collides on the
# (conversation_id, turn_index) unique constraint. Appends to one thread are
# effectively serial in practice, so a single retry almost always wins; the cap
# just prevents an unbounded loop under pathological contention.
_APPEND_MAX_RETRIES = 5


def derive_default_title(question: str) -> str:
    """Trim a first question into a Claude-style default thread title.

    Collapses whitespace, strips a trailing question mark for compactness, and
    caps the length with an ellipsis. Never empty (the caller only invokes this
    on a non-empty first question)."""
    cleaned = " ".join(question.strip().split())
    if len(cleaned) > _AUTO_TITLE_MAX:
        cleaned = cleaned[: _AUTO_TITLE_MAX - 1].rstrip() + "…"
    return cleaned


def _row_visible_to_user(
    row: "Conversation | None", customer_id: str, user_id: str
) -> bool:
    """The (customer_id, user_id) access predicate for a fetched row (#42).

    A thread is accessible iff it belongs to the tenant AND it is either owned by
    this user OR a legacy NULL-user row (org-visible back-compat). ``customer_id``
    is the hard outer boundary; ``user_id`` is the private inner boundary."""
    if row is None or row.customer_id != customer_id:
        return False
    return row.user_id is None or row.user_id == user_id


class PostgresConversationRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        conversation_id: str,
        customer_id: str,
        user_id: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        # New rows ALWAYS stamp a concrete user_id (#42) — the NULL case is legacy
        # rows only.
        row = Conversation(
            id=conversation_id,
            customer_id=customer_id,
            user_id=user_id,
            title=title,
        )
        self._session.add(row)
        await _commit(self._session)
        await self._session.refresh(row)
        result = _conversation_to_dict(row)
        await _release_read_transaction(self._session)
        return result

    async def list_for_user(
        self, customer_id: str, user_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        # Scope by BOTH tenant AND user (#42). Legacy NULL-user rows stay visible
        # to any user in the tenant (org-visible back-compat).
        stmt = (
            select(Conversation)
            .where(
                Conversation.customer_id == customer_id,
                or_(
                    Conversation.user_id == user_id,
                    Conversation.user_id.is_(None),
                ),
            )
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        result = [_conversation_to_dict(r) for r in rows]
        await _release_read_transaction(self._session)
        return result

    async def get(
        self, conversation_id: str, customer_id: str, user_id: str
    ) -> dict[str, Any] | None:
        row = await self._session.get(Conversation, conversation_id)
        result = (
            _conversation_to_dict(row)
            if _row_visible_to_user(row, customer_id, user_id)
            else None
        )
        await _release_read_transaction(self._session)
        return result

    async def get_with_turns(
        self, conversation_id: str, customer_id: str, user_id: str
    ) -> dict[str, Any] | None:
        row = await self._session.get(Conversation, conversation_id)
        if not _row_visible_to_user(row, customer_id, user_id):
            await _release_read_transaction(self._session)
            return None
        assert row is not None
        # Tenant isolation: even though the parent is already (customer, user)-
        # checked, scope the turns by customer_id too so a mis-tenanted turn row
        # (e.g. a bad backfill or a future denormalization bug) can never be
        # replayed. (Turns are not user-stamped — the parent thread carries the
        # user scope; a turn always rides its parent's private boundary.)
        stmt = (
            select(ConversationTurn)
            .where(
                ConversationTurn.conversation_id == conversation_id,
                ConversationTurn.customer_id == customer_id,
            )
            .order_by(ConversationTurn.turn_index.asc())
        )
        turns = (await self._session.execute(stmt)).scalars().all()
        result = _conversation_to_dict(row)
        result["turns"] = [_conversation_turn_to_dict(t) for t in turns]
        await _release_read_transaction(self._session)
        return result

    async def rename(
        self, conversation_id: str, customer_id: str, user_id: str, title: str
    ) -> dict[str, Any] | None:
        row = await self._session.get(Conversation, conversation_id)
        if not _row_visible_to_user(row, customer_id, user_id):
            await _release_read_transaction(self._session)
            return None
        assert row is not None
        row.title = title
        await _commit(self._session)
        await self._session.refresh(row)
        result = _conversation_to_dict(row)
        await _release_read_transaction(self._session)
        return result

    async def delete(
        self, conversation_id: str, customer_id: str, user_id: str
    ) -> bool:
        row = await self._session.get(Conversation, conversation_id)
        if not _row_visible_to_user(row, customer_id, user_id):
            await _release_read_transaction(self._session)
            return False
        assert row is not None
        await self._session.delete(row)
        await _commit(self._session)
        return True

    async def append_turn(
        self,
        *,
        turn_id: str,
        conversation_id: str,
        customer_id: str,
        user_id: str,
        question: str,
        answer: str,
        citations: list[Any],
        used_llm: bool,
    ) -> dict[str, Any] | None:
        row = await self._session.get(Conversation, conversation_id)
        if not _row_visible_to_user(row, customer_id, user_id):
            await _release_read_transaction(self._session)
            return None
        assert row is not None
        # next_index is computed in Python off a tenant-scoped count; the
        # uq_conversation_turns_conversation_id_turn_index unique constraint is the
        # backstop. On the rare concurrent-append collision the commit raises
        # IntegrityError — recompute the next index and retry a bounded number of
        # times so the caller gets a clean append, never a 500 or a dup index.
        last_error: IntegrityError | None = None
        for _ in range(_APPEND_MAX_RETRIES):
            # Tenant-scoped count so a mis-tenanted turn row can never perturb
            # this conversation's ordering.
            count_stmt = select(func.count(ConversationTurn.id)).where(
                ConversationTurn.conversation_id == conversation_id,
                ConversationTurn.customer_id == customer_id,
            )
            next_index = (await self._session.execute(count_stmt)).scalar_one()
            turn = ConversationTurn(
                id=turn_id,
                conversation_id=conversation_id,
                customer_id=customer_id,
                turn_index=next_index,
                question=question,
                answer=answer,
                citations_json=citations,
                used_llm=used_llm,
            )
            self._session.add(turn)
            # First turn on an untitled thread auto-titles it (Claude default).
            if next_index == 0 and not row.title:
                row.title = derive_default_title(question)
            # Touch updated_at so the thread floats to the top of newest-first.
            row.updated_at = datetime.now(timezone.utc)
            try:
                await _commit(self._session)
            except IntegrityError as exc:
                # _commit already rolled the transaction back. Re-fetch the parent
                # (the prior session objects are now detached) and retry.
                last_error = exc
                row = await self._session.get(Conversation, conversation_id)
                if not _row_visible_to_user(row, customer_id, user_id):
                    return None
                continue
            return await self.get_with_turns(conversation_id, customer_id, user_id)
        # Exhausted retries against a sustained collision — surface the integrity
        # error so the route returns a clean retry-able failure, not a silent dup.
        assert last_error is not None
        raise last_error


class InMemoryConversationRepo:
    def __init__(self) -> None:
        # conversation_id -> {meta..., "turns": [turn dicts]}
        self._threads: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _visible(
        row: dict[str, Any] | None, customer_id: str, user_id: str
    ) -> bool:
        """(customer_id, user_id) access predicate (#42), mirroring the Postgres
        ``_row_visible_to_user``: tenant-scoped AND (owned by this user OR a
        legacy NULL-user org-visible row)."""
        if row is None or row["customer_id"] != customer_id:
            return False
        return row.get("user_id") is None or row["user_id"] == user_id

    async def create(
        self,
        *,
        conversation_id: str,
        customer_id: str,
        user_id: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        row = {
            "id": conversation_id,
            "customer_id": customer_id,
            # New rows ALWAYS stamp a concrete user_id (#42).
            "user_id": user_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "turns": [],
        }
        self._threads[conversation_id] = row
        return _conversation_meta(row)

    async def list_for_user(
        self, customer_id: str, user_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        rows = [
            r
            for r in self._threads.values()
            if self._visible(r, customer_id, user_id)
        ]
        rows.sort(key=lambda r: r["updated_at"], reverse=True)
        return [_conversation_meta(r) for r in rows[:limit]]

    async def get(
        self, conversation_id: str, customer_id: str, user_id: str
    ) -> dict[str, Any] | None:
        row = self._threads.get(conversation_id)
        if not self._visible(row, customer_id, user_id):
            return None
        return _conversation_meta(row)

    async def get_with_turns(
        self, conversation_id: str, customer_id: str, user_id: str
    ) -> dict[str, Any] | None:
        row = self._threads.get(conversation_id)
        if not self._visible(row, customer_id, user_id):
            return None
        assert row is not None
        result = _conversation_meta(row)
        result["turns"] = [dict(t) for t in row["turns"]]
        return result

    async def rename(
        self, conversation_id: str, customer_id: str, user_id: str, title: str
    ) -> dict[str, Any] | None:
        row = self._threads.get(conversation_id)
        if not self._visible(row, customer_id, user_id):
            return None
        assert row is not None
        row["title"] = title
        row["updated_at"] = datetime.now(timezone.utc)
        return _conversation_meta(row)

    async def delete(
        self, conversation_id: str, customer_id: str, user_id: str
    ) -> bool:
        row = self._threads.get(conversation_id)
        if not self._visible(row, customer_id, user_id):
            return False
        del self._threads[conversation_id]
        return True

    async def append_turn(
        self,
        *,
        turn_id: str,
        conversation_id: str,
        customer_id: str,
        user_id: str,
        question: str,
        answer: str,
        citations: list[Any],
        used_llm: bool,
    ) -> dict[str, Any] | None:
        row = self._threads.get(conversation_id)
        if not self._visible(row, customer_id, user_id):
            return None
        assert row is not None
        next_index = len(row["turns"])
        row["turns"].append(
            {
                "id": turn_id,
                "conversation_id": conversation_id,
                "customer_id": customer_id,
                "turn_index": next_index,
                "question": question,
                "answer": answer,
                "citations_json": list(citations),
                "used_llm": used_llm,
                "created_at": datetime.now(timezone.utc),
            }
        )
        if next_index == 0 and not row["title"]:
            row["title"] = derive_default_title(question)
        row["updated_at"] = datetime.now(timezone.utc)
        return await self.get_with_turns(conversation_id, customer_id, user_id)


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────


def _conversation_to_dict(row: Conversation) -> dict[str, Any]:
    return {
        "id": row.id,
        "customer_id": row.customer_id,
        "user_id": row.user_id,
        "title": row.title,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _conversation_turn_to_dict(row: ConversationTurn) -> dict[str, Any]:
    return {
        "id": row.id,
        "conversation_id": row.conversation_id,
        "customer_id": row.customer_id,
        "turn_index": row.turn_index,
        "question": row.question,
        "answer": row.answer,
        "citations_json": row.citations_json or [],
        "used_llm": row.used_llm,
        "created_at": row.created_at,
    }


def _conversation_meta(row: dict[str, Any]) -> dict[str, Any]:
    """In-memory thread row → metadata dict (no turns), matching the Postgres
    ``_conversation_to_dict`` shape."""
    return {
        "id": row["id"],
        "customer_id": row["customer_id"],
        "user_id": row.get("user_id"),
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _persona_build_to_dict(row: PersonaBuildRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "customer_id": row.customer_id,
        "connection_id": row.connection_id,
        "status": row.status,
        "pack_version": row.pack_version,
        "stability_score": row.stability_score,
        "persona_count": row.persona_count,
        "error": row.error,
        "config_json": row.config_json,
        "created_at": row.created_at,
        "completed_at": row.completed_at,
    }


def _feature_store_connection_to_dict(row: FeatureStoreConnection) -> dict[str, Any]:
    return {
        "id": row.id,
        "customer_id": row.customer_id,
        "name": row.name,
        "kind": row.kind,
        "account": row.account,
        "user": row.user,
        "warehouse": row.warehouse,
        "role": row.role,
        "database": row.database,
        "schema": row.schema,
        "password_enc": row.password_enc,
        "updated_at": row.updated_at,
        # Per-connection health (#328) — last connectivity-test outcome. NULL on a
        # row that has never been tested (reads as UNTESTED in the register).
        "last_tested_at": row.last_tested_at,
        "last_test_status": row.last_test_status,
        "last_error_kind": row.last_error_kind,
        "last_error_message": row.last_error_message,
    }


def _experiment_connection_to_dict(row: ExperimentConnection) -> dict[str, Any]:
    return {
        "id": row.id,
        "customer_id": row.customer_id,
        "name": row.name,
        "kind": row.kind,
        "display_config": row.display_config,
        # Carried for the decrypt path (test / re-import) — the route NEVER
        # echoes it; the response model has no field for it.
        "credentials_enc": row.credentials_enc,
        "status": row.status,
        "created_by": row.created_by,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "last_import_at": row.last_import_at,
    }


def _experiment_import_run_to_dict(row: ExperimentImportRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "connection_id": row.connection_id,
        "customer_id": row.customer_id,
        "status": row.status,
        "started_at": row.started_at,
        "finished_at": row.finished_at,
        "imported_count": row.imported_count,
        "failed_count": row.failed_count,
        "error": row.error,
    }


def _crawl_run_to_dict(row: CrawlRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "customer_id": row.customer_id,
        "status": row.status,
        "crawl_date": row.crawl_date,
        "run_id": row.run_id,
        "run_url": row.run_url,
        "snapshot_version": row.snapshot_version,
        "error": row.error,
        "created_at": row.created_at,
        "completed_at": row.completed_at,
    }


def _crawl_config_to_dict(row: CrawlConfig) -> dict[str, Any]:
    return {
        "customer_id": row.customer_id,
        "setup_id": row.setup_id,
        "name": row.name,
        "config_json": row.config_json,
        "updated_at": row.updated_at,
    }


def _simulation_to_dict(row: Simulation) -> dict[str, Any]:
    return {
        "id": row.id,
        "customer_id": row.customer_id,
        "status": row.status,
        "persona_pack_version": row.persona_pack_version,
        "feature_pack_version": row.feature_pack_version,
        "setup_id": row.setup_id,
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
_in_memory_crawl_configs: InMemoryCrawlConfigRepo | None = None


def get_in_memory_crawl_config_repo() -> InMemoryCrawlConfigRepo:
    """Process-wide in-memory crawl-config repo (kept separate from the
    4-tuple in get_in_memory_repos so existing callers stay untouched)."""
    global _in_memory_crawl_configs
    if _in_memory_crawl_configs is None:
        _in_memory_crawl_configs = InMemoryCrawlConfigRepo()
    return _in_memory_crawl_configs


_in_memory_crawl_runs: InMemoryCrawlRunRepo | None = None


def get_in_memory_crawl_run_repo() -> InMemoryCrawlRunRepo:
    """Process-wide in-memory crawl-run repo (same pattern as crawl configs)."""
    global _in_memory_crawl_runs
    if _in_memory_crawl_runs is None:
        _in_memory_crawl_runs = InMemoryCrawlRunRepo()
    return _in_memory_crawl_runs


_in_memory_archived_feature_packs: InMemoryArchivedFeaturePackRepo | None = None


def get_in_memory_archived_feature_pack_repo() -> InMemoryArchivedFeaturePackRepo:
    """Process-wide in-memory archived-feature-pack repo (#214), same pattern as
    crawl configs/runs. Reset in tests via ``._archived.clear()``."""
    global _in_memory_archived_feature_packs
    if _in_memory_archived_feature_packs is None:
        _in_memory_archived_feature_packs = InMemoryArchivedFeaturePackRepo()
    return _in_memory_archived_feature_packs


_in_memory_feature_store_connections: InMemoryFeatureStoreConnectionRepo | None = None


def get_in_memory_feature_store_connection_repo() -> InMemoryFeatureStoreConnectionRepo:
    """Process-wide in-memory feature-store-connection repo (#22), same pattern
    as crawl configs/runs. Reset in tests via ``._connections.clear()``."""
    global _in_memory_feature_store_connections
    if _in_memory_feature_store_connections is None:
        _in_memory_feature_store_connections = InMemoryFeatureStoreConnectionRepo()
    return _in_memory_feature_store_connections


_in_memory_experiment_connections: InMemoryExperimentConnectionRepo | None = None
_in_memory_experiment_import_runs: InMemoryExperimentImportRunRepo | None = None


def get_in_memory_experiment_connection_repo() -> InMemoryExperimentConnectionRepo:
    """Process-wide in-memory experiment-connection repo (#46), same pattern as
    the feature-store repo. Reset in tests via ``._connections.clear()``."""
    global _in_memory_experiment_connections
    if _in_memory_experiment_connections is None:
        _in_memory_experiment_connections = InMemoryExperimentConnectionRepo()
    return _in_memory_experiment_connections


def get_in_memory_experiment_import_run_repo() -> InMemoryExperimentImportRunRepo:
    """Process-wide in-memory experiment-import-run repo (#46). Reset in tests via
    ``._runs.clear()``."""
    global _in_memory_experiment_import_runs
    if _in_memory_experiment_import_runs is None:
        _in_memory_experiment_import_runs = InMemoryExperimentImportRunRepo()
    return _in_memory_experiment_import_runs


_in_memory_persona_builds: InMemoryPersonaBuildRepo | None = None


def get_in_memory_persona_build_repo() -> InMemoryPersonaBuildRepo:
    """Process-wide in-memory persona-build repo (#24), same pattern as crawl
    configs/runs + feature-store connections. Reset in tests via
    ``._builds.clear()``."""
    global _in_memory_persona_builds
    if _in_memory_persona_builds is None:
        _in_memory_persona_builds = InMemoryPersonaBuildRepo()
    return _in_memory_persona_builds


_in_memory_conversations: InMemoryConversationRepo | None = None


def get_in_memory_conversation_repo() -> InMemoryConversationRepo:
    """Process-wide in-memory conversation repo (#41), same pattern as crawl
    configs/runs + persona builds. Reset in tests via ``._threads.clear()``."""
    global _in_memory_conversations
    if _in_memory_conversations is None:
        _in_memory_conversations = InMemoryConversationRepo()
    return _in_memory_conversations


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
