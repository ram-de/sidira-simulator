"""AgentInstance + chat schemas.

An AgentInstance is a persona materialized for a specific simulation, with
its own memory (identity prompt + initial reaction + appendable conversation).
After the simulation completes, PMs chat with AgentInstances to interrogate
*why* they reacted the way they did.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from sidira_simulator.schemas.identity import IdentitySeed


class AgentRole(str, Enum):
    AGENT = "agent"
    PM = "pm"
    SYSTEM = "system"


class AgentChatTurn(BaseModel):
    """One turn in a PM ↔ AgentInstance conversation."""

    role: AgentRole
    content: str
    created_at: datetime
    realistic_flag: bool | None = Field(
        default=None,
        description="PM-supplied feedback on the agent's response. Drives Layer-3 calibration.",
    )


class AgentInstanceMetadata(BaseModel):
    """Lightweight metadata stored in Postgres (the heavy stuff lives in R2).

    Phase 4.6 #89: `arm` carries A/B mode tag. None for single-arm sims
    (today's default; backwards-compat with all pre-#89 rows).
    `"treatment"` / `"control"` for A/B sims; pinned at materialization
    time and never changes for the lifetime of the agent (identity
    continuity per memory/agent_memory.py).
    """

    id: str
    customer_id: str
    simulation_id: str
    persona_id: str
    persona_pack_version: str
    persona_name: str
    created_at: datetime
    last_active_at: datetime
    message_count: int = 0
    arm: str | None = None


class AgentInstance(BaseModel):
    """Full AgentInstance — metadata + memory layers (loaded on demand)."""

    metadata: AgentInstanceMetadata
    identity_prompt: str
    initial_reaction: str
    conversation: list[AgentChatTurn] = Field(default_factory=list)
    identity_seed: IdentitySeed | None = None


class AgentChatRequest(BaseModel):
    """PM sends a follow-up question to a specific agent."""

    message: str


class AgentChatResponse(BaseModel):
    """Single-turn response from the agent."""

    turn: AgentChatTurn
