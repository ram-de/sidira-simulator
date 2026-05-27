"""Calibration feedback routes (#56).

Two surfaces, one storage:
  - `POST /agents/{agent_id}/turns/{turn_index}/feedback` — thumbs on an
    individual agent reply (in /agents/[id] surface).
  - `POST /simulations/{sim_id}/personas/{persona_id}/turns/{turn_index}/feedback`
    — thumbs on a synthesis OR collective reply (in the persona-group
    surface). The role lives on the turn itself; feedback is role-agnostic.

Both write to the same per-simulation `feedback.jsonl` so a sim's full
calibration history is one read away for Phase 9.

Validation contract: routes 404 when the target is unknown (so a typo'd
agent_id or persona_id can't silently grow the log). Out-of-range
turn_index also 404s. Failure to write is a 500 (caller can retry — the
feedback POST is idempotent in spirit: writing the same flag twice is
fine, latest-wins).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from pythia_simulator.adapters.r2 import get_store
from pythia_simulator.adapters.repositories import AgentInstanceRepo, SimulationRepo
from pythia_simulator.api.deps import current_customer_id, get_agent_repo, get_simulation_repo
from pythia_simulator.memory.agent_memory import AgentMemory
from pythia_simulator.memory.feedback_log import FeedbackLog
from pythia_simulator.memory.persona_group_log import PersonaGroupLog
from pythia_simulator.schemas.feedback import (
    FeedbackEvent,
    FeedbackRequest,
    FeedbackResponse,
    FeedbackTargetKind,
)

log = structlog.get_logger()

# Two prefixed routers so the URL hierarchies stay legible.
agent_router = APIRouter(prefix="/agents", tags=["feedback"])
group_router = APIRouter(prefix="/simulations", tags=["feedback"])


# Per-simulation asyncio.Lock to serialize feedback appends. Codex #85
# round-1 P2: R2ArtifactStore.append_line is a read-modify-write, so two
# concurrent feedback POSTs against the same simulation can both read the
# same feedback.jsonl and the later put overwrites the earlier event —
# losing audit history (which Phase 9 wants) AND potentially leaving
# latest_flags() with the wrong final thumb when a PM rapid-fires 👍/👎.
#
# Single-process scope: this lock only protects against in-process races.
# Multi-replica deployments would need an external lock (Redis, a per-sim
# row in a coordinator table) — not needed today. Documented here so a
# future move to multiple uvicorn workers re-opens the question.
_feedback_locks: dict[str, asyncio.Lock] = {}


def _lock_for(simulation_id: str) -> asyncio.Lock:
    lock = _feedback_locks.get(simulation_id)
    if lock is None:
        lock = asyncio.Lock()
        _feedback_locks[simulation_id] = lock
    return lock


@agent_router.post(
    "/{agent_id}/turns/{turn_index}/feedback",
    response_model=FeedbackResponse,
)
async def record_agent_turn_feedback(
    agent_id: str,
    turn_index: int,
    payload: FeedbackRequest,
    customer_id: str = Depends(current_customer_id),
    agent_repo: AgentInstanceRepo = Depends(get_agent_repo),
) -> FeedbackResponse:
    """Record 👍/👎/clear on one turn of an individual agent's conversation."""
    if turn_index < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="turn_index must be non-negative.",
        )

    row = await agent_repo.get(agent_id, customer_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    # Verify the turn exists by loading the agent's conversation. Cheap
    # safety net — without this, a typo'd turn_index would grow the log
    # with feedback that never resolves to anything renderable.
    store = get_store()
    memory = AgentMemory(store, store)
    from pythia_simulator.schemas.agent import AgentInstanceMetadata

    metadata = AgentInstanceMetadata(
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
    agent = await asyncio.to_thread(memory.load, metadata)
    conversation = agent.conversation or []
    if turn_index >= len(conversation):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"turn_index {turn_index} out of range "
                f"(agent has {len(conversation)} turns)"
            ),
        )
    # Codex #85 round-1 P2: same reply-only contract as the persona-group
    # route. PM turns aren't valid feedback targets — no LLM-generated
    # content to calibrate, and a buggy/direct client could otherwise
    # render thumbs on the PM's own messages.
    from pythia_simulator.schemas.agent import AgentRole

    if conversation[turn_index].role == AgentRole.PM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot feedback on a PM turn (only agent replies).",
        )

    now = datetime.now(timezone.utc)
    event = FeedbackEvent(
        target_kind=FeedbackTargetKind.AGENT,
        target_id=agent_id,
        turn_index=turn_index,
        realistic_flag=payload.realistic_flag,
        created_at=now,
    )
    feedback_log = FeedbackLog(store)
    # Codex #85 round-1 P2: serialize per-sim so concurrent thumbs on the
    # same simulation can't race the R2 read-modify-write append.
    async with _lock_for(metadata.simulation_id):
        await asyncio.to_thread(
            feedback_log.append,
            customer_id=customer_id,
            simulation_id=metadata.simulation_id,
            event=event,
        )

    return FeedbackResponse(
        target_kind=event.target_kind,
        target_id=event.target_id,
        turn_index=event.turn_index,
        realistic_flag=event.realistic_flag,
        created_at=now,
    )


@group_router.post(
    "/{sim_id}/personas/{persona_id}/turns/{turn_index}/feedback",
    response_model=FeedbackResponse,
)
async def record_persona_group_turn_feedback(
    sim_id: str,
    persona_id: str,
    turn_index: int,
    payload: FeedbackRequest,
    customer_id: str = Depends(current_customer_id),
    sim_repo: SimulationRepo = Depends(get_simulation_repo),
    agent_repo: AgentInstanceRepo = Depends(get_agent_repo),
) -> FeedbackResponse:
    """Record 👍/👎/clear on one turn of a persona-group conversation.

    Works on both synthesis turns (fan-out mode) and collective turns —
    the role lives on the turn; feedback is role-agnostic. PM turns are
    NOT a valid target (no LLM-generated content to calibrate); the
    route 400s if the targeted turn is a PM turn.
    """
    if turn_index < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="turn_index must be non-negative.",
        )

    sim = await sim_repo.get(sim_id, customer_id)
    if sim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation {sim_id} not found",
        )
    rows = await agent_repo.list_for_simulation(sim_id, customer_id)
    if not any(r["persona_id"] == persona_id for r in rows):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No agents found in simulation {sim_id} for persona {persona_id}"
            ),
        )

    store = get_store()
    group_log = PersonaGroupLog(store)
    turns = await asyncio.to_thread(
        group_log.read,
        customer_id=customer_id,
        simulation_id=sim_id,
        persona_id=persona_id,
    )
    if turn_index >= len(turns):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"turn_index {turn_index} out of range "
                f"(persona group has {len(turns)} turns)"
            ),
        )
    target_turn = turns[turn_index]
    # PM turns aren't meaningful targets — there's no LLM output to
    # calibrate. Reject explicitly so a buggy client UI can't accumulate
    # PM-turn feedback that Phase 9 then has to filter out.
    from pythia_simulator.schemas.persona_group import PersonaGroupRole

    if target_turn.role == PersonaGroupRole.PM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot feedback on a PM turn (only synthesis / collective).",
        )

    now = datetime.now(timezone.utc)
    target_id = f"{sim_id}/{persona_id}"
    event = FeedbackEvent(
        target_kind=FeedbackTargetKind.PERSONA_GROUP,
        target_id=target_id,
        turn_index=turn_index,
        realistic_flag=payload.realistic_flag,
        created_at=now,
    )
    feedback_log = FeedbackLog(store)
    async with _lock_for(sim_id):
        await asyncio.to_thread(
            feedback_log.append,
            customer_id=customer_id,
            simulation_id=sim_id,
            event=event,
        )

    return FeedbackResponse(
        target_kind=event.target_kind,
        target_id=event.target_id,
        turn_index=event.turn_index,
        realistic_flag=event.realistic_flag,
        created_at=now,
    )
