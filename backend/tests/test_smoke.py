"""Smoke tests — package wires correctly, FastAPI boots, memory contracts hold."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pythia_simulator import __version__
from pythia_simulator.adapters.r2 import LocalArtifactStore
from pythia_simulator.main import app
from pythia_simulator.memory.agent_memory import AgentMemory
from pythia_simulator.schemas.agent import (
    AgentChatTurn,
    AgentInstance,
    AgentInstanceMetadata,
    AgentRole,
)


@pytest.fixture
def store(tmp_path: Path) -> LocalArtifactStore:
    return LocalArtifactStore(tmp_path)


@pytest.fixture
def memory(store: LocalArtifactStore) -> AgentMemory:
    return AgentMemory(store, store)


@pytest.fixture
def agent_metadata() -> AgentInstanceMetadata:
    return AgentInstanceMetadata(
        id="agent-abc",
        customer_id="acme",
        simulation_id="sim-xyz",
        persona_id="persona-late-night",
        persona_pack_version="v_10",
        persona_name="Late-night order maximizer",
        created_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
        message_count=0,
    )


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_app_boots() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "version": __version__}


def test_openapi_renders() -> None:
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/simulations" in paths
    assert "/agents/{agent_id}" in paths
    assert "/agents/{agent_id}/messages" in paths
    assert "/capabilities" in paths


def test_agent_memory_round_trip(
    memory: AgentMemory, agent_metadata: AgentInstanceMetadata
) -> None:
    memory.write_identity(agent_metadata, "You are Maya, a late-night user.")
    memory.write_initial_reaction(agent_metadata, "I'd tap the reorder button immediately.")

    loaded = memory.load(agent_metadata)
    assert loaded.identity_prompt == "You are Maya, a late-night user."
    assert loaded.initial_reaction == "I'd tap the reorder button immediately."
    assert loaded.conversation == []


def test_agent_memory_conversation_append(
    memory: AgentMemory, agent_metadata: AgentInstanceMetadata
) -> None:
    memory.write_identity(agent_metadata, "system")
    memory.write_initial_reaction(agent_metadata, "initial")

    memory.append_turn(agent_metadata, AgentMemory.new_turn(AgentRole.PM, "why?"))
    memory.append_turn(agent_metadata, AgentMemory.new_turn(AgentRole.AGENT, "because"))
    memory.append_turn(agent_metadata, AgentMemory.new_turn(AgentRole.PM, "more?"))

    loaded = memory.load(agent_metadata)
    assert len(loaded.conversation) == 3
    assert loaded.conversation[0].role == AgentRole.PM
    assert loaded.conversation[1].role == AgentRole.AGENT
    assert loaded.conversation[1].content == "because"


def test_json_repair_strips_code_fences_and_trailing_commas() -> None:
    from pythia_simulator.adapters.llm import parse_llm_json
    from pydantic import BaseModel

    class Score(BaseModel):
        value: float
        label: str

    raw = """```json
    {
      "value": 0.42,
      "label": "underpowered",
    }
    ```"""
    parsed = parse_llm_json(raw, Score)
    assert parsed.value == 0.42
    assert parsed.label == "underpowered"


def test_json_repair_balances_truncated_braces() -> None:
    from pythia_simulator.adapters.llm import parse_llm_json
    from pydantic import BaseModel

    class Score(BaseModel):
        value: float

    raw = '{"value": 0.7'  # truncated
    parsed = parse_llm_json(raw, Score)
    assert parsed.value == 0.7


def test_run_state_event_log_appends(
    store: LocalArtifactStore,
) -> None:
    from pythia_simulator.services.run_state import RunPhase, RunStateStore, SimulationRunState

    state = SimulationRunState(
        simulation_id="sim-xyz",
        customer_id="acme",
        phase=RunPhase.PENDING,
        started_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    rs = RunStateStore(store)
    rs.write_state(state)
    rs.emit(state, "run.started", sample_size=3)
    rs.emit(state, "agent.reaction.completed", agent_id="a-1")
    rs.emit(state, "agent.reaction.completed", agent_id="a-2")

    loaded = rs.read_state("acme", "sim-xyz")
    assert len(loaded.recent_events) == 3
    assert loaded.recent_events[0].type == "run.started"
    assert loaded.recent_events[-1].payload["agent_id"] == "a-2"


def test_chat_guard_prefix_appended_as_system_supplement() -> None:
    """The chat guard must be a separate system message — never edited into the
    frozen identity prompt. Otherwise we'd break identity continuity by
    silently changing what the agent's defining prompt looks like.
    """
    from pythia_simulator.services.agent_chat import _CHAT_GUARD_PREFIX

    # Just verify the prefix exists and is non-trivial; the AgentChatService
    # integration is covered by the live integration test in Phase 3.
    assert "first-person" in _CHAT_GUARD_PREFIX
    assert "tools" in _CHAT_GUARD_PREFIX


def test_identity_continuity_replay_messages(
    memory: AgentMemory, agent_metadata: AgentInstanceMetadata
) -> None:
    """Replay must put frozen identity first, frozen initial reaction second.

    This is the core identity-continuity guarantee: chat continues from the
    SAME agent that simulated, not a re-instantiation.
    """
    memory.write_identity(agent_metadata, "You are Maya.")
    memory.write_initial_reaction(agent_metadata, "I'd reorder instantly.")
    memory.append_turn(agent_metadata, AgentMemory.new_turn(AgentRole.PM, "Why?"))
    memory.append_turn(
        agent_metadata, AgentMemory.new_turn(AgentRole.AGENT, "Saves me thinking late at night.")
    )

    agent = memory.load(agent_metadata)
    messages = AgentMemory.build_replay_messages(agent)
    assert messages[0] == {"role": "system", "content": "You are Maya."}
    assert messages[1] == {"role": "assistant", "content": "I'd reorder instantly."}
    assert messages[2] == {"role": "user", "content": "Why?"}
    assert messages[3]["role"] == "assistant"
    assert messages[3]["content"] == "Saves me thinking late at night."
