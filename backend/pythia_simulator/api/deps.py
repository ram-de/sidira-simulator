"""FastAPI dependencies — customer scope + orchestrator wiring.

MVP: hardcodes customer_id="demo" and uses in-memory repos. Phase 5 swaps the
customer_id resolver to read from Clerk session JWT and the repo selection to
Postgres-backed when DATABASE_URL is set.
"""

from __future__ import annotations

import os

from fastapi import Depends

from pythia_simulator.adapters.feature_pack_loader import FeaturePackLoader
from pythia_simulator.adapters.persona_loader import PersonaPackLoader
from pythia_simulator.adapters.repositories import (
    AgentFeedbackRepo,
    AgentInstanceRepo,
    CustomerRepo,
    SimulationRepo,
    get_in_memory_repos,
)
from pythia_simulator.services.simulation_orchestrator import SimulationOrchestrator

# MVP — hardcoded until Phase 5 wires Clerk.
DEMO_CUSTOMER_ID = "demo"


def current_customer_id() -> str:
    """Resolve the customer for the current request. MVP: hardcoded."""
    return DEMO_CUSTOMER_ID


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
