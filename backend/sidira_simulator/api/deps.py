"""FastAPI dependencies — customer scope + orchestrator wiring.

Resolves customer_id from the Clerk session (populated on ``request.state`` by
the auth gate in ``main.py``) and uses in-memory repos when Postgres is not
configured. The Clerk/JWT path takes precedence; the SIDIRA_CUSTOMER_ID env
(default "demo") remains the dev-time / unauthenticated fallback.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated, AsyncIterator

if TYPE_CHECKING:
    from sidira_simulator.adapters.github_actions import GitHubCrawlDispatcher

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from sidira_simulator.api import auth

from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.postgres import (
    database_configured,
    get_sessionmaker,
)
from sidira_simulator.adapters.r2 import ArtifactStore, get_store
from sidira_simulator.adapters.repositories import (
    AgentFeedbackRepo,
    AgentInstanceRepo,
    ArchivedFeaturePackRepo,
    ConversationRepo,
    CrawlConfigRepo,
    CrawlRunRepo,
    CustomerRepo,
    ExperimentConnectionRepo,
    ExperimentImportRunRepo,
    FeatureStoreConnectionRepo,
    PersonaBuildRepo,
    PostgresAgentFeedbackRepo,
    PostgresAgentInstanceRepo,
    PostgresArchivedFeaturePackRepo,
    PostgresConversationRepo,
    PostgresCrawlConfigRepo,
    PostgresCrawlRunRepo,
    PostgresCustomerRepo,
    PostgresExperimentConnectionRepo,
    PostgresExperimentImportRunRepo,
    PostgresFeatureStoreConnectionRepo,
    PostgresPersonaBuildRepo,
    PostgresSimulationRepo,
    SimulationRepo,
    get_in_memory_archived_feature_pack_repo,
    get_in_memory_conversation_repo,
    get_in_memory_crawl_config_repo,
    get_in_memory_crawl_run_repo,
    get_in_memory_experiment_connection_repo,
    get_in_memory_experiment_import_run_repo,
    get_in_memory_feature_store_connection_repo,
    get_in_memory_persona_build_repo,
    get_in_memory_repos,
)
from sidira_simulator.services.runtime_config import resolve_sidira_env
from sidira_simulator.services.simulation_orchestrator import (
    BackgroundOrchestratorFactory,
    SimulationOrchestrator,
)

DEFAULT_CUSTOMER_ID = "demo"
# Dev / test fallback user (the Clerk session `sub` in prod). Mirrors the
# DEFAULT_CUSTOMER_ID discipline: the env/fallback path only ever runs when the
# Clerk gate is disabled (local dev, the test suite). In prod the gate sets a
# concrete user_id on request.state and this fallback is never reached.
DEFAULT_USER_ID = "demo-user"


def current_customer_id(request: Request) -> str:
    """Resolve the customer (tenant / Clerk org) for the current request.

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


def current_user_id(request: Request) -> str:
    """Resolve the END USER (Clerk session ``sub``) for the current request.

    Distinct from ``current_customer_id``: the customer is the Clerk ORG (the
    tenant boundary), while this is the individual user inside that org. Used to
    scope conversations PRIVATELY per user (#42) — a user must never see another
    user's threads even within the same tenant.

    Prefers ``request.state.user_id`` set by the Clerk auth gate from the session
    token (the `sub` claim). Falls back to the SIDIRA_USER_ID env var (then
    "demo-user") for local dev and the test suite, mirroring
    ``current_customer_id``'s env/fallback discipline so the no-auth path stays
    deterministic.
    """
    from_session = getattr(request.state, "user_id", None)
    if from_session:
        return str(from_session)
    user_id = resolve_sidira_env("USER_ID", DEFAULT_USER_ID)
    assert user_id is not None
    return user_id


# Dev / test fallback org role (#45). The keyless path (local dev + the suite,
# where the Clerk gate is a pass-through) has no session and therefore no org
# role — so it falls back to "admin", mirroring DEFAULT_CUSTOMER_ID: the env /
# fallback path only ever runs when Clerk is disabled. This is what keeps the
# existing suite and local dev able to exercise the now-admin-gated config routes
# without auth fixtures. SIDIRA_ORG_ROLE lets a local dev simulate a member.
# CRITICAL: this fallback is ONLY consulted when Clerk is NOT configured. When
# Clerk IS configured, the role comes from the validated session and a member is
# denied — we never silently grant admin to a real member session.
DEFAULT_ORG_ROLE = "admin"


def current_org_role(request: Request) -> str | None:
    """Resolve the caller's org role (#45) — the admin/member privilege level.

    Prefers ``request.state.org_role`` set by the Clerk auth gate from the
    session `o.rol` claim. When the Clerk gate is active that value is
    authoritative (including ``None`` for a roleless session — we do NOT fall
    back). Only when Clerk is UNCONFIGURED (local dev / the test suite) does this
    resolve the SIDIRA_ORG_ROLE env var, defaulting to "admin", mirroring
    ``current_customer_id``'s env/fallback discipline so the no-auth path can
    still reach the admin-gated config routes."""
    if auth.clerk_configured():
        # Clerk is authoritative: whatever the gate resolved (role or None).
        return getattr(request.state, "org_role", None)
    # Keyless dev/test path — no session exists. Use the env fallback.
    return resolve_sidira_env("ORG_ROLE", DEFAULT_ORG_ROLE)


def require_admin(request: Request) -> None:
    """FastAPI dependency that gates a route to the admin tier (#45).

    owner/admin → allowed; member (or a roleless session) → 403. Configuration
    and credential-bearing writes (connect a source, save Snowflake creds, edit a
    crawl setup) are admin-only; execution (run a crawl, build personas, run a
    sim, re-import, read results) stays open to members — enforced by simply NOT
    depending on this. Resolves the role via ``current_org_role`` so the
    keyless/local/test path (no Clerk) falls back to admin and the suite stays
    green; with Clerk configured a member session is denied here, never granted
    the dev default."""
    if not auth.is_admin_role(current_org_role(request)):
        raise HTTPException(
            status_code=403,
            detail="admin role required for this action",
        )


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


def get_crawl_config_repo(session: RepositorySession = None) -> CrawlConfigRepo:
    if session is None:
        return get_in_memory_crawl_config_repo()
    return PostgresCrawlConfigRepo(session)


def get_crawl_run_repo(session: RepositorySession = None) -> CrawlRunRepo:
    if session is None:
        return get_in_memory_crawl_run_repo()
    return PostgresCrawlRunRepo(session)


def get_feature_store_connection_repo(
    session: RepositorySession = None,
) -> FeatureStoreConnectionRepo:
    if session is None:
        return get_in_memory_feature_store_connection_repo()
    return PostgresFeatureStoreConnectionRepo(session)


def get_experiment_connection_repo(
    session: RepositorySession = None,
) -> ExperimentConnectionRepo:
    if session is None:
        return get_in_memory_experiment_connection_repo()
    return PostgresExperimentConnectionRepo(session)


def get_experiment_import_run_repo(
    session: RepositorySession = None,
) -> ExperimentImportRunRepo:
    if session is None:
        return get_in_memory_experiment_import_run_repo()
    return PostgresExperimentImportRunRepo(session)


def get_persona_build_repo(session: RepositorySession = None) -> PersonaBuildRepo:
    if session is None:
        return get_in_memory_persona_build_repo()
    return PostgresPersonaBuildRepo(session)


def get_archived_feature_pack_repo(
    session: RepositorySession = None,
) -> ArchivedFeaturePackRepo:
    if session is None:
        return get_in_memory_archived_feature_pack_repo()
    return PostgresArchivedFeaturePackRepo(session)


def get_conversation_repo(session: RepositorySession = None) -> ConversationRepo:
    if session is None:
        return get_in_memory_conversation_repo()
    return PostgresConversationRepo(session)


async def get_crawl_dispatcher() -> AsyncIterator["GitHubCrawlDispatcher | None"]:
    """Request-scoped GitHub Actions dispatcher (#193). Yields None when the
    dispatch token is absent so the routes decide: POST 503s (crawls are
    un-dispatchable, not broken), while GET keeps serving terminal rows
    straight from the DB — finished crawls outlive a rotated-out token."""
    from sidira_simulator.adapters.github_actions import (
        GitHubCrawlDispatcher,
        dispatch_configured,
    )

    if not dispatch_configured():
        yield None
        return
    dispatcher = GitHubCrawlDispatcher()
    try:
        yield dispatcher
    finally:
        await dispatcher.aclose()


def get_artifact_store() -> ArtifactStore:
    """Raw artifact store, for routes that copy artifacts rather than load
    them through a typed loader (e.g. the sample-workspace clone)."""
    return get_store()


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


def get_input_lint_chat_client():
    """Chat client for the #312 / T3 pre-flight input lint judge.

    A dedicated dependency (rather than letting `assess_input_lint` lazily call
    `get_chat_client()`) so the test suite can override it with a stub — the
    judge MUST never hit a live LLM in the suite. In production it returns None,
    and `assess_input_lint` resolves the real client lazily inside the judge
    (the chat client is process-cheap to construct; resolving it at request time
    keeps this dep free of import-time LLM config requirements). The override is
    what the tests target.
    """
    return None


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
