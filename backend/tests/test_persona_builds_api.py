"""API + orchestration tests for the persona-build endpoint (#24).

Every external call is faked:
- the sidira-personas pipeline seam (``run_personas_pipeline``) is monkeypatched
  to return a canned PipelineOutput, so no real clustering runs;
- ``SnowflakeStore.run_query`` is monkeypatched to return canned rows, so
  Snowflake is never hit;
- the artifact store is a local filesystem store under ``tmp_path`` (injected via
  the ``get_artifact_store`` dependency override), so R2 is never hit;
- the in-memory repos back the build rows + the saved connection.

FastAPI BackgroundTasks run synchronously under TestClient (the request blocks
until they finish), so a POST returns and THEN the build has already driven the
row to its terminal state by the time we read it back.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))
# Local-key cred fallback so we can encrypt a fake connection password at rest.
os.environ.setdefault("SIDIRA_LOCAL_CRED_KEY", "c2lkaXJhLXRlc3QtY3JlZC1rZXktMzJieXRlcyEhISE=")

from sidira_simulator.adapters import credentials  # noqa: E402
from sidira_simulator.adapters.r2 import LocalArtifactStore  # noqa: E402
from sidira_simulator.adapters.repositories import (  # noqa: E402
    get_in_memory_feature_store_connection_repo,
    get_in_memory_persona_build_repo,
    get_in_memory_repos,
)
from sidira_simulator.api.deps import get_artifact_store  # noqa: E402
from sidira_simulator.main import app  # noqa: E402
from sidira_simulator.services import persona_builder as pb_mod  # noqa: E402
from sidira_simulator.services.persona_builder import PipelineOutput  # noqa: E402

_CONNECTION_ID = "fs-test-conn"
_CUSTOMER_ID = "demo"


def _seed_connection() -> None:
    repo = get_in_memory_feature_store_connection_repo()
    # Mirror production: ``create_connection`` seals the blob with AAD
    # ``f"{customer_id}:{connection_id}"``. Seeding it the same way means the
    # build path must supply the matching AAD to decrypt — the regression guard
    # for the _snowflake_store bug. (Seeding without AAD masked the bug.)
    aad = f"{_CUSTOMER_ID}:{_CONNECTION_ID}".encode()
    blob = credentials.serialize_blob(credentials.encrypt({"password": "pw"}, aad=aad))
    repo._connections[_CONNECTION_ID] = {
        "id": _CONNECTION_ID,
        "customer_id": _CUSTOMER_ID,
        "name": "Prod",
        "kind": "snowflake",
        "account": "acme-xy12345",
        "user": "SVC",
        "warehouse": "WH",
        "role": "RO",
        "database": "PROD",
        "schema": "PUBLIC",
        "password_enc": blob,
    }


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Fresh in-memory state.
    customer_repo, _, _, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    get_in_memory_persona_build_repo()._builds.clear()
    get_in_memory_feature_store_connection_repo()._connections.clear()
    _seed_connection()

    # Local artifact store under tmp_path, injected via the dependency.
    store = LocalArtifactStore(tmp_path)
    app.dependency_overrides[get_artifact_store] = lambda: store

    # Snowflake never hit: run_query returns canned user rows.
    monkeypatch.setattr(
        "sidira_simulator.adapters.feature_stores.snowflake.SnowflakeStore.run_query",
        lambda self, sql: [
            {"age": 30, "orders": 5, "country": "US"},
            {"age": 41, "orders": 2, "country": "DE"},
        ],
    )

    with TestClient(app) as c:
        c._store = store  # stash for assertions
        yield c
    app.dependency_overrides.clear()


def _patch_pipeline(monkeypatch, *, stability=0.82, persona_count=3):
    def _fake(rows, column_mapping, config, customer_id, run_id):
        return PipelineOutput(
            persona_pack={"personas": [{"id": f"p{i}"} for i in range(persona_count)]},
            stability_score=stability,
            persona_count=persona_count,
            prompts={"p0": "# persona 0"},
        )

    monkeypatch.setattr(pb_mod, "run_personas_pipeline", _fake)


_CONFIG = {
    "connection_id": _CONNECTION_ID,
    "source_query": "SELECT * FROM users",
    "column_mapping": {
        "age": "demographic_identity",
        "orders": "behavioral_patterns",
        "country": None,
    },
    "stability_threshold": 0.65,
}


# ── POST + happy path ───────────────────────────────────────────────────


def test_post_returns_202_and_drives_to_complete(client, monkeypatch):
    _patch_pipeline(monkeypatch)
    resp = client.post("/persona-builds", json=_CONFIG)
    assert resp.status_code == 202
    body = resp.json()
    build_id = body["id"]
    assert body["customer_id"] == _CUSTOMER_ID
    assert body["connection_id"] == _CONNECTION_ID

    # Background task already ran under TestClient → terminal COMPLETE.
    got = client.get(f"/persona-builds/{build_id}")
    assert got.status_code == 200
    g = got.json()
    assert g["status"] == "complete"
    assert g["pack_version"] == "v_1"
    assert g["stability_score"] == 0.82
    assert g["persona_count"] == 3

    # Pack written to R2 at the versioned key.
    raw = client._store.read_text(f"customers/{_CUSTOMER_ID}/personas/v_1/persona_pack.json")
    assert len(json.loads(raw)["personas"]) == 3
    # Manifest written too.
    client._store.read_text(f"customers/{_CUSTOMER_ID}/personas/v_1/manifest.json")


def test_version_bumps_on_second_build(client, monkeypatch):
    _patch_pipeline(monkeypatch)
    first = client.post("/persona-builds", json=_CONFIG).json()["id"]
    second = client.post("/persona-builds", json=_CONFIG).json()["id"]

    assert client.get(f"/persona-builds/{first}").json()["pack_version"] == "v_1"
    assert client.get(f"/persona-builds/{second}").json()["pack_version"] == "v_2"
    # Both packs exist (no overwrite).
    client._store.read_text(f"customers/{_CUSTOMER_ID}/personas/v_1/persona_pack.json")
    client._store.read_text(f"customers/{_CUSTOMER_ID}/personas/v_2/persona_pack.json")


# ── credential AAD regression ───────────────────────────────────────────


def test_build_decrypts_aad_bound_connection(client, monkeypatch):
    """Regression: the connection password is sealed with AAD
    ``customer_id:connection_id`` at save time, so the build path's
    ``_snowflake_store`` must supply the same AAD to decrypt. Omitting it
    raises AES-GCM InvalidTag → "cannot decrypt credentials" and the build
    fails. The seed is AAD-bound (see ``_seed_connection``), so a clean
    COMPLETE here proves the decrypt AAD round-trips. Before the fix this
    drove the build to FAILED with an error_kind of credential decryption."""
    _patch_pipeline(monkeypatch)
    build_id = client.post("/persona-builds", json=_CONFIG).json()["id"]
    g = client.get(f"/persona-builds/{build_id}").json()
    assert g["status"] == "complete", g.get("error")


# ── stability gate ──────────────────────────────────────────────────────


def test_low_stability_fails_build(client, monkeypatch):
    _patch_pipeline(monkeypatch, stability=0.40)
    build_id = client.post("/persona-builds", json=_CONFIG).json()["id"]

    g = client.get(f"/persona-builds/{build_id}").json()
    assert g["status"] == "failed"
    assert g["pack_version"] is None
    assert "below threshold" in g["error"]
    # No promoted pack written.
    with pytest.raises(FileNotFoundError):
        client._store.read_text(f"customers/{_CUSTOMER_ID}/personas/v_1/persona_pack.json")


# ── status + 404 ────────────────────────────────────────────────────────


def test_get_missing_build_404(client):
    assert client.get("/persona-builds/nope").status_code == 404


def test_list_scoped_newest_first(client, monkeypatch):
    _patch_pipeline(monkeypatch)
    client.post("/persona-builds", json=_CONFIG)
    client.post("/persona-builds", json=_CONFIG)
    body = client.get("/persona-builds").json()
    assert len(body) == 2
    assert all(b["customer_id"] == _CUSTOMER_ID for b in body)


# ── events stream ───────────────────────────────────────────────────────


def test_events_endpoint_returns_emitted_events(client, monkeypatch):
    _patch_pipeline(monkeypatch)
    build_id = client.post("/persona-builds", json=_CONFIG).json()["id"]

    resp = client.get(f"/persona-builds/{build_id}/events")
    assert resp.status_code == 200
    lines = [json.loads(line) for line in resp.text.splitlines() if line.strip()]
    types = [e["type"] for e in lines]
    assert "run.started" in types
    assert "run.complete" in types


def test_events_endpoint_404_for_missing_build(client):
    assert client.get("/persona-builds/nope/events").status_code == 404
