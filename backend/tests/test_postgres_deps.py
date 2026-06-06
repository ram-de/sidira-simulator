"""Phase 5a #68: Postgres dependency wiring contracts."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy.dialects import postgresql

from sidira_simulator.adapters import postgres
from sidira_simulator.adapters import migrations
from sidira_simulator.adapters.db_models import AgentInstance
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
        self.committed = False

    async def commit(self) -> None:
        self.committed = True

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


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        (
            "postgresql://user:pass@example.invalid:5432/sidira",
            "postgresql+asyncpg://user:pass@example.invalid:5432/sidira",
        ),
        (
            "postgres://user:pass@example.invalid/sidira",
            "postgresql+asyncpg://user:pass@example.invalid/sidira",
        ),
        (
            "postgresql+asyncpg://user:pass@example.invalid/sidira?sslmode=require&connect_timeout=5",
            "postgresql+asyncpg://user:pass@example.invalid/sidira?ssl=require&connect_timeout=5",
        ),
        (
            "postgresql://user:pass@example.invalid/sidira?sslmode=disable",
            "postgresql+asyncpg://user:pass@example.invalid/sidira?ssl=disable",
        ),
        (
            "postgresql://user:pass@example.invalid/sidira?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://user:pass@example.invalid/sidira?ssl=require",
        ),
    ],
)
def test_database_url_normalizes_provider_connection_strings(
    monkeypatch, raw: str, normalized: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", raw)

    assert postgres.database_url() == normalized


def test_database_url_normalizes_sidira_and_legacy_fallbacks(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SIDIRA_DATABASE_URL", "postgres://user:pass@example.invalid/sidira")
    monkeypatch.delenv("PYTHIA_DATABASE_URL", raising=False)

    assert postgres.database_url() == "postgresql+asyncpg://user:pass@example.invalid/sidira"

    monkeypatch.delenv("SIDIRA_DATABASE_URL", raising=False)
    monkeypatch.setenv("PYTHIA_DATABASE_URL", "postgresql://user:pass@example.invalid/legacy")

    assert postgres.database_url() == "postgresql+asyncpg://user:pass@example.invalid/legacy"


def test_repo_factories_use_postgres_repos_when_session_is_present(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://example.invalid/sidira")
    session = object()

    assert isinstance(deps.get_customer_repo(session), PostgresCustomerRepo)
    assert isinstance(deps.get_simulation_repo(session), PostgresSimulationRepo)
    assert isinstance(deps.get_agent_repo(session), PostgresAgentInstanceRepo)


class _StatementRecordingSession(_FakeSession):
    def __init__(self, result: Any = None) -> None:
        super().__init__()
        self.statements: list[Any] = []
        self._result = result
        self.rollback_count = 0

    async def execute(self, statement):
        self.statements.append(statement)
        return self._result

    async def rollback(self) -> None:
        await super().rollback()
        self.rollback_count += 1

    def in_transaction(self) -> bool:
        return True

    @property
    def new(self):
        return set()

    @property
    def dirty(self):
        return set()

    @property
    def deleted(self):
        return set()


class _EmptyScalarResult:
    def scalars(self):
        return self

    def all(self) -> list[Any]:
        return []


@pytest.mark.asyncio
async def test_postgres_customer_ensure_exists_is_atomic() -> None:
    session = _StatementRecordingSession()
    repo = PostgresCustomerRepo(session)

    await repo.ensure_exists("demo")

    assert session.committed is True
    sql = str(session.statements[0].compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (id) DO NOTHING" in sql


@pytest.mark.asyncio
async def test_postgres_customer_ensure_exists_backfills_clerk_fields_on_conflict() -> None:
    # A webhook delivery carries clerk_org_id, so the conflict path must UPDATE
    # the profile fields (closing the signup-then-act race) rather than skip.
    session = _StatementRecordingSession()
    repo = PostgresCustomerRepo(session)

    await repo.ensure_exists("org_x", name="Acme", clerk_org_id="org_x")

    assert session.committed is True
    sql = str(session.statements[0].compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (id) DO UPDATE" in sql
    assert "clerk_org_id" in sql


@pytest.mark.asyncio
async def test_in_memory_customer_ensure_exists_backfills_then_resists_clobber() -> None:
    repo = InMemoryCustomerRepo()
    # Orchestrator creates a placeholder row first (no clerk_org_id).
    await repo.ensure_exists("org_x")
    # Webhook backfills the org name + clerk_org_id.
    await repo.ensure_exists("org_x", name="Acme", clerk_org_id="org_x")
    assert repo._customers["org_x"] == {"id": "org_x", "name": "Acme", "clerk_org_id": "org_x"}
    # A later bare ensure_exists (orchestrator path) must NOT clobber the name.
    await repo.ensure_exists("org_x", name="org_x")
    assert repo._customers["org_x"]["name"] == "Acme"


@pytest.mark.asyncio
async def test_postgres_agent_listing_is_ordered_and_releases_read_transaction() -> None:
    session = _StatementRecordingSession(_EmptyScalarResult())
    repo = PostgresAgentInstanceRepo(session)

    assert await repo.list_for_simulation("sim_1", "demo") == []

    sql = str(session.statements[0].compile(dialect=postgresql.dialect()))
    assert (
        "ORDER BY agent_instances.materialization_index ASC NULLS LAST, "
        "agent_instances.created_at ASC, agent_instances.id ASC"
    ) in sql
    assert session.rollback_count == 1


@pytest.mark.asyncio
async def test_postgres_agent_get_releases_read_transaction_after_materializing_row() -> None:
    now = datetime.now(timezone.utc)
    row = AgentInstance(
        id="agent_1",
        customer_id="demo",
        simulation_id="sim_1",
        persona_id="maya",
        persona_pack_version="v1",
        persona_name="Maya",
        created_at=now,
        last_active_at=now,
        message_count=0,
        materialization_index=0,
        arm=None,
    )
    session = _StatementRecordingSession()

    async def get(model, key):
        return row

    session.get = get  # type: ignore[method-assign]
    repo = PostgresAgentInstanceRepo(session)

    result = await repo.get("agent_1", "demo")

    assert result is not None
    assert result["id"] == "agent_1"
    assert session.rollback_count == 1


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

    async def ensure_exists(
        self, customer_id: str, name: str | None = None, clerk_org_id: str | None = None
    ) -> None:
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
