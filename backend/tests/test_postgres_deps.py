"""Phase 5a #68: Postgres dependency wiring contracts."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import pytest

from sidira_simulator.adapters import postgres
from sidira_simulator.adapters import migrations
from sidira_simulator.adapters.repositories import (
    InMemoryAgentFeedbackRepo,
    InMemoryAgentInstanceRepo,
    InMemoryCustomerRepo,
    InMemorySimulationRepo,
    PostgresAgentInstanceRepo,
    PostgresCustomerRepo,
    PostgresSimulationRepo,
)
from sidira_simulator.api import deps
from sidira_simulator.schemas.persona import Persona, PersonaPack
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.simulation_orchestrator import SimulationOrchestrator


class _FakeSession:
    def __init__(self) -> None:
        self.rolled_back = False

    async def rollback(self) -> None:
        self.rolled_back = True


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session
        self.exited = False

    async def __aenter__(self) -> _FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.exited = True


@pytest.mark.asyncio
async def test_postgres_session_dependency_rolls_back_on_exception(monkeypatch) -> None:
    session = _FakeSession()
    context = _FakeSessionContext(session)
    monkeypatch.setattr(postgres, "get_sessionmaker", lambda: lambda: context)

    dependency = postgres.get_session()
    assert await dependency.__anext__() is session

    with pytest.raises(RuntimeError, match="route failed"):
        await dependency.athrow(RuntimeError("route failed"))

    assert session.rolled_back is True
    assert context.exited is True


@pytest.mark.asyncio
async def test_repository_session_dependency_rolls_back_on_exception(monkeypatch) -> None:
    session = _FakeSession()
    context = _FakeSessionContext(session)
    monkeypatch.setattr(deps, "database_configured", lambda: True)
    monkeypatch.setattr(deps, "get_sessionmaker", lambda: lambda: context)

    dependency = deps.get_repository_session()
    assert await dependency.__anext__() is session

    with pytest.raises(RuntimeError, match="route failed"):
        await dependency.athrow(RuntimeError("route failed"))

    assert session.rolled_back is True
    assert context.exited is True


def test_repo_factories_keep_in_memory_fallback_when_no_session(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SIDIRA_DATABASE_URL", raising=False)
    monkeypatch.delenv("PYTHIA_DATABASE_URL", raising=False)

    assert isinstance(deps.get_customer_repo(None), InMemoryCustomerRepo)
    assert isinstance(deps.get_simulation_repo(None), InMemorySimulationRepo)
    assert isinstance(deps.get_agent_repo(None), InMemoryAgentInstanceRepo)
    assert isinstance(deps.get_feedback_repo(None), InMemoryAgentFeedbackRepo)


def test_repo_factories_use_postgres_repos_when_session_is_present(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://example.invalid/sidira")
    session = object()

    assert isinstance(deps.get_customer_repo(session), PostgresCustomerRepo)
    assert isinstance(deps.get_simulation_repo(session), PostgresSimulationRepo)
    assert isinstance(deps.get_agent_repo(session), PostgresAgentInstanceRepo)


def test_startup_migrations_are_opt_in(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.delenv("SIDIRA_AUTO_MIGRATE", raising=False)
    monkeypatch.delenv("PYTHIA_AUTO_MIGRATE", raising=False)
    monkeypatch.setattr(
        migrations.command, "upgrade", lambda config, revision: calls.append(revision)
    )

    migrations.run_startup_migrations()

    assert calls == []


def test_startup_migrations_run_when_enabled_and_database_configured(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setenv("SIDIRA_AUTO_MIGRATE", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://example.invalid/sidira")
    monkeypatch.setattr(
        migrations.command, "upgrade", lambda config, revision: calls.append(revision)
    )

    migrations.run_startup_migrations()

    assert calls == ["head"]


@dataclass
class _RecordingRepo:
    name: str
    calls: list[str]

    async def ensure_exists(self, customer_id: str, name: str | None = None) -> None:
        self.calls.append(f"{self.name}.ensure_exists")

    async def create(self, **kwargs: Any) -> None:
        self.calls.append(f"{self.name}.create")

    async def update_status(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(f"{self.name}.update_status")

    async def list_for_simulation(self, sim_id: str, customer_id: str) -> list[dict[str, Any]]:
        self.calls.append(f"{self.name}.list_for_simulation")
        return []


class _PersonaLoader:
    def load_latest(self, customer_id: str) -> PersonaPack:
        return PersonaPack(
            customer_id=customer_id,
            version="v1",
            generated_at="2026-05-29T00:00:00Z",
            source={"type": "test"},
            personas=[
                Persona(
                    id="maya",
                    name="Maya",
                    description="Test persona",
                )
            ],
            weights={"head_count": {"maya": 1.0}},
            stability_score=1.0,
        )


class _FeatureLoader:
    def resolve_latest_version(self, customer_id: str) -> str:
        return "2026-W21"


class _RecordingOrchestrator(SimulationOrchestrator):
    async def _run_in_background(self, **kwargs: Any) -> None:
        await self._simulations.update_status(
            kwargs["sim_id"],
            kwargs["customer_id"],
            "complete",
        )


@pytest.mark.asyncio
async def test_background_run_uses_factory_orchestrator_instead_of_request_repos() -> None:
    request_calls: list[str] = []
    background_calls: list[str] = []

    @asynccontextmanager
    async def background_factory():
        yield _RecordingOrchestrator(
            customer_repo=_RecordingRepo("background_customers", background_calls),
            simulation_repo=_RecordingRepo("background_simulations", background_calls),
            agent_repo=_RecordingRepo("background_agents", background_calls),
            persona_loader=_PersonaLoader(),
            feature_pack_loader=_FeatureLoader(),
        )

    orchestrator = _RecordingOrchestrator(
        customer_repo=_RecordingRepo("request_customers", request_calls),
        simulation_repo=_RecordingRepo("request_simulations", request_calls),
        agent_repo=_RecordingRepo("request_agents", request_calls),
        persona_loader=_PersonaLoader(),
        feature_pack_loader=_FeatureLoader(),
        background_orchestrator_factory=background_factory,
    )

    _sim_id, run = await orchestrator.prepare(
        customer_id="demo",
        hypothesis=Hypothesis(
            capability_name="reorder",
            prose="Add a one-tap reorder button.",
        ),
    )
    await run()

    assert request_calls == ["request_customers.ensure_exists", "request_simulations.create"]
    assert background_calls == ["background_simulations.update_status"]
