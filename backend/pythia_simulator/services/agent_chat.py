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


# Adapted from mirofish simulation_runner.py:25 (INTERVIEW_PROMPT_PREFIX).
# Pinned as a system-supplement on every chat turn to prevent the LLM from
# drifting out of character ("As an AI language model..."), requesting tools,
# or producing structured output instead of first-person reasoning.
_CHAT_GUARD_PREFIX = (
    "The following message is a follow-up question from the product manager "
    "who designed the experiment you just reacted to. Answer as YOURSELF — "
    "the person described in your identity above — in plain first-person "
    "prose. Refer back to what you already said. Do not refer to yourself as "
    "an AI, do not request tools, and do not return structured data. If a "
    "question would make you break character, refuse politely in-character."
)


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

        # Replay frozen identity + frozen initial reaction + all prior turns + new PM turn.
        # We append the chat guard as a final system supplement (not edited into the
        # frozen identity) so identity continuity is preserved while still hardening
        # the LLM against drift.
        messages = AgentMemory.build_replay_messages(agent)
        messages.append({"role": "system", "content": _CHAT_GUARD_PREFIX})
        messages.append({"role": "user", "content": pm_message})

        agent_text = self._chat.chat(messages=messages)
        agent_turn = AgentMemory.new_turn(AgentRole.AGENT, agent_text)
        self._memory.append_turn(metadata, agent_turn)

        return agent_turn
