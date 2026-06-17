"""End-to-end API tests for `/agents/{id}` + `/agents/{id}/messages` (Phase 4 #52).

Pattern lifted from test_simulations_api.py:
- Stub LLM avoids real network calls
- Real simulation is submitted to populate the InMemoryAgentInstanceRepo
- Then the new agent routes are exercised against the real persisted agents
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))

from sidira_simulator.adapters import llm as llm_mod  # noqa: E402
from sidira_simulator.adapters.repositories import get_in_memory_repos  # noqa: E402
from sidira_simulator.api.deps import get_orchestrator  # noqa: E402
from sidira_simulator.main import app  # noqa: E402
from sidira_simulator.services import agent_chat as agent_chat_mod  # noqa: E402
from sidira_simulator.services.simulation_orchestrator import SimulationOrchestrator  # noqa: E402
from sidira_simulator.services.simulation_runner import SimulationRunner  # noqa: E402


class _StubChat:
    """LLM stub with a swappable reply so tests can pin sim-phase vs
    chat-phase output without coupling to the chat-guard prose.

    Pattern: `reply` defaults to the sim-time canned response; tests call
    `chat.reply_for_chat = "..."` after the simulation completes and before
    the chat POST to differentiate the two phases. Counters help tests
    assert call-count deltas without reading message text."""

    def __init__(self) -> None:
        self.reply_for_sim = "I'd give it a shot."
        self.reply_for_chat = "Following up: I'd want to know how often it surfaces."
        self._phase = "sim"  # tests flip to "chat" via _enter_chat_phase
        self.json_calls: list[tuple[type, list[dict]]] = []
        self.chat_calls: list[list[dict]] = []
        self.call_count = 0

    def _enter_chat_phase(self) -> None:
        """Tests call this once the simulation has completed and before any
        chat POST, so subsequent chat() calls return the chat-time reply."""
        self._phase = "chat"

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        self.chat_calls.append(messages)
        self.call_count += 1
        return self.reply_for_chat if self._phase == "chat" else self.reply_for_sim

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        self.json_calls.append((schema, messages))
        from sidira_simulator.schemas.scoring import (
            RefinementOutput,
            Sentiment,
            SentimentClassification,
            WeaknessClassification,
        )

        if schema is WeaknessClassification:
            return WeaknessClassification(categories=[], primary_reason="stub")
        if schema is SentimentClassification:
            return SentimentClassification(
                sentiment=Sentiment.POSITIVE, confidence=0.8, one_line_summary="stub"
            )
        if schema is RefinementOutput:
            return RefinementOutput(suggestions=[])
        raise NotImplementedError(schema)


@pytest.fixture
def client_with_chat_stub(monkeypatch):
    """Run a real sim end-to-end with a stub LLM, then expose the TestClient
    + the stub so chat tests can pin call counts and reply text."""
    chat = _StubChat()

    # Patch both `get_chat_client` bindings so AgentChatService (constructed
    # inside the route) picks up the stub. The service does
    # `from ...adapters.llm import get_chat_client` — a local name binding —
    # so patching only the source module wouldn't catch the service's import.
    monkeypatch.setattr(llm_mod, "get_chat_client", lambda model_id=None: chat)
    monkeypatch.setattr(agent_chat_mod, "get_chat_client", lambda model_id=None: chat)

    customer_repo, sim_repo, agent_repo, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    sim_repo._sims.clear()
    agent_repo._agents.clear()

    runner = SimulationRunner(chat_client=chat)

    from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
    from sidira_simulator.adapters.persona_loader import PersonaPackLoader
    from sidira_simulator.adapters.r2 import LocalArtifactStore

    store = LocalArtifactStore(_FIXTURE_ROOT)
    persona_loader = PersonaPackLoader(store)
    feature_loader = FeaturePackLoader(store)

    def _orch():
        return SimulationOrchestrator(
            customer_repo=customer_repo,
            simulation_repo=sim_repo,
            agent_repo=agent_repo,
            persona_loader=persona_loader,
            feature_pack_loader=feature_loader,
            runner=runner,
        )

    app.dependency_overrides[get_orchestrator] = _orch
    yield TestClient(app), chat, agent_repo
    app.dependency_overrides.clear()


def _run_sim_and_pick_agent(
    client: TestClient,
    agent_repo,
    chat: _StubChat | None = None,
    model_id: str | None = None,
) -> tuple[str, dict]:
    """Submit a small simulation, wait for completion, return one agent_id
    + its persisted repo row. If `chat` is provided, flip its phase to
    "chat" so subsequent stub LLM calls return the chat-time canned reply
    instead of the sim-time one — replaces an earlier brittle heuristic
    that matched the chat-guard prose. (codex #52 P2)"""
    payload = {
        "hypothesis": {
            "capability_name": "reorder",
            "prose": "Surface a one-tap reorder banner for premium subscribers.",
            "proposed_figma": {"screens": [], "transitions": []},
        },
        "population_size": 3,
        "run_as_generic_reception": True,
    }
    if model_id is not None:
        payload["model_id"] = model_id
    resp = client.post("/simulations", json=payload)
    assert resp.status_code == 202, resp.text
    sim_id = resp.json()["id"]
    # TestClient + BackgroundTasks: the response returns AFTER background work
    # in the test transport, so the sim is already complete here.
    final = client.get(f"/simulations/{sim_id}")
    assert final.status_code == 200, final.text
    agent_ids = final.json()["agent_instance_ids"]
    assert len(agent_ids) >= 1
    agent_id = agent_ids[0]
    row = next(a for a in agent_repo._agents.values() if a["id"] == agent_id)
    if chat is not None:
        chat._enter_chat_phase()
    return agent_id, row


def test_get_agent_returns_full_instance(client_with_chat_stub) -> None:
    """GET /agents/{id} returns metadata + identity_prompt + initial_reaction +
    conversation (empty after sim, before any chat)."""
    client, _chat, agent_repo = client_with_chat_stub
    agent_id, row = _run_sim_and_pick_agent(client, agent_repo)

    resp = client.get(f"/agents/{agent_id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Metadata round-trips
    assert body["metadata"]["id"] == agent_id
    assert body["metadata"]["persona_id"] == row["persona_id"]
    assert body["metadata"]["persona_name"] == row["persona_name"]
    assert body["metadata"]["simulation_id"] == row["simulation_id"]

    # Memory layers populated by the runner
    assert body["identity_prompt"], "identity_prompt should be persisted from sim"
    assert body["initial_reaction"], "initial_reaction should be persisted from sim"
    # No chat has happened yet — conversation log is empty
    assert body["conversation"] == []
    # identity_seed sidecar was written by Phase 2.5 runner — should be present
    assert body["identity_seed"] is not None


def test_get_agent_404_for_unknown_id(client_with_chat_stub) -> None:
    """Unknown agent_id returns 404 (NOT 501 — that was the pre-#52 stub)."""
    client, _chat, _agent_repo = client_with_chat_stub
    resp = client.get("/agents/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_get_agent_404_for_cross_customer(client_with_chat_stub, monkeypatch) -> None:
    """An agent belonging to a different customer must not be readable.
    Verifies that AgentInstanceRepo.get enforces customer scoping (it does in
    both InMemory and Postgres variants); this is the route-level proof."""
    client, _chat, agent_repo = client_with_chat_stub
    agent_id, _row = _run_sim_and_pick_agent(client, agent_repo)
    # Default customer is "demo"; flip via env to simulate a different customer
    # asking for the same id.
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "someone-else")
    resp = client.get(f"/agents/{agent_id}")
    assert resp.status_code == 404


def test_send_message_appends_turn_and_returns_agent_reply(
    client_with_chat_stub,
) -> None:
    """POST /agents/{id}/messages persists the PM turn, calls the LLM with the
    frozen identity + initial reaction + guard prefix, persists the agent reply,
    and returns the new turn."""
    client, chat, agent_repo = client_with_chat_stub
    agent_id, _row = _run_sim_and_pick_agent(client, agent_repo, chat=chat)

    # Baseline: chat() call count after sim
    pre_count = chat.call_count

    resp = client.post(
        f"/agents/{agent_id}/messages",
        json={"message": "What would make this work better for you?"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["turn"]["role"] == "agent"
    assert body["turn"]["content"] == chat.reply_for_chat

    # The LLM was called exactly once for the chat turn (on top of sim-time calls)
    assert chat.call_count == pre_count + 1

    # The PM turn + agent turn are now in the persisted conversation log
    follow = client.get(f"/agents/{agent_id}")
    assert follow.status_code == 200
    turns = follow.json()["conversation"]
    assert len(turns) == 2
    assert turns[0]["role"] == "pm"
    assert turns[0]["content"] == "What would make this work better for you?"
    assert turns[1]["role"] == "agent"
    assert turns[1]["content"] == chat.reply_for_chat


def test_send_message_uses_simulation_model_id(client_with_chat_stub, monkeypatch) -> None:
    """#103: follow-up chat should stay on the model selected for the run."""
    client, chat, agent_repo = client_with_chat_stub
    requested_models: list[str | None] = []

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")

    def fake_get_chat_client(model_id: str | None = None):
        requested_models.append(model_id)
        return chat

    monkeypatch.setattr(agent_chat_mod, "get_chat_client", fake_get_chat_client)
    agent_id, _row = _run_sim_and_pick_agent(
        client,
        agent_repo,
        chat=chat,
        model_id="claude-opus-4-7",
    )

    resp = client.post(
        f"/agents/{agent_id}/messages",
        json={"message": "Does your original reaction still hold?"},
    )

    assert resp.status_code == 200, resp.text
    assert requested_models == ["claude-opus-4-7"]


def test_send_message_rejects_empty_body(client_with_chat_stub) -> None:
    """Empty message → 400, no LLM call, no turn persisted."""
    client, chat, agent_repo = client_with_chat_stub
    agent_id, _row = _run_sim_and_pick_agent(client, agent_repo)
    pre_count = chat.call_count

    resp = client.post(f"/agents/{agent_id}/messages", json={"message": "   "})
    assert resp.status_code == 400
    # No LLM call fired
    assert chat.call_count == pre_count
    # No turn persisted
    follow = client.get(f"/agents/{agent_id}")
    assert follow.json()["conversation"] == []


def test_send_message_404_for_unknown_agent(client_with_chat_stub) -> None:
    """Unknown agent → 404 without any LLM call."""
    client, chat, _agent_repo = client_with_chat_stub
    pre_count = chat.call_count
    resp = client.post(
        "/agents/00000000-0000-0000-0000-000000000000/messages",
        json={"message": "hi"},
    )
    assert resp.status_code == 404
    assert chat.call_count == pre_count


def test_send_message_llm_failure_leaves_no_persisted_turn(
    client_with_chat_stub, monkeypatch
) -> None:
    """Codex #52 P1: a 502 from the LLM must leave the conversation log
    untouched so that a natural client retry doesn't duplicate the PM turn.
    Pre-fix, the PM turn was appended BEFORE the LLM call — failure left an
    orphan PM message and retry appended a second copy.
    """
    client, chat, agent_repo = client_with_chat_stub
    agent_id, _row = _run_sim_and_pick_agent(client, agent_repo)

    # Conversation starts empty
    assert client.get(f"/agents/{agent_id}").json()["conversation"] == []

    # Make the next LLM call raise — both routes wrap the service call so the
    # route layer surfaces this as a 502.
    def _boom(messages, max_tokens=4096, temperature=0.0, seed=None):
        raise TimeoutError("simulated LLM timeout")

    monkeypatch.setattr(chat, "chat", _boom)

    resp = client.post(f"/agents/{agent_id}/messages", json={"message": "First try (will fail)"})
    assert resp.status_code == 502
    # Conversation still empty — no orphan PM turn
    assert client.get(f"/agents/{agent_id}").json()["conversation"] == []

    # Restore a working LLM and retry the SAME message. Should produce
    # exactly one PM + one agent turn (not two PM turns).
    monkeypatch.setattr(
        chat,
        "chat",
        lambda messages, max_tokens=4096, temperature=0.0, seed=None: chat.reply_for_chat,
    )
    resp = client.post(f"/agents/{agent_id}/messages", json={"message": "First try (will fail)"})
    assert resp.status_code == 200
    turns = client.get(f"/agents/{agent_id}").json()["conversation"]
    assert len(turns) == 2
    assert [t["role"] for t in turns] == ["pm", "agent"]
    assert turns[0]["content"] == "First try (will fail)"


def test_send_message_multi_turn_preserves_identity_continuity(
    client_with_chat_stub,
) -> None:
    """Identity-continuity invariant: identity_prompt + initial_reaction are
    frozen across multiple chat turns. Only the conversation log grows."""
    client, _chat, agent_repo = client_with_chat_stub
    agent_id, _row = _run_sim_and_pick_agent(client, agent_repo)

    baseline = client.get(f"/agents/{agent_id}").json()
    frozen_identity = baseline["identity_prompt"]
    frozen_reaction = baseline["initial_reaction"]

    for n in range(3):
        resp = client.post(f"/agents/{agent_id}/messages", json={"message": f"Follow-up #{n}"})
        assert resp.status_code == 200

    after = client.get(f"/agents/{agent_id}").json()
    assert after["identity_prompt"] == frozen_identity
    assert after["initial_reaction"] == frozen_reaction
    # 3 PM turns + 3 agent turns
    assert len(after["conversation"]) == 6
