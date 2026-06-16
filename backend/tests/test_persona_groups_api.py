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
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))

from sidira_simulator.adapters import llm as llm_mod  # noqa: E402
from sidira_simulator.adapters.repositories import get_in_memory_repos  # noqa: E402
from sidira_simulator.api.deps import get_orchestrator  # noqa: E402
from sidira_simulator.main import app  # noqa: E402
from sidira_simulator.services import agent_chat as agent_chat_mod  # noqa: E402
from sidira_simulator.services import (  # noqa: E402
    persona_group_collective as collective_mod,
    persona_group_synthesis as synthesis_mod,
)
from sidira_simulator.services.simulation_orchestrator import (  # noqa: E402
    SimulationOrchestrator,
)
from sidira_simulator.services.simulation_runner import SimulationRunner  # noqa: E402


class _PhaseAwareChat:
    """Stub LLM that returns different canned replies for sim, fan-out reply,
    synthesis, and collective-voice phases. Phase detected by the system
    prompt — each service has a uniquely-identifiable system blob.

    Reply contracts:
      - Sim phase: the runner's per-agent initial reaction.
      - Fan-out reply phase: each persona-group fan-out reply.
      - Synthesis phase: a counted-shape line for fan-out mode.
      - Collective phase: a multi-sentence reply that cites every agent's
        label inline so reference-resolution has something to chew on.
    """

    def __init__(self) -> None:
        self.reply_for_sim = "I'd give it a shot."
        self.reply_for_chat = "Persona-group reply variant."
        self.synthesis_n: int = 0  # set by the test before posting fan-out
        # Labels the collective stub will cite inline. Set by the test
        # before posting collective; the stub will produce
        # `[label_a] said X. [label_b] said Y.` etc.
        self.collective_labels: list[str] = []
        self._phase = "sim"
        self.calls_by_phase: dict[str, int] = {
            "sim": 0,
            "chat": 0,
            "synthesis": 0,
            "collective": 0,
        }
        self.chat_messages: list[list[dict]] = []

    def _enter_chat_phase(self) -> None:
        self._phase = "chat"

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        self.chat_messages.append(messages)
        system_blob = "\n".join(m["content"] for m in messages if m["role"] == "system")
        # Phase detection — each service has a distinctive system-prompt
        # fingerprint. Sturdier than temperature or message-count heuristics.
        is_synthesis = "N of M" in system_blob and "Lead with" in system_blob
        is_collective = "speak in the voice of a PERSONA GROUP" in system_blob
        if is_collective:
            self.calls_by_phase["collective"] += 1
            return _format_collective_reply(self.collective_labels)
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


def _format_collective_reply(labels: list[str]) -> str:
    """Build a deterministic collective-voice reply that cites every
    `labels` token inline. Tests use this to verify reference resolution."""
    if not labels:
        return (
            "We don't have enough signal in our reactions to answer that — "
            "try asking about the hypothesis itself."
        )
    parts = [f"[{lbl}] would say their take." for lbl in labels]
    return "As a group, here is what each of us thinks: " + " ".join(parts)


@pytest.fixture
def client_with_persona_group_stub(monkeypatch):
    chat = _PhaseAwareChat()

    monkeypatch.setattr(llm_mod, "get_chat_client", lambda model_id=None: chat)
    monkeypatch.setattr(agent_chat_mod, "get_chat_client", lambda model_id=None: chat)
    monkeypatch.setattr(synthesis_mod, "get_chat_client", lambda model_id=None: chat)
    monkeypatch.setattr(collective_mod, "get_chat_client", lambda model_id=None: chat)

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
    yield TestClient(app), chat, agent_repo, sim_repo
    app.dependency_overrides.clear()


def _run_sim(client: TestClient, model_id: str | None = None) -> str:
    """Submit a small sim, return its sim_id."""
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
    return resp.json()["id"]


def _run_ab_sim(client: TestClient, population_size: int = 6) -> str:
    """Submit a 50/50 A/B sim, return its sim_id."""
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Surface a one-tap reorder banner for premium subscribers.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": population_size,
            "arm_split": {"treatment_fraction": 0.5},
            "run_as_generic_reception": True,
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


def _pick_ab_persona(client: TestClient, sim_id: str) -> tuple[str, dict[str, list[str]]]:
    """Return a persona represented in both A/B arms."""
    detail = client.get(f"/simulations/{sim_id}")
    assert detail.status_code == 200, detail.text
    agent_ids = detail.json()["agent_instance_ids"]
    assert agent_ids
    by_persona: dict[str, dict[str, list[str]]] = {}
    for aid in agent_ids:
        agent = client.get(f"/agents/{aid}").json()["metadata"]
        persona_arms = by_persona.setdefault(
            agent["persona_id"],
            {"treatment": [], "control": []},
        )
        arm = agent["arm"]
        assert arm in ("treatment", "control")
        persona_arms[arm].append(aid)

    for persona_id, arms in by_persona.items():
        if arms["treatment"] and arms["control"]:
            return persona_id, arms
    raise AssertionError(f"no persona had both arms: {by_persona}")


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
        json={
            "mode": "individual",
            "message": "If we shipped this, what would change for you on Friday?",
        },
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


def test_persona_group_fanout_uses_simulation_model_for_reply_and_synthesis(
    client_with_persona_group_stub,
    monkeypatch,
) -> None:
    """#103: individual fan-out replies and synthesis stay on the run model."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    requested_models: list[str | None] = []

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")

    def fake_get_chat_client(model_id: str | None = None):
        requested_models.append(model_id)
        return chat

    monkeypatch.setattr(agent_chat_mod, "get_chat_client", fake_get_chat_client)
    monkeypatch.setattr(synthesis_mod, "get_chat_client", fake_get_chat_client)

    sim_id = _run_sim(client, model_id="claude-sonnet-4-6")
    persona_id, agent_ids = _pick_persona(client, sim_id)

    chat._enter_chat_phase()
    chat.synthesis_n = len(agent_ids)

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "individual", "message": "Would this still work?"},
    )

    assert resp.status_code == 200, resp.text
    assert requested_models == ["claude-sonnet-4-6", "claude-sonnet-4-6"]


def test_persona_group_persists_turns_to_log(client_with_persona_group_stub, tmp_path) -> None:
    """T4: PM + synthesis turns must land in
    customers/<id>/simulations/<sim_id>/persona_groups/<pid>/turns.jsonl."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()
    chat.synthesis_n = len(agent_ids)

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "individual", "message": "Hi everyone."},
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
        json={"mode": "individual", "message": "Question one."},
    )
    # Two exchanges
    client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "individual", "message": "Question two."},
    )

    after = client.get(f"/simulations/{sim_id}/personas/{persona_id}/turns")
    assert after.status_code == 200
    turns = after.json()
    assert len(turns) == 4  # pm, synth, pm, synth
    assert [t["role"] for t in turns] == ["pm", "synthesis", "pm", "synthesis"]
    assert turns[0]["content"] == "Question one."
    assert turns[2]["content"] == "Question two."


def test_persona_group_ab_arm_query_scopes_fanout_and_log(
    client_with_persona_group_stub,
) -> None:
    """#98: `?arm=` creates independent A/B persona-group rooms."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_ab_sim(client)
    persona_id, arms = _pick_ab_persona(client, sim_id)

    chat._enter_chat_phase()
    chat.synthesis_n = len(arms["treatment"])
    treatment = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages?arm=treatment",
        json={"mode": "individual", "message": "Treatment-only question."},
    )
    assert treatment.status_code == 200, treatment.text
    body = treatment.json()
    assert {slot["agent_id"] for slot in body["per_agent"]} == set(arms["treatment"])

    treatment_turns = client.get(f"/simulations/{sim_id}/personas/{persona_id}/turns?arm=treatment")
    assert treatment_turns.status_code == 200, treatment_turns.text
    assert [t["content"] for t in treatment_turns.json()] == [
        "Treatment-only question.",
        f"{len(arms['treatment'])} of {len(arms['treatment'])} said the proposed change matters for their flow.",
    ]

    control_turns = client.get(f"/simulations/{sim_id}/personas/{persona_id}/turns?arm=control")
    assert control_turns.status_code == 200, control_turns.text
    assert control_turns.json() == []


def test_persona_group_ab_requires_arm_for_messages_and_turns(
    client_with_persona_group_stub,
) -> None:
    """#98: A/B persona rooms must never fall back to an unscoped room."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_ab_sim(client)
    persona_id, _arms = _pick_ab_persona(client, sim_id)

    turns = client.get(f"/simulations/{sim_id}/personas/{persona_id}/turns")
    assert turns.status_code == 400
    assert "arm" in turns.json()["detail"]

    chat._enter_chat_phase()
    before = chat.calls_by_phase.copy()
    msg = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "individual", "message": "This should not fan out."},
    )
    assert msg.status_code == 400
    assert "arm" in msg.json()["detail"]
    assert chat.calls_by_phase == before


def test_persona_group_404_for_unknown_simulation(
    client_with_persona_group_stub,
) -> None:
    client, _chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    resp = client.post(
        "/simulations/00000000-0000-0000-0000-000000000000/personas/p_anything/messages",
        json={"mode": "individual", "message": "hi"},
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
        json={"mode": "individual", "message": "hi"},
    )
    assert resp.status_code == 404


def test_persona_group_rejects_empty_message(client_with_persona_group_stub) -> None:
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, _ = _pick_persona(client, sim_id)
    pre_total = sum(chat.calls_by_phase.values())

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "individual", "message": "    "},
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
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 15,
            "run_as_generic_reception": True,
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
        system_blob = "\n".join(m["content"] for m in messages if m["role"] == "system")
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
        json={"mode": "individual", "message": "Try this."},
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
        system_blob = "\n".join(m["content"] for m in messages if m["role"] == "system")
        if "N of M" in system_blob and "Lead with" in system_blob:
            # Synthesis should not be reached in this test
            return original_chat(messages, max_tokens, temperature, seed)
        raise RuntimeError("simulated total fan-out failure")

    monkeypatch.setattr(chat, "chat", _all_boom)

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "individual", "message": "Try this."},
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
        system_blob = "\n".join(m["content"] for m in messages if m["role"] == "system")
        is_synthesis = "N of M" in system_blob and "Lead with" in system_blob
        if is_synthesis:
            raise TimeoutError("simulated synthesis LLM timeout")
        return original_chat(messages, max_tokens, temperature, seed)

    monkeypatch.setattr(chat, "chat", _fail_synthesis_only)

    pm_msg = "Question that triggers a synthesis failure."
    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "individual", "message": pm_msg},
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
    from sidira_simulator.api import persona_groups as route_mod

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
        json={"mode": "individual", "message": pm_msg},
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
        json={"mode": "individual", "message": pm_msg},
    )
    assert resp.status_code == 200

    # Every agent's individual conversation log has the PM message + the
    # agent reply (in that order, per AgentChatService.send_message contract).
    for aid in agent_ids:
        detail = client.get(f"/agents/{aid}").json()
        turns = detail["conversation"]
        assert len(turns) == 2, f"agent {aid} should have PM+agent turn; got {turns}"
        assert turns[0]["role"] == "pm"
        assert turns[0]["content"] == pm_msg
        assert turns[1]["role"] == "agent"
        assert turns[1]["content"] == chat.reply_for_chat


# ──────────────────────────────────────────────────────────────────────
# Collective mode (#54 collective)
# ──────────────────────────────────────────────────────────────────────


def test_collective_default_when_mode_omitted(client_with_persona_group_stub) -> None:
    """Per spec Surface 2: when the request omits `mode`, default is collective."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()
    # Set the collective stub to cite every agent in the group
    chat.collective_labels = (
        [persona_id]
        if len(agent_ids) == 1
        else [f"{persona_id}_{chr(ord('a') + i)}" for i in range(len(agent_ids))]
    )

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"message": "What's the consensus here?"},  # NO mode field
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["role"] == "collective"
    assert body["content"] is not None
    assert body["references"] is not None
    # Synthesis/per_agent fields are absent for collective mode
    assert body.get("synthesis") is None
    assert body.get("per_agent") is None
    # Exactly ONE LLM call for collective mode (one synthesis-ish call,
    # not N fan-out + 1 synthesis)
    assert chat.calls_by_phase["collective"] == 1
    assert chat.calls_by_phase["chat"] == 0
    assert chat.calls_by_phase["synthesis"] == 0


def test_collective_uses_simulation_model(client_with_persona_group_stub, monkeypatch) -> None:
    """#103: collective-mode chat stays on the model selected for the run."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    requested_models: list[str | None] = []

    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")

    def fake_get_chat_client(model_id: str | None = None):
        requested_models.append(model_id)
        return chat

    monkeypatch.setattr(collective_mod, "get_chat_client", fake_get_chat_client)

    sim_id = _run_sim(client, model_id="gpt-5.4-mini")
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()
    chat.collective_labels = (
        [persona_id]
        if len(agent_ids) == 1
        else [f"{persona_id}_{chr(ord('a') + i)}" for i in range(len(agent_ids))]
    )

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "collective", "message": "What's the consensus here?"},
    )

    assert resp.status_code == 200, resp.text
    assert requested_models == ["gpt-5.4-mini"]


def test_collective_resolves_inline_labels_to_agent_ids(
    client_with_persona_group_stub,
) -> None:
    """The `[label]` tokens in the collective prose must resolve to real
    agent_ids in the `references` array so the frontend can linkify them."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()

    # When N=1, _build_labels uses persona_id directly. Otherwise it appends
    # _a / _b / _c suffixes.
    if len(agent_ids) == 1:
        expected_labels = [persona_id]
    else:
        expected_labels = [f"{persona_id}_{chr(ord('a') + i)}" for i in range(len(agent_ids))]
    chat.collective_labels = expected_labels

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "collective", "message": "Who reacted negatively?"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Every cited label is in references mapped to a real agent_id
    refs = body["references"]
    assert len(refs) == len(expected_labels)
    ref_labels = {r["agent_label"] for r in refs}
    assert ref_labels == set(expected_labels)
    for r in refs:
        assert r["agent_id"] in agent_ids
    # Every [label] token in content matches a reference
    for lbl in expected_labels:
        assert f"[{lbl}]" in body["content"]


def test_collective_hallucinated_label_is_dropped_from_references(
    client_with_persona_group_stub,
) -> None:
    """If the LLM hallucinates a label not in the input (e.g. 'rivka_005'
    when there are only 3 agents), the prose carries the token verbatim but
    `references` does NOT include it. The frontend renders unresolved
    tokens as plain text — no broken links."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()

    # Cite one real label + one hallucinated label
    real_label = persona_id if len(agent_ids) == 1 else f"{persona_id}_a"
    chat.collective_labels = [real_label, "made_up_agent_xyz"]

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "collective", "message": "Anyone surprised you?"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Both labels appear inline in the prose...
    assert f"[{real_label}]" in body["content"]
    assert "[made_up_agent_xyz]" in body["content"]
    # ...but only the real one is in references
    assert len(body["references"]) == 1
    assert body["references"][0]["agent_label"] == real_label


def test_collective_persists_pm_and_collective_turn_to_log(
    client_with_persona_group_stub,
) -> None:
    """The collective turn (with full `references` payload) must land in
    turns.jsonl so the audit trail is self-contained."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()
    real_label = persona_id if len(agent_ids) == 1 else f"{persona_id}_a"
    chat.collective_labels = [real_label]

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "collective", "message": "Quick question."},
    )
    assert resp.status_code == 200

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
    assert log_path.exists()
    lines = [json.loads(ln) for ln in log_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 2
    assert lines[0]["role"] == "pm"
    assert lines[0]["content"] == "Quick question."
    assert lines[1]["role"] == "collective"
    assert lines[1]["references"] is not None
    assert lines[1]["references"][0]["agent_label"] == real_label


def test_collective_does_not_touch_individual_agent_logs(
    client_with_persona_group_stub,
) -> None:
    """Identity-continuity caveat (spec § collective mode): a collective
    turn does NOT append to any individual agent's conversation log. The
    collective voice is a meta layer; the individuals have not been
    independently re-prompted. Drill-down lands on Surface 3 with whatever
    turns the agent ACTUALLY has — none here."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()
    chat.collective_labels = [persona_id] if len(agent_ids) == 1 else [f"{persona_id}_a"]

    # Baseline: every agent has zero conversation turns post-sim
    for aid in agent_ids:
        assert client.get(f"/agents/{aid}").json()["conversation"] == []

    client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "collective", "message": "Collective question."},
    )

    # Still zero — collective mode is meta-only
    for aid in agent_ids:
        assert (
            client.get(f"/agents/{aid}").json()["conversation"] == []
        ), f"collective should not touch agent {aid}'s individual log"


def test_collective_multi_turn_passes_prior_conversation_to_llm(
    client_with_persona_group_stub,
) -> None:
    """The collective LLM call must see prior PM + collective turns so
    multi-turn collective chats stay coherent. We assert this by checking
    that the 2nd POST's user-message blob includes content from the 1st turn."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()
    chat.collective_labels = [persona_id] if len(agent_ids) == 1 else [f"{persona_id}_a"]

    # Turn 1
    client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "collective", "message": "TURN_ONE_QUESTION"},
    )
    # Turn 2 — should include turn-1 context in the LLM input
    client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "collective", "message": "TURN_TWO_QUESTION"},
    )

    # The collective LLM was called twice. The 2nd call's messages must
    # include the 1st PM turn's content (carried via prior_conversation).
    collective_calls = [
        msgs
        for msgs in chat.chat_messages
        if any(
            "speak in the voice of a PERSONA GROUP" in m.get("content", "")
            for m in msgs
            if m["role"] == "system"
        )
    ]
    assert len(collective_calls) == 2
    second_user_msg = next(m["content"] for m in collective_calls[1] if m["role"] == "user")
    assert (
        "TURN_ONE_QUESTION" in second_user_msg
    ), "2nd call must carry prior PM turn into the LLM input"


def test_collective_after_individual_pairs_prior_turns(
    client_with_persona_group_stub,
) -> None:
    """Codex #82 round-1 P2: when the user mixes modes (individual fan-out
    first, then collective), the collective LLM must see the PAIRED prior
    turns — the PM question AND its synthesis reply — not a dangling
    unanswered PM. Otherwise multi-turn collective drift becomes confused
    multi-turn collective garbage."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()
    chat.synthesis_n = len(agent_ids)
    chat.collective_labels = [persona_id] if len(agent_ids) == 1 else [f"{persona_id}_a"]

    # Turn 1: individual fan-out
    client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "individual", "message": "INDIVIDUAL_TURN_QUESTION"},
    )
    # Turn 2: collective — must see the synthesis reply, not just the PM
    client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "collective", "message": "COLLECTIVE_TURN_QUESTION"},
    )

    # The collective LLM call's user message must include BOTH the prior
    # PM question AND the synthesis reply that answered it.
    collective_calls = [
        msgs
        for msgs in chat.chat_messages
        if any(
            "speak in the voice of a PERSONA GROUP" in m.get("content", "")
            for m in msgs
            if m["role"] == "system"
        )
    ]
    assert len(collective_calls) == 1
    user_msg = next(m["content"] for m in collective_calls[0] if m["role"] == "user")
    assert "INDIVIDUAL_TURN_QUESTION" in user_msg, "prior PM must appear"
    # Synthesis reply must appear (paired with the PM); the stub's
    # synthesis reply contains "said the proposed change matters for their flow".
    assert (
        "said the proposed change matters" in user_msg
    ), "prior synthesis reply must be paired with its PM, not filtered out"


def test_collective_drops_orphan_pm_with_no_reply(
    client_with_persona_group_stub, monkeypatch
) -> None:
    """If a PM turn lives in the log without a following reply (audit-trail
    append failed mid-turn — rare but possible), it must be DROPPED from
    the collective LLM input rather than passed in as an unanswered question."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, agent_ids = _pick_persona(client, sim_id)
    chat._enter_chat_phase()

    # Manually inject an orphan PM into the group log (bypassing the route)
    # to simulate the partial-append failure mode.
    from sidira_simulator.adapters.r2 import LocalArtifactStore
    from sidira_simulator.memory.persona_group_log import PersonaGroupLog
    from sidira_simulator.schemas.persona_group import (
        PersonaGroupRole,
        PersonaGroupTurn,
    )
    from datetime import datetime, timezone

    store = LocalArtifactStore(_FIXTURE_ROOT)
    log = PersonaGroupLog(store)
    log.append(
        customer_id="demo",
        simulation_id=sim_id,
        persona_id=persona_id,
        turn=PersonaGroupTurn(
            role=PersonaGroupRole.PM,
            content="ORPHAN_PM_NO_REPLY",
            created_at=datetime.now(timezone.utc),
        ),
    )

    chat.collective_labels = [persona_id] if len(agent_ids) == 1 else [f"{persona_id}_a"]

    client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "collective", "message": "live question"},
    )

    collective_calls = [
        msgs
        for msgs in chat.chat_messages
        if any(
            "speak in the voice of a PERSONA GROUP" in m.get("content", "")
            for m in msgs
            if m["role"] == "system"
        )
    ]
    assert len(collective_calls) == 1
    user_msg = next(m["content"] for m in collective_calls[0] if m["role"] == "user")
    assert "ORPHAN_PM_NO_REPLY" not in user_msg, (
        "an orphan PM with no reply must be dropped, not passed in as "
        "an unanswered prior question"
    )


def test_collective_surfaces_unavailable_agents_on_load_failure(
    client_with_persona_group_stub, monkeypatch
) -> None:
    """Codex #82 round-1 P2: a partial agent-load failure must surface in
    `unavailable_agents` so the frontend can warn 'answer reflects N-1 of N
    agents'. Silently shrinking the collective would let the LLM confidently
    speak FOR a group that's smaller than the user thinks."""
    # Run a sim with multiple agents in one persona
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Surface a one-tap reorder banner for premium subscribers.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 15,
            "run_as_generic_reception": True,
        },
    )
    sim_id = resp.json()["id"]
    persona_id, agent_ids = _pick_persona(client, sim_id, prefer_multi=True)
    if len(agent_ids) < 2:
        pytest.skip("need a persona with N>=2 to exercise partial load failure")

    chat._enter_chat_phase()
    chat.collective_labels = [
        persona_id if len(agent_ids) == 1 else f"{persona_id}_{chr(ord('a') + i)}"
        for i in range(len(agent_ids))
    ]

    # Monkeypatch AgentMemory.load to fail for ONE specific agent.
    from sidira_simulator.memory.agent_memory import AgentMemory

    target_failed_id = agent_ids[0]
    original_load = AgentMemory.load

    def _selective_load(self, metadata):
        if metadata.id == target_failed_id:
            raise IOError(f"simulated R2 read failure on {target_failed_id}")
        return original_load(self, metadata)

    monkeypatch.setattr(AgentMemory, "load", _selective_load)

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "collective", "message": "What do you all think?"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Collective ran against the survivors
    assert body["role"] == "collective"
    # But unavailable_agents surfaces the one we lost
    assert body["unavailable_agents"] is not None
    assert len(body["unavailable_agents"]) == 1
    unavail = body["unavailable_agents"][0]
    assert unavail["agent_id"] == target_failed_id
    assert "IOError" in unavail["error"] or "OSError" in unavail["error"]


def test_collective_all_loads_fail_returns_502(client_with_persona_group_stub, monkeypatch) -> None:
    """If EVERY agent load fails, route returns 502 — don't synthesize over
    a phantom group."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, _ = _pick_persona(client, sim_id)
    chat._enter_chat_phase()

    from sidira_simulator.memory.agent_memory import AgentMemory

    def _always_fail(self, metadata):
        raise IOError("simulated total store failure")

    monkeypatch.setattr(AgentMemory, "load", _always_fail)

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "collective", "message": "anything"},
    )
    assert resp.status_code == 502
    assert "Could not load any agent identities" in resp.json()["detail"]


def test_collective_llm_failure_returns_200_with_fallback(
    client_with_persona_group_stub, monkeypatch
) -> None:
    """Service contract: collective LLM exception must not 500 the route.
    Degrades to deterministic fallback + empty references. Same lesson
    as #80 round-1 P1 — never invite a client retry on irreversible
    upstream work (the PM turn is already implied; let the user see a
    safe-default reply and ask again)."""
    client, chat, _agent_repo, _sim_repo = client_with_persona_group_stub
    sim_id = _run_sim(client)
    persona_id, _ = _pick_persona(client, sim_id)
    chat._enter_chat_phase()

    original_chat = chat.chat

    def _fail_collective_only(messages, max_tokens=4096, temperature=0.0, seed=None):
        system_blob = "\n".join(m["content"] for m in messages if m["role"] == "system")
        if "speak in the voice of a PERSONA GROUP" in system_blob:
            raise TimeoutError("simulated collective LLM timeout")
        return original_chat(messages, max_tokens, temperature, seed)

    monkeypatch.setattr(chat, "chat", _fail_collective_only)

    resp = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": "collective", "message": "anything"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["role"] == "collective"
    # Deterministic-fallback prose
    assert "collective voice is unavailable" in body["content"]
    # No references — the fallback doesn't cite anyone
    assert body["references"] == []
