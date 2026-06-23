"""Fire-and-watch crawl trigger (#193).

POST /crawls inserts a run row and dispatches the crawler CI workflow; GET
/crawls/{id} maps the CI run onto CrawlSummary. The GitHub side is faked at
the dispatcher seam — the dispatch/correlation/phase contract itself is
unit-tested against httpx.MockTransport in test_github_actions.py.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))
# A configured tenant's saved setup now carries an at-rest credential blob
# (#206 Slice C), and the trigger refuses to dispatch a real tenant whose setup
# lacks it — so seeds must produce that blob. Same test-only key as the other
# crawl suites.
os.environ.setdefault(
    "SIDIRA_LOCAL_CRED_KEY", "c2lkaXJhLXRlc3QtY3JlZC1rZXktMzJieXRlcyEhISE="
)
# The dispatch preflight also refuses to dispatch a real tenant when the
# credential-pull bearer is unset (the pull would 503 mid-crawl). Configure it
# so the happy-path tests dispatch; the dedicated test below clears it.
os.environ.setdefault("SIDIRA_CRAWLER_CREDENTIALS_TOKEN", "ci-pull-token-trigger-tests")

from sidira_simulator.adapters import credentials  # noqa: E402
from sidira_simulator.adapters.github_actions import (  # noqa: E402
    CrawlDispatchError,
    WorkflowRunState,
)
from sidira_simulator.adapters.repositories import (  # noqa: E402
    get_in_memory_crawl_config_repo,
    get_in_memory_crawl_run_repo,
    get_in_memory_repos,
)
from sidira_simulator.api.deps import (  # noqa: E402
    get_crawl_dispatcher,
    get_feature_pack_loader,
)
from sidira_simulator.main import app  # noqa: E402
from sidira_simulator.schemas.crawl import (  # noqa: E402
    CrawlCapability,
    CrawlRoleCredential,
    CrawlSetup,
)


def _setup_dict(sandbox_url: str = "https://sandbox.example.com") -> dict:
    """A minimal valid CrawlSetup, stored as the repo persists it."""
    return CrawlSetup(
        capabilities=[
            CrawlCapability(name="onboarding", entry_urls=[f"{sandbox_url}/start"]),
        ],
        sandbox_url=sandbox_url,
        test_users=[CrawlRoleCredential(role="member", username="member@example.com")],
        walk_depth=3,
    ).model_dump()


def _seed_config(customer_id: str, *, with_credentials: bool = True) -> None:
    """Persist a crawl setup for ``customer_id`` straight into the in-memory
    repo (the route refuses to dispatch a tenant that has none). By default it
    also attaches the at-rest credential blob the real PUT path produces; pass
    ``with_credentials=False`` to simulate a setup saved before #206 Slice C."""
    from sidira_simulator.api.crawls import CREDENTIALS_ENC_KEY

    config = _setup_dict()
    if with_credentials:
        blob = credentials.encrypt({"member": "member-pw-s3cret"})
        config[CREDENTIALS_ENC_KEY] = credentials.serialize_blob(blob)
    get_in_memory_crawl_config_repo()._configs[(customer_id, "default")] = {
        "customer_id": customer_id,
        "setup_id": "default",
        "name": "Default",
        "config_json": config,
        "updated_at": datetime.now(timezone.utc),
    }


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
        self.dispatched: list[tuple[str, str, str, str | None]] = []
        self.find_run_result: WorkflowRunState | None = None
        self.run_states: dict[int, WorkflowRunState] = {}
        self.phase: str | None = None
        self.dispatch_error: CrawlDispatchError | None = None
        self.lookup_error: CrawlDispatchError | None = None
        self.lookups: list[tuple[str, object]] = []

    async def dispatch(
        self,
        *,
        crawl_id: str,
        customer_id: str,
        crawl_date: str,
        config_json: str | None = None,
    ) -> None:
        if self.dispatch_error is not None:
            raise self.dispatch_error
        self.dispatched.append((crawl_id, customer_id, crawl_date, config_json))

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
    get_in_memory_crawl_config_repo()._configs.clear()
    # Most tests post as the default "demo" tenant; a real tenant must have a
    # saved setup before the route will dispatch (#206), so seed one here.
    _seed_config("demo")
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
    crawl_id, customer_id, crawl_date, config_json = fake_dispatcher.dispatched[0]
    assert crawl_id == body["id"]
    assert customer_id == body["customer_id"]
    # Explicit date, never runner-resolved "today" (CI dates are UTC).
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", crawl_date)
    # A configured tenant ships its non-secret setup to the workflow.
    assert config_json is not None
    payload = json.loads(config_json)
    assert payload["sandbox_url"] == "https://sandbox.example.com"
    assert payload["product_id"] == "default"
    assert payload["roles"] == ["member"]
    assert [c["name"] for c in payload["capabilities"]] == ["onboarding"]
    # Credentials never cross the dispatch boundary.
    assert "username" not in config_json
    assert "password" not in config_json


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
    org = "org_2NXxKpDuS3vLkAhQeFdGhI8mWyZ"
    _seed_config(org)
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", org)
    resp = client.post("/crawls")
    assert resp.status_code == 202
    assert len(fake_dispatcher.dispatched) == 1


def test_unconfigured_tenant_cannot_crawl(client, fake_dispatcher, monkeypatch):
    """A real tenant with no saved setup is 400'd before any run row or
    dispatch — a crawl without capabilities could never produce a pack."""
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "org_neverConfigured123")
    resp = client.post("/crawls")
    assert resp.status_code == 400
    assert "crawl setup" in resp.json()["detail"]
    assert fake_dispatcher.dispatched == []
    assert client.get("/crawls").json() == []  # no orphaned pending row


def test_setup_without_stored_credentials_is_blocked_before_dispatch(
    client, fake_dispatcher, monkeypatch
):
    """A setup saved before Slice C has no at-rest credential blob, so the
    crawler's pull would 404 and CI would start a ~40-min walk with no logins.
    Reject it up front with the same re-save guidance — nothing dispatches
    (codex P2, #206 Slice C)."""
    _seed_config("org_preSliceC", with_credentials=False)
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "org_preSliceC")
    resp = client.post("/crawls")
    assert resp.status_code == 400
    assert "re-save" in resp.json()["detail"]
    assert fake_dispatcher.dispatched == []
    assert client.get("/crawls").json() == []  # no orphaned pending row


def test_dispatch_blocked_when_pull_token_unconfigured(client, fake_dispatcher, monkeypatch):
    """A real tenant with stored credentials still must not dispatch when the
    credential-pull bearer is unset — the crawler's run-start pull would 503 and
    CI would walk for ~40 min with no logins. Fail closed with a 503 before
    dispatch (codex P2, #206 Slice C)."""
    monkeypatch.delenv("SIDIRA_CRAWLER_CREDENTIALS_TOKEN", raising=False)
    monkeypatch.delenv("PYTHIA_CRAWLER_CREDENTIALS_TOKEN", raising=False)
    resp = client.post("/crawls")  # demo is seeded with credentials by the fixture
    assert resp.status_code == 503
    assert "SIDIRA_CRAWLER_CREDENTIALS_TOKEN" in resp.json()["detail"]
    assert fake_dispatcher.dispatched == []
    assert client.get("/crawls").json() == []  # no orphaned pending row


def test_dispatch_blocked_when_stored_credentials_undecryptable(client, fake_dispatcher):
    """A blob that is present but undecryptable (key rotated after it was written,
    or ciphertext corrupted) must 503 before dispatch — otherwise the failure
    only surfaces when the crawler's run-start pull 503s mid-crawl (codex P2,
    #206 Slice C)."""
    from sidira_simulator.api.crawls import CREDENTIALS_ENC_KEY

    row = get_in_memory_crawl_config_repo()._configs[("demo", "default")]
    row["config_json"][CREDENTIALS_ENC_KEY]["ciphertext"] = "QUJDREVG"  # valid b64, bad tag
    resp = client.post("/crawls")
    assert resp.status_code == 503
    assert "decrypt" in resp.json()["detail"]
    assert fake_dispatcher.dispatched == []
    assert client.get("/crawls").json() == []  # no orphaned pending row


def test_dispatch_blocked_when_a_role_login_is_missing(client, fake_dispatcher):
    """The blob decrypts but lacks a login for a role the setup expects (e.g. a
    role added after the last save) — reject with re-save guidance rather than
    dispatch a partial-login crawl (codex P2, #206 Slice C)."""
    from sidira_simulator.api.crawls import CREDENTIALS_ENC_KEY

    row = get_in_memory_crawl_config_repo()._configs[("demo", "default")]
    # Re-encrypt an empty secret map: the setup's "member" role now has no login.
    row["config_json"][CREDENTIALS_ENC_KEY] = credentials.serialize_blob(credentials.encrypt({}))
    resp = client.post("/crawls")
    assert resp.status_code == 400
    assert "member" in resp.json()["detail"]
    assert fake_dispatcher.dispatched == []
    assert client.get("/crawls").json() == []  # no orphaned pending row


def test_sandbox_dispatches_without_the_pull_token(client, fake_dispatcher, monkeypatch):
    """The sandbox runs the mock path and never pulls credentials, so a missing
    pull bearer must not block it (the exemption mirrors the missing-blob case)."""
    monkeypatch.delenv("SIDIRA_CRAWLER_CREDENTIALS_TOKEN", raising=False)
    monkeypatch.delenv("PYTHIA_CRAWLER_CREDENTIALS_TOKEN", raising=False)
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "streamly-sandbox")
    resp = client.post("/crawls")
    assert resp.status_code == 202
    assert len(fake_dispatcher.dispatched) == 1


def test_streamly_sandbox_dispatches_without_a_saved_setup(client, fake_dispatcher, monkeypatch):
    """The sandbox demo is the one exemption: it runs crawl.yml's mock
    acceptance path, so it dispatches with no config_json (#206 Slice B)."""
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "streamly-sandbox")
    resp = client.post("/crawls")
    assert resp.status_code == 202
    assert len(fake_dispatcher.dispatched) == 1
    _, customer_id, _, config_json = fake_dispatcher.dispatched[0]
    assert customer_id == "streamly-sandbox"
    assert config_json is None


def test_legacy_invalid_setup_is_409_not_500(client, fake_dispatcher, monkeypatch):
    """A row saved before #206 tightened URL validation (e.g. a basic-auth
    sandbox URL) must not 500 on rehydration — the trigger and the setup GET
    both surface a controlled 409 asking the operator to re-save, and nothing
    dispatches."""
    bad = _setup_dict()
    bad["sandbox_url"] = "https://user:pass@legacy.example.com"
    get_in_memory_crawl_config_repo()._configs[("org_legacy", "default")] = {
        "customer_id": "org_legacy",
        "setup_id": "default",
        "name": "Default",
        "config_json": bad,
        "updated_at": datetime.now(timezone.utc),
    }
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "org_legacy")

    trigger = client.post("/crawls")
    assert trigger.status_code == 409
    assert "re-save" in trigger.json()["detail"]
    assert fake_dispatcher.dispatched == []
    assert client.get("/crawls").json() == []  # no orphaned pending row

    assert client.get("/crawl-setup").status_code == 409


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
