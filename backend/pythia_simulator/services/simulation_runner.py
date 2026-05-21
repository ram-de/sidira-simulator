"""Simulation runner — orchestrates a single simulation end-to-end.

Flow:
1. Load latest Persona Pack and Feature Pack for the customer
2. For each sampled persona: compose identity_prompt + call LLM → initial_reaction
3. Persist AgentInstance with FROZEN identity + reaction (the agents the PM will chat with)
4. Aggregate reactions → confidence_score + weaknesses
5. Persist SimulationResult
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog

from pythia_simulator.adapters.llm import ChatClient, get_chat_client
from pythia_simulator.adapters.r2 import ArtifactStore, get_store
from pythia_simulator.memory.agent_memory import AgentMemory
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

log = structlog.get_logger()


class SimulationRunner:
    def __init__(
        self,
        store: ArtifactStore | None = None,
        chat_client: ChatClient | None = None,
    ) -> None:
        self._store = store or get_store()
        self._chat = chat_client or get_chat_client()
        self._memory = AgentMemory(self._store, self._store)

    def run(
        self,
        customer_id: str,
        persona_pack: PersonaPack,
        capability: Capability,
        hypothesis: Hypothesis,
        sample_size: int = 10,
    ) -> Simulation:
        sim_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        sampled_personas = self._sample_personas(persona_pack, sample_size)
        agent_ids: list[str] = []

        for persona in sampled_personas:
            agent_id = str(uuid.uuid4())
            agent_ids.append(agent_id)

            identity_prompt = compose_identity_prompt(
                customer_id=customer_id,
                persona=persona,
                capability=capability,
                hypothesis=hypothesis,
            )

            initial_reaction = self._chat.chat(
                messages=[
                    {"role": "system", "content": identity_prompt},
                    {
                        "role": "user",
                        "content": "React to the proposed change as yourself. Give your honest, specific reaction.",
                    },
                ]
            )

            metadata = AgentInstanceMetadata(
                id=agent_id,
                customer_id=customer_id,
                simulation_id=sim_id,
                persona_id=persona.id,
                persona_pack_version=persona_pack.version,
                persona_name=persona.name,
                created_at=now,
                last_active_at=now,
                message_count=0,
            )

            # FROZEN at simulation time — see identity-continuity guarantee
            # in pythia_simulator/memory/agent_memory.py
            self._memory.write_identity(metadata, identity_prompt)
            self._memory.write_initial_reaction(metadata, initial_reaction)

            log.info(
                "agent.materialized",
                sim_id=sim_id,
                agent_id=agent_id,
                persona=persona.name,
            )

        # Aggregation (stubbed — Phase 1 implements proper scoring)
        result = SimulationResult(
            confidence_score=0.0,
            weaknesses=[
                Weakness(
                    category="untestable_hypothesis",
                    summary="Scoring not yet implemented — see Phase 1 milestone.",
                )
            ],
            refinement_suggestions=[],
        )

        return Simulation(
            id=sim_id,
            customer_id=customer_id,
            created_at=now,
            status=SimulationStatus.COMPLETE,
            persona_pack_version=persona_pack.version,
            feature_pack_version="2026-W21",  # TODO load from caller
            hypothesis=hypothesis,
            agent_instance_ids=agent_ids,
            result=result,
        )

    @staticmethod
    def _sample_personas(pack: PersonaPack, n: int) -> list[Persona]:
        """Sample personas weighted by head-count. MVP: deterministic top-N."""
        weights = pack.weights.head_count
        ranked = sorted(pack.personas, key=lambda p: weights.get(p.id, 0.0), reverse=True)
        return ranked[:n]
