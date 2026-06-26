"""Tests for the fused, multi-turn experiment-memory conversation (#31, #32).

Covers:
- #31 FUSION: retrieval draws on BOTH the measured experiment archive and the
  predicted simulation archive; predicted↔measured pairs tell a story; citations
  are labeled MEASURED vs PREDICTED; a prediction MISS is surfaced honestly.
- #32 MULTI-TURN: a bare follow-up resolves against the prior turn's subject;
  suggested follow-up chips are returned; the offline extractive + injected-LLM
  paths both stay grounded.

No test hits a live LLM (the chat dep returns None → extractive path, or a stub).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from sidira_simulator.api.deps import get_orchestrator
from sidira_simulator.api.experiments import get_experiment_chat_client
from sidira_simulator.main import app
from sidira_simulator.schemas.experiment_memory import (
    CitationSource,
    ConversationTurn,
    ExperimentCategory,
)
from sidira_simulator.schemas.simulation import SimulationStatus
from sidira_simulator.schemas.simulation_archive import (
    PredictedDirection,
    SimulatedHypothesis,
)
from sidira_simulator.services.experiment_fusion import (
    FusedConversationService,
    _predicted_effect_label,
    _resolve_query,
)
from sidira_simulator.services.simulation_archive import seed_simulations

# ── simulation seed sanity ────────────────────────────────────────────────────


def test_simulation_seed_is_clean_and_pairs_to_experiments() -> None:
    sims = seed_simulations()
    assert len(sims) >= 8
    ids = [s.id for s in sims]
    assert len(ids) == len(set(ids)), "simulation ids must be unique"
    assert all(s.id.startswith("sim-") for s in sims)
    # Most carry a paired experiment; at least one is unpaired (prediction with
    # no measured counterpart yet).
    paired = [s for s in sims if s.paired_experiment_id]
    unpaired = [s for s in sims if not s.paired_experiment_id]
    assert paired, "fusion needs paired predictions to tell a story"
    assert unpaired, "an unpaired prediction must exist (prediction-only path)"
    # Confidence is the uncalibrated 0-100 agreement scale.
    assert all(0.0 <= s.confidence_score <= 100.0 for s in sims)


def test_simulation_seed_returns_independent_copies() -> None:
    a = seed_simulations()
    a[0].change_description = "MUTATED"
    b = seed_simulations()
    assert b[0].change_description != "MUTATED", "seed must not share mutable state"


def test_seed_contains_a_directional_miss() -> None:
    """The most valuable fusion row: a prediction that got the direction wrong.

    sim-0001 predicted the urgency timer UP; exp-0001 measured a LOSS.
    """
    sims = {s.id: s for s in seed_simulations()}
    s = sims["sim-0001"]
    assert s.predicted_direction is PredictedDirection.UP
    assert s.paired_experiment_id == "exp-0001"


# ── fusion retrieval ──────────────────────────────────────────────────────────


def test_conversation_fuses_both_sources() -> None:
    svc = FusedConversationService()  # offline, extractive
    resp = svc.answer("what do we know about an urgency countdown timer at checkout?")
    sources = {c.source for c in resp.citations}
    assert CitationSource.MEASURED in sources, "must cite the real experiment"
    assert CitationSource.PREDICTED in sources, "must cite the Sidira simulation"
    # The paired ids both appear.
    cited = {c.id for c in resp.citations}
    assert "exp-0001" in cited and "sim-0001" in cited


def test_fused_answer_surfaces_the_prediction_miss() -> None:
    svc = FusedConversationService()
    resp = svc.answer("did the urgency countdown timer at checkout work?")
    text = resp.answer.lower()
    # The story must name both sides and be honest the prediction missed.
    assert "predicted" in text and "measured" in text
    assert "wrong" in text or "miss" in text, "a directional miss must not be smoothed over"


def test_predicted_citation_is_labeled_uncalibrated() -> None:
    svc = FusedConversationService()
    resp = svc.answer("raise the pro plan price")
    pred = [c for c in resp.citations if c.source is CitationSource.PREDICTED]
    assert pred, "expected a predicted citation for a pricing change with a sim"
    assert any("uncalibrated" in c.effect_label.lower() for c in pred)
    # And a measured citation carries a real percentage effect.
    meas = [c for c in resp.citations if c.source is CitationSource.MEASURED]
    assert any("%" in c.effect_label for c in meas)


def test_unpaired_prediction_stands_alone() -> None:
    """A prediction with no measured counterpart is shown as predicted-only."""
    svc = FusedConversationService()
    resp = svc.answer("AI-written summary card at the top of every report")
    cited = {c.id for c in resp.citations}
    assert "sim-0101" in cited
    sim_cite = next(c for c in resp.citations if c.id == "sim-0101")
    assert sim_cite.source is CitationSource.PREDICTED


def test_follow_ups_are_grounded_and_capped() -> None:
    svc = FusedConversationService()
    resp = svc.answer("what do we know about the urgency countdown timer?")
    assert resp.follow_ups, "a conversation turn suggests follow-ups"
    assert len(resp.follow_ups) <= 3


# ── multi-turn context (#32) ──────────────────────────────────────────────────


def test_resolve_query_folds_prior_turn_subject() -> None:
    history = [
        ConversationTurn(
            question="What happened with the urgency countdown timer at checkout?",
            answer="Sidira predicted it would lift checkout conversion; the real A/B measured a loss.",
        )
    ]
    resolved = _resolve_query("why did that one lose?", history)
    # The bare follow-up gains the prior subject's content tokens.
    assert "urgency" in resolved or "checkout" in resolved or "timer" in resolved
    # The original message is preserved at the front.
    assert resolved.startswith("why did that one lose?")


def test_follow_up_resolves_against_prior_turn() -> None:
    svc = FusedConversationService()
    # Turn 1 establishes the subject.
    first = svc.answer("Tell me about the urgency countdown timer at checkout.")
    # Turn 2 is a bare follow-up that, alone, retrieves nothing specific.
    history = [
        ConversationTurn(
            question="Tell me about the urgency countdown timer at checkout.", answer=first.answer
        )
    ]
    second = svc.answer("why did that one lose?", history=history)
    cited = {c.id for c in second.citations}
    # Carried context steers retrieval back to the timer experiment/sim.
    assert "exp-0001" in cited, "follow-up must resolve against the prior turn's subject"
    # And it is surfaced as a TOP match (the pair story leads), not buried filler.
    assert second.citations[0].id in {"sim-0001", "exp-0001"}


def test_bare_followup_without_history_does_not_resolve_subject() -> None:
    """Control: the same bare follow-up with NO history must NOT surface the timer
    pair as a top match.

    A bare "why did that one lose?" carries no retrievable subject — the chat
    still returns top_k filler (every experiment scores ~0 and ties break by id),
    but the timer pair (sim-0001 / exp-0001) must NOT lead the citations. With
    history it does (see ``test_follow_up_resolves_against_prior_turn``); this
    proves the multi-turn resolution — not coincidence — is what surfaces it.
    """
    svc = FusedConversationService()
    resp = svc.answer("why did that one lose?")  # no history
    assert resp.citations[0].id not in {"sim-0001", "exp-0001"}


# ── endpoints ─────────────────────────────────────────────────────────────────


class _FakeOrchestrator:
    """Stands in for SimulationOrchestrator: returns the rows it was given.

    ``list_recent`` is the only method the conversation route calls. Rows mirror
    the dict shape the real orchestrator yields (hypothesis_json / result_json).
    """

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    async def list_recent(self, customer_id: str, limit: int = 50) -> list[dict]:
        return list(self._rows)


def _override_orchestrator(rows: list[dict]) -> None:
    app.dependency_overrides[get_orchestrator] = lambda: _FakeOrchestrator(rows)


def _clear_orchestrator() -> None:
    app.dependency_overrides.pop(get_orchestrator, None)


def _completed_sim_row(sim_id: str, prose: str, *, metric_lift_pp: float) -> dict:
    return {
        "id": sim_id,
        "status": SimulationStatus.COMPLETE.value,  # "complete", not "completed"
        "hypothesis_json": {"prose": prose, "metric_name": "retention"},
        "result_json": {"confidence_score": 64.0, "metric_lift_pp": metric_lift_pp},
        "completed_at": "2026-06-24T10:00:00+00:00",
        "created_at": "2026-06-23T09:00:00+00:00",
    }


def test_conversation_endpoint_offline_extractive() -> None:
    # No tenant simulations → the synthetic seed fallback (deterministic).
    _override_orchestrator([])
    try:
        resp = TestClient(app).post(
            "/experiments/conversation",
            json={
                "message": "what have we predicted vs measured on pricing?",
                "history": [],
                "top_k": 6,
            },
        )
    finally:
        _clear_orchestrator()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["used_llm"] is False
    assert body["grounded"] is True
    assert body["citations"], "answer must cite retrieved evidence"
    assert {c["source"] for c in body["citations"]} <= {"measured", "predicted"}
    assert isinstance(body["follow_ups"], list)


def test_conversation_endpoint_carries_history() -> None:
    _override_orchestrator([])  # seed fallback
    try:
        resp = TestClient(app).post(
            "/experiments/conversation",
            json={
                "message": "why did that one lose?",
                "history": [
                    {
                        "question": "Tell me about the urgency countdown timer at checkout.",
                        "answer": "Sidira predicted a lift; the real A/B measured a loss on checkout conversion.",
                    }
                ],
                "top_k": 6,
            },
        )
    finally:
        _clear_orchestrator()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    cited = {c["id"] for c in body["citations"]}
    assert "exp-0001" in cited


def test_conversation_reads_tenant_simulations_not_seed() -> None:
    """#33: with the customer's own completed simulations present, the chat
    retrieves over THEM (not the demo seed) — the "Continue Watching" hypothesis
    that exists on the Hypotheses tab now surfaces here."""
    rows = [
        _completed_sim_row(
            "sim-cw-1",
            "Add a 'Continue Watching' rail to the Streamly home screen",
            metric_lift_pp=1.6,
        ),
        _completed_sim_row(
            "sim-cw-2",
            "Personalize 'Top Picks' below Continue Watching",
            metric_lift_pp=-0.8,
        ),
    ]
    _override_orchestrator(rows)
    try:
        resp = TestClient(app).post(
            "/experiments/conversation",
            json={"message": "what do we know about continue watching?", "top_k": 6},
        )
    finally:
        _clear_orchestrator()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    cited = {c["id"] for c in body["citations"]}
    assert "sim-cw-1" in cited, "tenant's own continue-watching sim must be retrieved"
    # Tenant has no measured experiment archive yet → predicted-only, never the seed.
    assert {c["source"] for c in body["citations"]} == {"predicted"}
    assert "exp-0001" not in cited and "sim-0001" not in cited, "demo seed must not leak in"


def test_conversation_endpoint_rejects_empty_message() -> None:
    resp = TestClient(app).post("/experiments/conversation", json={"message": ""})
    assert resp.status_code == 422


def test_conversation_endpoint_uses_injected_llm_stub() -> None:
    class _StubChat:
        def chat(self, messages, **kwargs):  # noqa: ANN001, ANN003
            # The fused system prompt + evidence context must be present.
            assert any("MEASURED" in m["content"] for m in messages)
            assert any("Evidence (context)" in m["content"] for m in messages)
            return "We predicted UP (sim-0001), the real A/B measured a loss (exp-0001)."

    app.dependency_overrides[get_experiment_chat_client] = lambda: _StubChat()
    _override_orchestrator([])  # seed fallback so the MEASURED side is present
    try:
        resp = TestClient(app).post(
            "/experiments/conversation",
            json={"message": "did the timer work?", "history": [], "top_k": 3},
        )
    finally:
        app.dependency_overrides.pop(get_experiment_chat_client, None)
        _clear_orchestrator()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["used_llm"] is True
    assert body["answer"].startswith("We predicted UP")
    assert body["citations"]


def test_predicted_citation_without_metric_lift_is_direction_only() -> None:
    """A prediction with no metric delta must cite DIRECTION only — never a
    fabricated ~+0.0pp that could contradict the direction (DESIGN.md §8.3)."""
    sim = SimulatedHypothesis(
        id="sim-live-x",
        change_description="Add a Continue Watching rail",
        primary_metric="home_screen",
        category=ExperimentCategory.UI,
        predicted_direction=PredictedDirection.DOWN,
        confidence_score=58.0,
        predicted_metric_lift_pp=None,
        sim_date="2026-06-24",
    )
    label = _predicted_effect_label(sim)
    assert "DOWN" in label and "uncalibrated" in label
    assert "pp" not in label, "no fabricated magnitude when none was computed"


def test_tenant_with_only_pending_sims_never_sees_demo_seed() -> None:
    """#33/P2: a customer that HAS simulations (even if all still pending) must not
    be shown synthetic demo-seed data — the seed is only for an empty workspace."""
    pending = {
        "id": "sim-pending",
        "status": "running",
        "hypothesis_json": {"prose": "Add a Continue Watching rail", "metric_name": "retention"},
        "result_json": None,
        "completed_at": None,
        "created_at": "2026-06-25T09:00:00+00:00",
    }
    _override_orchestrator([pending])
    try:
        resp = TestClient(app).post(
            "/experiments/conversation",
            json={"message": "what do we know about continue watching?", "top_k": 6},
        )
    finally:
        _clear_orchestrator()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    cited = {c["id"] for c in body["citations"]}
    assert "exp-0001" not in cited and "sim-0001" not in cited, "demo seed must not leak"
    assert not body["citations"], "no completed simulations → nothing to cite"
