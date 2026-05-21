"""Agent routes — list agents from a simulation, view one, chat with one."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from pythia_simulator.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentInstance,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/{agent_id}", response_model=AgentInstance)
async def get_agent(agent_id: str) -> AgentInstance:
    """Load an agent's full state: identity, initial reaction, conversation history.

    The same agent that participated in the simulation — identity is frozen,
    conversation grows.
    """
    raise HTTPException(status_code=501, detail="get_agent — implement once Postgres layer lands")


@router.post("/{agent_id}/messages", response_model=AgentChatResponse)
async def send_message(agent_id: str, payload: AgentChatRequest) -> AgentChatResponse:
    """Send a follow-up message to a specific agent."""
    raise HTTPException(
        status_code=501, detail="send_message — wires AgentChatService once Postgres lookup is in"
    )
