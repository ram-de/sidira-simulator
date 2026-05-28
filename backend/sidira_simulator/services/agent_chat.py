"""Post-simulation PM ↔ agent chat.

THE agent here is the SAME entity that ran in the simulation — not a re-instantiation.
The frozen identity_prompt and initial_reaction are replayed on every chat call so the
LLM continues from the agent's simulation-time state. See identity-continuity guarantee
in sidira_simulator/memory/agent_memory.py.
"""

from __future__ import annotations

from sidira_simulator.adapters.llm import ChatClient, get_chat_client
from sidira_simulator.adapters.r2 import ArtifactStore, get_store
from sidira_simulator.memory.agent_memory import AgentMemory
from sidira_simulator.schemas.agent import AgentChatTurn, AgentInstanceMetadata, AgentRole

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
        model_id: str | None = None,
    ) -> None:
        self._store = store or get_store()
        if chat_client is not None:
            self._chat = chat_client
        elif model_id is not None:
            self._chat = get_chat_client(model_id)
        else:
            self._chat = get_chat_client()
        self._memory = AgentMemory(self._store, self._store)

    def send_message(
        self,
        metadata: AgentInstanceMetadata,
        pm_message: str,
    ) -> AgentChatTurn:
        """PM sends a follow-up; the same agent that ran in the simulation responds.

        Ordering note (codex #52 P1): the PM turn is persisted ONLY after the
        LLM call succeeds, alongside the agent turn. The earlier "persist PM
        first, then call LLM" pattern meant a transient LLM failure (timeout,
        JSON parse error, rate limit) left a half-written turn pair: PM
        persisted, no reply. The natural client retry then appended the SAME
        PM message a second time, permanently corrupting the conversation log.

        With the fix, retries are safe for the LLM-failure class (the common
        case): nothing is persisted on failure, so retry produces exactly
        one pair. They are NOT safe for:
          - Partial persistence failure (PM append succeeds, agent append
            raises) — leaves an orphan PM turn. Documented as codex #52 P2
            round-2; mitigation would be an atomic append_turns([pm, agent])
            batch on AgentMemory. Deferred — rare in practice with local /
            R2 stores, and the orphan PM is visually unambiguous (no reply
            below it) so a thoughtful user can decide what to do.
          - Concurrent double-submits from the UI for the same agent —
            both LLM calls fire, both persist. Mitigation would be a
            per-agent send lock or a client-supplied idempotency key
            (#56 territory).
          - Client timeouts AFTER both turns persist — server has the data,
            client doesn't know, retry duplicates. Same idempotency-key fix.

        Tradeoff for the LLM-failure path: the PM's typed message isn't
        recoverable from the server. Client still has it in the input box
        and can retry. Better failure mode than the pre-fix footgun.
        """
        agent = self._memory.load(metadata)

        # Build the replay stack WITHOUT yet persisting the PM turn. Identity
        # continuity is preserved (frozen identity_prompt + frozen
        # initial_reaction + the prior conversation log) and the new PM
        # message is supplied as the final user turn for the LLM call.
        messages = AgentMemory.build_replay_messages(agent)
        messages.append({"role": "system", "content": _CHAT_GUARD_PREFIX})
        messages.append({"role": "user", "content": pm_message})

        agent_text = self._chat.chat(messages=messages)

        # LLM call succeeded — now persist both turns. The two appends are
        # sequential (PM first so the conversation reads correctly on reload);
        # in the rare case the second append fails the agent turn is lost but
        # the PM turn remains, which is still preferable to the pre-fix
        # "PM persisted, no reply" footgun because the next retry just sees
        # an orphan PM message and the user can decide what to do.
        pm_turn = AgentMemory.new_turn(AgentRole.PM, pm_message)
        self._memory.append_turn(metadata, pm_turn)

        agent_turn = AgentMemory.new_turn(AgentRole.AGENT, agent_text)
        self._memory.append_turn(metadata, agent_turn)

        return agent_turn
