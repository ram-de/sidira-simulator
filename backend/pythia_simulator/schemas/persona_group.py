"""Persona-group chat schemas (#54).

A persona-group chat is a PM ↔ N-agents fan-out: the PM types one question,
the system delivers it to every agent in the persona, collects N replies,
and produces a one-sentence synthesis.

Identity continuity is preserved per-agent — the same `AgentChatService` powers
each individual reply, so drilling from a group answer into the individual
chat (`/agents/[id]`) shows the same PM/agent turn pair already in that
agent's log.

The synthesis itself does NOT live on any individual agent. It lives in a
per-persona-group turn log at
`customers/<id>/simulations/<sim_id>/persona_groups/<pid>/turns.jsonl`.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PersonaGroupRole(str, Enum):
    PM = "pm"
    SYNTHESIS = "synthesis"


class PerAgentReply(BaseModel):
    """One agent's response within a persona-group fan-out.

    `content` is None when `error` is set — the agent's LLM call failed and
    nothing was persisted to that agent's individual conversation log
    (`AgentChatService.send_message`'s LLM-failure contract).
    """

    agent_id: str
    agent_label: str = Field(
        description=(
            "Short, human-readable label used in the synthesis sentence. "
            "Derived from persona_id (+ a/b/c suffix when N>1 per persona)."
        ),
    )
    persona_name: str
    content: str | None = None
    error: str | None = None


class PersonaGroupChatRequest(BaseModel):
    """PM sends one message; the system fans it out to every agent in the persona."""

    message: str


class PersonaGroupChatResponse(BaseModel):
    """Synthesis + per-agent replies returned to the chat UI."""

    synthesis: str
    per_agent: list[PerAgentReply]
    created_at: datetime


class PersonaGroupTurn(BaseModel):
    """One row in the persona-group turn log (turns.jsonl)."""

    role: PersonaGroupRole
    content: str
    created_at: datetime
    per_agent: list[PerAgentReply] | None = Field(
        default=None,
        description=(
            "Populated only on synthesis turns. Mirrors what the route "
            "returned so the audit trail is self-contained."
        ),
    )
