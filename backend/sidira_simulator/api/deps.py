"""FastAPI dependencies — customer scope + orchestrator wiring.

MVP: resolves customer_id from SIDIRA_CUSTOMER_ID env (default "demo") and uses
in-memory repos. Phase 5 will swap the resolver to read from a Clerk session
JWT; the JWT path will take precedence over the env, and the env will continue
to act as the dev-time default.
"""

from __future__ import annotations

import os

from fastapi import Depends

from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.repositories import (
    AgentFeedbackRepo,
    AgentInstanceRepo,
    CustomerRepo,
    SimulationRepo,
    get_in_memory_repos,
)
from sidira_simulator.services.runtime_config import resolve_sidira_env
from sidira_simulator.services.simulation_orchestrator import SimulationOrchestrator

DEFAULT_CUSTOMER_ID = "demo"


def current_customer_id() -> str:
    """Resolve the customer for the current request.

    MVP: read from SIDIRA_CUSTOMER_ID env var, fall back through legacy
    PYTHIA_CUSTOMER_ID, then to "demo". Phase 5 will layer a Clerk JWT resolver
    on top.
    """
    customer_id = resolve_sidira_env("CUSTOMER_ID", DEFAULT_CUSTOMER_ID)
    assert customer_id is not None
    return customer_id


def _repos() -> tuple[CustomerRepo, SimulationRepo, AgentInstanceRepo, AgentFeedbackRepo]:
    if os.environ.get("DATABASE_URL"):
        # Phase 2 wiring: real Postgres-backed repos. Deferred.
        raise NotImplementedError(
            "DATABASE_URL is set but Postgres repo wiring requires an async session "
            "dependency. For now, unset DATABASE_URL to use in-memory repos."
        )
    return get_in_memory_repos()


def get_customer_repo() -> CustomerRepo:
    return _repos()[0]


def get_simulation_repo() -> SimulationRepo:
    return _repos()[1]


def get_agent_repo() -> AgentInstanceRepo:
    return _repos()[2]


def get_feedback_repo() -> AgentFeedbackRepo:
    return _repos()[3]


def get_persona_loader() -> PersonaPackLoader:
    return PersonaPackLoader()


def get_feature_pack_loader() -> FeaturePackLoader:
    return FeaturePackLoader()


def get_orchestrator(
    customer_repo: CustomerRepo = Depends(get_customer_repo),
    simulation_repo: SimulationRepo = Depends(get_simulation_repo),
    agent_repo: AgentInstanceRepo = Depends(get_agent_repo),
    persona_loader: PersonaPackLoader = Depends(get_persona_loader),
    feature_pack_loader: FeaturePackLoader = Depends(get_feature_pack_loader),
) -> SimulationOrchestrator:
    return SimulationOrchestrator(
        customer_repo=customer_repo,
        simulation_repo=simulation_repo,
        agent_repo=agent_repo,
        persona_loader=persona_loader,
        feature_pack_loader=feature_pack_loader,
    )
