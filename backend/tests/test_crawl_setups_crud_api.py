"""Multi-setup CRUD + setup threading (#215/#245 PR 2).

Covers: list/create/get/put/delete on /crawl-setups; create slugifies the name
into a server-minted id and never collides with "default"; delete refuses
"default"; delete is config-only (a stored pack still resolves via the loader —
the integrity invariant); dispatch routes to the chosen setup's config + creds;
the credential pull returns the right setup's creds and never plaintext on GET;
cross-tenant isolation 404s. The singular /crawl-setup endpoints stay covered by
test_crawls_api.py (kept green).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))
os.environ.setdefault(
    "SIDIRA_LOCAL_CRED_KEY", "c2lkaXJhLXRlc3QtY3JlZC1rZXktMzJieXRlcyEhISE="
)

from sidira_simulator.adapters.repositories import (  # noqa: E402
    get_in_memory_crawl_config_repo,
    get_in_memory_repos,
)
from sidira_simulator.main import app  # noqa: E402

_CRED_TOKEN = "ci-pull-token-abc123"


@pytest.fixture
def client(monkeypatch):
    customer_repo, _, _, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    get_in_memory_crawl_config_repo()._configs.clear()
    monkeypatch.setenv("SIDIRA_CRAWLER_CREDENTIALS_TOKEN", _CRED_TOKEN)
    with TestClient(app) as c:
        yield c


def _create_payload(name="iOS Sandbox", **overrides):
    payload = {
        "name": name,
        "capabilities": [
            {"name": "onboarding", "entry_urls": ["https://app.lumen.dev/welcome"]},
        ],
        "sandbox_url": "https://sandbox.lumen.dev",
        "test_users": [
            {"role": "admin", "username": "ios-admin@lumen.dev", "password": "ios-pw-1"},
        ],
        "cadence": "weekly",
        "walk_depth": 4,
    }
    payload.update(overrides)
    return payload


def _put_payload(**overrides):
    payload = {
        "capabilities": [
            {"name": "checkout", "entry_urls": ["https://app.lumen.dev/checkout"]},
        ],
        "sandbox_url": "https://sandbox2.lumen.dev",
        "test_users": [
            {"role": "admin", "username": "ios-admin@lumen.dev", "password": "ios-pw-2"},
        ],
    }
    payload.update(overrides)
    return payload


# ── List / create ──────────────────────────────────────────────────────────


def test_list_empty_then_after_create(client):
    assert client.get("/crawl-setups").json() == []

    resp = client.post("/crawl-setups", json=_create_payload())
    assert resp.status_code == 201
    created = resp.json()
    assert created["name"] == "iOS Sandbox"
    assert created["setup_id"] == "ios-sandbox"  # slugified from the name
    assert created["setup_id"] != "default"
    # No credentials anywhere in the create response.
    assert "ios-pw-1" not in resp.text and "password" not in resp.text

    rows = client.get("/crawl-setups").json()
    assert len(rows) == 1
    assert rows[0]["setup_id"] == "ios-sandbox"
    assert rows[0]["capability_count"] == 1
    assert rows[0]["sandbox_url"] == "https://sandbox.lumen.dev"


def test_create_duplicate_name_gets_unique_suffix(client):
    a = client.post("/crawl-setups", json=_create_payload(name="iOS Sandbox")).json()
    b = client.post("/crawl-setups", json=_create_payload(name="iOS Sandbox")).json()
    assert a["setup_id"] == "ios-sandbox"
    assert b["setup_id"] != a["setup_id"]
    assert b["setup_id"].startswith("ios-sandbox")


def test_create_named_default_does_not_collide_with_reserved(client):
    # A name that slugifies to "default" must NOT claim the reserved id.
    created = client.post("/crawl-setups", json=_create_payload(name="Default")).json()
    assert created["setup_id"] != "default"


# ── Get / put ────────────────────────────────────────────────────────────────


def test_get_by_id_secret_free_and_404_when_absent(client):
    created = client.post("/crawl-setups", json=_create_payload()).json()
    sid = created["setup_id"]

    got = client.get(f"/crawl-setups/{sid}")
    assert got.status_code == 200
    body = got.json()
    assert body["setup_id"] == sid
    assert body["setup"]["sandbox_url"] == "https://sandbox.lumen.dev"
    assert "ios-pw-1" not in got.text and "password" not in got.text

    assert client.get("/crawl-setups/nope").status_code == 404


def test_put_updates_existing_and_404s_for_unknown(client):
    sid = client.post("/crawl-setups", json=_create_payload()).json()["setup_id"]

    resp = client.put(f"/crawl-setups/{sid}", json=_put_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["setup"]["sandbox_url"] == "https://sandbox2.lumen.dev"
    assert [c["name"] for c in body["setup"]["capabilities"]] == ["checkout"]
    assert "ios-pw-2" not in resp.text

    # PUT updates only — it does not create.
    assert client.put("/crawl-setups/ghost", json=_put_payload()).status_code == 404


# ── Delete ───────────────────────────────────────────────────────────────────


def test_delete_removes_setup(client):
    sid = client.post("/crawl-setups", json=_create_payload()).json()["setup_id"]
    assert client.delete(f"/crawl-setups/{sid}").status_code == 204
    assert client.get(f"/crawl-setups/{sid}").status_code == 404
    assert client.get("/crawl-setups").json() == []


def test_delete_refuses_default(client):
    # Seed the default setup via the singular endpoint.
    client.put("/crawl-setup", json=_put_payload())
    resp = client.delete("/crawl-setups/default")
    assert resp.status_code == 409
    # And it's still there.
    assert client.get("/crawl-setup").json()["setup"] is not None


def test_delete_unknown_is_404(client):
    assert client.delete("/crawl-setups/never-existed").status_code == 404


def test_delete_is_config_only_pack_still_resolves(client, tmp_path):
    """Deleting a setup's config row must NOT touch R2: a frozen/stored pack for
    that setup still resolves via the loader (the #214/#215 integrity invariant).

    The pack is written into an ISOLATED tmp store (never the shared fixture), so
    this also proves the delete route has no R2 side effect at all — it only ever
    talks to the config repo."""
    from sidira_simulator.adapters.feature_pack_loader import (
        FeaturePackLoader,
        feature_pack_prefix,
    )
    from sidira_simulator.adapters.r2 import LocalArtifactStore

    created = client.post("/crawl-setups", json=_create_payload()).json()
    sid = created["setup_id"]

    # Write a pack under that setup's R2 prefix in a tmp store, as a crawl would.
    store = LocalArtifactStore(tmp_path)
    base = feature_pack_prefix("demo", sid)
    store.write_text(f"{base}/latest", "2026-W31")
    store.write_text(
        f"{base}/2026-W31/manifest.json",
        '{"customer_id": "demo", "snapshot_version": "2026-W31", '
        '"generated_at": "2026-07-27T00:00:00Z", "capabilities": []}',
    )

    # Delete the CONFIG (the route never touches R2 — no store dependency).
    assert client.delete(f"/crawl-setups/{sid}").status_code == 204
    assert client.get(f"/crawl-setups/{sid}").status_code == 404

    # The pack STILL resolves — config delete left R2 untouched.
    loader = FeaturePackLoader(store)
    assert loader.resolve_latest_version("demo", sid) == "2026-W31"
    assert loader.load_latest_manifest("demo", sid).snapshot_version == "2026-W31"


# ── Cross-tenant isolation ───────────────────────────────────────────────────


def test_cross_tenant_get_is_404(client, monkeypatch):
    sid = client.post("/crawl-setups", json=_create_payload()).json()["setup_id"]
    # Switch tenants — the other org must not see this setup (404, not 403).
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "other-tenant")
    assert client.get(f"/crawl-setups/{sid}").status_code == 404
    assert client.get("/crawl-setups").json() == []
    assert client.delete(f"/crawl-setups/{sid}").status_code == 404


# ── Credential pull selects the right setup, never leaks plaintext on GET ─────


def test_credential_pull_selects_named_setup(client):
    created = client.post(
        "/crawl-setups",
        json=_create_payload(
            test_users=[
                {"role": "admin", "username": "named-admin@x.dev", "password": "named-secret"}
            ]
        ),
    ).json()
    sid = created["setup_id"]
    # Also seed the default setup with a DIFFERENT password, to prove selection.
    client.put(
        "/crawl-setup",
        json=_put_payload(
            test_users=[
                {"role": "admin", "username": "default-admin@x.dev", "password": "default-secret"}
            ]
        ),
    )
    headers = {"Authorization": f"Bearer {_CRED_TOKEN}"}

    # Named setup → named creds.
    resp = client.get(f"/internal/crawl-credentials/demo?setup_id={sid}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["setup_id"] == sid
    logins = {lg["role"]: lg for lg in body["logins"]}
    assert logins["admin"]["password"] == "named-secret"

    # No setup_id → default setup's creds (byte-identical to legacy behavior).
    default_resp = client.get("/internal/crawl-credentials/demo", headers=headers)
    assert default_resp.json()["setup_id"] == "default"
    assert default_resp.json()["logins"][0]["password"] == "default-secret"


def test_crud_get_never_leaks_credentials(client):
    """Belt-and-suspenders: no plaintext password appears in ANY /crawl-setups
    GET — list, detail, or the create/put echo."""
    secret = "never-echo-this-pw"
    created = client.post(
        "/crawl-setups",
        json=_create_payload(
            test_users=[{"role": "admin", "username": "a@x.dev", "password": secret}]
        ),
    )
    sid = created.json()["setup_id"]
    assert secret not in created.text
    assert secret not in client.get("/crawl-setups").text
    assert secret not in client.get(f"/crawl-setups/{sid}").text
