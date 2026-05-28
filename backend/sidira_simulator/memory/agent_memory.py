"""AgentMemory — owns the read/write contract for an AgentInstance's three memory layers.

Storage split:
- Postgres holds the AgentInstanceMetadata row (used for listing / search).
- R2 holds the heavy blobs at:
    customers/<customer_id>/simulations/<sim_id>/agents/<agent_id>/
        identity.md
        initial_reaction.md
        conversation.jsonl   (append-only)

This class is the only place that knows the on-disk layout. Services and API
routes go through it.

============================================================================
IDENTITY-CONTINUITY GUARANTEE
============================================================================
The agent a PM chats with after a simulation is the SAME agent that
participated — not a freshly-instantiated twin from the same persona template.

This is enforced by two invariants:

  1. `identity.md` (the system prompt) is written ONCE at simulation time and
     is NEVER recomputed. It captures the persona description, the Feature
     Pack slice that was current, and the hypothesis context — all as they
     existed when the agent reacted.

  2. `initial_reaction.md` is the verbatim simulation-time output and is
     replayed as the FIRST assistant message on every subsequent chat call,
     so the LLM continues from the exact conversational state the agent
     produced during the simulation.

Chat NEVER re-runs the prompt-composer. It loads these frozen artifacts and
appends. This avoids the mirofish failure mode where the chat-time agent is
a re-instantiation from the persona template (which loses the simulation-time
reasoning and produces a different "agent" than the one that participated).
============================================================================
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from sidira_simulator.schemas.agent import (
    AgentChatTurn,
    AgentInstance,
    AgentInstanceMetadata,
    AgentRole,
)
from sidira_simulator.schemas.identity import IdentitySeed


class ArtifactReader(Protocol):
    def read_text(self, key: str) -> str: ...
    def read_lines(self, key: str) -> list[str]: ...


class ArtifactWriter(Protocol):
    def write_text(self, key: str, body: str) -> None: ...
    def append_line(self, key: str, line: str) -> None: ...


class AgentMemory:
    """Read/write the three memory layers of a single AgentInstance."""

    def __init__(self, reader: ArtifactReader, writer: ArtifactWriter) -> None:
        self._reader = reader
        self._writer = writer

    @staticmethod
    def _base_key(metadata: AgentInstanceMetadata) -> str:
        return (
            f"customers/{metadata.customer_id}"
            f"/simulations/{metadata.simulation_id}"
            f"/agents/{metadata.id}"
        )

    def write_identity(self, metadata: AgentInstanceMetadata, identity_prompt: str) -> None:
        self._writer.write_text(f"{self._base_key(metadata)}/identity.md", identity_prompt)

    def write_initial_reaction(self, metadata: AgentInstanceMetadata, reaction: str) -> None:
        self._writer.write_text(f"{self._base_key(metadata)}/initial_reaction.md", reaction)

    def write_identity_seed(
        self, metadata: AgentInstanceMetadata, identity_seed: IdentitySeed
    ) -> None:
        self._writer.write_text(
            f"{self._base_key(metadata)}/identity_seed.json",
            identity_seed.model_dump_json(),
        )

    def append_turn(self, metadata: AgentInstanceMetadata, turn: AgentChatTurn) -> None:
        line = turn.model_dump_json()
        self._writer.append_line(f"{self._base_key(metadata)}/conversation.jsonl", line)

    def load(self, metadata: AgentInstanceMetadata) -> AgentInstance:
        base = self._base_key(metadata)
        identity = self._reader.read_text(f"{base}/identity.md")
        reaction = self._reader.read_text(f"{base}/initial_reaction.md")
        try:
            lines = self._reader.read_lines(f"{base}/conversation.jsonl")
        except FileNotFoundError:
            lines = []
        conversation = [AgentChatTurn.model_validate_json(ln) for ln in lines if ln.strip()]
        try:
            seed_json = self._reader.read_text(f"{base}/identity_seed.json")
            identity_seed: IdentitySeed | None = IdentitySeed.model_validate_json(seed_json)
        except FileNotFoundError:
            identity_seed = None
        return AgentInstance(
            metadata=metadata,
            identity_prompt=identity,
            initial_reaction=reaction,
            conversation=conversation,
            identity_seed=identity_seed,
        )

    @staticmethod
    def build_replay_messages(agent: AgentInstance) -> list[dict[str, str]]:
        """Reconstruct full LLM message history for a chat-completion call.

        MVP strategy: full transcript replay — no summarization. The system
        prompt is the identity; the first assistant message is the initial
        reaction; subsequent turns alternate as recorded.
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": agent.identity_prompt},
            {"role": "assistant", "content": agent.initial_reaction},
        ]
        for turn in agent.conversation:
            llm_role = "user" if turn.role == AgentRole.PM else "assistant"
            messages.append({"role": llm_role, "content": turn.content})
        return messages

    @staticmethod
    def new_turn(role: AgentRole, content: str) -> AgentChatTurn:
        return AgentChatTurn(
            role=role,
            content=content,
            created_at=datetime.now(timezone.utc),
        )
