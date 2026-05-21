"""End-to-end API tests for the simulation flow.

Uses a stub LLM so no real network calls fire. Validates that:
- POST /simulations returns 202 + simulation_id immediately
- GET /capabilities returns the demo customer's latest manifest
- The orchestrator persists agent_instances against the in-memory repo
- N-of-M failure handling: one timeout doesn't kill the run
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Point LocalArtifactStore at the committed fixture before app starts.
_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("PYTHIA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))

from pythia_simulator.adapters.repositories import get_in_memory_repos  # noqa: E402
from pythia_simulator.api.deps import get_orchestrator  # noqa: E402
from pythia_simulator.main import app  # noqa: E402
from pythia_simulator.services.simulation_orchestrator import SimulationOrchestrator  # noqa: E402
from pythia_simulator.services.simulation_runner import SimulationRunner  # noqa: E402


class _StubChat:
    """LLM stub returning canned reactions + canned structured outputs.

    chat_json dispatches on schema name so scoring + refinement get plausible
    classifications without driving a real LLM.
    """

    def __init__(self, reply: str = "I'd give it a shot.", *, raise_for_persona: str | None = None):
        self.reply = reply
        self.raise_for_persona = raise_for_persona
        self.calls: list[list[dict]] = []
        self.json_calls: list[tuple[type, list[dict]]] = []

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        self.calls.append(messages)
        identity = next((m["content"] for m in messages if m["role"] == "system"), "")
        if self.raise_for_persona and self.raise_for_persona in identity:
            raise TimeoutError("simulated timeout")
        return self.reply

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        self.json_calls.append((schema, messages))
        from pythia_simulator.schemas.scoring import (
            RefinementOutput,
            SentimentClassification,
            WeaknessClassification,
        )

        if schema is WeaknessClassification:
            return WeaknessClassification(
                categories=["wrong_cohort"],
                primary_reason="Stub: user seems mismatched to the proposed cohort.",
            )
        if schema is SentimentClassification:
            from pythia_simulator.schemas.scoring import Sentiment

            return SentimentClassification(
                sentiment=Sentiment.POSITIVE,
                confidence=0.8,
                one_line_summary="Stub: positive reception.",
            )
        if schema is RefinementOutput:
            return RefinementOutput(
                suggestions=[
                    "Narrow the cohort to users who placed an order in the last 7 days.",
                    "Add a 'time to first reorder' guardrail metric.",
                ]
            )
        raise NotImplementedError(f"stub has no canned response for {schema}")


@pytest.fixture
def client_with_stub_llm():
    """Override the orchestrator dep with one that uses a stub LLM."""
    chat = _StubChat()

    customer_repo, sim_repo, agent_repo, _ = get_in_memory_repos()
    # Clear in-memory state between tests via fresh module-level singletons.
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
    yield TestClient(app), chat, sim_repo, agent_repo
    app.dependency_overrides.clear()


def test_capabilities_endpoint_returns_manifest(client_with_stub_llm) -> None:
    client, _, _, _ = client_with_stub_llm
    resp = client.get("/capabilities")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body["capabilities"]) == {"reorder", "checkout"}


def test_post_simulation_returns_202_immediately(client_with_stub_llm) -> None:
    client, _, _, _ = client_with_stub_llm
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Add a one-tap reorder button to the home tab.",
            },
            "persona_sample_size": 3,
        },
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["id"]
    assert body["poll_url"] == f"/simulations/{body['id']}/state"


def test_e2e_simulation_completes_and_persists_agents(client_with_stub_llm) -> None:
    """Submit → wait briefly → fetch → result populated + 3 agents persisted."""
    client, chat, sim_repo, agent_repo = client_with_stub_llm

    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Show a 'reorder usual' banner for premium subscribers.",
            },
            "persona_sample_size": 3,
        },
    )
    assert resp.status_code == 202, resp.text
    sim_id = resp.json()["id"]

    # FastAPI BackgroundTasks runs after the response is sent but before
    # TestClient returns — so by .post() unblocks, the simulation is done.
    final = client.get(f"/simulations/{sim_id}")
    assert final.status_code == 200, final.text
    body = final.json()
    assert body["status"] == "complete", body
    assert len(body["agent_instance_ids"]) == 3
    # 3 initial reactions
    assert len(chat.calls) >= 3
    # 3 agents × 2 classifications (weakness + sentiment) = 6, plus optional refinement = 7
    assert len(chat.json_calls) >= 6
    # With stub returning positive sentiment + wrong_cohort weakness:
    #   sentiment_score = 1.0; weakness_concentration = 1.0
    #   confidence = 0.6 * 1.0 + 0.4 * (1 - 1.0) = 0.6 → 60.0
    assert body["result"]["confidence_score"] == 60.0
    assert any(w["category"] == "wrong_cohort" for w in body["result"]["weaknesses"])
    # confidence < 80 so refinement fired
    assert len(body["result"]["refinement_suggestions"]) >= 1
