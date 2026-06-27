"""Append-only workspace audit log — #48.

Covers, end to end against the in-memory stack:

  * EVENTS ARE WRITTEN on each instrumented workspace-mutating action
    (experiment-source connected/tested/deleted/reimported, feature-store
    created/deleted, crawl-config created/updated/deleted, persona rebuild
    triggered) — actor = current_user_id, customer = current_customer_id.
  * APPEND-ONLY — the repo API exposes only record + list; it has NO update or
    delete method (a structural assertion, so a future mutate method fails here).
  * READ ENDPOINT — GET /admin/audit is admin-only (member → 403), customer-
    scoped (a cross-tenant read is empty), newest-first, and paginated.
  * NO SECRET LEAKS — a connected source's api_key / a connection password never
    lands in any audit row's metadata.
"""

from __future__ import annotations

import asyncio
import inspect
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))
# Connecting a source / feature store encrypts at rest — set the local-key
# fallback before the app imports (mirrors the other route-test modules).
os.environ.setdefault("SIDIRA_LOCAL_CRED_KEY", "c2lkaXJhLXRlc3QtY3JlZC1rZXktMzJieXRlcyEhISE=")

from sidira_simulator.api import auth  # noqa: E402
from sidira_simulator.adapters.repositories import (  # noqa: E402
    AuditLogRepo,
    InMemoryAuditLogRepo,
    get_in_memory_audit_log_repo,
    get_in_memory_crawl_config_repo,
    get_in_memory_crawl_run_repo,
    get_in_memory_experiment_connection_repo,
    get_in_memory_experiment_import_run_repo,
    get_in_memory_feature_store_connection_repo,
    get_in_memory_persona_build_repo,
    get_in_memory_repos,
)
from sidira_simulator.main import app, create_app  # noqa: E402
from sidira_simulator.services.connectors import csv_connector, statsig_connector  # noqa: E402
from sidira_simulator.services.connectors.ingestion_store import get_ingestion_store  # noqa: E402
from sidira_simulator.services.connectors.mapping import suggest_mapping  # noqa: E402

DUMMY_SECRET = "sk_test_dummy"
_STATSIG_SECRET = "secret-statsig-key"
_SNOWFLAKE_PASSWORD = "super-secret-pw"


def _clear_state() -> None:
    customer_repo, _, _, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    get_in_memory_experiment_connection_repo()._connections.clear()
    get_in_memory_experiment_import_run_repo()._runs.clear()
    get_in_memory_feature_store_connection_repo()._connections.clear()
    get_in_memory_crawl_config_repo()._configs.clear()
    get_in_memory_crawl_run_repo()._runs.clear()
    get_in_memory_persona_build_repo()._builds.clear()
    get_in_memory_audit_log_repo()._entries.clear()
    get_ingestion_store().clear()


@pytest.fixture
def client(monkeypatch):
    for prefix in ("SIDIRA_", "PYTHIA_"):
        monkeypatch.delenv(f"{prefix}CLERK_SECRET_KEY", raising=False)
        monkeypatch.delenv(f"{prefix}ORG_ROLE", raising=False)
    _clear_state()
    with TestClient(app) as c:
        yield c


def _statsig_mapping() -> dict:
    return suggest_mapping(list(csv_connector.TEMPLATE_COLUMNS)).model_dump()


def _source_body(name: str = "Prod Statsig") -> dict:
    return {
        "name": name,
        "kind": "statsig",
        "config": {"api_key": _STATSIG_SECRET},
        "mapping": _statsig_mapping(),
    }


def _fs_body(name: str = "Prod Snowflake") -> dict:
    return {
        "name": name,
        "kind": "snowflake",
        "account": "acme-xy12345",
        "user": "SVC",
        "password": _SNOWFLAKE_PASSWORD,
        "warehouse": "WH",
        "role": "RO",
        "database": "PROD",
        "schema": "PUBLIC",
    }


def _crawl_setup_body() -> dict:
    return {
        "capabilities": [
            {"name": "onboarding", "entry_urls": ["https://app.example.com/welcome"]},
        ],
        "sandbox_url": "https://sandbox.example.com",
        "test_users": [
            {"role": "admin", "username": "admin@example.com", "password": "pw-1"},
        ],
        "cadence": "weekly",
        "walk_depth": 4,
    }


def _actions(client: TestClient) -> list[str]:
    rows = client.get("/admin/audit").json()
    return [r["action"] for r in rows]


# ── Events are written per instrumented action ──────────────────────────────


def test_experiment_source_connect_emits_event(client) -> None:
    cid = client.post("/experiment-sources", json=_source_body()).json()["id"]
    rows = client.get("/admin/audit").json()
    assert len(rows) == 1
    row = rows[0]
    assert row["action"] == "experiment_source.connected"
    assert row["target_type"] == "experiment_source"
    assert row["target_id"] == cid
    # actor = current_user_id (keyless dev/test fallback).
    assert row["actor_user_id"] == "demo-user"


def test_experiment_source_test_delete_reimport_emit(client, monkeypatch) -> None:
    monkeypatch.setattr(
        statsig_connector, "_fetch_experiments", lambda api_key, *, timeout=20.0: []
    )
    cid = client.post("/experiment-sources", json=_source_body()).json()["id"]
    assert client.post(f"/experiment-sources/{cid}/test").status_code == 204
    assert client.post(f"/experiment-sources/{cid}/reimport").status_code == 200
    assert client.delete(f"/experiment-sources/{cid}").status_code == 204
    # Newest-first: delete is the most recent event.
    actions = _actions(client)
    assert actions[0] == "experiment_source.deleted"
    assert set(actions) == {
        "experiment_source.connected",
        "experiment_source.tested",
        "experiment_source.reimported",
        "experiment_source.deleted",
    }


def test_feature_store_create_and_delete_emit(client) -> None:
    cid = client.post("/feature-stores", json=_fs_body()).json()["id"]
    assert client.delete(f"/feature-stores/{cid}").status_code == 204
    actions = _actions(client)
    assert actions == ["feature_store.deleted", "feature_store.created"]


def test_crawl_config_create_update_delete_emit(client) -> None:
    created = client.post(
        "/crawl-setups", json={"name": "Marketing site", **_crawl_setup_body()}
    )
    assert created.status_code == 201
    setup_id = created.json()["setup_id"]
    assert client.put(f"/crawl-setups/{setup_id}", json=_crawl_setup_body()).status_code == 200
    assert client.delete(f"/crawl-setups/{setup_id}").status_code == 204
    actions = _actions(client)
    assert actions == ["crawl_config.deleted", "crawl_config.updated", "crawl_config.created"]


def test_singular_crawl_setup_save_emits_update(client) -> None:
    assert client.put("/crawl-setup", json=_crawl_setup_body()).status_code == 200
    rows = client.get("/admin/audit").json()
    assert rows[0]["action"] == "crawl_config.updated"
    assert rows[0]["target_id"] == "default"


def test_persona_rebuild_trigger_emits_event(client, monkeypatch) -> None:
    # Worker mode → POST only inserts the PENDING row + audits, never runs the
    # in-process build (which needs the ML stack). The TRIGGER is what we audit.
    monkeypatch.setenv("SIDIRA_PERSONA_BUILD_MODE", "worker")
    body = {
        "connection_id": "fs-nonexistent",
        "source_query": "SELECT * FROM users",
        "column_mapping": {},
        "stability_threshold": 0.65,
    }
    resp = client.post("/persona-builds", json=body)
    assert resp.status_code == 202
    build_id = resp.json()["id"]
    rows = client.get("/admin/audit").json()
    assert rows[0]["action"] == "persona_build.triggered"
    assert rows[0]["target_id"] == build_id
    assert rows[0]["metadata"]["connection_id"] == "fs-nonexistent"


# ── No secret leaks into metadata ───────────────────────────────────────────


def test_no_secret_in_any_audit_row(client) -> None:
    client.post("/experiment-sources", json=_source_body())
    client.post("/feature-stores", json=_fs_body())
    text = client.get("/admin/audit").text
    assert _STATSIG_SECRET not in text
    assert _SNOWFLAKE_PASSWORD not in text
    # No secret keys leaked as metadata keys either.
    for row in client.get("/admin/audit").json():
        meta = row.get("metadata") or {}
        assert "api_key" not in meta
        assert "password" not in meta
        assert "connection_string" not in meta


# ── Newest-first + pagination ───────────────────────────────────────────────


def test_list_is_newest_first_and_paginated(client) -> None:
    for i in range(5):
        client.post("/experiment-sources", json=_source_body(name=f"S{i}")).raise_for_status()
    page1 = client.get("/admin/audit?limit=2&offset=0").json()
    page2 = client.get("/admin/audit?limit=2&offset=2").json()
    assert len(page1) == 2 and len(page2) == 2
    # Distinct pages, all newest-first by created_at.
    ids = [r["id"] for r in page1 + page2]
    assert len(set(ids)) == 4
    all_rows = client.get("/admin/audit?limit=50").json()
    times = [r["created_at"] for r in all_rows]
    assert times == sorted(times, reverse=True)


# ── RBAC + tenant scoping on the read endpoint ──────────────────────────────


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
        resp = c.get("/admin/audit")
    assert resp.status_code == 403


def _admin_client(monkeypatch, *, customer_id: str, user_id: str = "user_a"):
    for prefix in ("SIDIRA_", "PYTHIA_"):
        monkeypatch.delenv(f"{prefix}CLERK_SECRET_KEY", raising=False)
        monkeypatch.delenv(f"{prefix}ORG_ROLE", raising=False)
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    monkeypatch.setattr(
        auth,
        "authenticate",
        lambda request: auth.AuthState(
            user_id=user_id, customer_id=customer_id, org_role="admin"
        ),
    )
    return TestClient(create_app())


def test_admin_session_reaches_audit(monkeypatch) -> None:
    _clear_state()
    with _admin_client(monkeypatch, customer_id="org_admin") as c:
        assert c.get("/admin/audit").status_code == 200


def test_audit_is_tenant_scoped(monkeypatch) -> None:
    _clear_state()
    # Org A connects a source (and audits it under org_a).
    with _admin_client(monkeypatch, customer_id="org_a", user_id="user_a") as ca:
        ca.post("/experiment-sources", json=_source_body()).raise_for_status()
        a_rows = ca.get("/admin/audit").json()
    assert len(a_rows) == 1 and a_rows[0]["actor_user_id"] == "user_a"
    # Org B sees an empty trail — a cross-tenant read never surfaces A's events.
    with _admin_client(monkeypatch, customer_id="org_b", user_id="user_b") as cb:
        b_rows = cb.get("/admin/audit").json()
    assert b_rows == []


# ── Append-only: the repo API has no mutate/delete ──────────────────────────


def test_repo_api_is_append_only() -> None:
    repo: AuditLogRepo = InMemoryAuditLogRepo()
    public = {n for n in dir(repo) if not n.startswith("_")}
    # The ONLY public methods are the append (record) + the read (list).
    assert public == {"record", "list_for_customer"}
    # Defensive: no update/delete-flavored method sneaked in.
    for forbidden in ("update", "delete", "remove", "edit", "patch", "set"):
        assert not any(forbidden in n for n in public), forbidden


def test_inmemory_repo_records_and_lists_newest_first() -> None:
    repo = InMemoryAuditLogRepo()

    async def _run() -> None:
        for i in range(3):
            await repo.record(
                entry_id=f"al-{i}",
                customer_id="org_a",
                actor_user_id="user_a",
                action=f"thing.{i}",
                target_type="thing",
                target_id=str(i),
            )
        await repo.record(
            entry_id="al-other",
            customer_id="org_b",
            actor_user_id="user_b",
            action="thing.x",
            target_type="thing",
        )
        rows = await repo.list_for_customer("org_a")
        # Newest-first, tenant-scoped (org_b's row excluded).
        assert [r["action"] for r in rows] == ["thing.2", "thing.1", "thing.0"]
        assert all(r["customer_id"] == "org_a" for r in rows)
        # Pagination.
        assert len(await repo.list_for_customer("org_a", limit=1)) == 1
        assert (await repo.list_for_customer("org_a", limit=1, offset=1))[0]["action"] == "thing.1"

    asyncio.run(_run())


def test_record_returns_timestamped_row() -> None:
    repo = InMemoryAuditLogRepo()
    row = asyncio.run(
        repo.record(
            entry_id="al-1",
            customer_id="org_a",
            actor_user_id=None,
            action="thing.created",
            target_type="thing",
        )
    )
    assert isinstance(row["created_at"], datetime)
    assert row["created_at"].tzinfo is not None
    # actor may be None (a future system event); the row still records.
    assert row["actor_user_id"] is None


def test_record_signature_takes_no_mutating_kwargs() -> None:
    # The record() signature is INSERT-shaped only — there is no row-id-to-update
    # parameter, which would be the seam an in-place mutation would need.
    sig = inspect.signature(InMemoryAuditLogRepo.record)
    params = set(sig.parameters)
    assert "entry_id" in params  # minted by the caller, INSERT-only
    assert not (params & {"existing_id", "update_fields", "patch"})
