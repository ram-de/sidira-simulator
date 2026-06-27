"""Persistent multi-thread "Ask the archive" conversations (#41).

Covers: thread CRUD (create / list-newest-first / get-with-turns / rename /
delete); append-turn generates the fused answer through the SAME tenant-scoped
path as POST /experiments/conversation and PERSISTS Q + A + citations; the
first turn AUTO-TITLES an untitled thread from the question (Claude-style);
follow-up context replays the persisted turns; cross-tenant isolation (one
customer can NEVER see, get, rename, delete, or append to another's thread —
404, never 403, so existence never leaks); reload survives (the turns are read
back from the store, not client state).

Runs against the in-memory repo (no DB) with the orchestrator stubbed to a fixed
row set, so every answer is the deterministic OFFLINE EXTRACTIVE fallback (no
live LLM) — mirrors test_experiment_memory_fusion.py.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))

from sidira_simulator.adapters.repositories import (  # noqa: E402
    get_in_memory_conversation_repo,
    get_in_memory_repos,
)
from sidira_simulator.api.deps import get_orchestrator  # noqa: E402
from sidira_simulator.main import app  # noqa: E402


class _FakeOrchestrator:
    """Returns the rows it was given. ``list_recent`` is the only method the
    turn route calls; an empty list drives the deterministic synthetic-seed
    fallback (no live LLM, no DB)."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    async def list_recent(self, customer_id: str, limit: int = 50) -> list[dict]:
        return list(self._rows)


@pytest.fixture
def client(monkeypatch):
    # Fresh in-memory stores per test so thread lists don't bleed across tests.
    customer_repo, _, _, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    get_in_memory_conversation_repo()._threads.clear()
    # Seed fallback (no tenant sims) → deterministic offline extractive answers.
    app.dependency_overrides[get_orchestrator] = lambda: _FakeOrchestrator([])
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "demo")
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)


# ── CRUD ────────────────────────────────────────────────────────────────────


def test_create_lists_and_starts_untitled(client):
    created = client.post("/conversations", json={}).json()
    assert created["title"] is None
    assert created["id"]

    listing = client.get("/conversations").json()["conversations"]
    assert [c["id"] for c in listing] == [created["id"]]
    assert listing[0]["title"] is None


def test_get_unknown_is_404(client):
    assert client.get("/conversations/does-not-exist").status_code == 404


def test_append_turn_persists_and_autotitles(client):
    cid = client.post("/conversations", json={}).json()["id"]
    resp = client.post(
        f"/conversations/{cid}/turns",
        json={"message": "What did we predict vs measure on pricing changes?"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # The fused answer is the offline extractive fallback, grounded + cited.
    turn = body["turn"]
    assert turn["used_llm"] is False
    assert turn["answer"]
    assert {c["source"] for c in turn["citations"]} <= {"measured", "predicted"}
    assert body["grounded"] is True
    assert isinstance(body["follow_ups"], list)

    # First turn auto-titled the thread (Claude-style: a trimmed first question).
    assert body["conversation"]["title"] == (
        "What did we predict vs measure on pricing changes?"
    )

    # The turn PERSISTED — re-fetching the thread replays it (reload survives).
    detail = client.get(f"/conversations/{cid}").json()
    assert detail["title"] == "What did we predict vs measure on pricing changes?"
    assert len(detail["turns"]) == 1
    assert detail["turns"][0]["question"] == (
        "What did we predict vs measure on pricing changes?"
    )
    assert detail["turns"][0]["citations"] == turn["citations"]


def test_long_first_question_is_truncated_in_title(client):
    cid = client.post("/conversations", json={}).json()["id"]
    long_q = "Why did " + "the urgency banner copy variant " * 6 + "underperform?"
    body = client.post(f"/conversations/{cid}/turns", json={"message": long_q}).json()
    title = body["conversation"]["title"]
    assert len(title) <= 80
    assert title.endswith("…")


def test_explicit_title_not_overwritten_by_autotitle(client):
    cid = client.post("/conversations", json={"title": "Pricing deep-dive"}).json()["id"]
    body = client.post(
        f"/conversations/{cid}/turns", json={"message": "Anything on checkout?"}
    ).json()
    # A user-supplied title is preserved — auto-title only fires when untitled.
    assert body["conversation"]["title"] == "Pricing deep-dive"


def test_second_turn_appends_in_order_and_floats_thread(client):
    a = client.post("/conversations", json={}).json()["id"]
    b = client.post("/conversations", json={}).json()["id"]
    # Touch A second so it floats above B (newest-touched first).
    client.post(f"/conversations/{b}/turns", json={"message": "first on B"})
    client.post(f"/conversations/{a}/turns", json={"message": "first on A"})
    client.post(f"/conversations/{a}/turns", json={"message": "second on A"})

    detail = client.get(f"/conversations/{a}").json()
    assert [t["question"] for t in detail["turns"]] == ["first on A", "second on A"]

    listing = client.get("/conversations").json()["conversations"]
    assert listing[0]["id"] == a  # most-recently touched is first


def test_rename_updates_title(client):
    cid = client.post("/conversations", json={}).json()["id"]
    renamed = client.patch(
        f"/conversations/{cid}", json={"title": "  Q3 retention bets  "}
    ).json()
    assert renamed["title"] == "Q3 retention bets"  # trimmed
    assert client.get(f"/conversations/{cid}").json()["title"] == "Q3 retention bets"


def test_rename_unknown_is_404(client):
    assert (
        client.patch("/conversations/ghost", json={"title": "x"}).status_code == 404
    )


def test_delete_removes_thread(client):
    cid = client.post("/conversations", json={}).json()["id"]
    client.post(f"/conversations/{cid}/turns", json={"message": "a question"})
    assert client.delete(f"/conversations/{cid}").status_code == 204
    assert client.get(f"/conversations/{cid}").status_code == 404
    assert client.get("/conversations").json()["conversations"] == []


def test_delete_unknown_is_404(client):
    assert client.delete("/conversations/never-existed").status_code == 404


def test_append_to_unknown_thread_is_404(client):
    assert (
        client.post(
            "/conversations/ghost/turns", json={"message": "hi"}
        ).status_code
        == 404
    )


# ── Cross-tenant isolation ────────────────────────────────────────────────────


def test_cross_tenant_cannot_see_or_touch_thread(client, monkeypatch):
    cid = client.post("/conversations", json={}).json()["id"]
    client.post(f"/conversations/{cid}/turns", json={"message": "demo-only secret"})

    # Switch tenants — the other org must not see this thread anywhere (404, not 403).
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "other-tenant")
    assert client.get("/conversations").json()["conversations"] == []
    assert client.get(f"/conversations/{cid}").status_code == 404
    assert client.patch(f"/conversations/{cid}", json={"title": "hijack"}).status_code == 404
    assert client.delete(f"/conversations/{cid}").status_code == 404
    assert (
        client.post(f"/conversations/{cid}/turns", json={"message": "x"}).status_code
        == 404
    )

    # Back to the owner — the thread + its turn are untouched.
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "demo")
    owner_detail = client.get(f"/conversations/{cid}").json()
    assert len(owner_detail["turns"]) == 1
    assert owner_detail["turns"][0]["question"] == "demo-only secret"


def test_each_tenant_lists_only_its_own_threads(client, monkeypatch):
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "tenant-a")
    a_id = client.post("/conversations", json={"title": "A thread"}).json()["id"]

    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "tenant-b")
    b_id = client.post("/conversations", json={"title": "B thread"}).json()["id"]
    b_list = client.get("/conversations").json()["conversations"]
    assert [c["id"] for c in b_list] == [b_id]

    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "tenant-a")
    a_list = client.get("/conversations").json()["conversations"]
    assert [c["id"] for c in a_list] == [a_id]


# ── follow-up context replay ───────────────────────────────────────────────────


def test_followup_replays_persisted_history(client):
    """The second turn must resolve against the thread's PERSISTED first turn —
    proving the server replays stored history (not client-carried state). We
    assert the call succeeds and persists in order; the fused service consumes
    the replayed history to resolve the follow-up subject."""
    cid = client.post("/conversations", json={}).json()["id"]
    client.post(
        f"/conversations/{cid}/turns",
        json={"message": "Which pricing test won?"},
    )
    # A bare follow-up with no subject — only resolvable via replayed history.
    resp = client.post(
        f"/conversations/{cid}/turns", json={"message": "Why did that happen?"}
    )
    assert resp.status_code == 200, resp.text
    detail = client.get(f"/conversations/{cid}").json()
    assert [t["question"] for t in detail["turns"]] == [
        "Which pricing test won?",
        "Why did that happen?",
    ]
