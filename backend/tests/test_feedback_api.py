"""End-to-end API tests for calibration feedback (#56).

Both POST endpoints + the GET joins (per-agent + persona-group). Reuses
the stub-LLM pattern from test_persona_groups_api so each test starts
with a real-shaped sim + persona-group conversation populated.
"""

from __future__ import annotations

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
    persona_group_collective as collective_mod,
    persona_group_synthesis as synthesis_mod,
)
from pythia_simulator.services.simulation_orchestrator import (  # noqa: E402
    SimulationOrchestrator,
)
from pythia_simulator.services.simulation_runner import SimulationRunner  # noqa: E402

from test_persona_groups_api import _PhaseAwareChat  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    chat = _PhaseAwareChat()
    monkeypatch.setattr(llm_mod, "get_chat_client", lambda: chat)
    monkeypatch.setattr(agent_chat_mod, "get_chat_client", lambda: chat)
    monkeypatch.setattr(synthesis_mod, "get_chat_client", lambda: chat)
    monkeypatch.setattr(collective_mod, "get_chat_client", lambda: chat)

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
    yield TestClient(app), chat
    app.dependency_overrides.clear()


def _run_sim_and_send_one_agent_turn(client: TestClient, chat: _PhaseAwareChat):
    """Submit a small sim, send ONE PM turn on the first agent so it has
    a conversation log with two turns (pm + agent). Return (sim_id, agent_id)."""
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Surface a one-tap reorder banner.",
            },
            "population_size": 3,
        },
    )
    sim_id = resp.json()["id"]
    agent_ids = client.get(f"/simulations/{sim_id}").json()["agent_instance_ids"]
    agent_id = agent_ids[0]
    chat._enter_chat_phase()
    client.post(
        f"/agents/{agent_id}/messages",
        json={"message": "follow-up question"},
    )
    return sim_id, agent_id


# ──────────────────────────────────────────────────────────────────────
# Agent-turn feedback
# ──────────────────────────────────────────────────────────────────────


def test_agent_feedback_thumb_up_round_trips(client) -> None:
    """POST 👍 → GET /agents/{id} surfaces realistic_flag=True on that turn."""
    c, chat = client
    sim_id, agent_id = _run_sim_and_send_one_agent_turn(c, chat)
    # Conversation has 2 turns: pm (index 0), agent (index 1). Thumb the agent reply.
    resp = c.post(
        f"/agents/{agent_id}/turns/1/feedback",
        json={"realistic_flag": True},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["target_kind"] == "agent"
    assert body["target_id"] == agent_id
    assert body["turn_index"] == 1
    assert body["realistic_flag"] is True

    agent = c.get(f"/agents/{agent_id}").json()
    assert agent["conversation"][0]["role"] == "pm"
    assert agent["conversation"][0].get("realistic_flag") is None
    assert agent["conversation"][1]["role"] == "agent"
    assert agent["conversation"][1]["realistic_flag"] is True


def test_agent_feedback_clear_overwrites_thumb(client) -> None:
    """👍 then clear → GET shows None, not stale True."""
    c, chat = client
    _sim_id, agent_id = _run_sim_and_send_one_agent_turn(c, chat)
    c.post(f"/agents/{agent_id}/turns/1/feedback", json={"realistic_flag": True})
    c.post(f"/agents/{agent_id}/turns/1/feedback", json={"realistic_flag": None})

    agent = c.get(f"/agents/{agent_id}").json()
    assert agent["conversation"][1]["realistic_flag"] is None


def test_agent_feedback_thumb_down_overrides_thumb_up(client) -> None:
    """👍 → 👎 → GET shows 👎 (latest wins)."""
    c, chat = client
    _sim_id, agent_id = _run_sim_and_send_one_agent_turn(c, chat)
    c.post(f"/agents/{agent_id}/turns/1/feedback", json={"realistic_flag": True})
    c.post(f"/agents/{agent_id}/turns/1/feedback", json={"realistic_flag": False})

    agent = c.get(f"/agents/{agent_id}").json()
    assert agent["conversation"][1]["realistic_flag"] is False


def test_agent_feedback_404_for_unknown_agent(client) -> None:
    c, _chat = client
    resp = c.post(
        "/agents/00000000-0000-0000-0000-000000000000/turns/0/feedback",
        json={"realistic_flag": True},
    )
    assert resp.status_code == 404


def test_agent_feedback_404_for_out_of_range_turn_index(client) -> None:
    c, chat = client
    _sim_id, agent_id = _run_sim_and_send_one_agent_turn(c, chat)
    # Conversation has 2 turns (index 0 + 1). Index 5 is out of range.
    resp = c.post(
        f"/agents/{agent_id}/turns/5/feedback",
        json={"realistic_flag": True},
    )
    assert resp.status_code == 404
    assert "out of range" in resp.json()["detail"]


def test_agent_feedback_rejects_pm_turn(client) -> None:
    """Codex #85 round-1 P2: same contract as the persona-group route —
    PM turns aren't valid feedback targets (no LLM-generated content to
    calibrate). The route must 400 if turn_index points at a PM turn."""
    c, chat = client
    _sim_id, agent_id = _run_sim_and_send_one_agent_turn(c, chat)
    # Conversation is [pm (0), agent (1)]. Thumb the PM turn → 400.
    resp = c.post(
        f"/agents/{agent_id}/turns/0/feedback",
        json={"realistic_flag": True},
    )
    assert resp.status_code == 400
    assert "PM turn" in resp.json()["detail"]


def test_agent_feedback_concurrent_thumbs_all_persisted(client) -> None:
    """Codex #85 round-1 P2: R2 read-modify-write append on a hot
    feedback log can lose events under concurrent POSTs. Per-sim lock
    in the route serializes them. Fire several concurrent thumb-flip
    POSTs and verify EVERY event is in the audit history (Phase 9 reads
    the full sequence, not just latest)."""
    import asyncio
    import httpx

    c, chat = client
    _sim_id, agent_id = _run_sim_and_send_one_agent_turn(c, chat)
    # Send many concurrent POSTs flipping the thumb. With the per-sim
    # lock they serialize cleanly; without it the R2 race would drop
    # entries.
    n = 12

    async def _hit(flag: bool):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.post(
                f"/agents/{agent_id}/turns/1/feedback",
                json={"realistic_flag": flag},
            )
            assert r.status_code == 200

    async def _run() -> None:
        await asyncio.gather(*[_hit(i % 2 == 0) for i in range(n)])

    asyncio.get_event_loop().run_until_complete(_run())

    # Read raw events from the feedback log to verify all were persisted.
    from pythia_simulator.adapters.r2 import LocalArtifactStore
    from pythia_simulator.memory.feedback_log import FeedbackLog

    store = LocalArtifactStore(_FIXTURE_ROOT)
    flog = FeedbackLog(store)
    events = flog.read_all(customer_id="demo", simulation_id=_sim_id)
    agent_events = [e for e in events if e.target_kind.value == "agent" and e.target_id == agent_id]
    assert len(agent_events) == n, (
        f"expected {n} feedback events under per-sim lock, got "
        f"{len(agent_events)} — concurrent appends were lost"
    )


def test_agent_feedback_400_for_negative_turn_index(client) -> None:
    c, chat = client
    _sim_id, agent_id = _run_sim_and_send_one_agent_turn(c, chat)
    resp = c.post(
        f"/agents/{agent_id}/turns/-1/feedback",
        json={"realistic_flag": True},
    )
    # FastAPI path validation may convert to 422, but our handler
    # additionally guards with an explicit 400 for negative values.
    # Either is acceptable; both are client errors.
    assert resp.status_code in (400, 422)


# ──────────────────────────────────────────────────────────────────────
# Persona-group feedback
# ──────────────────────────────────────────────────────────────────────


def _send_group_message(
    c: TestClient, sim_id: str, persona_id: str, mode: str, chat: _PhaseAwareChat
):
    """Post one persona-group turn so the log has [pm, reply] entries."""
    if mode == "collective":
        chat.collective_labels = [persona_id]
    else:
        chat.synthesis_n = 1
    c.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages",
        json={"mode": mode, "message": "live question"},
    )


def _pick_persona(c: TestClient, sim_id: str) -> tuple[str, list[str]]:
    detail = c.get(f"/simulations/{sim_id}")
    agent_ids = detail.json()["agent_instance_ids"]
    persona_to_agents: dict[str, list[str]] = {}
    for aid in agent_ids:
        a = c.get(f"/agents/{aid}").json()
        persona_to_agents.setdefault(a["metadata"]["persona_id"], []).append(aid)
    persona_id = next(iter(persona_to_agents))
    return persona_id, persona_to_agents[persona_id]


def _run_sim_and_send_group_turn(
    client: TestClient, chat: _PhaseAwareChat, mode: str = "collective"
):
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Surface a one-tap reorder banner.",
            },
            "population_size": 3,
        },
    )
    sim_id = resp.json()["id"]
    persona_id, _ = _pick_persona(client, sim_id)
    chat._enter_chat_phase()
    _send_group_message(client, sim_id, persona_id, mode, chat)
    return sim_id, persona_id


def _run_ab_sim_pick_persona_and_send_group_turn(
    client: TestClient,
    chat: _PhaseAwareChat,
    mode: str = "collective",
):
    """Create a 50/50 A/B sim and send one turn to each arm-scoped room."""
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Surface a one-tap reorder banner.",
            },
            "population_size": 6,
            "arm_split": {"treatment_fraction": 0.5},
        },
    )
    sim_id = resp.json()["id"]

    detail = client.get(f"/simulations/{sim_id}")
    agent_ids = detail.json()["agent_instance_ids"]
    by_persona: dict[str, dict[str, int]] = {}
    for aid in agent_ids:
        agent = client.get(f"/agents/{aid}").json()["metadata"]
        arm = agent["arm"]
        assert arm in ("treatment", "control")
        arms = by_persona.setdefault(agent["persona_id"], {"treatment": 0, "control": 0})
        arms[arm] += 1

    persona_id = next(
        pid for pid, arms in by_persona.items() if arms["treatment"] > 0 and arms["control"] > 0
    )

    chat._enter_chat_phase()
    if mode == "collective":
        chat.collective_labels = [persona_id]
    else:
        chat.synthesis_n = by_persona[persona_id]["treatment"]
    treatment = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages?arm=treatment",
        json={"mode": mode, "message": "treatment question"},
    )
    assert treatment.status_code == 200, treatment.text

    if mode == "collective":
        chat.collective_labels = [persona_id]
    else:
        chat.synthesis_n = by_persona[persona_id]["control"]
    control = client.post(
        f"/simulations/{sim_id}/personas/{persona_id}/messages?arm=control",
        json={"mode": mode, "message": "control question"},
    )
    assert control.status_code == 200, control.text
    return sim_id, persona_id


def test_persona_group_feedback_on_collective_turn_round_trips(client) -> None:
    """POST 👍 on the collective turn (index 1) → GET turns surfaces it."""
    c, chat = client
    sim_id, persona_id = _run_sim_and_send_group_turn(c, chat, mode="collective")
    resp = c.post(
        f"/simulations/{sim_id}/personas/{persona_id}/turns/1/feedback",
        json={"realistic_flag": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["target_kind"] == "persona_group"
    assert body["target_id"] == f"{sim_id}/{persona_id}"

    turns = c.get(f"/simulations/{sim_id}/personas/{persona_id}/turns").json()
    assert turns[0]["role"] == "pm"
    assert turns[0]["realistic_flag"] is None
    assert turns[1]["role"] == "collective"
    assert turns[1]["realistic_flag"] is True


def test_persona_group_feedback_on_synthesis_turn_round_trips(client) -> None:
    """Same end-to-end against a synthesis (fan-out) turn — the feedback
    surface is role-agnostic; only the rendered turn carries the role."""
    c, chat = client
    sim_id, persona_id = _run_sim_and_send_group_turn(c, chat, mode="individual")
    c.post(
        f"/simulations/{sim_id}/personas/{persona_id}/turns/1/feedback",
        json={"realistic_flag": False},
    )
    turns = c.get(f"/simulations/{sim_id}/personas/{persona_id}/turns").json()
    assert turns[1]["role"] == "synthesis"
    assert turns[1]["realistic_flag"] is False


def test_persona_group_feedback_rejects_pm_turn(client) -> None:
    """PM turns (index 0) aren't valid targets — nothing LLM-generated to
    calibrate. Reject explicitly so a buggy client can't pollute the log."""
    c, chat = client
    sim_id, persona_id = _run_sim_and_send_group_turn(c, chat)
    resp = c.post(
        f"/simulations/{sim_id}/personas/{persona_id}/turns/0/feedback",
        json={"realistic_flag": True},
    )
    assert resp.status_code == 400
    assert "PM turn" in resp.json()["detail"]


def test_persona_group_feedback_404_for_unknown_simulation(client) -> None:
    c, _chat = client
    resp = c.post(
        "/simulations/00000000-0000-0000-0000-000000000000/personas/p/turns/0/feedback",
        json={"realistic_flag": True},
    )
    assert resp.status_code == 404


def test_persona_group_feedback_404_for_unknown_persona(client) -> None:
    c, chat = client
    sim_id, _ = _run_sim_and_send_group_turn(c, chat)
    resp = c.post(
        f"/simulations/{sim_id}/personas/p_does_not_exist/turns/0/feedback",
        json={"realistic_flag": True},
    )
    assert resp.status_code == 404


def test_persona_group_feedback_404_for_out_of_range_turn(client) -> None:
    c, chat = client
    sim_id, persona_id = _run_sim_and_send_group_turn(c, chat)
    resp = c.post(
        f"/simulations/{sim_id}/personas/{persona_id}/turns/99/feedback",
        json={"realistic_flag": True},
    )
    assert resp.status_code == 404


def test_persona_group_feedback_clear_overwrites(client) -> None:
    c, chat = client
    sim_id, persona_id = _run_sim_and_send_group_turn(c, chat)
    c.post(
        f"/simulations/{sim_id}/personas/{persona_id}/turns/1/feedback",
        json={"realistic_flag": True},
    )
    c.post(
        f"/simulations/{sim_id}/personas/{persona_id}/turns/1/feedback",
        json={"realistic_flag": None},
    )
    turns = c.get(f"/simulations/{sim_id}/personas/{persona_id}/turns").json()
    assert turns[1]["realistic_flag"] is None


def test_persona_group_feedback_is_arm_scoped(client) -> None:
    """#98: thumbs in the treatment room must not paint the control room."""
    c, chat = client
    sim_id, persona_id = _run_ab_sim_pick_persona_and_send_group_turn(c, chat, mode="collective")

    resp = c.post(
        f"/simulations/{sim_id}/personas/{persona_id}/turns/1/feedback?arm=treatment",
        json={"realistic_flag": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["target_id"] == f"{sim_id}/{persona_id}/treatment"

    treatment_turns = c.get(
        f"/simulations/{sim_id}/personas/{persona_id}/turns?arm=treatment"
    ).json()
    control_turns = c.get(f"/simulations/{sim_id}/personas/{persona_id}/turns?arm=control").json()

    assert treatment_turns[1]["role"] == "collective"
    assert treatment_turns[1]["realistic_flag"] is True
    assert control_turns[1]["role"] == "collective"
    assert control_turns[1]["realistic_flag"] is None


def test_persona_group_feedback_ab_requires_arm(client) -> None:
    """#98: A/B feedback must target an arm-scoped transcript."""
    c, chat = client
    sim_id, persona_id = _run_ab_sim_pick_persona_and_send_group_turn(c, chat, mode="collective")

    resp = c.post(
        f"/simulations/{sim_id}/personas/{persona_id}/turns/1/feedback",
        json={"realistic_flag": True},
    )
    assert resp.status_code == 400
    assert "arm" in resp.json()["detail"]
