"""Persistent, multi-thread "Ask the archive" conversations (#41).

Turns the single ephemeral /memory thread into a real PERSISTENT, MULTI-THREAD
assistant (Claude / ChatGPT style), scoped to the customer (tenant). Every route
is ``current_customer_id``-scoped — a thread (and its turns) is ONLY ever visible
to its owning tenant, and an unknown / cross-tenant id 404s so existence never
leaks across customers.

Routes (all under ``/conversations``):

- ``POST   /conversations``            — open a new (empty) thread.
- ``GET    /conversations``            — list the tenant's threads, newest first.
- ``GET    /conversations/{id}``       — one thread with its full turn history.
- ``POST   /conversations/{id}/turns`` — ask one turn: generate the fused answer
  via the SAME path as ``POST /experiments/conversation`` (replaying the thread's
  persisted turns as context), then persist Q + A + citations. Auto-titles the
  thread from the first question when still untitled.
- ``PATCH  /conversations/{id}``       — rename the thread.
- ``DELETE /conversations/{id}``       — delete the thread (turns cascade).

The fused-answer logic, tenant scoping, and the PREDICTED/MEASURED firewall are
REUSED verbatim — this router only adds persistence + thread management.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from sidira_simulator.adapters.llm import ChatClient
from sidira_simulator.adapters.repositories import ConversationRepo
from sidira_simulator.api.deps import (
    current_customer_id,
    get_conversation_repo,
    get_customer_repo,
    get_orchestrator,
)
from sidira_simulator.api.experiments import (
    build_fused_conversation_service,
    get_experiment_chat_client,
)
from sidira_simulator.adapters.repositories import CustomerRepo
from sidira_simulator.schemas.experiment_memory import (
    AppendTurnRequest,
    AppendTurnResponse,
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
    ConversationTurn,
    CreateConversationRequest,
    FusedCitation,
    PersistedTurn,
    RenameConversationRequest,
)
from sidira_simulator.services.simulation_orchestrator import SimulationOrchestrator

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _new_id() -> str:
    return uuid.uuid4().hex


def _summary(row: dict) -> ConversationSummary:
    return ConversationSummary(
        id=row["id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _persisted_turn(turn: dict) -> PersistedTurn:
    return PersistedTurn(
        id=turn["id"],
        question=turn["question"],
        answer=turn["answer"],
        citations=[FusedCitation(**c) for c in (turn.get("citations_json") or [])],
        used_llm=turn["used_llm"],
        created_at=turn["created_at"],
    )


@router.post("", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    req: CreateConversationRequest,
    customer_id: str = Depends(current_customer_id),
    repo: ConversationRepo = Depends(get_conversation_repo),
    customer_repo: CustomerRepo = Depends(get_customer_repo),
) -> ConversationSummary:
    """Open a new (empty) thread for the customer. Title is optional — it
    auto-derives from the first appended turn when left unset."""
    # Ensure the tenant row exists (the conversations FK references customers),
    # mirroring how the orchestrator backfills a customer on first write.
    await customer_repo.ensure_exists(customer_id)
    row = await repo.create(
        conversation_id=_new_id(),
        customer_id=customer_id,
        title=req.title,
    )
    return _summary(row)


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    customer_id: str = Depends(current_customer_id),
    repo: ConversationRepo = Depends(get_conversation_repo),
) -> ConversationListResponse:
    """The customer's threads, newest-touched first (the switcher list)."""
    rows = await repo.list_for_customer(customer_id)
    return ConversationListResponse(conversations=[_summary(r) for r in rows])


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    customer_id: str = Depends(current_customer_id),
    repo: ConversationRepo = Depends(get_conversation_repo),
) -> ConversationDetail:
    """One thread with its full ordered turn history. 404 when the id is unknown
    OR belongs to another tenant (existence never leaks)."""
    row = await repo.get_with_turns(conversation_id, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetail(
        id=row["id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        turns=[_persisted_turn(t) for t in row["turns"]],
    )


@router.patch("/{conversation_id}", response_model=ConversationSummary)
async def rename_conversation(
    conversation_id: str,
    req: RenameConversationRequest,
    customer_id: str = Depends(current_customer_id),
    repo: ConversationRepo = Depends(get_conversation_repo),
) -> ConversationSummary:
    """Rename a thread (PATCH title). 404 when unknown / cross-tenant."""
    row = await repo.rename(conversation_id, customer_id, req.title.strip())
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _summary(row)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    customer_id: str = Depends(current_customer_id),
    repo: ConversationRepo = Depends(get_conversation_repo),
) -> None:
    """Delete a thread (its turns cascade). 404 when unknown / cross-tenant."""
    ok = await repo.delete(conversation_id, customer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.post("/{conversation_id}/turns", response_model=AppendTurnResponse)
async def append_turn(
    conversation_id: str,
    req: AppendTurnRequest,
    customer_id: str = Depends(current_customer_id),
    repo: ConversationRepo = Depends(get_conversation_repo),
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
    chat_client: ChatClient | None = Depends(get_experiment_chat_client),
) -> AppendTurnResponse:
    """Ask one turn IN a persistent thread (#41).

    Replays the thread's PERSISTED turns as conversation context (so a follow-up
    resolves against what was discussed even after a reload), generates the fused
    answer through the SAME tenant-scoped path as ``POST
    /experiments/conversation``, then persists Q + A + citations to the thread and
    auto-titles it from the first question when still untitled. 404 when the
    thread is unknown / cross-tenant — never generates for a thread the caller
    doesn't own."""
    existing = await repo.get_with_turns(conversation_id, customer_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Replay persisted turns as context — same shape the live /conversation path
    # carries in its request body, so the answer is identical to the ephemeral one.
    history = [
        ConversationTurn(question=t["question"], answer=t["answer"])
        for t in existing["turns"]
    ]

    service = await build_fused_conversation_service(
        orchestrator, customer_id, chat_client
    )
    answer = service.answer(req.message, history, req.top_k)

    updated = await repo.append_turn(
        turn_id=_new_id(),
        conversation_id=conversation_id,
        customer_id=customer_id,
        question=req.message,
        answer=answer.answer,
        citations=[c.model_dump() for c in answer.citations],
        used_llm=answer.used_llm,
    )
    if updated is None:
        # The thread was deleted between the existence check and the append (a
        # concurrent delete). Treat as not-found rather than 500.
        raise HTTPException(status_code=404, detail="Conversation not found")

    new_turn = updated["turns"][-1]
    return AppendTurnResponse(
        turn=_persisted_turn(new_turn),
        follow_ups=answer.follow_ups,
        grounded=answer.grounded,
        conversation=_summary(updated),
    )
