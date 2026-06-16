"""Tests for the persona-build worker (#268 Phase 2) + the supporting repo/API
changes that let a build run out-of-process.

The build pipeline + Snowflake + R2 are faked exactly as in
``test_persona_builds_api.py`` (canned PipelineOutput, canned rows, a local
artifact store). The worker's production path opens a Postgres session via
``get_sessionmaker()`` and builds Postgres repos; for these unit tests we
monkeypatch that seam in the worker module so the in-memory repos stand in,
keeping the Postgres claim/SKIP-LOCKED behavior untouched in production.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))
os.environ.setdefault("SIDIRA_LOCAL_CRED_KEY", "c2lkaXJhLXRlc3QtY3JlZC1rZXktMzJieXRlcyEhISE=")

from sidira_simulator.adapters import credentials  # noqa: E402
from sidira_simulator.adapters.r2 import LocalArtifactStore  # noqa: E402
from sidira_simulator.adapters.repositories import (  # noqa: E402
    InMemoryFeatureStoreConnectionRepo,
    InMemoryPersonaBuildRepo,
    get_in_memory_feature_store_connection_repo,
    get_in_memory_persona_build_repo,
    get_in_memory_repos,
)
from sidira_simulator.api.deps import get_artifact_store  # noqa: E402
from sidira_simulator.main import app  # noqa: E402
from sidira_simulator.services import persona_builder as pb_mod  # noqa: E402
from sidira_simulator.services.persona_builder import BuildConfig, PipelineOutput  # noqa: E402
from sidira_simulator.worker import persona_worker  # noqa: E402

_CONNECTION_ID = "fs-test-conn"
_CUSTOMER_ID = "demo"

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


def _seed_connection(repo: InMemoryFeatureStoreConnectionRepo) -> None:
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


def _patch_pipeline(monkeypatch, *, stability=0.82, persona_count=3):
    def _fake(rows, column_mapping, config, customer_id, run_id):
        return PipelineOutput(
            persona_pack={
                "schema_version": "1.1",
                "company_id": customer_id,
                "run_id": run_id,
                "created_at": "2026-06-15T00:00:00",
                "overall_stability": stability,
                "personas": [
                    {
                        "id": f"P{i:02d}",
                        "name": f"Persona {i}",
                        "description": "",
                        "jtbd": None,
                        "weights": {"by_headcount": 1.0 / persona_count},
                        "top_features": [],
                    }
                    for i in range(persona_count)
                ],
            },
            stability_score=stability,
            persona_count=persona_count,
            prompts={"P00": "# persona 0"},
        )

    monkeypatch.setattr(pb_mod, "run_personas_pipeline", _fake)


# ── repo: claim_next_pending (in-memory) ────────────────────────────────


@pytest.mark.asyncio
async def test_claim_next_pending_claims_oldest_and_flips_running():
    repo = InMemoryPersonaBuildRepo()
    await repo.create(build_id="b1", customer_id="c1", connection_id="x")
    await repo.create(build_id="b2", customer_id="c2", connection_id="y")

    first = await repo.claim_next_pending()
    assert first is not None
    assert first["id"] == "b1"  # oldest by created_at
    assert first["status"] == "running"
    # The stored row is flipped, not just the returned copy.
    assert repo._builds["b1"]["status"] == "running"

    # A second claim returns the next pending, not the already-running one.
    second = await repo.claim_next_pending()
    assert second is not None
    assert second["id"] == "b2"

    # Nothing left pending → None.
    assert await repo.claim_next_pending() is None


@pytest.mark.asyncio
async def test_claim_next_pending_none_when_empty():
    repo = InMemoryPersonaBuildRepo()
    assert await repo.claim_next_pending() is None


# ── repo: config_json round-trip ────────────────────────────────────────


@pytest.mark.asyncio
async def test_config_json_round_trips_through_create_and_get():
    repo = InMemoryPersonaBuildRepo()
    cfg = BuildConfig.model_validate(_CONFIG)
    await repo.create(
        build_id="b1",
        customer_id=_CUSTOMER_ID,
        connection_id=_CONNECTION_ID,
        config_json=cfg.model_dump(mode="json"),
    )
    got = await repo.get("b1", _CUSTOMER_ID)
    assert got is not None
    rebuilt = BuildConfig.model_validate(got["config_json"])
    assert rebuilt == cfg


# ── worker: claim_and_run_once ──────────────────────────────────────────


@pytest.fixture
def worker_env(tmp_path, monkeypatch):
    """Wire the worker's Postgres seam to fresh in-memory repos + fakes."""
    build_repo = InMemoryPersonaBuildRepo()
    conn_repo = InMemoryFeatureStoreConnectionRepo()
    _seed_connection(conn_repo)
    store = LocalArtifactStore(tmp_path)

    @asynccontextmanager
    async def _fake_session_ctx():
        yield object()  # the repos are patched, so the session is never touched

    def _fake_sessionmaker():
        return _fake_session_ctx

    monkeypatch.setattr(persona_worker, "get_sessionmaker", _fake_sessionmaker)
    monkeypatch.setattr(persona_worker, "PostgresPersonaBuildRepo", lambda session: build_repo)
    monkeypatch.setattr(
        persona_worker, "PostgresFeatureStoreConnectionRepo", lambda session: conn_repo
    )
    # Snowflake never hit: canned rows.
    monkeypatch.setattr(
        "sidira_simulator.adapters.feature_stores.snowflake.SnowflakeStore.run_query",
        lambda self, sql: [
            {"age": 30, "orders": 5, "country": "US"},
            {"age": 41, "orders": 2, "country": "DE"},
        ],
    )
    return build_repo, store


@pytest.mark.asyncio
async def test_claim_and_run_once_drives_to_complete(worker_env, monkeypatch):
    build_repo, store = worker_env
    _patch_pipeline(monkeypatch)
    cfg = BuildConfig.model_validate(_CONFIG)
    await build_repo.create(
        build_id="b1",
        customer_id=_CUSTOMER_ID,
        connection_id=_CONNECTION_ID,
        config_json=cfg.model_dump(mode="json"),
    )

    processed = await persona_worker.claim_and_run_once(store)
    assert processed is True
    row = await build_repo.get("b1", _CUSTOMER_ID)
    assert row is not None
    assert row["status"] == "complete", row.get("error")
    assert row["pack_version"] == "v_1"

    # Nothing pending now → False.
    assert await persona_worker.claim_and_run_once(store) is False


@pytest.mark.asyncio
async def test_claim_and_run_once_missing_config_marks_failed(worker_env, monkeypatch):
    build_repo, store = worker_env
    _patch_pipeline(monkeypatch)
    # Pre-worker row: no config_json.
    await build_repo.create(
        build_id="b1", customer_id=_CUSTOMER_ID, connection_id=_CONNECTION_ID
    )

    processed = await persona_worker.claim_and_run_once(store)
    assert processed is True  # claimed + handled, did not crash
    row = await build_repo.get("b1", _CUSTOMER_ID)
    assert row is not None
    assert row["status"] == "failed"
    assert "not persisted" in row["error"]


@pytest.mark.asyncio
async def test_claim_and_run_once_invalid_config_marks_failed(worker_env, monkeypatch):
    """A non-null but invalid config_json (e.g. a row queued before a schema
    change) must be failed cleanly, not crash the poll loop."""
    build_repo, store = worker_env
    _patch_pipeline(monkeypatch)
    # Non-null config missing required fields → BuildConfig.model_validate raises.
    await build_repo.create(
        build_id="b1",
        customer_id=_CUSTOMER_ID,
        connection_id=_CONNECTION_ID,
        config_json={"connection_id": _CONNECTION_ID},  # missing source_query etc.
    )

    processed = await persona_worker.claim_and_run_once(store)
    assert processed is True  # handled, did not raise out of the loop
    row = await build_repo.get("b1", _CUSTOMER_ID)
    assert row is not None
    assert row["status"] == "failed"
    assert "invalid" in row["error"]


# ── repo / worker: orphaned-running recovery ────────────────────────────


@pytest.mark.asyncio
async def test_fail_orphaned_running_reaps_running_rows():
    repo = InMemoryPersonaBuildRepo()
    await repo.create(build_id="r1", customer_id="c1", connection_id="x")
    await repo.create(build_id="p1", customer_id="c2", connection_id="y")
    # Drive r1 to running (as a claim would), leave p1 pending.
    await repo.claim_next_pending()  # claims r1 (oldest) → running

    reaped = await repo.fail_orphaned_running(error="worker restarted")
    assert reaped == 1
    r1 = await repo.get("r1", "c1")
    assert r1 is not None and r1["status"] == "failed"
    assert r1["error"] == "worker restarted"
    assert r1["completed_at"] is not None
    # The pending row is untouched — still claimable.
    p1 = await repo.get("p1", "c2")
    assert p1 is not None and p1["status"] == "pending"


@pytest.mark.asyncio
async def test_run_forever_recovers_orphaned_running_before_polling(worker_env, monkeypatch):
    """Worker-mode startup must reap orphaned RUNNING rows before the first claim
    so a build killed mid-flight doesn't hang RUNNING forever."""
    build_repo, store = worker_env
    monkeypatch.delenv("PYTHIA_PERSONA_BUILD_MODE", raising=False)
    monkeypatch.setenv("SIDIRA_PERSONA_BUILD_MODE", "worker")
    # An orphaned running row (worker died last time before it finished).
    await build_repo.create(build_id="r1", customer_id=_CUSTOMER_ID, connection_id="x")
    await build_repo.claim_next_pending()  # r1 → running

    class _StopLoop(Exception):
        pass

    async def _stop_sleep(_seconds):
        raise _StopLoop

    # No pending work after recovery → loop sleeps → we break out.
    monkeypatch.setattr(persona_worker.asyncio, "sleep", _stop_sleep)

    with pytest.raises(_StopLoop):
        await persona_worker.run_forever(store)

    r1 = await build_repo.get("r1", _CUSTOMER_ID)
    assert r1 is not None and r1["status"] == "failed"
    assert "worker restarted" in r1["error"]


# ── worker: mode gate (rollback safety) ─────────────────────────────────


@pytest.mark.parametrize(
    "value,expected",
    [("worker", True), ("inprocess", False), (None, False), ("", False)],
)
def test_worker_should_claim_honours_mode(monkeypatch, value, expected):
    monkeypatch.delenv("PYTHIA_PERSONA_BUILD_MODE", raising=False)
    if value is None:
        monkeypatch.delenv("SIDIRA_PERSONA_BUILD_MODE", raising=False)
    else:
        monkeypatch.setenv("SIDIRA_PERSONA_BUILD_MODE", value)
    assert persona_worker.worker_should_claim() is expected


@pytest.mark.asyncio
async def test_run_forever_idles_without_claiming_in_inprocess_mode(
    worker_env, monkeypatch
):
    """In the rollback (mode != worker) the worker must NOT claim — otherwise it
    would double-run the build the API is doing in-process. It idles instead."""
    build_repo, store = worker_env
    monkeypatch.delenv("PYTHIA_PERSONA_BUILD_MODE", raising=False)
    monkeypatch.setenv("SIDIRA_PERSONA_BUILD_MODE", "inprocess")

    claimed_calls = 0

    async def _spy(_store):
        nonlocal claimed_calls
        claimed_calls += 1
        return False

    monkeypatch.setattr(persona_worker, "claim_and_run_once", _spy)

    class _StopLoop(Exception):
        pass

    async def _stop_sleep(_seconds):
        raise _StopLoop

    monkeypatch.setattr(persona_worker.asyncio, "sleep", _stop_sleep)

    with pytest.raises(_StopLoop):
        await persona_worker.run_forever(store)
    assert claimed_calls == 0  # idle branch never claims


# ── worker: main() entry-point mode/DB gating ───────────────────────────


def test_main_idles_in_inprocess_mode_without_postgres(monkeypatch):
    """Compose box with no DATABASE_URL + mode=inprocess: main() must NOT exit
    (which would restart-loop the container) — it idles via run_forever."""
    monkeypatch.setattr(persona_worker, "worker_should_claim", lambda: False)
    monkeypatch.setattr(persona_worker, "database_configured", lambda: False)
    ran = {}

    def _fake_run(coro):
        ran["called"] = True
        coro.close()  # we never actually loop; avoid an un-awaited warning

    monkeypatch.setattr(persona_worker.asyncio, "run", _fake_run)
    persona_worker.main()  # must not raise SystemExit
    assert ran.get("called") is True


def test_main_exits_in_worker_mode_without_postgres(monkeypatch):
    """Worker mode genuinely needs Postgres: main() exits non-zero when it's
    missing (the operator must fix DB creds)."""
    monkeypatch.setattr(persona_worker, "worker_should_claim", lambda: True)
    monkeypatch.setattr(persona_worker, "database_configured", lambda: False)
    with pytest.raises(SystemExit) as exc:
        persona_worker.main()
    assert exc.value.code == 1


# ── API worker-mode dispatch ────────────────────────────────────────────


@pytest.fixture
def client(tmp_path, monkeypatch):
    customer_repo, _, _, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    get_in_memory_persona_build_repo()._builds.clear()
    get_in_memory_feature_store_connection_repo()._connections.clear()
    _seed_connection(get_in_memory_feature_store_connection_repo())

    store = LocalArtifactStore(tmp_path)
    app.dependency_overrides[get_artifact_store] = lambda: store

    monkeypatch.setattr(
        "sidira_simulator.adapters.feature_stores.snowflake.SnowflakeStore.run_query",
        lambda self, sql: [
            {"age": 30, "orders": 5, "country": "US"},
            {"age": 41, "orders": 2, "country": "DE"},
        ],
    )

    with TestClient(app) as c:
        c._store = store
        yield c
    app.dependency_overrides.clear()


def test_worker_mode_leaves_row_pending(client, monkeypatch):
    """With SIDIRA_PERSONA_BUILD_MODE=worker the API must NOT run the build
    in-process — the row stays PENDING for the worker to claim."""
    _patch_pipeline(monkeypatch)
    monkeypatch.setenv("SIDIRA_PERSONA_BUILD_MODE", "worker")
    resp = client.post("/persona-builds", json=_CONFIG)
    assert resp.status_code == 202
    build_id = resp.json()["id"]

    got = client.get(f"/persona-builds/{build_id}").json()
    assert got["status"] == "pending"
    assert got["pack_version"] is None
    # No pack written (the worker would do it, not the API).
    with pytest.raises(FileNotFoundError):
        client._store.read_text(f"customers/{_CUSTOMER_ID}/personas/v_1/persona_pack.json")


def test_default_mode_runs_inprocess(client, monkeypatch):
    """Default (no env) preserves the legacy in-process path: the build runs
    under the BackgroundTask and reaches COMPLETE before we read it back."""
    _patch_pipeline(monkeypatch)
    monkeypatch.delenv("SIDIRA_PERSONA_BUILD_MODE", raising=False)
    monkeypatch.delenv("PYTHIA_PERSONA_BUILD_MODE", raising=False)
    build_id = client.post("/persona-builds", json=_CONFIG).json()["id"]
    got = client.get(f"/persona-builds/{build_id}").json()
    assert got["status"] == "complete", got.get("error")
