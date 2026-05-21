"""Simulation runner — orchestrates one simulation end-to-end.

Flow:
1. Load latest Persona Pack + Feature Pack capability (caller supplies)
2. Materialize N AgentInstances (one per sampled persona) — each gets a FROZEN
   identity prompt and FROZEN initial reaction. These are the agents the PM
   will chat with later. See identity-continuity guarantee in
   pythia_simulator/memory/agent_memory.py.
3. Aggregate reactions → confidence score + weaknesses (stubbed; Phase 3 scoring).
4. Persist results + live state via RunStateStore (event log + state.json).

Parallelism: agent reactions run concurrently via `asyncio.gather`. Adapted
from mirofish oasis_profile_generator.py:851-1014 (ThreadPoolExecutor with
progress callbacks); we use async-native primitives because our LLM SDKs are
async and FastAPI already runs an event loop.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import structlog

from pythia_simulator.adapters.llm import ChatClient, get_chat_client
from pythia_simulator.adapters.r2 import ArtifactStore, get_store
from pythia_simulator.memory.agent_memory import AgentMemory
from dataclasses import dataclass

from pythia_simulator.schemas.agent import AgentInstanceMetadata
from pythia_simulator.schemas.feature_pack import Capability
from pythia_simulator.schemas.persona import Persona, PersonaPack
from pythia_simulator.schemas.simulation import (
    Hypothesis,
    Simulation,
    SimulationResult,
    SimulationStatus,
    Weakness,
)
from pythia_simulator.services.prompt_composer import compose_identity_prompt
from pythia_simulator.services.run_state import (
    RunPhase,
    RunStateStore,
    SimulationRunState,
)

log = structlog.get_logger()


@dataclass
class AgentRecord:
    """Lightweight record returned from _materialize_agent for repo persistence."""

    agent_id: str
    persona_id: str
    persona_name: str
    created_at: datetime


class SimulationRunner:
    def __init__(
        self,
        store: ArtifactStore | None = None,
        chat_client: ChatClient | None = None,
        max_concurrent_agents: int = 5,
        per_agent_timeout_s: float = 60.0,
    ) -> None:
        self._store = store or get_store()
        # Lazy chat client — don't crash app startup when no LLM key is set.
        # The first .chat() call will raise RuntimeError with a clear message.
        self._chat_explicit = chat_client
        self._memory = AgentMemory(self._store, self._store)
        self._run_state = RunStateStore(self._store)
        self._semaphore = asyncio.Semaphore(max_concurrent_agents)
        self._per_agent_timeout_s = per_agent_timeout_s

    @property
    def _chat(self) -> ChatClient:
        if self._chat_explicit is None:
            self._chat_explicit = get_chat_client()
        return self._chat_explicit

    async def run(
        self,
        customer_id: str,
        persona_pack: PersonaPack,
        capability: Capability,
        feature_pack_version: str,
        hypothesis: Hypothesis,
        sample_size: int = 10,
        sim_id: str | None = None,
    ) -> Simulation:
        sim_id = sim_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        state = SimulationRunState(
            simulation_id=sim_id,
            customer_id=customer_id,
            phase=RunPhase.LOADING_PACKS,
            started_at=now,
            updated_at=now,
        )
        self._run_state.write_state(state)
        self._run_state.emit(state, "run.started", sample_size=sample_size)

        sampled = self._sample_personas(persona_pack, sample_size)
        state.agents_total = len(sampled)
        state.mark_phase(RunPhase.MATERIALIZING_AGENTS)
        self._run_state.write_state(state)

        # Fan out: each persona gets its own AgentInstance with frozen identity + reaction.
        state.mark_phase(RunPhase.AGENTS_REACTING)
        self._run_state.write_state(state)

        # N-of-M handling: a single agent failure / timeout MUST NOT crash the whole
        # simulation. return_exceptions=True keeps the gather alive; failed agents
        # surface via agent.reaction.failed events that the frontend already renders.
        results = await asyncio.gather(
            *(
                self._materialize_agent(
                    state, customer_id, sim_id, persona, capability, hypothesis, persona_pack.version
                )
                for persona in sampled
            ),
            return_exceptions=True,
        )
        agent_records: list[AgentRecord] = [r for r in results if isinstance(r, AgentRecord)]
        agent_ids = [r.agent_id for r in agent_records]
        self._last_run_agent_records = agent_records  # caller can read for repo persistence

        state.mark_phase(RunPhase.SCORING)
        self._run_state.write_state(state)
        result = self._score(state, sim_id)

        state.mark_phase(RunPhase.COMPLETE)
        self._run_state.emit(state, "run.complete", score=result.confidence_score)

        return Simulation(
            id=sim_id,
            customer_id=customer_id,
            created_at=now,
            status=SimulationStatus.COMPLETE,
            persona_pack_version=persona_pack.version,
            feature_pack_version=feature_pack_version,
            hypothesis=hypothesis,
            agent_instance_ids=list(agent_ids),
            result=result,
        )

    async def _materialize_agent(
        self,
        state: SimulationRunState,
        customer_id: str,
        sim_id: str,
        persona: Persona,
        capability: Capability,
        hypothesis: Hypothesis,
        persona_pack_version: str,
    ) -> AgentRecord:
        async with self._semaphore:
            agent_id = str(uuid.uuid4())
            self._run_state.emit(
                state,
                "agent.reaction.started",
                agent_id=agent_id,
                persona=persona.name,
            )

            identity_prompt = compose_identity_prompt(
                customer_id=customer_id,
                persona=persona,
                capability=capability,
                hypothesis=hypothesis,
            )

            try:
                initial_reaction = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._chat.chat,
                        [
                            {"role": "system", "content": identity_prompt},
                            {
                                "role": "user",
                                "content": (
                                    "React to the proposed change as yourself. Give your honest, "
                                    "specific reaction in first-person prose. Reference the current "
                                    "product flows and copy where relevant."
                                ),
                            },
                        ],
                    ),
                    timeout=self._per_agent_timeout_s,
                )
            except asyncio.TimeoutError:
                state.agents_failed += 1
                self._run_state.emit(
                    state,
                    "agent.reaction.failed",
                    agent_id=agent_id,
                    persona=persona.name,
                    error=f"timeout_after_{int(self._per_agent_timeout_s)}s",
                )
                raise
            except Exception as exc:
                state.agents_failed += 1
                self._run_state.emit(
                    state,
                    "agent.reaction.failed",
                    agent_id=agent_id,
                    persona=persona.name,
                    error=str(exc)[:500],
                )
                raise

            now = datetime.now(timezone.utc)
            metadata = AgentInstanceMetadata(
                id=agent_id,
                customer_id=customer_id,
                simulation_id=sim_id,
                persona_id=persona.id,
                persona_pack_version=persona_pack_version,
                persona_name=persona.name,
                created_at=now,
                last_active_at=now,
                message_count=0,
            )

            # FROZEN — the identity-continuity guarantee starts here.
            self._memory.write_identity(metadata, identity_prompt)
            self._memory.write_initial_reaction(metadata, initial_reaction)

            state.agents_complete += 1
            self._run_state.emit(
                state,
                "agent.reaction.completed",
                agent_id=agent_id,
                persona=persona.name,
                reaction_length=len(initial_reaction),
            )
            log.info(
                "agent.materialized",
                sim_id=sim_id,
                agent_id=agent_id,
                persona=persona.name,
            )
            return AgentRecord(
                agent_id=agent_id,
                persona_id=persona.id,
                persona_name=persona.name,
                created_at=now,
            )

    def _score(self, state: SimulationRunState, sim_id: str) -> SimulationResult:
        """Stub. Phase 3 implements: load each agent's initial_reaction, run a
        weakness-classification LLM call across all reactions, aggregate to a
        confidence score, and surface 1–3 refinement suggestions."""
        self._run_state.emit(state, "score.updated", score=0.0, note="scoring not yet implemented")
        return SimulationResult(
            confidence_score=0.0,
            weaknesses=[
                Weakness(
                    category="untestable_hypothesis",
                    summary="Scoring not yet implemented — see Phase 3 milestone.",
                )
            ],
            refinement_suggestions=[],
        )

    @staticmethod
    def _sample_personas(pack: PersonaPack, n: int) -> list[Persona]:
        weights = pack.weights.head_count
        ranked = sorted(pack.personas, key=lambda p: weights.get(p.id, 0.0), reverse=True)
        return ranked[:n]
