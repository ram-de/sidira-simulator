"""End-to-end API tests for the simulation flow.

Uses a stub LLM so no real network calls fire. Validates that:
- POST /simulations returns 202 + simulation_id immediately
- GET /capabilities returns the demo customer's latest manifest
- The orchestrator persists agent_instances against the in-memory repo
- N-of-M failure handling: one timeout doesn't kill the run
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Point LocalArtifactStore at the committed fixture before app starts.
_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))

from sidira_simulator.adapters.repositories import get_in_memory_repos  # noqa: E402
from sidira_simulator.api.deps import (  # noqa: E402
    get_input_lint_chat_client,
    get_orchestrator,
)
from sidira_simulator.main import app  # noqa: E402
from sidira_simulator.services.simulation_orchestrator import SimulationOrchestrator  # noqa: E402
from sidira_simulator.services.simulation_runner import SimulationRunner  # noqa: E402


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
        from sidira_simulator.schemas.scoring import (
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
            from sidira_simulator.schemas.scoring import Sentiment

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


# Handle to the input-lint judge stub the active `client_with_stub_llm` fixture
# installed, so the T3 (#312) input-lint tests can flip its verdict without
# widening the 4-tuple every other test unpacks. Set/cleared by the fixture.
_ACTIVE_LINT_JUDGE: "_StubInputLintJudgeChat | None" = None


class _StubInputLintJudgeChat:
    """Stubbed ChatClient for the T3 (#312) pre-flight input-lint judge.

    Injected via `app.dependency_overrides[get_input_lint_chat_client]` so the
    judge NEVER hits a live LLM in the suite. Mutable `verdict` / `reasons` let a
    test flip the pre-flight lint between green (default — every existing test is
    unaffected) and amber/red. `chat_json` builds the passed `_JudgeOutput`
    schema so its taxonomy field-validator runs exactly as in prod.
    """

    def __init__(self) -> None:
        self.verdict = "green"
        self.reasons: list[str] = []
        self.call_count = 0

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):  # pragma: no cover
        raise NotImplementedError("input-lint judge uses chat_json only")

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        self.call_count += 1
        return schema(verdict=self.verdict, reasons=list(self.reasons))


@pytest.fixture
def client_with_stub_llm():
    """Override the orchestrator dep with one that uses a stub LLM."""
    chat = _StubChat()
    lint_judge = _StubInputLintJudgeChat()

    customer_repo, sim_repo, agent_repo, _ = get_in_memory_repos()
    # Clear in-memory state between tests via fresh module-level singletons.
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
    # T3 (#312): stub the pre-flight input-lint judge so it never hits a live
    # LLM. Default verdict is green (no input_flags) — every existing test is
    # unaffected; the input-lint tests below reach the judge via
    # `client.app` / the module-level `_LAST_LINT_JUDGE` handle to flip it.
    app.dependency_overrides[get_input_lint_chat_client] = lambda: lint_judge
    # Stash the active judge stub so the input-lint tests can mutate its verdict
    # without widening the 4-tuple every other test unpacks.
    global _ACTIVE_LINT_JUDGE
    _ACTIVE_LINT_JUDGE = lint_judge
    yield TestClient(app), chat, sim_repo, agent_repo
    _ACTIVE_LINT_JUDGE = None
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
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 3,
            "run_as_generic_reception": True,
        },
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["id"]
    assert body["poll_url"] == f"/simulations/{body['id']}/state"


# ── #310 / T1: pre-flight answerability gate ────────────────────────────────


def test_oec_undeclared_blocks_with_override_payload(client_with_stub_llm) -> None:
    """metric_name omitted (non-structural prose) -> 422 with a refinement-shaped
    payload that advertises the generic-reception override."""
    client, _, _, _ = client_with_stub_llm
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Reword the welcome message to sound friendlier.",
            },
            "population_size": 3,
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["error"] == "needs_input"
    assert "oec_undeclared" in detail["reason_codes"]
    assert detail["allow_override"] is True
    assert detail["override_field"] == "run_as_generic_reception"
    assert detail["reasons"] and detail["fixes"]


def test_oec_override_proceeds_to_202(client_with_stub_llm) -> None:
    """Resubmitting with run_as_generic_reception=true proceeds past the gate."""
    client, _, _, _ = client_with_stub_llm
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Reword the welcome message to sound friendlier.",
            },
            "population_size": 3,
            "run_as_generic_reception": True,
        },
    )
    assert resp.status_code == 202, resp.text
    assert resp.json()["status"] == "pending"


def test_structurally_invisible_change_blocks_without_override(
    client_with_stub_llm,
) -> None:
    """UI-structure prose + no proposed_figma -> 422; the override does NOT
    clear it (allow_override stays False even with the flag set)."""
    client, _, _, _ = client_with_stub_llm
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Move the reorder button to the top of the home screen.",
            },
            "population_size": 3,
            # Override the OEC defect; the structural defect must still block.
            "run_as_generic_reception": True,
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert "structurally_invisible_change" in detail["reason_codes"]
    assert detail["allow_override"] is False


# ── #313 / T4: deterministic pre-flight preview endpoint ────────────────────


def test_preflight_oec_undeclared_mirrors_post_block(client_with_stub_llm) -> None:
    """The preview endpoint returns the SAME needs_input verdict the POST path
    422s on — caught at the keyboard, before submit — with the override
    advertised. Zero-LLM and never persists a sim."""
    client, _, sim_repo, _ = client_with_stub_llm
    resp = client.post(
        "/simulations/preflight",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Reword the welcome message to sound friendlier.",
            }
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["state"] == "needs_input"
    assert "oec_undeclared" in body["reason_codes"]
    assert body["allow_override"] is True
    assert body["override_field"] == "run_as_generic_reception"
    assert body["reasons"] and body["fixes"]
    # The preview must NOT persist a simulation.
    assert sim_repo._sims == {}


def test_preflight_override_clears_oec_block(client_with_stub_llm) -> None:
    """run_as_generic_reception=true in the preview clears the OEC block, so the
    wizard knows the override resubmit will proceed."""
    client, _, _, _ = client_with_stub_llm
    resp = client.post(
        "/simulations/preflight",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Reword the welcome message to sound friendlier.",
            },
            "run_as_generic_reception": True,
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["state"] == "answerable"


def test_preflight_structural_invisibility_not_overridable(client_with_stub_llm) -> None:
    """UI-structure prose + no figma stays blocking in the preview even with the
    override, mirroring the POST gate (no faithful prose-only structural run)."""
    client, _, _, _ = client_with_stub_llm
    resp = client.post(
        "/simulations/preflight",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Move the reorder button to the top of the home screen.",
            },
            "run_as_generic_reception": True,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["state"] == "needs_input"
    assert "structurally_invisible_change" in body["reason_codes"]
    assert body["allow_override"] is False


def test_preflight_out_of_scope_surfaced(client_with_stub_llm) -> None:
    """A long-horizon OEC previews as out_of_scope (abstain) so the wizard can
    warn the PM the verdict will be withheld — without running the sim."""
    client, _, _, _ = client_with_stub_llm
    resp = client.post(
        "/simulations/preflight",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Lift 90-day revenue by reordering the home feed.",
                "metric_name": "conversion",
                "conversion_action": "checkout",
                "conversion_action_label": "complete checkout",
                "decision_point": "you've added 2 items to your cart",
                "proposed_figma": {"screens": [], "transitions": []},
            }
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["state"] == "out_of_scope"
    assert "out_of_scope_long_horizon" in body["reason_codes"]


def test_preflight_leading_framing_surfaced_advisory(client_with_stub_llm) -> None:
    """The deterministic leading-framing lint surfaces in the preview as advisory
    reasons + neutralize fixes, alongside an otherwise-answerable verdict (it
    does NOT block — the T3 LLM judge finalizes amber/red at submit, not here)."""
    client, _, _, _ = client_with_stub_llm
    resp = client.post(
        "/simulations/preflight",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "We're excited to ship a reorder button users will love.",
                "metric_name": "conversion",
                "conversion_action": "checkout",
                "conversion_action_label": "complete checkout",
                "decision_point": "you've added 2 items to your cart",
                "proposed_figma": {"screens": [], "transitions": []},
            }
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["state"] == "answerable"
    assert body["leading_framing_reasons"]
    assert body["leading_framing_fixes"]


def test_preflight_answerable_clean(client_with_stub_llm) -> None:
    """A well-posed hypothesis with a declared OEC and no framing previews
    answerable with empty reasons/framing."""
    client, _, _, _ = client_with_stub_llm
    resp = client.post(
        "/simulations/preflight",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Reword the welcome message to be more concise.",
                "metric_name": "conversion",
                "conversion_action": "checkout",
                "conversion_action_label": "complete checkout",
                "decision_point": "you've added 2 items to your cart",
            }
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["state"] == "answerable"
    assert body["reasons"] == []
    assert body["leading_framing_reasons"] == []


def test_happy_path_with_declared_metric_unaffected(client_with_stub_llm) -> None:
    """A hypothesis with a declared OEC and no structural-invisibility passes
    the gate unchanged (today's 202 path)."""
    client, _, _, _ = client_with_stub_llm
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Reword the welcome message to sound friendlier.",
                "metric_name": "conversion",
                "conversion_action": "checkout",
                "conversion_action_label": "complete checkout",
                "decision_point": "you've added 2 items to your cart",
            },
            "population_size": 3,
        },
    )
    assert resp.status_code == 202, resp.text


def test_post_simulation_rejects_unavailable_model_id(monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    resp = TestClient(app).post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Show a reorder banner for premium subscribers.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 3,
            "model_id": "gpt-5.5",
            "run_as_generic_reception": True,
        },
    )

    assert resp.status_code == 400, resp.text
    assert "model_id" in resp.text


def test_post_simulation_persists_model_id(client_with_stub_llm, monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-groq")
    client, _chat, _sim_repo, _agent_repo = client_with_stub_llm

    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Show a reorder banner for premium subscribers.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 3,
            "model_id": "llama-3.3-70b-versatile",
            "run_as_generic_reception": True,
        },
    )

    assert resp.status_code == 202, resp.text
    sim_id = resp.json()["id"]
    final = client.get(f"/simulations/{sim_id}")
    assert final.status_code == 200, final.text
    assert final.json()["model_id"] == "llama-3.3-70b-versatile"


def test_e2e_simulation_completes_and_persists_agents(client_with_stub_llm) -> None:
    """Submit → wait briefly → fetch → result populated + 3 agents persisted."""
    client, chat, sim_repo, agent_repo = client_with_stub_llm

    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Show a 'reorder usual' banner for premium subscribers.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 3,
            "run_as_generic_reception": True,
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
    # Phase 2.5: population_size + sampled_agent_count round-trip through the API.
    assert body["population_size"] == 3
    assert body["sampled_agent_count"] == 3
    # 3 initial reactions
    assert len(chat.calls) >= 3
    # 3 agents × 2 classifications (weakness + sentiment) = 6, plus optional refinement = 7
    assert len(chat.json_calls) >= 6
    # Codex-reviewed formula (Wave 4). Stub returns: positive sentiment at conf=0.8,
    # one wrong_cohort weakness per agent. With ScoringConfig defaults
    # (sent_w=0.6, weak_w=0.4, prior_k=1, min_sample=3):
    #   sentiment numerator   = 3*0.8*1.0 + 1.0*0.5 = 2.9
    #   sentiment denominator = 3*0.8 + 1.0 = 3.4
    #   sentiment_score = 2.9 / 3.4 ≈ 0.853
    #   any_flag_share  = 3/3 = 1.0 → weakness_signal = 0.0
    #   score = 100 * (0.6 * 0.853 + 0.4 * 0.0) ≈ 51.2
    assert body["result"]["confidence_score"] == pytest.approx(51.2, abs=0.1)
    assert any(w["category"] == "wrong_cohort" for w in body["result"]["weaknesses"])
    # Phase 2.5 #6: the API contract surfaces the bootstrap CI on the score
    # and a Wilson CI on every observed-frequency weakness row.
    ci = body["result"]["confidence_score_ci"]
    assert ci is not None
    lo, hi = ci
    assert 0.0 <= lo <= body["result"]["confidence_score"] <= hi <= 100.0
    # Every weakness with a populated frequency must also carry both CI bounds.
    # The injected `underpowered_design` (structural flag, no frequency) is
    # exempt — see ScoringService.aggregate's underpowered gate.
    for w in body["result"]["weaknesses"]:
        if w.get("frequency") is not None:
            assert w["ci_low"] is not None and w["ci_high"] is not None
            assert 0.0 <= w["ci_low"] <= w["frequency"] <= w["ci_high"] <= 1.0


def test_per_agent_analyses_persisted_on_result_and_join_into_agent_summary(
    client_with_stub_llm,
) -> None:
    """#51: SimulationResult.per_agent_analyses is populated at score time
    AND the /agents endpoint joins it onto AgentSummary so the result-table
    cells render without N extra fetches."""
    client, chat, _sim_repo, _agent_repo = client_with_stub_llm
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Show a reorder banner for premium subscribers.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 3,
            "run_as_generic_reception": True,
        },
    )
    sim_id = resp.json()["id"]
    final = client.get(f"/simulations/{sim_id}")
    assert final.status_code == 200
    body = final.json()
    # Persisted on the result
    analyses = body["result"]["per_agent_analyses"]
    assert isinstance(analyses, list)
    assert len(analyses) == 3
    for a in analyses:
        assert a["sentiment"] in {"positive", "neutral", "negative"}
        assert 0.0 <= a["sentiment_confidence"] <= 1.0
        assert isinstance(a["top_quote"], str)
        # The stub LLM uses "I'd give it a shot." as the canned reaction.
        assert a["top_quote"].startswith("I'd give it a shot")

    # Joined onto AgentSummary
    agents_resp = client.get(f"/simulations/{sim_id}/agents")
    assert agents_resp.status_code == 200
    agents = agents_resp.json()
    assert len(agents) == 3
    for row in agents:
        # New fields populated for completed sims
        assert row["sentiment"] in {"positive", "neutral", "negative"}
        assert 0.0 <= row["sentiment_confidence"] <= 1.0
        assert row["top_quote"]


def test_agent_summary_fields_are_none_for_pre_51_result_json(
    client_with_stub_llm,
) -> None:
    """Backwards-compat: a sim whose result_json predates #51 (no
    per_agent_analyses field) must not 500 — the join falls back to None
    on every row."""
    client, _chat, sim_repo, _agent_repo = client_with_stub_llm
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Show a reorder banner.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 3,
            "run_as_generic_reception": True,
        },
    )
    sim_id = resp.json()["id"]
    # Mutate the persisted result to remove per_agent_analyses, simulating
    # a sim that ran before this field existed.
    sim = sim_repo._sims[sim_id]
    sim["result_json"].pop("per_agent_analyses", None)

    agents_resp = client.get(f"/simulations/{sim_id}/agents")
    assert agents_resp.status_code == 200
    for row in agents_resp.json():
        assert row["sentiment"] is None
        assert row["sentiment_confidence"] is None
        assert row["top_quote"] is None


def test_default_run_seed_is_persisted_on_db_row(client_with_stub_llm) -> None:
    """Codex P1: when the caller omits run_seed, the orchestrator must persist
    the seed it actually used -- otherwise the simulation can't be replayed."""
    client, _, sim_repo, _ = client_with_stub_llm

    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Add a one-tap reorder button to the home tab.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 3,
            "run_as_generic_reception": True,
            # run_seed deliberately omitted.
        },
    )
    assert resp.status_code == 202, resp.text
    sim_id = resp.json()["id"]

    row = sim_repo._sims[sim_id]
    assert row["run_seed"] is not None, "default run_seed must be persisted, not NULL"
    assert isinstance(row["run_seed"], int)
    # Codex P2: must be JS-safe so frontend round-trip doesn't round and break
    # replay reproducibility.
    assert (
        0 <= row["run_seed"] <= 2**53 - 1
    ), f"default run_seed {row['run_seed']} exceeds JS Number.MAX_SAFE_INTEGER"
    # And the API response surfaces the same seed.
    final = client.get(f"/simulations/{sim_id}").json()
    assert final["run_seed"] == row["run_seed"]


def test_runner_agent_count_matches_persisted_cap_under_bad_env(
    client_with_stub_llm, monkeypatch
) -> None:
    """Codex P2: when SIDIRA_MAX_AGENTS is misconfigured (e.g. '0'), the runner
    must produce exactly sampled_agent_count agents -- not silently fall back
    to the population_sampler default of 50."""
    client, _, sim_repo, agent_repo = client_with_stub_llm
    monkeypatch.delenv("PYTHIA_MAX_AGENTS", raising=False)
    monkeypatch.setenv("SIDIRA_MAX_AGENTS", "0")

    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Add a one-tap reorder button to the home tab.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 1000,  # would yield 50 agents under default cap
            "run_as_generic_reception": True,
        },
    )
    assert resp.status_code == 202, resp.text
    sim_id = resp.json()["id"]

    body = client.get(f"/simulations/{sim_id}").json()
    # API clamps SIDIRA_MAX_AGENTS=0 to 1; the runner must honor the same cap.
    assert body["sampled_agent_count"] == 1
    assert len(body["agent_instance_ids"]) == 1


# ── Phase 5 #101: persona-filter end-to-end ─────────────────────────────────


def test_post_simulation_with_unknown_persona_returns_400(
    client_with_stub_llm,
) -> None:
    """selected_personas with an id not in the active pack -> 400.

    Eager-validated in orchestrator.prepare() before the sim row is persisted,
    so a bad request never creates a dangling sim that would fail in the
    background.
    """
    client, _, sim_repo, _ = client_with_stub_llm
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Add a one-tap reorder button.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 5,
            "selected_personas": ["made_up_persona_id"],
            "run_as_generic_reception": True,
        },
    )
    assert resp.status_code == 400, resp.text
    assert "not present in the active Persona Pack" in resp.json()["detail"]


def test_post_simulation_with_empty_selected_personas_returns_422(
    client_with_stub_llm,
) -> None:
    """Empty selected_personas is rejected by the Pydantic validator (422)."""
    client, _, _, _ = client_with_stub_llm
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Add a one-tap reorder button.",
            },
            "population_size": 5,
            "selected_personas": [],
        },
    )
    assert resp.status_code == 422, resp.text


def test_simulation_with_persona_filter_completes_against_subset(
    client_with_stub_llm,
) -> None:
    """selected_personas=[<one valid id>] -> sim runs against ONLY that persona.

    Acceptance criterion: full population_size lands on the selected cohort
    (re-weight invariant), not a proportional share of it.
    """
    client, _, sim_repo, agent_repo = client_with_stub_llm

    # Hardcoded id from the fixture demo pack. There is no read-side
    # /personas endpoint yet (#101 frontend lands one next); the wizard
    # will use it, but the test fixture loads the demo pack directly.
    chosen = ["maya_late_night_premium"]

    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Test the persona-filter end-to-end.",
            },
            "population_size": 3,
            "selected_personas": chosen,
            "run_as_generic_reception": True,
        },
    )
    assert resp.status_code == 202, resp.text
    sim_id = resp.json()["id"]

    final = client.get(f"/simulations/{sim_id}").json()
    assert final["status"] == "complete", final
    # Filter round-trips through the persisted sim row.
    assert final["selected_personas"] == chosen
    # All materialized agents belong to the selected persona (re-weight
    # invariant: the full population_size lands on the cohort, not a share).
    agent_ids = final["agent_instance_ids"]
    assert len(agent_ids) == 3
    agents = client.get(f"/simulations/{sim_id}/agents").json()
    assert {a["persona_id"] for a in agents} == set(chosen)


def test_simulation_without_persona_filter_runs_against_all_personas(
    client_with_stub_llm,
) -> None:
    """Backwards-compat: omitting selected_personas == today's behavior.

    The persisted row exposes selected_personas=None on GET so the frontend
    cohort banner can branch off it.
    """
    client, _, _, _ = client_with_stub_llm
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Unfiltered control case.",
            },
            "population_size": 5,
            "run_as_generic_reception": True,
        },
    )
    assert resp.status_code == 202, resp.text
    sim_id = resp.json()["id"]
    final = client.get(f"/simulations/{sim_id}").json()
    assert final["selected_personas"] is None


# ── #312 / T3: pre-flight ordinal input lint (disclose-and-run) ──────────────


def test_flagged_input_stamps_result_flags_and_still_returns_202(
    client_with_stub_llm,
) -> None:
    """A semantically-flagged input (judge amber) NEVER 422s — the create call
    returns 202 and the persisted result carries `input_flags` (state + reasons),
    while confidence_score is computed unchanged."""
    client, _chat, _sim_repo, _agent_repo = client_with_stub_llm
    _ACTIVE_LINT_JUDGE.verdict = "amber"
    _ACTIVE_LINT_JUDGE.reasons = ["wrong_cohort"]

    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Make the thing better for some users.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 3,
            "run_as_generic_reception": True,
        },
    )
    # Semantic judgment never hard-refuses a paying user.
    assert resp.status_code == 202, resp.text
    sim_id = resp.json()["id"]

    body = client.get(f"/simulations/{sim_id}").json()
    assert body["status"] == "complete", body
    flags = body["result"]["input_flags"]
    assert flags is not None
    assert flags["state"] == "amber"
    assert "wrong_cohort" in flags["reason_codes"]
    assert flags["reasons"]
    # The headline score is still computed and persisted (the lint ROUTES, it
    # does not discount).
    assert body["result"]["confidence_score"] is not None


def test_green_input_leaves_input_flags_none(client_with_stub_llm) -> None:
    """A green pre-flight verdict (the fixture default) leaves input_flags None —
    a clean run is byte-identical and migration-free."""
    client, _chat, _sim_repo, _agent_repo = client_with_stub_llm
    assert _ACTIVE_LINT_JUDGE.verdict == "green"

    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Add a one-tap reorder button to the home tab.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 3,
            "run_as_generic_reception": True,
        },
    )
    assert resp.status_code == 202, resp.text
    sim_id = resp.json()["id"]
    body = client.get(f"/simulations/{sim_id}").json()
    assert body["result"]["input_flags"] is None


def test_flagged_input_fires_refinement_even_when_score_high(
    client_with_stub_llm,
) -> None:
    """The refinement trigger moved earlier (#312): a flagged INPUT earns a
    rewrite offer regardless of the post-run score. The stub LLM's all-positive
    reactions push the score ≥80, yet refinement_suggestions are still
    populated because the input was flagged."""
    client, _chat, _sim_repo, _agent_repo = client_with_stub_llm
    _ACTIVE_LINT_JUDGE.verdict = "amber"
    _ACTIVE_LINT_JUDGE.reasons = ["untestable_hypothesis"]

    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                # All-positive stub reactions -> high score; the flag is what
                # must trigger refinement here.
                "prose": "Make engagement better.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 3,
            "run_as_generic_reception": True,
        },
    )
    assert resp.status_code == 202, resp.text
    sim_id = resp.json()["id"]
    body = client.get(f"/simulations/{sim_id}").json()
    result = body["result"]
    assert result["input_flags"] is not None
    # Refinement fired despite (potentially) high score, because the input was
    # flagged. The stub RefinementOutput returns two suggestions.
    assert result["refinement_suggestions"], result["confidence_score"]
