"""Agent routes — view one agent's full state, send a follow-up message.

The PM chats with the same AgentInstance that participated in the simulation.
Identity is frozen (persona prompt + initial reaction are immutable). The
conversation log is append-only — every PM message and every agent reply
gets persisted via `AgentMemory.append_turn` before the next turn renders.

The two routes here un-stub what was previously 501 placeholders pending
Phase 4. They consume the `AgentChatService` + `AgentMemory` infrastructure
that's been in place since the Magic Moment sprint.
"""

from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from pythia_simulator.adapters.repositories import AgentInstanceRepo, SimulationRepo
from pythia_simulator.api.deps import (
    current_customer_id,
    get_agent_repo,
    get_simulation_repo,
)
from pythia_simulator.memory.agent_memory import AgentMemory
from pythia_simulator.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentInstance,
    AgentInstanceMetadata,
)
from pythia_simulator.services.agent_chat import AgentChatService

log = structlog.get_logger()
router = APIRouter(prefix="/agents", tags=["agents"])


def _metadata_from_row(row: dict) -> AgentInstanceMetadata:
    """Build AgentInstanceMetadata from a repo dict, ignoring any extras
    the repo decides to surface (e.g. denormalized timestamps from joins)."""
    return AgentInstanceMetadata(
        id=row["id"],
        customer_id=row["customer_id"],
        simulation_id=row["simulation_id"],
        persona_id=row["persona_id"],
        persona_pack_version=row["persona_pack_version"],
        persona_name=row["persona_name"],
        created_at=row["created_at"],
        last_active_at=row["last_active_at"],
        message_count=row.get("message_count", 0) or 0,
        arm=row.get("arm"),
    )


@router.get("/{agent_id}", response_model=AgentInstance)
async def get_agent(
    agent_id: str,
    customer_id: str = Depends(current_customer_id),
    agent_repo: AgentInstanceRepo = Depends(get_agent_repo),
) -> AgentInstance:
    """Load an agent's full state: identity, initial reaction, conversation history.

    Identity is frozen at simulation time — calling this twice with no
    intervening chat returns identical `identity_prompt` and `initial_reaction`.
    Only the `conversation` array grows.
    """
    row = await agent_repo.get(agent_id, customer_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )
    metadata = _metadata_from_row(row)
    # AgentMemory.load is sync (reads from R2 / local store). Wrap to keep
    # the event loop responsive on slow object-store reads.
    from pythia_simulator.adapters.r2 import get_store
    from pythia_simulator.memory.feedback_log import FeedbackLog
    from pythia_simulator.schemas.feedback import FeedbackTargetKind

    store = get_store()
    memory = AgentMemory(store, store)
    agent = await asyncio.to_thread(memory.load, metadata)

    # #56: join calibration feedback onto the conversation turns. The
    # canonical turn log is append-only, so feedback lives in a separate
    # JSONL and we paint the `realistic_flag` onto each turn at read time.
    # Latest event per turn_index wins; cleared thumbs (None) overwrite
    # prior 👍/👎 so the UI sees the actual state.
    flags = await asyncio.to_thread(
        FeedbackLog(store).latest_flags,
        customer_id=customer_id,
        simulation_id=metadata.simulation_id,
        target_kind=FeedbackTargetKind.AGENT,
        target_id=agent_id,
    )
    if flags and agent.conversation:
        for idx, turn in enumerate(agent.conversation):
            if idx in flags:
                turn.realistic_flag = flags[idx]
    return agent


@router.post("/{agent_id}/messages", response_model=AgentChatResponse)
async def send_message(
    agent_id: str,
    payload: AgentChatRequest,
    customer_id: str = Depends(current_customer_id),
    agent_repo: AgentInstanceRepo = Depends(get_agent_repo),
    sim_repo: SimulationRepo = Depends(get_simulation_repo),
) -> AgentChatResponse:
    """Send a follow-up message to a specific agent.

    The PM's message is appended to the agent's conversation log before the
    LLM call so the new turn persists even if the LLM call fails. The
    agent's reply is then generated from the frozen identity + frozen
    initial reaction + the full conversation log (including the new PM
    message), with `_CHAT_GUARD_PREFIX` keeping the model in character.

    Returns the single new agent turn. The PM turn is already persisted on
    the server; clients render it optimistically from the request payload.
    """
    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message body must be non-empty.",
        )

    row = await agent_repo.get(agent_id, customer_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )
    metadata = _metadata_from_row(row)
    sim = await sim_repo.get(metadata.simulation_id, customer_id)
    model_id = sim.get("model_id") if sim is not None else None

    # AgentChatService.send_message is sync (network LLM call). Wrap to keep
    # the FastAPI worker available for other requests during the round-trip.
    try:
        service = AgentChatService(model_id=model_id)
        agent_turn = await asyncio.to_thread(service.send_message, metadata, message)
    except Exception as exc:
        # Surface a structured error rather than a generic 500. The PM-side
        # turn is already persisted; a retry will skip re-appending it
        # (AgentChatService.send_message appends BEFORE the LLM call, so on
        # retry the user will see two PM turns. Out of scope for #52 — the
        # idempotency story lands with a request_id in #56's calibration work).
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agent reply failed: {exc}",
        ) from exc

    # Touch the metadata row so list views can sort by activity. Failure
    # here is non-fatal — the turn is already persisted to R2; the touch is
    # a convenience for UI sorting. Log so a broken metadata layer or DB
    # connectivity issue is visible in observability instead of silent
    # (codex #52 P2).
    try:
        await agent_repo.touch(agent_id, customer_id)
    except Exception as exc:
        log.warning(
            "agents.touch_failed",
            agent_id=agent_id,
            customer_id=customer_id,
            error=str(exc),
            exc_type=type(exc).__name__,
        )

    return AgentChatResponse(turn=agent_turn)
