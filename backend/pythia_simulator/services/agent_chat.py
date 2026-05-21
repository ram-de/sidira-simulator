"""Post-simulation PM ↔ agent chat.

THE agent here is the SAME entity that ran in the simulation — not a re-instantiation.
The frozen identity_prompt and initial_reaction are replayed on every chat call so the
LLM continues from the agent's simulation-time state. See identity-continuity guarantee
in pythia_simulator/memory/agent_memory.py.
"""

from __future__ import annotations

from pythia_simulator.adapters.llm import ChatClient, get_chat_client
from pythia_simulator.adapters.r2 import ArtifactStore, get_store
from pythia_simulator.memory.agent_memory import AgentMemory
from pythia_simulator.schemas.agent import AgentChatTurn, AgentInstanceMetadata, AgentRole


class AgentChatService:
    def __init__(
        self,
        store: ArtifactStore | None = None,
        chat_client: ChatClient | None = None,
    ) -> None:
        self._store = store or get_store()
        self._chat = chat_client or get_chat_client()
        self._memory = AgentMemory(self._store, self._store)

    def send_message(
        self,
        metadata: AgentInstanceMetadata,
        pm_message: str,
    ) -> AgentChatTurn:
        """PM sends a follow-up; the same agent that ran in the simulation responds."""
        agent = self._memory.load(metadata)

        # Append the PM's message before composing the LLM call so the new turn is
        # part of the persisted history regardless of LLM outcome.
        pm_turn = AgentMemory.new_turn(AgentRole.PM, pm_message)
        self._memory.append_turn(metadata, pm_turn)

        # Replay frozen identity + frozen initial reaction + all prior turns + new PM turn
        messages = AgentMemory.build_replay_messages(agent)
        messages.append({"role": "user", "content": pm_message})

        agent_text = self._chat.chat(messages=messages)
        agent_turn = AgentMemory.new_turn(AgentRole.AGENT, agent_text)
        self._memory.append_turn(metadata, agent_turn)

        return agent_turn
