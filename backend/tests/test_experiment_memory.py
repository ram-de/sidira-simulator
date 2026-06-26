"""Tests for experiment-memory: similarity search, trust-ordering, endpoints.

Covers the #29 dedup pipeline (ranking + the three-way trust verdict and its
thresholds) and the #28 RAG chat endpoint (offline extractive path + an injected
LLM stub). No test hits a live LLM.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from sidira_simulator.api.experiments import get_experiment_chat_client
from sidira_simulator.main import app
from sidira_simulator.schemas.experiment_memory import Verdict
from sidira_simulator.services.experiment_archive import seed_experiments
from sidira_simulator.services.experiment_similarity import (
    ALREADY_TESTED_THRESHOLD,
    SIMILAR_THRESHOLD,
    ExperimentIndex,
    classify,
    search_similar,
)

# ── seed archive sanity ──────────────────────────────────────────────────────


def test_seed_archive_is_clean_and_diverse() -> None:
    experiments = seed_experiments()
    assert len(experiments) >= 25
    ids = [e.id for e in experiments]
    assert len(ids) == len(set(ids)), "experiment ids must be unique"
    categories = {e.category.value for e in experiments}
    assert categories == {"copy", "pricing", "ui", "flow"}, "all 4 change-types present"
    # Counter-intuitive results exist (some treatments lost / were flat).
    results = {e.result.value for e in experiments}
    assert {"win", "loss", "flat"} <= results


def test_seed_returns_independent_copies() -> None:
    a = seed_experiments()
    a[0].change_description = "MUTATED"
    b = seed_experiments()
    assert b[0].change_description != "MUTATED", "seed must not share mutable state"


# ── similarity ranking ───────────────────────────────────────────────────────


def test_ranking_surfaces_the_obviously_relevant_experiment_first() -> None:
    index = ExperimentIndex(seed_experiments())
    matches = index.rank("add a countdown urgency timer to checkout", top_k=3)
    assert matches, "expected at least one match"
    assert matches[0].experiment.id == "exp-0001"  # the urgency-timer experiment
    # Cosine scores are monotonic non-increasing.
    sims = [m.similarity for m in matches]
    assert sims == sorted(sims, reverse=True)


def test_ranking_is_deterministic() -> None:
    index = ExperimentIndex(seed_experiments())
    a = index.rank("raise the price of the pro plan", top_k=5)
    b = index.rank("raise the price of the pro plan", top_k=5)
    assert [m.experiment.id for m in a] == [m.experiment.id for m in b]


def test_similarity_bounded_zero_to_one() -> None:
    index = ExperimentIndex(seed_experiments())
    for m in index.rank("pricing plan change", top_k=10):
        assert 0.0 <= m.similarity <= 1.0


# ── trust-ordering thresholds ────────────────────────────────────────────────


def test_classify_threshold_boundaries() -> None:
    assert classify(ALREADY_TESTED_THRESHOLD) is Verdict.ALREADY_TESTED
    assert classify(ALREADY_TESTED_THRESHOLD - 0.001) is Verdict.SIMILAR
    assert classify(SIMILAR_THRESHOLD) is Verdict.SIMILAR
    assert classify(SIMILAR_THRESHOLD - 0.001) is Verdict.NOVEL
    assert classify(0.0) is Verdict.NOVEL


def test_already_tested_verdict_shows_real_result() -> None:
    # A near-restatement of exp-0008 (raise Pro plan price $29 -> $39).
    resp = search_similar(
        "Raise the Pro plan price from $29 to $39 per month",
        seed_experiments(),
        top_k=5,
    )
    assert resp.verdict is Verdict.ALREADY_TESTED
    assert resp.matches[0].experiment.id == "exp-0008"
    assert resp.caveat is None
    # Headline carries the REAL recorded effect, not a prediction.
    assert "+18.5%" in resp.headline


def test_similar_verdict_carries_honesty_caveat() -> None:
    resp = search_similar(
        "Try a different monthly subscription price for our paid tier",
        seed_experiments(),
        top_k=5,
    )
    assert resp.verdict is Verdict.SIMILAR
    assert resp.caveat is not None
    assert "guaranteed" in resp.caveat.lower()
    assert resp.matches, "similar verdict must surface analogical priors"


def test_novel_verdict_shows_no_matches() -> None:
    resp = search_similar(
        "Switch our datacenter region to reduce backend p99 latency for API calls",
        seed_experiments(),
        top_k=5,
    )
    assert resp.verdict is Verdict.NOVEL
    assert resp.matches == [], "novel must not surface weak matches as evidence"
    assert resp.caveat is None
    assert "candidate for testing" in resp.headline.lower()


# ── firewall: outcome never drives retrieval ─────────────────────────────────


def test_outcome_fields_do_not_affect_ranking() -> None:
    """The winner/result/effect should not be part of the indexed text — a query
    of pure outcome vocabulary must not rank a high-effect experiment first."""
    index = ExperimentIndex(seed_experiments())
    # Pure OUTCOME-side vocabulary (winner / result words). None of it is indexed
    # — retrieval reads only the input side — so the best match must be weak.
    matches = index.rank("winner won lost flat treatment beat control", top_k=1)
    assert matches[0].similarity < SIMILAR_THRESHOLD


# ── endpoints ────────────────────────────────────────────────────────────────


def test_search_similar_endpoint() -> None:
    resp = TestClient(app).post(
        "/experiments/search-similar",
        json={"hypothesis": "add an urgency countdown timer to checkout", "top_k": 3},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["verdict"] in {"already_tested", "similar", "novel"}
    assert body["matches"][0]["experiment"]["id"] == "exp-0001"
    # Real outcome present on the match.
    assert "effect_size_pct" in body["matches"][0]["experiment"]


def test_search_similar_rejects_empty_hypothesis() -> None:
    resp = TestClient(app).post("/experiments/search-similar", json={"hypothesis": ""})
    assert resp.status_code == 422


def test_chat_endpoint_offline_extractive_fallback() -> None:
    # No LLM key in the suite and the dep returns None, so the extractive path runs.
    resp = TestClient(app).post(
        "/experiments/chat",
        json={"message": "what have we learned about pricing?", "top_k": 4},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["used_llm"] is False
    assert body["grounded"] is True
    assert body["citations"], "answer must cite retrieved experiments"
    # Extractive answer references the cited experiment ids.
    assert body["citations"][0]["id"] in body["answer"]


def test_chat_endpoint_uses_injected_llm_stub() -> None:
    class _StubChat:
        def chat(self, messages, **kwargs):  # noqa: ANN001, ANN003
            # Echo that it saw the grounded context.
            assert any("Past experiments" in m["content"] for m in messages)
            return "Grounded answer citing exp-0008."

    app.dependency_overrides[get_experiment_chat_client] = lambda: _StubChat()
    try:
        resp = TestClient(app).post(
            "/experiments/chat",
            json={"message": "did raising prices work?", "top_k": 3},
        )
    finally:
        app.dependency_overrides.pop(get_experiment_chat_client, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["used_llm"] is True
    assert body["answer"] == "Grounded answer citing exp-0008."
    assert body["citations"]
