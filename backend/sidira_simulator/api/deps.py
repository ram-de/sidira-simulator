"""FastAPI dependencies — customer scope + orchestrator wiring.

Resolves customer_id from the Clerk session (populated on ``request.state`` by
the auth gate in ``main.py``) and uses in-memory repos when Postgres is not
configured. The Clerk/JWT path takes precedence; the SIDIRA_CUSTOMER_ID env
(default "demo") remains the dev-time / unauthenticated fallback.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated, AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.postgres import (
    database_configured,
    get_sessionmaker,
)
from sidira_simulator.adapters.repositories import (
    AgentFeedbackRepo,
    AgentInstanceRepo,
    CustomerRepo,
    PostgresAgentFeedbackRepo,
    PostgresAgentInstanceRepo,
    PostgresCustomerRepo,
    PostgresSimulationRepo,
    SimulationRepo,
    get_in_memory_repos,
)
from sidira_simulator.services.runtime_config import resolve_sidira_env
from sidira_simulator.services.simulation_orchestrator import (
    BackgroundOrchestratorFactory,
    SimulationOrchestrator,
)

DEFAULT_CUSTOMER_ID = "demo"


def current_customer_id(request: Request) -> str:
    """Resolve the customer for the current request.

    Prefers ``request.state.customer_id`` set by the Clerk auth gate from the
    session token. Falls back to the SIDIRA_CUSTOMER_ID env var (with legacy
    PYTHIA_CUSTOMER_ID fallback, then "demo") for local dev and the test suite,
    where Clerk auth is disabled.
    """
    from_session = getattr(request.state, "customer_id", None)
    if from_session:
        return str(from_session)
    customer_id = resolve_sidira_env("CUSTOMER_ID", DEFAULT_CUSTOMER_ID)
    assert customer_id is not None
    return customer_id


async def get_repository_session() -> AsyncIterator[AsyncSession | None]:
    """Yield a request-scoped DB session when Postgres is configured.

    Keeping the no-DB path as `None` lets local dev and the existing test suite
    continue to use process-wide InMemory repos without creating an engine.
    """
    if not database_configured():
        yield None
        return

    async with get_sessionmaker()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


RepositorySession = Annotated[AsyncSession | None, Depends(get_repository_session)]


def _repos(
    session: AsyncSession | None,
) -> tuple[CustomerRepo, SimulationRepo, AgentInstanceRepo, AgentFeedbackRepo]:
    if session is None:
        return get_in_memory_repos()
    return (
        PostgresCustomerRepo(session),
        PostgresSimulationRepo(session),
        PostgresAgentInstanceRepo(session),
        PostgresAgentFeedbackRepo(session),
    )


def get_customer_repo(session: RepositorySession = None) -> CustomerRepo:
    return _repos(session)[0]


def get_simulation_repo(session: RepositorySession = None) -> SimulationRepo:
    return _repos(session)[1]


def get_agent_repo(session: RepositorySession = None) -> AgentInstanceRepo:
    return _repos(session)[2]


def get_feedback_repo(session: RepositorySession = None) -> AgentFeedbackRepo:
    return _repos(session)[3]


def get_persona_loader() -> PersonaPackLoader:
    return PersonaPackLoader()


def get_feature_pack_loader() -> FeaturePackLoader:
    return FeaturePackLoader()


def get_background_orchestrator_factory(
    persona_loader: PersonaPackLoader = Depends(get_persona_loader),
    feature_pack_loader: FeaturePackLoader = Depends(get_feature_pack_loader),
) -> BackgroundOrchestratorFactory | None:
    if not database_configured():
        return None

    @asynccontextmanager
    async def factory() -> AsyncIterator[SimulationOrchestrator]:
        async with get_sessionmaker()() as session:
            try:
                yield SimulationOrchestrator(
                    customer_repo=PostgresCustomerRepo(session),
                    simulation_repo=PostgresSimulationRepo(session),
                    agent_repo=PostgresAgentInstanceRepo(session),
                    persona_loader=persona_loader,
                    feature_pack_loader=feature_pack_loader,
                )
            except Exception:
                await session.rollback()
                raise

    return factory


def get_orchestrator(
    customer_repo: CustomerRepo = Depends(get_customer_repo),
    simulation_repo: SimulationRepo = Depends(get_simulation_repo),
    agent_repo: AgentInstanceRepo = Depends(get_agent_repo),
    persona_loader: PersonaPackLoader = Depends(get_persona_loader),
    feature_pack_loader: FeaturePackLoader = Depends(get_feature_pack_loader),
    background_orchestrator_factory: BackgroundOrchestratorFactory | None = Depends(
        get_background_orchestrator_factory
    ),
) -> SimulationOrchestrator:
    return SimulationOrchestrator(
        customer_repo=customer_repo,
        simulation_repo=simulation_repo,
        agent_repo=agent_repo,
        persona_loader=persona_loader,
        feature_pack_loader=feature_pack_loader,
        background_orchestrator_factory=background_orchestrator_factory,
    )
