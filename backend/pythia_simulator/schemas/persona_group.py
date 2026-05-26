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
from typing import Literal

from pydantic import BaseModel, Field


class PersonaGroupRole(str, Enum):
    PM = "pm"
    SYNTHESIS = "synthesis"
    COLLECTIVE = "collective"


# Mode literal used in PersonaGroupChatRequest. "collective" is the default
# (single LLM call speaking for the persona as a group); "individual" preserves
# the original #54 fan-out semantics (one reply per agent + synthesis line).
PersonaGroupMode = Literal["collective", "individual"]


class AgentReference(BaseModel):
    """One agent cited inline by a collective reply.

    The collective LLM emits `[agent_label]` tokens in its prose; the route
    resolves each label to the canonical `agent_id` so the frontend can
    linkify the citation to `/agents/{agent_id}`. Unresolved labels (LLM
    hallucinated a name that doesn't exist in the persona group) are dropped
    rather than producing a broken link.
    """

    agent_id: str
    agent_label: str = Field(
        description=(
            "The exact token the LLM used inline (e.g. 'rivka_001'). The "
            "frontend matches this against `[token]` occurrences in `content`."
        ),
    )


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
    """PM sends one message; routed to collective synthesis or individual fan-out.

    `mode="collective"` (default): single LLM call answering in the voice of
    the persona group; cites individuals via inline `[label]` tokens.
    `mode="individual"`: fans out to every agent and returns N replies + a
    one-line synthesis (the original #54 behaviour).
    """

    message: str
    mode: PersonaGroupMode = "collective"


class UnavailableAgent(BaseModel):
    """An agent that should have participated in a collective reply but
    couldn't be loaded (artifact read failure, transient storage error)."""

    agent_id: str
    agent_label: str
    persona_name: str
    error: str


class PersonaGroupChatResponse(BaseModel):
    """Discriminated response shape.

    `role="collective"` populates `content` + `references`. May also
    populate `unavailable_agents` when one or more agent loads failed
    so the frontend can surface "answer reflects N-1 of N agents" to the PM
    (codex #82 round-1 P2: don't silently shrink the collective).
    `role="synthesis"` populates `synthesis` + `per_agent`.
    The frontend branches on `role`.
    """

    role: PersonaGroupRole
    created_at: datetime
    # Collective-mode fields
    content: str | None = None
    references: list[AgentReference] | None = None
    unavailable_agents: list[UnavailableAgent] | None = None
    # Individual-fanout-mode fields
    synthesis: str | None = None
    per_agent: list[PerAgentReply] | None = None


class PersonaGroupTurn(BaseModel):
    """One row in the persona-group turn log (turns.jsonl).

    Roles:
      - `pm`: the PM's question. `content` only.
      - `synthesis`: individual-fan-out result. `content` is the one-line
        synthesis; `per_agent` carries the full payload.
      - `collective`: collective-mode result. `content` is the collective
        voice's reply with `[label]` tokens inline; `references` carries
        the resolved `[label]` → `agent_id` mapping.
    """

    role: PersonaGroupRole
    content: str
    created_at: datetime
    per_agent: list[PerAgentReply] | None = Field(
        default=None,
        description=(
            "Populated only on synthesis turns (individual fan-out). Mirrors "
            "what the route returned so the audit trail is self-contained."
        ),
    )
    references: list[AgentReference] | None = Field(
        default=None,
        description=(
            "Populated only on collective turns. Resolved [label] → agent_id "
            "citations from the collective reply prose."
        ),
    )
    realistic_flag: bool | None = Field(
        default=None,
        description=(
            "#56: PM calibration thumb. True = 👍, False = 👎, None = "
            "no thumb / cleared. Joined from the feedback log at read "
            "time; the turn JSONL itself stays append-only."
        ),
    )
