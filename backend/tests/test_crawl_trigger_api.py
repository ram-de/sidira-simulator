"""Fire-and-watch crawl trigger (#193).

POST /crawls inserts a run row and dispatches the crawler CI workflow; GET
/crawls/{id} maps the CI run onto CrawlSummary. The GitHub side is faked at
the dispatcher seam — the dispatch/correlation/phase contract itself is
unit-tested against httpx.MockTransport in test_github_actions.py.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))

from sidira_simulator.adapters.github_actions import (  # noqa: E402
    CrawlDispatchError,
    WorkflowRunState,
)
from sidira_simulator.adapters.repositories import (  # noqa: E402
    get_in_memory_crawl_run_repo,
    get_in_memory_repos,
)
from sidira_simulator.api.deps import (  # noqa: E402
    get_crawl_dispatcher,
    get_feature_pack_loader,
)
from sidira_simulator.main import app  # noqa: E402


def _state(run_id=7001, status="queued", conclusion=None):
    return WorkflowRunState(
        run_id=run_id,
        status=status,
        conclusion=conclusion,
        html_url=f"https://github.com/ram-de/sidira-crawler/actions/runs/{run_id}",
    )


class FakeDispatcher:
    """Scriptable stand-in for GitHubCrawlDispatcher."""

    def __init__(self) -> None:
        self.dispatched: list[tuple[str, str, str]] = []
        self.find_run_result: WorkflowRunState | None = None
        self.run_states: dict[int, WorkflowRunState] = {}
        self.phase: str | None = None
        self.dispatch_error: CrawlDispatchError | None = None
        self.lookup_error: CrawlDispatchError | None = None
        self.lookups: list[tuple[str, object]] = []

    async def dispatch(self, *, crawl_id: str, customer_id: str, crawl_date: str) -> None:
        if self.dispatch_error is not None:
            raise self.dispatch_error
        self.dispatched.append((crawl_id, customer_id, crawl_date))

    async def find_run(self, crawl_id: str) -> WorkflowRunState | None:
        if self.lookup_error is not None:
            raise self.lookup_error
        self.lookups.append(("find_run", crawl_id))
        return self.find_run_result

    async def get_run(self, run_id: int) -> WorkflowRunState:
        if self.lookup_error is not None:
            raise self.lookup_error
        self.lookups.append(("get_run", run_id))
        return self.run_states[run_id]

    async def get_phase(self, run_id: int) -> str | None:
        return self.phase


class FakeLoader:
    def resolve_latest_version(self, customer_id: str) -> str:
        return "2026-W25"


@pytest.fixture
def fake_dispatcher():
    return FakeDispatcher()


@pytest.fixture
def client(fake_dispatcher):
    customer_repo, _, _, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    get_in_memory_crawl_run_repo()._runs.clear()
    app.dependency_overrides[get_crawl_dispatcher] = lambda: fake_dispatcher
    app.dependency_overrides[get_feature_pack_loader] = lambda: FakeLoader()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _start(client):
    resp = client.post("/crawls")
    assert resp.status_code == 202
    return resp.json()


def test_post_dispatches_and_returns_202_pending(client, fake_dispatcher):
    body = _start(client)
    assert re.fullmatch(r"cr-[0-9a-f]{12}", body["id"])
    assert body["status"] == "pending"
    assert body["completed_at"] is None

    assert len(fake_dispatcher.dispatched) == 1
    crawl_id, customer_id, crawl_date = fake_dispatcher.dispatched[0]
    assert crawl_id == body["id"]
    assert customer_id == body["customer_id"]
    # Explicit date, never runner-resolved "today" (CI dates are UTC).
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", crawl_date)


def test_post_dispatch_failure_is_502_and_row_failed(client, fake_dispatcher):
    fake_dispatcher.dispatch_error = CrawlDispatchError("GitHub API unreachable: boom")
    resp = client.post("/crawls")
    assert resp.status_code == 502

    crawls = client.get("/crawls").json()
    assert len(crawls) == 1
    assert crawls[0]["status"] == "failed"
    assert "dispatch failed" in crawls[0]["error"]


def test_get_unknown_id_404s(client):
    assert client.get("/crawls/cr-doesnotexist0").status_code == 404


def test_get_is_customer_scoped(client, monkeypatch):
    body = _start(client)
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "other-tenant")
    assert client.get(f"/crawls/{body['id']}").status_code == 404


def test_pending_until_github_materializes_the_run(client, fake_dispatcher):
    body = _start(client)
    fake_dispatcher.find_run_result = None  # dispatch accepted, run not visible yet
    got = client.get(f"/crawls/{body['id']}").json()
    assert got["status"] == "pending"
    assert got["run_url"] is None


def test_status_lifecycle_pending_running_complete(client, fake_dispatcher):
    body = _start(client)
    crawl_id = body["id"]

    fake_dispatcher.find_run_result = _state(status="queued")
    got = client.get(f"/crawls/{crawl_id}").json()
    assert got["status"] == "pending"
    assert got["run_url"].endswith("/runs/7001")

    # run_id is now persisted — subsequent polls go straight to get_run.
    fake_dispatcher.run_states[7001] = _state(status="in_progress")
    fake_dispatcher.phase = "walking"
    got = client.get(f"/crawls/{crawl_id}").json()
    assert got["status"] == "running"
    assert got["phase"] == "walking"
    assert fake_dispatcher.lookups[-1] == ("get_run", 7001)

    fake_dispatcher.run_states[7001] = _state(status="completed", conclusion="success")
    got = client.get(f"/crawls/{crawl_id}").json()
    assert got["status"] == "complete"
    assert got["snapshot_version"] == "2026-W25"
    assert got["completed_at"] is not None
    assert got["error"] is None

    # Terminal rows answer from the DB — no further GitHub calls.
    lookups_before = len(fake_dispatcher.lookups)
    got = client.get(f"/crawls/{crawl_id}").json()
    assert got["status"] == "complete"
    assert len(fake_dispatcher.lookups) == lookups_before


def test_concurrency_held_run_is_pending_not_failed(client, fake_dispatcher):
    """GitHub reports status "pending" (not in the queued/waiting/requested
    trio) for a run held by a concurrency group — which is exactly what our
    own one-pending-run-per-customer contract produces for a second crawl.
    Only "completed" may terminalize a row."""
    body = _start(client)
    fake_dispatcher.find_run_result = _state(status="pending")
    got = client.get(f"/crawls/{body['id']}").json()
    assert got["status"] == "pending"
    assert got["error"] is None


def test_run_that_never_materializes_eventually_fails(client, fake_dispatcher):
    """Without a cutoff, a dispatch whose run is never found (rejected, or
    pushed out of the lookup window before any poll) reports pending forever."""
    body = _start(client)
    fake_dispatcher.find_run_result = None
    repo = get_in_memory_crawl_run_repo()
    repo._runs[body["id"]]["created_at"] = datetime.now(timezone.utc) - timedelta(minutes=20)

    got = client.get(f"/crawls/{body['id']}").json()
    assert got["status"] == "failed"
    assert "never materialized" in got["error"]


def test_terminal_rows_stay_readable_without_the_dispatch_token(client, fake_dispatcher):
    """A rotated-out token must not lock users out of finished crawls — the
    terminal early-return answers from the DB before the dispatcher is needed.
    A non-terminal row, by contrast, needs GitHub and 503s."""
    done = _start(client)
    fake_dispatcher.find_run_result = _state(status="completed", conclusion="success")
    assert client.get(f"/crawls/{done['id']}").json()["status"] == "complete"
    pending = _start(client)

    app.dependency_overrides[get_crawl_dispatcher] = lambda: None  # token gone
    assert client.get(f"/crawls/{done['id']}").json()["status"] == "complete"
    assert client.get(f"/crawls/{pending['id']}").status_code == 503
    assert client.post("/crawls").status_code == 503


def test_uncrawlable_customer_id_is_rejected_before_dispatch(client, fake_dispatcher, monkeypatch):
    """customer becomes an R2 key segment and a workflow input in the
    secret-bearing crawler repo — mirror crawl.yml's validation here."""
    for bad in ("Bad Tenant!", "../acceptance", "-leading-dash", "a" * 65):
        monkeypatch.setenv("SIDIRA_CUSTOMER_ID", bad)
        resp = client.post("/crawls")
        assert resp.status_code == 400, bad
    assert fake_dispatcher.dispatched == []


def test_clerk_org_id_is_a_crawlable_customer(client, fake_dispatcher, monkeypatch):
    """The production tenant key is the Clerk org id, passed through verbatim
    (api/auth.py) — underscore + mixed case must clear the charset check."""
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "org_2NXxKpDuS3vLkAhQeFdGhI8mWyZ")
    resp = client.post("/crawls")
    assert resp.status_code == 202
    assert len(fake_dispatcher.dispatched) == 1


def test_cancelled_run_reports_superseded(client, fake_dispatcher):
    body = _start(client)
    fake_dispatcher.find_run_result = _state(status="completed", conclusion="cancelled")
    got = client.get(f"/crawls/{body['id']}").json()
    assert got["status"] == "failed"
    assert "superseded" in got["error"]


def test_failed_run_carries_conclusion(client, fake_dispatcher):
    body = _start(client)
    fake_dispatcher.find_run_result = _state(status="completed", conclusion="failure")
    got = client.get(f"/crawls/{body['id']}").json()
    assert got["status"] == "failed"
    assert "failure" in got["error"]


def test_flaky_github_poll_is_502_not_a_failed_crawl(client, fake_dispatcher):
    body = _start(client)
    fake_dispatcher.lookup_error = CrawlDispatchError("rate limited")
    assert client.get(f"/crawls/{body['id']}").status_code == 502

    # The row kept its last-known status; the next poll recovers.
    fake_dispatcher.lookup_error = None
    fake_dispatcher.find_run_result = _state(status="queued")
    got = client.get(f"/crawls/{body['id']}").json()
    assert got["status"] == "pending"


def test_list_is_newest_first_and_customer_scoped(client, monkeypatch):
    first = _start(client)
    second = _start(client)
    listed = client.get("/crawls").json()
    assert [c["id"] for c in listed] == [second["id"], first["id"]]

    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "other-tenant")
    assert client.get("/crawls").json() == []
