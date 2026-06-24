"""Phase 8 (#42 + #43) refinement-loop API tests.

Covers the additive lineage + compare surface on top of the existing
simulation flow:

- #43 parent_simulation_id persists + round-trips through POST → GET
- #43 lineage chain on GET /simulations/{id}: depth cap (≤10) + cycle detection
- #43 lineage is customer-scoped (a foreign ancestor terminates the walk)
- #42 GET /simulations/compare happy path (score delta + weakness-category diff
  + refinement deltas + sentiment shift)
- #42 compare 404 on a missing / not-owned / incomplete sim
- #42 cross-customer isolation on compare

Reuses the same stub-LLM + in-memory-repo harness as test_simulations_api so no
real network calls fire.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))

from sidira_simulator.adapters.repositories import get_in_memory_repos  # noqa: E402
from sidira_simulator.api.deps import (  # noqa: E402
    current_customer_id,
    get_orchestrator,
)
from sidira_simulator.main import app  # noqa: E402
from sidira_simulator.services.simulation_orchestrator import (  # noqa: E402
    SimulationOrchestrator,
)
from sidira_simulator.services.simulation_runner import SimulationRunner  # noqa: E402


class _StubChat:
    """Canned-reaction LLM stub (mirrors test_simulations_api)."""

    def __init__(self, reply: str = "I'd give it a shot."):
        self.reply = reply

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        return self.reply

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        from sidira_simulator.schemas.scoring import (
            RefinementOutput,
            Sentiment,
            SentimentClassification,
            WeaknessClassification,
        )

        if schema is WeaknessClassification:
            return WeaknessClassification(
                categories=["wrong_cohort"],
                primary_reason="Stub: user seems mismatched to the proposed cohort.",
            )
        if schema is SentimentClassification:
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


def _build_orchestrator(customer_repo, sim_repo, agent_repo):
    chat = _StubChat()
    runner = SimulationRunner(chat_client=chat)

    from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
    from sidira_simulator.adapters.persona_loader import PersonaPackLoader
    from sidira_simulator.adapters.r2 import LocalArtifactStore

    store = LocalArtifactStore(_FIXTURE_ROOT)
    persona_loader = PersonaPackLoader(store)
    feature_loader = FeaturePackLoader(store)

    return SimulationOrchestrator(
        customer_repo=customer_repo,
        simulation_repo=sim_repo,
        agent_repo=agent_repo,
        persona_loader=persona_loader,
        feature_pack_loader=feature_loader,
        runner=runner,
    )


@pytest.fixture
def client_with_stub_llm():
    """TestClient with the orchestrator dep overridden to use a stub LLM."""
    customer_repo, sim_repo, agent_repo, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    sim_repo._sims.clear()
    agent_repo._agents.clear()

    def _orch():
        return _build_orchestrator(customer_repo, sim_repo, agent_repo)

    app.dependency_overrides[get_orchestrator] = _orch
    yield TestClient(app), sim_repo, agent_repo
    app.dependency_overrides.clear()


def _run_sim(client: TestClient, *, prose: str, parent: str | None = None) -> str:
    """POST a sim, return its id (BackgroundTasks completes it before .post returns)."""
    body = {
        "hypothesis": {"capability_name": "reorder", "prose": prose},
        "population_size": 3,
        # The worktree POST path runs a T1 answerability gate that 422s an
        # OEC-undeclared hypothesis. Override to run as generic-reception so the
        # refinement-loop wiring under test isn't blocked on the unrelated gate.
        "run_as_generic_reception": True,
    }
    if parent is not None:
        body["parent_simulation_id"] = parent
    resp = client.post("/simulations", json=body)
    assert resp.status_code == 202, resp.text
    return resp.json()["id"]


# ── #43: parent linkage + lineage ──────────────────────────────────────────


def test_parent_simulation_id_persists_and_round_trips(client_with_stub_llm) -> None:
    """A run submitted with parent_simulation_id persists it + surfaces it on GET."""
    client, sim_repo, _ = client_with_stub_llm
    root = _run_sim(client, prose="Root run.")
    child = _run_sim(client, prose="Refined run.", parent=root)

    # Persisted on the row.
    assert sim_repo._sims[child]["parent_simulation_id"] == root

    body = client.get(f"/simulations/{child}").json()
    assert body["parent_simulation_id"] == root
    # And the lineage chain surfaces the parent as the nearest ancestor.
    assert [e["id"] for e in body["lineage"]] == [root]
    entry = body["lineage"][0]
    assert entry["status"] == "complete"
    assert entry["confidence_score"] is not None
    assert entry["hypothesis_label"].startswith("Root run")


def test_fresh_run_has_no_parent_and_empty_lineage(client_with_stub_llm) -> None:
    """Backwards-compat: omitting parent_simulation_id == today's behavior."""
    client, _, _ = client_with_stub_llm
    root = _run_sim(client, prose="Unparented run.")
    body = client.get(f"/simulations/{root}").json()
    assert body["parent_simulation_id"] is None
    assert body["lineage"] == []


def test_lineage_chain_orders_nearest_ancestor_first(client_with_stub_llm) -> None:
    """A → B → C lineage on C lists [B, A] (nearest first)."""
    client, _, _ = client_with_stub_llm
    a = _run_sim(client, prose="Gen A.")
    b = _run_sim(client, prose="Gen B.", parent=a)
    c = _run_sim(client, prose="Gen C.", parent=b)

    body = client.get(f"/simulations/{c}").json()
    assert [e["id"] for e in body["lineage"]] == [b, a]


def test_lineage_depth_capped_at_10(client_with_stub_llm) -> None:
    """A 15-deep chain surfaces at most 10 ancestors (the depth cap)."""
    client, _, _ = client_with_stub_llm
    ids: list[str] = []
    parent: str | None = None
    for i in range(15):
        sim_id = _run_sim(client, prose=f"Gen {i}.", parent=parent)
        ids.append(sim_id)
        parent = sim_id

    leaf = ids[-1]
    body = client.get(f"/simulations/{leaf}").json()
    lineage = body["lineage"]
    assert len(lineage) == 10
    # Nearest 10 ancestors, nearest first: ids[-2], ids[-3], ... ids[-11].
    assert [e["id"] for e in lineage] == list(reversed(ids[-11:-1]))


def test_lineage_cycle_detection_stops_gracefully(client_with_stub_llm) -> None:
    """A self-/cyclic parent pointer must not infinite-loop the GET handler."""
    client, sim_repo, _ = client_with_stub_llm
    a = _run_sim(client, prose="Cycle A.")
    b = _run_sim(client, prose="Cycle B.", parent=a)
    # Force a cycle: A now points back at B (A → B → A → …).
    sim_repo._sims[a]["parent_simulation_id"] = b

    body = client.get(f"/simulations/{b}").json()
    # The walk visits A (b's parent), then A points to B which is already seen
    # → stop. So exactly one ancestor surfaces, no hang.
    assert [e["id"] for e in body["lineage"]] == [a]


def test_lineage_self_cycle_stops_gracefully(client_with_stub_llm) -> None:
    """A sim that is its own parent yields an empty lineage (seen-set guard)."""
    client, sim_repo, _ = client_with_stub_llm
    a = _run_sim(client, prose="Self loop.")
    sim_repo._sims[a]["parent_simulation_id"] = a

    body = client.get(f"/simulations/{a}").json()
    # The starting row is pre-seeded in the seen-set, so its own id as parent
    # is immediately recognised as a cycle.
    assert body["lineage"] == []


def _inject_completed_sim(
    sim_repo,
    *,
    customer_id: str,
    sim_id: str,
    prose: str,
    parent: str | None = None,
    weaknesses: list[dict] | None = None,
    refinement_suggestions: list[str] | None = None,
) -> str:
    """Inject a completed sim row owned by an arbitrary customer.

    Bypasses POST so we can stand up a sim for a customer that has no fixture
    persona pack (the cross-customer isolation tests need a foreign-owned sim
    without depending on multi-tenant fixtures).
    """
    from datetime import datetime, timezone

    sim_repo._sims[sim_id] = {
        "id": sim_id,
        "customer_id": customer_id,
        "status": "complete",
        "persona_pack_version": "v_test",
        "feature_pack_version": "v_test",
        "setup_id": "default",
        "hypothesis_json": {"capability_name": "reorder", "prose": prose},
        "result_json": {
            "confidence_score": 50.0,
            "weaknesses": weaknesses or [],
            "refinement_suggestions": refinement_suggestions or [],
            "per_agent_analyses": [],
        },
        "parent_simulation_id": parent,
        "error": None,
        "created_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
        "population_size": 3,
        "sampled_agent_count": 3,
        "run_seed": 1,
        "treatment_fraction": None,
        "selected_personas": None,
        "model_id": None,
    }
    return sim_id


def test_lineage_stops_at_foreign_ancestor(client_with_stub_llm) -> None:
    """A parent owned by another customer terminates the walk (no leak)."""
    client, sim_repo, _ = client_with_stub_llm
    # Cust A ("demo") owns the root; cust B owns a child that (illegally)
    # points at it. The child is injected directly so cust B needs no fixture.
    root = _run_sim(client, prose="Customer-A root.")
    child = _inject_completed_sim(
        sim_repo,
        customer_id="other-customer",
        sim_id="foreign-child",
        prose="Customer-B child.",
        parent=root,
    )

    app.dependency_overrides[current_customer_id] = lambda: "other-customer"
    try:
        body = client.get(f"/simulations/{child}").json()
    finally:
        app.dependency_overrides.pop(current_customer_id, None)
    # parent_simulation_id is still surfaced (it's on the row), but the walk
    # can't fetch the foreign ancestor, so the lineage is empty.
    assert body["parent_simulation_id"] == root
    assert body["lineage"] == []


# ── #42: compare ───────────────────────────────────────────────────────────


def test_compare_happy_path(client_with_stub_llm) -> None:
    """compare returns score delta + weakness-category diff + refinement deltas."""
    client, _, _ = client_with_stub_llm
    old = _run_sim(client, prose="Old run.")
    new = _run_sim(client, prose="New run.", parent=old)

    resp = client.get("/simulations/compare", params={"old": old, "new": new})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["old"]["id"] == old
    assert body["new"]["id"] == new
    # Both runs use the identical stub → identical score → zero delta.
    assert body["old_confidence_score"] is not None
    assert body["new_confidence_score"] is not None
    assert body["confidence_score_delta"] == pytest.approx(0.0, abs=1e-9)

    # The stub injects one wrong_cohort weakness per run → present in BOTH →
    # "unchanged" (same supporting-agent count), nothing appeared/disappeared.
    categories = {d["category"]: d for d in body["weakness_category_diffs"]}
    assert "wrong_cohort" in categories
    assert categories["wrong_cohort"]["change"] in {"unchanged", "changed"}
    assert body["weakness_categories_appeared"] == []
    assert body["weakness_categories_disappeared"] == []

    # Refinement suggestions are identical → none added, none resolved.
    assert body["old_refinement_suggestions"]
    assert body["refinement_suggestions_added"] == []
    assert body["refinement_suggestions_resolved"] == []

    # Sentiment shift present (both runs all-positive → 1.0 share, zero delta).
    assert body["old_sentiment_positive_share"] == pytest.approx(1.0)
    assert body["sentiment_positive_share_delta"] == pytest.approx(0.0, abs=1e-9)


def test_compare_weakness_category_diff_appeared_disappeared(
    client_with_stub_llm,
) -> None:
    """A hand-edited result diff surfaces appeared / disappeared / changed."""
    client, sim_repo, _ = client_with_stub_llm
    old = _run_sim(client, prose="Old run.")
    new = _run_sim(client, prose="New run.", parent=old)

    # Rewrite the two persisted results to engineer a clean category diff:
    #   old: wrong_cohort (2 agents), wrong_metric (1 agent)
    #   new: wrong_cohort (1 agent), broken_mechanism (3 agents)
    # → wrong_metric disappeared, broken_mechanism appeared, wrong_cohort changed.
    sim_repo._sims[old]["result_json"]["weaknesses"] = [
        {"category": "wrong_cohort", "summary": "x", "supporting_agent_ids": ["a1", "a2"]},
        {"category": "wrong_metric", "summary": "y", "supporting_agent_ids": ["a3"]},
    ]
    sim_repo._sims[new]["result_json"]["weaknesses"] = [
        {"category": "wrong_cohort", "summary": "x", "supporting_agent_ids": ["b1"]},
        {
            "category": "broken_mechanism",
            "summary": "z",
            "supporting_agent_ids": ["b2", "b3", "b4"],
        },
    ]

    body = client.get("/simulations/compare", params={"old": old, "new": new}).json()
    assert body["weakness_categories_appeared"] == ["broken_mechanism"]
    assert body["weakness_categories_disappeared"] == ["wrong_metric"]
    assert body["weakness_categories_changed"] == ["wrong_cohort"]

    diffs = {d["category"]: d for d in body["weakness_category_diffs"]}
    assert diffs["wrong_cohort"]["old_agent_count"] == 2
    assert diffs["wrong_cohort"]["new_agent_count"] == 1
    assert diffs["wrong_cohort"]["agent_count_delta"] == -1
    assert diffs["broken_mechanism"]["new_agent_count"] == 3


def test_compare_refinement_suggestion_deltas(client_with_stub_llm) -> None:
    """Added/resolved refinement suggestions are set-diffed on the raw strings."""
    client, sim_repo, _ = client_with_stub_llm
    old = _run_sim(client, prose="Old run.")
    new = _run_sim(client, prose="New run.", parent=old)

    sim_repo._sims[old]["result_json"]["refinement_suggestions"] = ["keep", "drop me"]
    sim_repo._sims[new]["result_json"]["refinement_suggestions"] = ["keep", "brand new"]

    body = client.get("/simulations/compare", params={"old": old, "new": new}).json()
    assert body["refinement_suggestions_added"] == ["brand new"]
    assert body["refinement_suggestions_resolved"] == ["drop me"]


def test_compare_404_when_old_missing(client_with_stub_llm) -> None:
    """A non-existent `old` id → 404."""
    client, _, _ = client_with_stub_llm
    new = _run_sim(client, prose="Real run.")
    resp = client.get(
        "/simulations/compare", params={"old": "does-not-exist", "new": new}
    )
    assert resp.status_code == 404, resp.text


def test_compare_404_when_new_incomplete(client_with_stub_llm) -> None:
    """A `new` sim that isn't completed → 404 (no diffing a half-built result)."""
    client, sim_repo, _ = client_with_stub_llm
    old = _run_sim(client, prose="Completed run.")
    new = _run_sim(client, prose="Pending run.")
    # Force the new sim back to a non-comparable state.
    sim_repo._sims[new]["status"] = "running"

    resp = client.get("/simulations/compare", params={"old": old, "new": new})
    assert resp.status_code == 404, resp.text


def test_compare_404_cross_customer_isolation(client_with_stub_llm) -> None:
    """compare must 404 when one sim belongs to a different customer."""
    client, sim_repo, _ = client_with_stub_llm
    # Cust A ("demo") owns `old`; cust B owns `new` (injected directly).
    old = _run_sim(client, prose="Customer-A run.")
    new = _inject_completed_sim(
        sim_repo,
        customer_id="other-customer",
        sim_id="foreign-new",
        prose="Customer-B run.",
    )

    # Cust B tries to compare A's sim against its own → 404 (A not owned by B).
    app.dependency_overrides[current_customer_id] = lambda: "other-customer"
    try:
        resp = client.get("/simulations/compare", params={"old": old, "new": new})
        assert resp.status_code == 404, resp.text
    finally:
        app.dependency_overrides.pop(current_customer_id, None)


def test_compare_route_not_captured_as_simulation_id(client_with_stub_llm) -> None:
    """GET /simulations/compare resolves to the compare route, not /{id}.

    Without `old`/`new` it must 422 (missing required query params), proving the
    path matched the compare handler rather than being captured as a sim id GET
    (which would 404).
    """
    client, _, _ = client_with_stub_llm
    resp = client.get("/simulations/compare")
    assert resp.status_code == 422, resp.text


# ── codex P1: parent ownership validated before create (no existence oracle) ──


def _post_with_parent(client: TestClient, *, prose: str, parent: str):
    """POST a sim with an explicit parent, returning the raw response (no 202
    assertion — these cases expect a 404 from the ownership pre-check)."""
    return client.post(
        "/simulations",
        json={
            "hypothesis": {"capability_name": "reorder", "prose": prose},
            "population_size": 3,
            "run_as_generic_reception": True,
            "parent_simulation_id": parent,
        },
    )


def test_create_with_nonexistent_parent_404s(client_with_stub_llm) -> None:
    """A parent id that doesn't exist → 404 before the row is created (the plain
    FK would otherwise fail the insert and leak 'this id is unknown')."""
    client, sim_repo, _ = client_with_stub_llm
    before = len(sim_repo._sims)
    resp = _post_with_parent(client, prose="Orphan refinement.", parent="ghost-id")
    assert resp.status_code == 404, resp.text
    assert len(sim_repo._sims) == before  # nothing persisted


def test_create_with_foreign_parent_404s_and_does_not_link(client_with_stub_llm) -> None:
    """A parent owned by ANOTHER customer → 404, identical to the missing case, so
    a caller can't use create success/failure as a cross-customer existence oracle
    (codex P1). No lineage edge to an unowned sim is persisted."""
    client, sim_repo, _ = client_with_stub_llm
    foreign = _inject_completed_sim(
        sim_repo,
        customer_id="other-customer",
        sim_id="foreign-parent",
        prose="Another tenant's sim.",
    )
    before = len(sim_repo._sims)
    # Default customer ("demo") tries to parent onto cust B's sim.
    resp = _post_with_parent(client, prose="Sneaky refinement.", parent=foreign)
    assert resp.status_code == 404, resp.text
    assert len(sim_repo._sims) == before  # no row created, no foreign edge stored


# ── codex P2: weakness diff uses true support_count, not capped id list ──


def test_compare_uses_true_support_count_over_capped_ids(client_with_stub_llm) -> None:
    """supporting_agent_ids is capped for display; support_count is the truth.
    A category whose true backing grew 10→50 must read as `changed`, even though
    both sides expose the same 3 capped ids (len-based math would call it
    `unchanged` — codex P2)."""
    client, sim_repo, _ = client_with_stub_llm
    old = _run_sim(client, prose="Old run.")
    new = _run_sim(client, prose="New run.", parent=old)

    sim_repo._sims[old]["result_json"]["weaknesses"] = [
        {
            "category": "wrong_cohort",
            "summary": "x",
            "supporting_agent_ids": ["a1", "a2", "a3"],  # capped
            "support_count": 10,  # true backing
        },
    ]
    sim_repo._sims[new]["result_json"]["weaknesses"] = [
        {
            "category": "wrong_cohort",
            "summary": "x",
            "supporting_agent_ids": ["b1", "b2", "b3"],  # same capped length
            "support_count": 50,  # true backing grew
        },
    ]

    body = client.get("/simulations/compare", params={"old": old, "new": new}).json()
    assert body["weakness_categories_changed"] == ["wrong_cohort"]
    diff = {d["category"]: d for d in body["weakness_category_diffs"]}["wrong_cohort"]
    assert diff["old_agent_count"] == 10
    assert diff["new_agent_count"] == 50
    assert diff["agent_count_delta"] == 40
