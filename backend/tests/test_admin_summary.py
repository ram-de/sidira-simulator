"""Admin-console summary endpoint (#49) — GET /admin/summary.

Covers, in three layers:
  1. RBAC — admin-only (a member session → 403; the keyless dev/test path and an
     admin session reach it);
  2. tenant scoping — one org's aggregate never counts another org's rows;
  3. NO secret leakage — the payload is counts / status / metadata only; no
     credential, host, password, connection string, or api_key ever appears,
     and no per-user conversation field is present (no cross-user backdoor, #42).

The aggregation is pure (no migration): it reduces the existing per-family repo
rows to counts + last-status, so the in-memory repos drive every assertion.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))
# Source/connection creation in the seed path encrypts at rest — set the local
# key fallback before the app imports (mirrors the other route-test modules).
os.environ.setdefault("SIDIRA_LOCAL_CRED_KEY", "c2lkaXJhLXRlc3QtY3JlZC1rZXktMzJieXRlcyEhISE=")

from sidira_simulator.api import auth  # noqa: E402
from sidira_simulator.adapters.repositories import (  # noqa: E402
    get_in_memory_crawl_config_repo,
    get_in_memory_crawl_run_repo,
    get_in_memory_experiment_connection_repo,
    get_in_memory_feature_store_connection_repo,
    get_in_memory_persona_build_repo,
    get_in_memory_repos,
)
from sidira_simulator.main import app, create_app  # noqa: E402

DUMMY_SECRET = "sk_test_dummy"


def _clear_state() -> None:
    customer_repo, _, _, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    get_in_memory_experiment_connection_repo()._connections.clear()
    get_in_memory_feature_store_connection_repo()._connections.clear()
    get_in_memory_crawl_config_repo()._configs.clear()
    get_in_memory_crawl_run_repo()._runs.clear()
    get_in_memory_persona_build_repo()._builds.clear()


def _seed(customer_id: str) -> None:
    """Seed one of each family for ``customer_id`` directly via the repos.

    The in-memory repos are plain dict stores — their async methods never touch
    an event loop, so a private ``asyncio.run`` here is safe and does not collide
    with the TestClient's loop.
    """
    asyncio.run(_seed_async(customer_id))


async def _seed_async(customer_id: str) -> None:
    now = datetime.now(timezone.utc)

    exp = get_in_memory_experiment_connection_repo()
    await exp.insert(
        {
            "id": f"es-{customer_id}",
            "customer_id": customer_id,
            "name": "Prod Statsig",
            "kind": "statsig",
            "display_config": {"_mapping": {"columns": {}}},
            # A real-looking encrypted blob; the summary must never read it.
            "credentials_enc": {"v": 1, "ct": "ZW5jcnlwdGVk", "iv": "aXY="},
            "status": "connected",
            "created_by": "user_x",
        }
    )
    await exp.mark_import(f"es-{customer_id}", customer_id, status="connected", imported_at=now)

    fs = get_in_memory_feature_store_connection_repo()
    await fs.insert(
        {
            "id": f"fs-{customer_id}",
            "customer_id": customer_id,
            "name": "Warehouse",
            "kind": "snowflake",
            "account": "acme-xy12345",
            "user": "SVC_SIDIRA",
            "warehouse": "WH",
            "role": "RO",
            "database": "PROD",
            "schema": "PUBLIC",
            "password_enc": {"v": 1, "ct": "cGFzc3dvcmQ=", "iv": "aXY="},
        }
    )

    crawl = get_in_memory_crawl_config_repo()
    await crawl.upsert(customer_id, {"sandbox_url": "https://s.example"}, name="Default")

    runs = get_in_memory_crawl_run_repo()
    await runs.insert(
        {
            "id": f"cr-{customer_id}",
            "customer_id": customer_id,
            "status": "complete",
            "created_at": now,
        }
    )

    builds = get_in_memory_persona_build_repo()
    row = await builds.create(
        build_id=f"pb-{customer_id}",
        customer_id=customer_id,
        connection_id=f"fs-{customer_id}",
    )
    await builds.update_status(
        row["id"],
        customer_id,
        "complete",
        pack_version="2026.06.01",
        persona_count=7,
        completed_at=now,
    )


# ── Keyless (dev/test) client — require_admin falls back to admin ──────────────


@pytest.fixture
def client(monkeypatch):
    for prefix in ("SIDIRA_", "PYTHIA_"):
        monkeypatch.delenv(f"{prefix}CLERK_SECRET_KEY", raising=False)
        monkeypatch.delenv(f"{prefix}ORG_ROLE", raising=False)
    _clear_state()
    with TestClient(app) as c:
        yield c


def _admin_client(monkeypatch, *, customer_id: str):
    for prefix in ("SIDIRA_", "PYTHIA_"):
        monkeypatch.delenv(f"{prefix}CLERK_SECRET_KEY", raising=False)
        monkeypatch.delenv(f"{prefix}ORG_ROLE", raising=False)
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    monkeypatch.setattr(
        auth,
        "authenticate",
        lambda request: auth.AuthState(
            user_id="user_a", customer_id=customer_id, org_role="admin"
        ),
    )
    return TestClient(create_app())


# ── RBAC ───────────────────────────────────────────────────────────────────


def test_member_is_forbidden(monkeypatch) -> None:
    _clear_state()
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    monkeypatch.setattr(
        auth,
        "authenticate",
        lambda request: auth.AuthState(
            user_id="user_m", customer_id="org_member", org_role="basic_member"
        ),
    )
    with TestClient(create_app()) as c:
        resp = c.get("/admin/summary")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "admin role required for this action"


def test_keyless_path_reaches_summary(client) -> None:
    # The suite's default keyless path → admin fallback → 200.
    resp = client.get("/admin/summary")
    assert resp.status_code == 200


def test_admin_session_reaches_summary(monkeypatch) -> None:
    _clear_state()
    with _admin_client(monkeypatch, customer_id="org_admin") as c:
        resp = c.get("/admin/summary")
    assert resp.status_code == 200


# ── Aggregation correctness ─────────────────────────────────────────────────


def test_summary_aggregates_each_family(client) -> None:
    # Seed for the keyless default customer ("demo").
    _seed("demo")

    resp = client.get("/admin/summary")
    assert resp.status_code == 200
    body = resp.json()

    assert body["customer_id"] == "demo"
    assert body["experiment_sources"]["total"] == 1
    assert body["experiment_sources"]["connected"] == 1
    assert body["experiment_sources"]["last_import_at"] is not None

    assert body["feature_stores"]["total"] == 1
    # never tested → untested bucket
    assert body["feature_stores"]["untested"] == 1

    assert body["crawl"]["configured"] is True
    assert body["crawl"]["setup_count"] == 1
    assert body["crawl"]["last_run_status"] == "complete"

    assert body["personas"]["pack_version"] == "2026.06.01"
    assert body["personas"]["persona_count"] == 7
    assert body["personas"]["total_builds"] == 1


def test_empty_workspace_is_all_zeros(client) -> None:
    resp = client.get("/admin/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["experiment_sources"]["total"] == 0
    assert body["feature_stores"]["total"] == 0
    assert body["crawl"]["configured"] is False
    assert body["personas"]["pack_version"] is None
    assert body["personas"]["total_builds"] == 0


# ── Tenant isolation ─────────────────────────────────────────────────────────


def test_tenant_scoped(monkeypatch) -> None:
    _clear_state()
    # Seed org A only; org B's summary must see nothing.
    _seed("org_a")

    with _admin_client(monkeypatch, customer_id="org_a") as ca:
        a = ca.get("/admin/summary").json()
    with _admin_client(monkeypatch, customer_id="org_b") as cb:
        b = cb.get("/admin/summary").json()

    assert a["experiment_sources"]["total"] == 1
    assert a["feature_stores"]["total"] == 1
    assert a["crawl"]["configured"] is True

    assert b["customer_id"] == "org_b"
    assert b["experiment_sources"]["total"] == 0
    assert b["feature_stores"]["total"] == 0
    assert b["crawl"]["configured"] is False
    assert b["personas"]["total_builds"] == 0


# ── No secret leakage / no conversation backdoor ─────────────────────────────


def test_no_secret_in_payload(client) -> None:
    _seed("demo")
    resp = client.get("/admin/summary")
    raw = resp.text.lower()

    # The encrypted blob ciphertext + any credential-shaped token must NOT appear.
    for needle in (
        "credentials_enc",
        "password_enc",
        "password",
        "api_key",
        "connection_string",
        "zw5jcnlwdgvk",  # the seeded exp ciphertext (lowercased)
        "cgfzc3dvcmq=",  # the seeded fs password ciphertext (lowercased)
    ):
        assert needle not in raw, f"leaked {needle!r} in summary payload"


def test_no_conversation_view(client) -> None:
    # The admin summary must NOT add any cross-user conversation surface (#42 /
    # council "no view-all-conversations backdoor"). Assert the aggregate has no
    # conversation/thread/memory key at any level.
    resp = client.get("/admin/summary")
    body = json.loads(resp.text)
    flat = json.dumps(body).lower()
    for forbidden in ("conversation", "thread", "memory", "message"):
        assert forbidden not in flat, f"unexpected {forbidden!r} key in summary"
