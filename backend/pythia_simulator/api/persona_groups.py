"""Persona-group chat route (#54).

`POST /simulations/{sim_id}/personas/{persona_id}/messages` fans out one PM
message to every agent that participated in `sim_id` with persona `persona_id`,
collects the per-agent replies, computes a one-sentence synthesis from those
replies (via `PersonaGroupSynthesisService`), and persists both the PM turn
and the synthesis to a per-persona-group log.

Identity-continuity invariant: every fan-out reply goes through the same
`AgentChatService.send_message` path the individual chat surface uses. So
drilling from a group answer into `/agents/[id]` shows the exact PM/agent
turn pair already in that agent's conversation log. Re-instantiation is
forbidden — see `memory/agent_memory.py` IDENTITY-CONTINUITY GUARANTEE.

Failure handling: best-effort fan-out. If one agent's LLM call fails, its
slot in the response carries `error` (and `content` is None); the synthesis
is still computed against the agents that DID reply. The PM sees which
agents failed and can decide what to do. Per-agent retry is not yet
supported — that's #56 territory (idempotency keys per message).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from pythia_simulator.adapters.r2 import get_store
from pythia_simulator.adapters.repositories import AgentInstanceRepo, SimulationRepo
from pythia_simulator.api.deps import current_customer_id, get_agent_repo, get_simulation_repo
from pythia_simulator.memory.persona_group_log import PersonaGroupLog
from pythia_simulator.schemas.agent import AgentInstanceMetadata
from pythia_simulator.schemas.persona_group import (
    PerAgentReply,
    PersonaGroupChatRequest,
    PersonaGroupChatResponse,
    PersonaGroupRole,
    PersonaGroupTurn,
)
from pythia_simulator.services.agent_chat import AgentChatService
from pythia_simulator.services.persona_group_synthesis import (
    AgentReply,
    PersonaGroupSynthesisService,
)

log = structlog.get_logger()
router = APIRouter(prefix="/simulations", tags=["persona-groups"])


def _metadata_from_row(row: dict) -> AgentInstanceMetadata:
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
    )


def _build_labels(persona_id: str, n: int) -> list[str]:
    """Short, human-readable labels for the synthesis prompt.

    N=1: `[persona_id]`.
    N>1: `[persona_id_a]`, `[persona_id_b]`, ... — gives the synthesis LLM
    something stable to point at when one outlier diverges from the rest.
    """
    if n == 1:
        return [persona_id]
    return [f"{persona_id}_{chr(ord('a') + i)}" for i in range(n)]


@router.post(
    "/{sim_id}/personas/{persona_id}/messages",
    response_model=PersonaGroupChatResponse,
)
async def send_persona_group_message(
    sim_id: str,
    persona_id: str,
    payload: PersonaGroupChatRequest,
    customer_id: str = Depends(current_customer_id),
    agent_repo: AgentInstanceRepo = Depends(get_agent_repo),
    sim_repo: SimulationRepo = Depends(get_simulation_repo),
) -> PersonaGroupChatResponse:
    """Fan out one PM message to every agent in the persona; return synthesis + per-agent replies."""
    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message body must be non-empty.",
        )

    sim = await sim_repo.get(sim_id, customer_id)
    if sim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation {sim_id} not found",
        )

    rows = await agent_repo.list_for_simulation(sim_id, customer_id)
    persona_rows = [r for r in rows if r["persona_id"] == persona_id]
    if not persona_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No agents found in simulation {sim_id} for persona {persona_id}"
            ),
        )

    # Deterministic ordering so labels (rivka_a, rivka_b, ...) are stable
    # across calls. Sort by created_at, then id as a tiebreaker.
    persona_rows.sort(key=lambda r: (r["created_at"], r["id"]))
    metadatas = [_metadata_from_row(r) for r in persona_rows]
    labels = _build_labels(persona_id, len(metadatas))

    # Fan-out: run each agent's send_message concurrently. The service is
    # sync (network LLM call) so each call gets its own thread. A per-agent
    # failure is captured into PerAgentReply.error and DOES NOT cancel the
    # rest of the fan-out.
    chat_service = AgentChatService()

    async def _one_agent(meta: AgentInstanceMetadata) -> tuple[str, Exception | None]:
        try:
            turn = await asyncio.to_thread(chat_service.send_message, meta, message)
            return turn.content, None
        except Exception as exc:  # noqa: BLE001 — surfaced into per_agent.error
            log.warning(
                "persona_group.fanout_failed",
                agent_id=meta.id,
                persona_id=persona_id,
                simulation_id=sim_id,
                exc_type=type(exc).__name__,
                error=str(exc),
            )
            return "", exc

    fan_results = await asyncio.gather(*[_one_agent(m) for m in metadatas])

    per_agent: list[PerAgentReply] = []
    successful_replies: list[AgentReply] = []
    for meta, label, (content, exc) in zip(metadatas, labels, fan_results, strict=True):
        if exc is None:
            per_agent.append(
                PerAgentReply(
                    agent_id=meta.id,
                    agent_label=label,
                    persona_name=meta.persona_name,
                    content=content,
                )
            )
            successful_replies.append(AgentReply(agent_label=label, content=content))
        else:
            per_agent.append(
                PerAgentReply(
                    agent_id=meta.id,
                    agent_label=label,
                    persona_name=meta.persona_name,
                    content=None,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    if not successful_replies:
        # Every fan-out failed. Don't run synthesis on zero replies — return
        # a 502 so the client can surface "all agents failed" instead of
        # rendering a synthesis line about zero replies.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "All agent replies failed in fan-out; see per-agent errors. "
                "Retry the message — agents that already received the PM "
                "turn will not duplicate."
            ),
        )

    # Synthesis runs against the agents that actually replied. This is
    # honest about count ("3 of 3 said X" when 2 of 5 failed and 3 succeeded).
    synthesis_service = PersonaGroupSynthesisService()
    synthesis_text = await asyncio.to_thread(
        synthesis_service.synthesize, message, successful_replies
    )

    now = datetime.now(timezone.utc)

    # Persist BOTH the PM turn and the synthesis to the per-persona-group
    # log. Synthesis carries the full per_agent payload so the audit trail
    # is self-contained — replaying the log doesn't require re-fanning out.
    group_log = PersonaGroupLog(get_store())
    pm_turn = PersonaGroupTurn(
        role=PersonaGroupRole.PM,
        content=message,
        created_at=now,
    )
    synth_turn = PersonaGroupTurn(
        role=PersonaGroupRole.SYNTHESIS,
        content=synthesis_text,
        created_at=now,
        per_agent=per_agent,
    )
    # Persona-group log writes are best-effort by the same logic as the
    # synthesis fallback above (codex #80 [P2]): the per-agent fan-out has
    # already persisted the source-of-truth PM/agent pairs to individual
    # logs. If the group-log append fails (R2 hiccup, transient storage
    # error), 500ing would invite a client retry that re-fans-out the same
    # PM message to every agent, duplicating their individual conversations.
    # The audit trail is downstream of the data we care about — degrade it
    # rather than corrupt the per-agent logs.
    for turn in (pm_turn, synth_turn):
        try:
            await asyncio.to_thread(
                group_log.append,
                customer_id=customer_id,
                simulation_id=sim_id,
                persona_id=persona_id,
                turn=turn,
            )
        except Exception as exc:  # noqa: BLE001 - audit trail is best-effort
            log.warning(
                "persona_group.log_append_failed",
                simulation_id=sim_id,
                persona_id=persona_id,
                turn_role=turn.role.value,
                exc_type=type(exc).__name__,
                error=str(exc),
            )

    return PersonaGroupChatResponse(
        synthesis=synthesis_text,
        per_agent=per_agent,
        created_at=now,
    )


@router.get(
    "/{sim_id}/personas/{persona_id}/turns",
    response_model=list[PersonaGroupTurn],
)
async def list_persona_group_turns(
    sim_id: str,
    persona_id: str,
    customer_id: str = Depends(current_customer_id),
    sim_repo: SimulationRepo = Depends(get_simulation_repo),
    agent_repo: AgentInstanceRepo = Depends(get_agent_repo),
) -> list[PersonaGroupTurn]:
    """Replay the persona-group conversation log.

    Used by the frontend `/simulations/[id]/personas/[persona_id]` route to
    render prior turns on page load.
    """
    sim = await sim_repo.get(sim_id, customer_id)
    if sim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation {sim_id} not found",
        )
    # Confirm the persona exists in this sim before returning (avoids
    # leaking "empty log" as a positive answer for a typo'd persona_id).
    rows = await agent_repo.list_for_simulation(sim_id, customer_id)
    if not any(r["persona_id"] == persona_id for r in rows):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No agents found in simulation {sim_id} for persona {persona_id}"
            ),
        )

    group_log = PersonaGroupLog(get_store())
    return await asyncio.to_thread(
        group_log.read,
        customer_id=customer_id,
        simulation_id=sim_id,
        persona_id=persona_id,
    )
