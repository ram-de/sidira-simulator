"""Pydantic schemas — single source of truth.

Frontend TypeScript types are generated from FastAPI's OpenAPI export via
`openapi-typescript` so there's no drift between Python and TS shapes.

These schemas will move to a separate `pythia-schemas` package once a second
consumer (beyond backend + frontend codegen) needs them.
"""

from pythia_simulator.schemas.agent import (
    AgentChatTurn,
    AgentInstance,
    AgentInstanceMetadata,
)
from pythia_simulator.schemas.feature_pack import (
    Capability,
    FeaturePackManifest,
    ReverseFigma,
)
from pythia_simulator.schemas.persona import Persona, PersonaPack
from pythia_simulator.schemas.simulation import (
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
    "Capability",
    "FeaturePackManifest",
    "Hypothesis",
    "Persona",
    "PersonaPack",
    "ReverseFigma",
    "Simulation",
    "SimulationRequest",
    "SimulationResult",
    "Weakness",
]
