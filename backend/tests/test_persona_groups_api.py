"""End-to-end API tests for `/simulations/{id}/personas/{pid}/messages` (#54).

Pattern lifted from test_agents_api.py:
- Stub LLM avoids real network calls
- A real simulation populates the in-memory agent repo
- Then the persona-group route is exercised against the persisted agents
- The stub LLM is taught to recognize the synthesis call by its system prompt
  and return a counted-shape reply, so the rubric in the service passes
  without hitting the network
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("PYTHIA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))

from pythia_simulator.adapters import llm as llm_mod  # noqa: E402
from pythia_simulator.adapters.repositories import get_in_memory_repos  # noqa: E402
from pythia_simulator.api.deps import get_orchestrator  # noqa: E402
from pythia_simulator.main import app  # noqa: E402
from pythia_simulator.services import agent_chat as agent_chat_mod  # noqa: E402
from pythia_simulator.services import (  # noqa: E402
    persona_group_synthesis as synthesis_mod,
)
from pythia_simulator.services.simulation_orchestrator import (  # noqa: E402
    SimulationOrchestrator,
)
from pythia_simulator.services.simulation_runner import SimulationRunner  # noqa: E402


class _PhaseAwareChat:
    """Stub LLM that returns different canned replies for sim, chat, and
    synthesis phases. The synthesis call is detected by the system prompt
    (which uniquely contains 'N of M' framing language from
    persona_group_synthesis._SYSTEM_PROMPT).

    Reply contracts:
      - Sim phase: the runner's per-agent initial reaction.
      - Chat phase: each persona-group fan-out reply.
      - Synthesis phase: a counted-shape line ("N of N said …") that passes
        the count-accuracy post-process for whatever N the route surfaces.
    """

    def __init__(self) -> None:
        self.reply_for_sim = "I'd give it a shot."
        self.reply_for_chat = "Personal-group reply variant."
        self.synthesis_n: int = 0  # set by the test before posting
        self._phase = "sim"
        self.calls_by_phase: dict[str, int] = {"sim": 0, "chat": 0, "synthesis": 0}
        self.chat_messages: list[list[dict]] = []

    def _enter_chat_phase(self) -> None:
        self._phase = "chat"

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        self.chat_messages.append(messages)
        # Synthesis detection: the synthesis system prompt is the only one
        # that contains the literal "N of M" framing. (We could also detect
        # via temperature=0.1; system-prompt match is sturdier.)
        system_blob = "\n".join(
            m["content"] for m in messages if m["role"] == "system"
        )
        is_synthesis = "N of M" in system_blob and "Lead with" in system_blob
        if is_synthesis:
            self.calls_by_phase["synthesis"] += 1
            n = self.synthesis_n
            return f"{n} of {n} said the proposed change matters for their flow."
        if self._phase == "chat":
            self.calls_by_phase["chat"] += 1
            return self.reply_for_chat
        self.calls_by_phase["sim"] += 1
        return self.reply_for_sim

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        from pythia_simulator.schemas.scoring import (
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
def client_with_persona_group_stub(monkeypatch):
    chat = _PhaseAwareChat()

    monkeypatch.setattr(llm_mod, "get_chat_client", lambda: chat)
    monkeypatch.setattr(agent_chat_mod, "get_chat_client", lambda: chat)
    monkeypatch.setattr(synthesis_mod, "get_chat_client", lambda: chat)

    customer_repo, sim_repo, agent_repo, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    sim_repo._sims.clear()
    agent_repo._agents.clear()

    runner = SimulationRunner(chat_client=chat)

    from pythia_simulator.adapters.feature_pack_loader import FeaturePackLoader
    from pythia_simulator.adapters.persona_loader import PersonaPackLoader
    from pythia_simulator.adapters.r2 import LocalArtifactStore

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
    yield TestClient(app), chat, agent_repo, sim_repo
    app.dependency_overrides.clear()


def _run_sim(client: TestClient) -> str:
    """Submit a small sim, return its sim_id."""
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Surface a one-tap reorder banner for premium subscribers.",
            },
            "population_size": 3,
        },
    )
    assert resp.status_code == 202, resp.text
    return resp.json()["id"]


def _pick_persona(
    client: TestClient, sim_id: str, prefer_multi: bool = False
) -> tuple[str, list[str]]:
    """Return (persona_id, [agent_ids in that persona]) for a persona in the
    sim. With `prefer_multi=True`, returns the persona with the most agents
    (so partial-failure tests can exercise multi-agent fan-out)."""
    detail = client.get(f"/simulations/{sim_id}")
    assert detail.status_code == 200, detail.text
    agent_ids = detail.json()["agent_instance_ids"]
    assert agent_ids
    persona_to_agents: dict[str, list[str]] = {}
    for aid in agent_ids:
        a = client.get(f"/agents/{aid}").json()
        persona_to_agents.setdefault(a["metadata"]["persona_id"], []).append(aid)
    if prefer_multi:
        persona_id = max(persona_to_agents, key=lambda p: len(persona_to_agents[p]))
    else:
        persona_id = next(iter(persona_to_agents))
    return persona_id, persona_to_agents[persona_id]


def test_persona_group_fanout_returns_synthesis_and_per_agent(
    client_with_persona_group_stub,
) -> None:
    """Happy path: fan-out hits each agent in the persona, synthesis runs
    against successful replies, response carries both."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)

    chat._enter_chat_phase()
    chat.synthesis_n = len(agent_ids)

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"message": "If we shipped this, what would change for you on Friday?"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Synthesis is the canned counted-shape line
    n = len(agent_ids)
    assert body["synthesis"] == f"{n} of {n} said the proposed change matters for their flow."

    # Every agent has a per_agent slot with the chat-phase reply
    assert len(body["per_agent"]) == n
    for slot in body["per_agent"]:
        assert slot["agent_id"] in agent_ids
        assert slot["content"] == chat.reply_for_chat
        assert slot["error"] is None

    # LLM call accounting:
    #   - N chat calls (one per agent in the persona)
    #   - 1 synthesis call
    assert chat.calls_by_phase["chat"] == n
    assert chat.calls_by_phase["synthesis"] == 1


def test_persona_group_persists_turns_to_log(
    client_with_persona_group_stub, tmp_path
) -> None:
    """T4: PM + synthesis turns must land in
    customers/<id>/simulations/<sim_id>/persona_groups/<pid>/turns.jsonl."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()
    chat.synthesis_n = len(agent_ids)

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"message": "Hi everyone."},
    )
    assert resp.status_code == 200

    # File on disk
    log_path = (
        _FIXTURE_ROOT
        / "customers"
        / "demo"
        / "simulations"
        / sim_id
        / "persona_groups"
        / persona_id
        / "turns.jsonl"
    )
    assert log_path.exists(), f"expected log at {log_path}"
    lines = [json.loads(ln) for ln in log_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 2
    assert lines[0]["role"] == "pm"
    assert lines[0]["content"] == "Hi everyone."
    assert lines[1]["role"] == "synthesis"
    assert "of" in lines[1]["content"]
    # Synthesis carries the full per_agent payload for self-contained replay
    assert lines[1]["per_agent"] is not None
    assert len(lines[1]["per_agent"]) == len(agent_ids)


def test_persona_group_get_turns_returns_persisted_log(
    client_with_persona_group_stub,
) -> None:
    """GET endpoint replays the log for page load."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()
    chat.synthesis_n = len(agent_ids)

    # Initially empty
    pre = client.get(f"/simulations/{sim_id}/personas/{persona_id}/turns")
    assert pre.status_code == 200
    assert pre.json() == []

    # One exchange
    client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"message": "Question one."},
    )
    # Two exchanges
    client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"message": "Question two."},
    )

    after = client.get(f"/simulations/{sim_id}/personas/{persona_id}/turns")
    assert after.status_code == 200
    turns = after.json()
    assert len(turns) == 4  # pm, synth, pm, synth
    assert [t["role"] for t in turns] == ["pm", "synthesis", "pm", "synthesis"]
    assert turns[0]["content"] == "Question one."
    assert turns[2]["content"] == "Question two."


def test_persona_group_404_for_unknown_simulation(
    client_with_persona_group_stub,
) -> None:
    client, _chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    resp = client.post(
        "/simulations/00000000-0000-0000-0000-000000000000/personas/p_anything/messages",
        json={"message": "hi"},
    )
    assert resp.status_code == 404
    assert "simulation" in resp.json()["detail"].lower()


def test_persona_group_404_for_unknown_persona(
    client_with_persona_group_stub,
) -> None:
    client, _chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    resp = client.post(
        f"/simulations/{sim_id}/personas/p_does_not_exist/messages",
        json={"message": "hi"},
    )
    assert resp.status_code == 404


def test_persona_group_rejects_empty_message(client_with_persona_group_stub) -> None:
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, _ = _pick_persona(client, sim_id)
    pre_total = sum(chat.calls_by_phase.values())

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"message": "    "},
    )
    assert resp.status_code == 400
    # No fan-out, no synthesis
    assert sum(chat.calls_by_phase.values()) == pre_total


def test_persona_group_partial_failure_records_per_agent_error(
    client_with_persona_group_stub, monkeypatch
) -> None:
    """If one agent's LLM call fails, the other agents still reply; synthesis
    runs against the survivors; the failed agent's slot carries `error`."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    # Use a larger population so at least one persona has N>=2 (the demo pack
    # has 6 personas; pop=15 guarantees largest-remainder gives at least one
    # persona two agents).
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Surface a one-tap reorder banner for premium subscribers.",
            },
            "population_size": 15,
        },
    )
    assert resp.status_code == 202, resp.text
    sim_id = resp.json()["id"]
    persona_id, agent_ids = _pick_persona(client, sim_id, prefer_multi=True)

    if len(agent_ids) < 2:
        pytest.skip(
            "Partial-failure semantics need a persona with N>=2; sampling "
            "didn't produce one in this run."
        )

    chat._enter_chat_phase()
    # Synthesis will see len(agent_ids) - 1 successful replies
    chat.synthesis_n = len(agent_ids) - 1

    # Make the FIRST chat-phase call (after sim) raise. Need a counter
    # because the same chat() handles both fan-out replies and the synthesis;
    # we only want to fail one fan-out call.
    original_chat = chat.chat
    state = {"fanout_calls_seen": 0, "failed_agent_index": 0}

    def _selective_boom(messages, max_tokens=4096, temperature=0.0, seed=None):
        system_blob = "\n".join(
            m["content"] for m in messages if m["role"] == "system"
        )
        is_synthesis = "N of M" in system_blob and "Lead with" in system_blob
        if is_synthesis:
            return original_chat(messages, max_tokens, temperature, seed)
        # Fan-out call
        idx = state["fanout_calls_seen"]
        state["fanout_calls_seen"] += 1
        if idx == state["failed_agent_index"]:
            raise TimeoutError("simulated agent LLM timeout")
        return original_chat(messages, max_tokens, temperature, seed)

    monkeypatch.setattr(chat, "chat", _selective_boom)

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"message": "Try this."},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Exactly one per_agent has error set
    failed = [s for s in body["per_agent"] if s["error"] is not None]
    succeeded = [s for s in body["per_agent"] if s["error"] is None]
    assert len(failed) == 1
    assert len(succeeded) == len(agent_ids) - 1
    assert "TimeoutError" in failed[0]["error"]
    assert failed[0]["content"] is None

    # Synthesis ran and matches the survivor count
    n = chat.synthesis_n
    assert body["synthesis"] == f"{n} of {n} said the proposed change matters for their flow."


def test_persona_group_all_failures_returns_502(
    client_with_persona_group_stub, monkeypatch
) -> None:
    """If every fan-out fails, return 502 — don't synthesize against zero."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, _ = _pick_persona(client, sim_id)

    chat._enter_chat_phase()

    original_chat = chat.chat

    def _all_boom(messages, max_tokens=4096, temperature=0.0, seed=None):
        system_blob = "\n".join(
            m["content"] for m in messages if m["role"] == "system"
        )
        if "N of M" in system_blob and "Lead with" in system_blob:
            # Synthesis should not be reached in this test
            return original_chat(messages, max_tokens, temperature, seed)
        raise RuntimeError("simulated total fan-out failure")

    monkeypatch.setattr(chat, "chat", _all_boom)

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"message": "Try this."},
    )
    assert resp.status_code == 502
    assert "All agent replies failed" in resp.json()["detail"]


def test_persona_group_synthesis_failure_returns_200_with_fallback(
    client_with_persona_group_stub, monkeypatch
) -> None:
    """Codex #80 [P1]: when the synthesis LLM call fails AFTER the per-agent
    fan-out has already persisted PM/agent turns, the route must still
    return 200 with a deterministic-fallback synthesis. A 500 here would
    invite a client retry that re-fans-out the same PM message to every
    agent, duplicating their individual conversation logs.

    This test makes synthesis-only LLM calls raise (fan-out calls succeed),
    verifies the route returns 200, verifies the synthesis is the
    deterministic fallback (count-correct), and verifies the per-agent
    individual logs each contain exactly one PM/agent turn pair (no
    duplication from the recovery path)."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()

    original_chat = chat.chat

    def _fail_synthesis_only(messages, max_tokens=4096, temperature=0.0, seed=None):
        system_blob = "\n".join(
            m["content"] for m in messages if m["role"] == "system"
        )
        is_synthesis = "N of M" in system_blob and "Lead with" in system_blob
        if is_synthesis:
            raise TimeoutError("simulated synthesis LLM timeout")
        return original_chat(messages, max_tokens, temperature, seed)

    monkeypatch.setattr(chat, "chat", _fail_synthesis_only)

    pm_msg = "Question that triggers a synthesis failure."
    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"message": pm_msg},
    )
    # Route returns 200 — synthesis degraded to deterministic fallback
    assert resp.status_code == 200, resp.text
    body = resp.json()
    n = len(agent_ids)
    assert body["synthesis"] == f"{n} agents replied — see individual answers below."
    # Per-agent fan-out succeeded
    assert len(body["per_agent"]) == n
    assert all(slot["error"] is None for slot in body["per_agent"])

    # Each individual agent's conversation log has EXACTLY one PM/agent
    # turn pair — no duplication from a client recovery path.
    for aid in agent_ids:
        detail = client.get(f"/agents/{aid}").json()
        turns = detail["conversation"]
        assert len(turns) == 2, f"agent {aid} has {len(turns)} turns; expected 2"
        assert turns[0]["role"] == "pm"
        assert turns[0]["content"] == pm_msg
        assert turns[1]["role"] == "agent"


def test_persona_group_log_persistence_failure_returns_200(
    client_with_persona_group_stub, monkeypatch
) -> None:
    """Codex #80 [P2]: when the persona-group log append raises after the
    per-agent fan-out has already persisted PM/agent turns, the route must
    still return 200. A 500 here would invite the same client-retry
    duplication that the synthesis-failure fix prevents. The audit trail
    degrades; the per-agent logs (source of truth) stay intact."""
    from pythia_simulator.api import persona_groups as route_mod

    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()
    chat.synthesis_n = len(agent_ids)

    # Make the group_log.append always raise. The route MUST swallow these.
    class _BoomLog:
        def append(self, **kwargs):
            raise IOError("simulated R2 hiccup on group-log append")

    monkeypatch.setattr(route_mod, "PersonaGroupLog", lambda store: _BoomLog())

    pm_msg = "Question that triggers a group-log failure."
    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"message": pm_msg},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Synthesis still present (came from successful fan-out)
    assert "of" in body["synthesis"] or "agents" in body["synthesis"]
    # Each agent's individual log has exactly the one PM/agent turn pair
    # — no duplication via client recovery.
    for aid in agent_ids:
        detail = client.get(f"/agents/{aid}").json()
        turns = detail["conversation"]
        assert len(turns) == 2, f"agent {aid} has {len(turns)} turns; expected 2"
        assert turns[0]["content"] == pm_msg


def test_persona_group_individual_chat_log_grew_too(
    client_with_persona_group_stub,
) -> None:
    """Identity-continuity invariant: every fan-out reply goes through
    AgentChatService.send_message, so the same PM/agent turn pair appears in
    each individual agent's conversation log. Drilling into /agents/[id]
    must show that turn."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()
    chat.synthesis_n = len(agent_ids)

    pm_msg = "Did this remind you of anything?"
    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"message": pm_msg},
    )
    assert resp.status_code == 200

    # Every agent's individual conversation log has the PM message + the
    # agent reply (in that order, per AgentChatService.send_message contract).
    for aid in agent_ids:
        detail = client.get(f"/agents/{aid}").json()
        turns = detail["conversation"]
        assert len(turns) == 2, (
            f"agent {aid} should have PM+agent turn; got {turns}"
        )
        assert turns[0]["role"] == "pm"
        assert turns[0]["content"] == pm_msg
        assert turns[1]["role"] == "agent"
        assert turns[1]["content"] == chat.reply_for_chat
