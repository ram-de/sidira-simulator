"""Persona-group chat route (#54 + collective mode).

`POST /simulations/{sim_id}/personas/{persona_id}/messages` accepts a `mode`
field (`"collective"` default, `"individual"` for fan-out).

**Collective mode (default):** single LLM call answers in the voice of the
persona group; cites individual agents via `[label]` tokens which the route
resolves to canonical agent_ids so the frontend can render drill-down links.
Does NOT touch individual agent conversation logs — the collective voice is
a meta layer over the agents' frozen identities + initial reactions.

**Individual mode:** original #54 fan-out — one PM message goes to every
agent via `AgentChatService.send_message`, each replies in their own voice,
a one-line counted synthesis runs against the survivors. Each fan-out reply
lands in the agent's individual conversation log.

Identity-continuity invariant (fan-out): every fan-out reply goes through
the same `AgentChatService.send_message` path the individual chat surface
uses. Drilling from a fan-out reply into `/agents/[id]` shows the exact
PM/agent turn pair already in that agent's conversation log. Re-instantiation
is forbidden — see `memory/agent_memory.py` IDENTITY-CONTINUITY GUARANTEE.

Failure handling — both modes: services downstream of any per-agent work
NEVER raise into the route. LLM exceptions degrade to deterministic
fallbacks; log appends degrade silently. This prevents the codex #80 class
of bug where a 500 after fan-out invites a client retry that duplicates
upstream per-agent state.
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
from pythia_simulator.memory.persona_group_log import PersonaGroupLog
from pythia_simulator.schemas.agent import AgentInstanceMetadata
from pythia_simulator.schemas.persona_group import (
    AgentReference,
    PerAgentReply,
    PersonaGroupChatRequest,
    PersonaGroupChatResponse,
    PersonaGroupRole,
    PersonaGroupTurn,
)
from pythia_simulator.services.agent_chat import AgentChatService
from pythia_simulator.services.persona_group_collective import (
    CollectiveAgentContext,
    PersonaGroupCollectiveService,
    build_identity_seed_summary,
)
from pythia_simulator.services.persona_group_synthesis import (
    AgentReply,
    PersonaGroupSynthesisService,
)

log = structlog.get_logger()
router = APIRouter(prefix="/simulations", tags=["persona-groups"])

# Match SimulationRunner's per-sim concurrency cap (services/simulation_runner.py:75).
# A persona group with N=8-10 agents (Phase 2.5 weighted_population) would
# otherwise burst Groq with every call at once and trip rate-limits faster
# than the per-call exponential backoff in adapters/llm.py can absorb.
# Codex #80 round-3 [P2].
_FANOUT_MAX_CONCURRENCY = 5


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
    """Send one PM message to the persona group. `mode` selects collective
    voice (default) or individual fan-out. See docs/agent-chat-ui-spec.md
    Surface 2."""
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

    # Deterministic ordering so labels are stable across calls and across
    # collective/individual modes within the same persona group.
    persona_rows.sort(key=lambda r: (r["created_at"], r["id"]))
    metadatas = [_metadata_from_row(r) for r in persona_rows]
    labels = _build_labels(persona_id, len(metadatas))

    if payload.mode == "collective":
        return await _handle_collective(
            customer_id=customer_id,
            sim_id=sim_id,
            persona_id=persona_id,
            message=message,
            metadatas=metadatas,
            labels=labels,
        )
    return await _handle_individual_fanout(
        customer_id=customer_id,
        sim_id=sim_id,
        persona_id=persona_id,
        message=message,
        metadatas=metadatas,
        labels=labels,
    )


# ──────────────────────────────────────────────────────────────────────
# Collective mode
# ──────────────────────────────────────────────────────────────────────


async def _handle_collective(
    *,
    customer_id: str,
    sim_id: str,
    persona_id: str,
    message: str,
    metadatas: list[AgentInstanceMetadata],
    labels: list[str],
) -> PersonaGroupChatResponse:
    """One LLM call answering in the voice of the persona group.

    Loads each agent's frozen identity_seed + initial_reaction (via
    AgentMemory) to give the collective LLM enough signal to speak honestly
    AS the group. Does NOT call AgentChatService.send_message — collective
    mode does not touch individual agent conversation logs.
    """
    store = get_store()
    memory = AgentMemory(store, store)
    group_log = PersonaGroupLog(store)

    # Load every agent's frozen state concurrently. Each load is a sync
    # R2/local-store read; wrap to keep the event loop responsive. Same
    # concurrency cap as fan-out — large groups shouldn't burst the store.
    load_sem = asyncio.Semaphore(_FANOUT_MAX_CONCURRENCY)

    async def _load_one(meta: AgentInstanceMetadata, label: str):
        async with load_sem:
            try:
                agent = await asyncio.to_thread(memory.load, meta)
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "collective.agent_load_failed",
                    agent_id=meta.id,
                    persona_id=persona_id,
                    simulation_id=sim_id,
                    exc_type=type(exc).__name__,
                    error=str(exc),
                )
                return None
            seed = agent.identity_seed
            return CollectiveAgentContext(
                agent_id=meta.id,
                agent_label=label,
                persona_name=meta.persona_name,
                identity_seed_summary=build_identity_seed_summary(
                    age_band=seed.age_band if seed else None,
                    locale_band=seed.locale_band if seed else None,
                    tenure_band=seed.tenure_band if seed else None,
                    current_state=seed.current_state if seed else None,
                    recent_gripe=seed.recent_gripe if seed else None,
                ),
                initial_reaction=agent.initial_reaction,
            )

    contexts_with_none = await asyncio.gather(
        *[_load_one(m, lbl) for m, lbl in zip(metadatas, labels, strict=True)]
    )
    contexts: list[CollectiveAgentContext] = [c for c in contexts_with_none if c is not None]

    if not contexts:
        # Every load failed — same shape as fan-out's all-failed branch.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Could not load any agent identities for this persona group. "
                "Try again, or switch to individual fan-out."
            ),
        )

    # Read prior collective conversation so multi-turn collective chats stay
    # coherent. Skip `synthesis` turns (they belong to the fan-out audit
    # trail; including them would confuse the collective voice with prose
    # framed differently).
    try:
        prior_turns = await asyncio.to_thread(
            group_log.read,
            customer_id=customer_id,
            simulation_id=sim_id,
            persona_id=persona_id,
        )
    except Exception as exc:  # noqa: BLE001 — read failure is recoverable
        log.warning(
            "collective.prior_log_read_failed",
            simulation_id=sim_id,
            persona_id=persona_id,
            exc_type=type(exc).__name__,
            error=str(exc),
        )
        prior_turns = []

    prior_conversation: list[tuple[str, str]] = [
        (t.role.value, t.content)
        for t in prior_turns
        if t.role in (PersonaGroupRole.PM, PersonaGroupRole.COLLECTIVE)
    ]

    persona_name = metadatas[0].persona_name
    collective_service = PersonaGroupCollectiveService()
    content, references = await asyncio.to_thread(
        collective_service.collective_reply,
        persona_name=persona_name,
        pm_question=message,
        agents=contexts,
        prior_conversation=prior_conversation,
    )

    now = datetime.now(timezone.utc)
    pm_turn = PersonaGroupTurn(
        role=PersonaGroupRole.PM,
        content=message,
        created_at=now,
    )
    collective_turn = PersonaGroupTurn(
        role=PersonaGroupRole.COLLECTIVE,
        content=content,
        created_at=now,
        references=references,
    )
    await _append_group_log_best_effort(
        group_log=group_log,
        customer_id=customer_id,
        sim_id=sim_id,
        persona_id=persona_id,
        turns=(pm_turn, collective_turn),
    )

    return PersonaGroupChatResponse(
        role=PersonaGroupRole.COLLECTIVE,
        created_at=now,
        content=content,
        references=references,
    )


# ──────────────────────────────────────────────────────────────────────
# Individual fan-out mode (preserved from #54)
# ──────────────────────────────────────────────────────────────────────


async def _handle_individual_fanout(
    *,
    customer_id: str,
    sim_id: str,
    persona_id: str,
    message: str,
    metadatas: list[AgentInstanceMetadata],
    labels: list[str],
) -> PersonaGroupChatResponse:
    """Original #54 fan-out + synthesis path. Behaviour unchanged."""
    chat_service = AgentChatService()
    semaphore = asyncio.Semaphore(_FANOUT_MAX_CONCURRENCY)

    async def _one_agent(meta: AgentInstanceMetadata) -> tuple[str, Exception | None]:
        async with semaphore:
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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "All agent replies failed in fan-out; see per-agent errors. "
                "Retry the message — agents that already received the PM "
                "turn will not duplicate."
            ),
        )

    synthesis_service = PersonaGroupSynthesisService()
    synthesis_text = await asyncio.to_thread(
        synthesis_service.synthesize, message, successful_replies
    )

    now = datetime.now(timezone.utc)
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
    await _append_group_log_best_effort(
        group_log=group_log,
        customer_id=customer_id,
        sim_id=sim_id,
        persona_id=persona_id,
        turns=(pm_turn, synth_turn),
    )

    return PersonaGroupChatResponse(
        role=PersonaGroupRole.SYNTHESIS,
        created_at=now,
        synthesis=synthesis_text,
        per_agent=per_agent,
    )


# ──────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────


async def _append_group_log_best_effort(
    *,
    group_log: PersonaGroupLog,
    customer_id: str,
    sim_id: str,
    persona_id: str,
    turns: tuple[PersonaGroupTurn, ...],
) -> None:
    """Append every turn to the group log, swallowing per-turn failures.

    Codex #80 [P2] lesson: audit-trail writes are downstream of any
    irreversible work; a 500 here invites a client retry that may duplicate
    upstream state. Appends are sequential — the JSONL log expects ordered
    lines, so we do NOT parallelize even though concurrent writes would
    technically work.
    """
    for turn in turns:
        try:
            await asyncio.to_thread(
                group_log.append,
                customer_id=customer_id,
                simulation_id=sim_id,
                persona_id=persona_id,
                turn=turn,
            )
        except Exception as exc:  # noqa: BLE001 — audit trail is best-effort
            log.warning(
                "persona_group.log_append_failed",
                simulation_id=sim_id,
                persona_id=persona_id,
                turn_role=turn.role.value,
                exc_type=type(exc).__name__,
                error=str(exc),
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
