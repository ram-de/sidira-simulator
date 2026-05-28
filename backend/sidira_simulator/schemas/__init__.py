"""Pydantic schemas — single source of truth.

Frontend TypeScript types are generated from FastAPI's OpenAPI export via
`openapi-typescript` so there's no drift between Python and TS shapes.

These schemas will move to a separate `pythia-schemas` package once a second
consumer (beyond backend + frontend codegen) needs them.
"""

from sidira_simulator.schemas.agent import (
    AgentChatTurn,
    AgentInstance,
    AgentInstanceMetadata,
)
from sidira_simulator.schemas.feature_pack import (
    Capability,
    FeaturePackManifest,
    ReverseFigma,
)
from sidira_simulator.schemas.identity import IdentitySeed
from sidira_simulator.schemas.persona import BehavioralSeedSchema, Persona, PersonaPack
from sidira_simulator.schemas.simulation import (
    Hypothesis,
    Simulation,
    SimulationRequest,
    SimulationResult,
    Weakness,
)

__all__ = [
    "AgentChatTurn",
    "AgentInstance",
    "AgentInstanceMetadata",
    "BehavioralSeedSchema",
    "Capability",
    "FeaturePackManifest",
    "Hypothesis",
    "IdentitySeed",
    "Persona",
    "PersonaPack",
    "ReverseFigma",
    "Simulation",
    "SimulationRequest",
    "SimulationResult",
    "Weakness",
]
