"""Experiment-memory routes (#28, #29).

Pure RETRIEVAL over an archive of PAST, already-resolved experiments — no model
prediction. Two endpoints, both NEW (no existing route is touched):

- ``POST /experiments/search-similar`` — pre-gate hypothesis dedup. A new
  hypothesis returns trust-ordered similar past experiments + their real results
  BEFORE any prediction (#29).
- ``POST /experiments/chat`` — RAG chat grounded in the archive (#28).

The archive is the seed sample (we have no customer yet). When a real customer
arrives, the archive load is swapped for their stored history; the similarity,
trust-ordering, and chat pipeline are unchanged.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from sidira_simulator.adapters.llm import ChatClient
from sidira_simulator.api.deps import current_customer_id, get_orchestrator
from sidira_simulator.schemas.experiment_memory import (
    ConversationRequest,
    ConversationResponse,
    ExperimentChatRequest,
    ExperimentChatResponse,
    SubmitGateRequest,
    SubmitGateResponse,
)
from sidira_simulator.services.experiment_chat import ExperimentChatService
from sidira_simulator.services.experiment_fusion import FusedConversationService
from sidira_simulator.services.experiment_gate import gate_similar
from sidira_simulator.services.live_simulations import to_simulated_hypotheses
from sidira_simulator.services.simulation_archive import seed_simulations
from sidira_simulator.services.simulation_orchestrator import SimulationOrchestrator

router = APIRouter(prefix="/experiments", tags=["experiments"])

# How many of the customer's most-recent simulations the fused conversation reads
# over. Mirrors the /simulations Hypotheses-tab default (simulations.list_recent),
# so the chat sees the same recent window the tab shows.
_LIVE_SIM_LIMIT = 50


def get_experiment_chat_client() -> ChatClient | None:
    """Chat client for the RAG endpoint.

    A dedicated dependency (mirrors ``get_input_lint_chat_client``) so the test
    suite can override it with a stub — RAG chat MUST never hit a live LLM in the
    suite. In production it returns None and ``ExperimentChatService`` resolves
    the real client lazily, falling back to an offline extractive answer when no
    provider key is configured (keyless local demo stays functional).
    """
    return None


@router.post("/search-similar", response_model=SubmitGateResponse)
async def post_search_similar(
    req: SubmitGateRequest,
    customer_id: str = Depends(current_customer_id),
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
) -> SubmitGateResponse:
    """Submit-time ADVISORY dedup gate for a NEW hypothesis (#38).

    TENANT-SCOPED (#38a): ranks the caller's OWN prior Sidira PREDICTIONS — the
    same completed simulations the ``/simulations`` Hypotheses tab lists, loaded
    via the orchestrator and scoped to ``customer_id`` — NOT the shared demo seed.
    Falls back to the synthetic seed ONLY when the tenant has no simulations at all
    (a fresh workspace / the keyless local demo), mirroring ``post_conversation``.

    SOURCE-AWARE / HONEST (#38b): a match is a ``GateMatch`` (a prior PREDICTION),
    never the measured-``Experiment`` shape. Every figure is uncalibrated
    simulated-agent agreement, never a measured winner/effect (DESIGN.md §8.3).
    Re-runs of the same hypothesis are grouped with their agreement spread.

    Trust-ordered verdict, ADVISORY only — the run is NEVER blocked on it:

    - ``already_tested`` — Sidira has effectively predicted this before; show the
      prior prediction(s) + agreement spread.
    - ``similar`` — an analogical prior prediction only; ``caveat`` carries the
      "a prediction is not a measurement" honesty label.
    - ``novel`` — no prior prediction to lean on; ``matches`` is empty.

    This runs BEFORE the new run starts and never calls the simulation engine.
    """
    rows = await orchestrator.list_recent(customer_id, limit=_LIVE_SIM_LIMIT)
    if rows:
        # The tenant HAS simulations → gate over THEIR completed ones, never the
        # demo seed. ``sims`` may be empty when their recent rows are all still
        # pending; that yields an honest NOVEL ("running it fresh") rather than
        # leaking synthetic demo predictions to a real customer.
        sims = to_simulated_hypotheses(rows)
    else:
        # Brand-new workspace / keyless local demo → the demoable synthetic seed.
        sims = seed_simulations()
    return gate_similar(req.hypothesis, sims, req.top_k)


@router.post("/chat", response_model=ExperimentChatResponse)
def post_chat(
    req: ExperimentChatRequest,
    chat_client: ChatClient | None = Depends(get_experiment_chat_client),
) -> ExperimentChatResponse:
    """Grounded RAG answer over the experiment archive (#28).

    The answer is built only from retrieved past experiments and cites them.
    With an LLM provider key configured the model composes the prose; without
    one it degrades to a grounded extractive answer (``used_llm=false``).
    """
    service = ExperimentChatService(chat_client=chat_client)
    return service.answer(req.message, req.top_k)


@router.post("/conversation", response_model=ConversationResponse)
async def post_conversation(
    req: ConversationRequest,
    customer_id: str = Depends(current_customer_id),
    orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
    chat_client: ChatClient | None = Depends(get_experiment_chat_client),
) -> ConversationResponse:
    """Multi-turn, fused conversation over the customer's simulations (#31, #32, #33).

    Extends the single-shot ``/chat`` in two ways, without touching it:

    - FUSION (#31): retrieval draws on BOTH a MEASURED experiment side and the
      Sidira PREDICTED simulation side. When a simulation and an experiment tested
      the same change, the answer tells the predicted-vs-measured story; every
      citation is labeled MEASURED or PREDICTED.
    - MULTI-TURN (#32): the request carries prior turns so a follow-up resolves
      against the prior turn's subject. Suggested follow-up chips are returned.

    TENANT SCOPING (#33): the PREDICTED side is the CUSTOMER'S OWN completed
    simulations — the same source the ``/simulations`` Hypotheses tab lists, loaded
    via the orchestrator and scoped to ``customer_id`` — not the synthetic demo
    seed. This is why a hypothesis that exists on the Hypotheses tab (e.g. a
    "Continue Watching" change) is now retrievable here. We hold no MEASURED
    experiment archive for a real tenant yet (that arrives with connector
    ingestion, #19/#20), so the measured side is empty rather than mixing in
    unrelated demo experiments. When the tenant has NO completed simulations (a
    fresh workspace or the offline/keyless demo), we fall back to the synthetic
    seed so the fused predicted-vs-measured story still demonstrates.

    Grounded/extractive-fallback behavior is preserved: with an LLM key the model
    composes the prose; without one it degrades to a grounded extractive fused
    answer (``used_llm=false``).
    """
    rows = await orchestrator.list_recent(customer_id, limit=_LIVE_SIM_LIMIT)
    if rows:
        # The tenant HAS simulations → retrieve over THEIR completed ones, never the
        # demo seed. ``live_sims`` may be empty when their recent simulations are all
        # still pending; that yields an honest "nothing completed to draw on yet"
        # answer rather than leaking synthetic demo data to a real customer. The
        # seed is reserved for a workspace with NO simulations at all.
        service = FusedConversationService(
            experiments=[],
            simulations=to_simulated_hypotheses(rows),
            chat_client=chat_client,
        )
    else:
        # Brand-new workspace / keyless local demo → the demoable synthetic seed.
        service = FusedConversationService(chat_client=chat_client)
    return service.answer(req.message, req.history, req.top_k)
