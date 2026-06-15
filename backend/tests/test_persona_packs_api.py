"""GET /persona-packs/{pack_id} endpoint tests + list/promote tests (#25).

The Library's persona-pack detail page (#207) reads this to render each
persona's description / JTBD / weight — the fields the wizard-shaped
`GET /personas` projection deliberately omits. `pack_id="latest"` resolves the
active pack (with the #212 starter fallback for empty tenants); an explicit
version loads that snapshot and 404s when it is genuinely missing.

The list/promote coverage (#25) at the bottom uses an in-memory persona-build
repo (each COMPLETE build with a `pack_version` IS a pack version) and a
`LocalArtifactStore(tmp_path)` so nothing hits real R2; `promote` writes the
same `latest` pointer key the loader reads.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.r2 import LocalArtifactStore
from sidira_simulator.adapters.repositories import get_in_memory_persona_build_repo
from sidira_simulator.api.deps import (
    current_customer_id,
    get_artifact_store,
    get_persona_loader,
)
from sidira_simulator.main import app

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"


@pytest.fixture(autouse=True)
def _customer() -> None:
    app.dependency_overrides[current_customer_id] = lambda: "demo"
    yield
    app.dependency_overrides.clear()


def test_get_latest_returns_full_pack_with_descriptions() -> None:
    """`latest` resolves the real active pack with the detail fields the page needs."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    resp = TestClient(app).get("/persona-packs/latest")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_starter"] is False
    assert body["version"] == "v_1"
    assert len(body["personas"]) == 6
    # The whole point of this endpoint over /personas: full persona bodies.
    assert all(p["description"].strip() for p in body["personas"])
    # Weights + stability surface so the detail page can show "% of population".
    assert "head_count" in body["weights"]
    assert isinstance(body["stability_score"], (int, float))


def test_get_explicit_version_matches_latest() -> None:
    """Addressing the version directly returns the same snapshot as `latest`."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    client = TestClient(app)
    explicit = client.get("/persona-packs/v_1")
    assert explicit.status_code == 200, explicit.text
    assert explicit.json() == client.get("/persona-packs/latest").json()


def test_empty_tenant_latest_returns_starter(tmp_path: Path) -> None:
    """No pack in the store → `latest` serves the #212 starter, not a 404."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(tmp_path)
    )
    resp = TestClient(app).get("/persona-packs/latest")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_starter"] is True
    assert body["version"] == "starter-v1"
    assert len(body["personas"]) >= 1


def test_unknown_version_404s() -> None:
    """An explicit version that does not exist is a real not-found, not a starter."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    resp = TestClient(app).get("/persona-packs/v_999")
    assert resp.status_code == 404, resp.text


def test_detail_renders_blocks_and_weight_schemes() -> None:
    """`/{id}/detail` returns the rendered view: centroid block, schemes, honesty."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    resp = TestClient(app).get("/persona-packs/latest/detail")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["version"] == "v_1"
    assert body["schema_version"] == "1.0"
    assert body["persona_count"] == 6
    # The demo fixture is a v1.0 pack — no individual-row tier, honest empty-state.
    assert body["has_individual_rows"] is False
    # Centroid tier renders for personas with salient centroid_features.
    assert any(p["how_you_compare"] for p in body["personas"])
    assert all(p["distinctive"] is None for p in body["personas"])
    # All three weight schemes are reported (present-or-not), headcount always present.
    schemes = {s["key"]: s for s in body["weight_schemes"]}
    assert schemes["head_count"]["available"] is True
    assert {"head_count", "order_weighted", "revenue_weighted"} == set(schemes)
    # The raw bulky v1.1 arrays are NOT echoed into the view payload.
    first = body["personas"][0]
    assert "sample_rows" not in first and "centroid_full" not in first


def test_detail_unknown_version_404s() -> None:
    """The detail view shares the raw endpoint's not-found semantics."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    resp = TestClient(app).get("/persona-packs/v_999/detail")
    assert resp.status_code == 404, resp.text


# ── list + promote (#25) ──────────────────────────────────────────────────

_CUSTOMER_ID = "demo"


def _write_pack(store: LocalArtifactStore, version: str) -> None:
    """Write a schema-valid PersonaPack snapshot at `version`.

    Reuses the demo fixture pack (a real, validated PersonaPack) so that a
    follow-up GET can actually load it, just restamping the version field.
    """
    fixture = (
        _FIXTURE_ROOT / "customers" / _CUSTOMER_ID / "personas" / "v_1" / "persona_pack.json"
    )
    pack = json.loads(fixture.read_text())
    pack["version"] = version
    key = f"customers/{_CUSTOMER_ID}/personas/{version}/persona_pack.json"
    store.write_text(key, json.dumps(pack))


def _seed_build(
    *,
    build_id: str,
    status: str,
    pack_version: str | None,
    created_at: datetime,
    stability: float = 0.8,
    persona_count: int = 2,
) -> None:
    repo = get_in_memory_persona_build_repo()
    repo._builds[build_id] = {
        "id": build_id,
        "customer_id": _CUSTOMER_ID,
        "connection_id": "conn",
        "status": status,
        "pack_version": pack_version,
        "stability_score": stability,
        "persona_count": persona_count,
        "error": None,
        "created_at": created_at,
        "completed_at": created_at,
    }


@pytest.fixture
def packs_client(tmp_path: Path):
    """Client wired to a tmp LocalArtifactStore + clean in-memory build repo."""
    get_in_memory_persona_build_repo()._builds.clear()
    store = LocalArtifactStore(tmp_path)
    loader = PersonaPackLoader(store=store)
    app.dependency_overrides[get_artifact_store] = lambda: store
    app.dependency_overrides[get_persona_loader] = lambda: loader
    with TestClient(app) as c:
        c._store = store
        c._loader = loader
        yield c
    app.dependency_overrides.clear()


def test_list_empty_tenant_returns_empty_not_404(packs_client) -> None:
    resp = packs_client.get("/persona-packs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_newest_first_only_complete(packs_client) -> None:
    base = datetime(2026, 6, 15, tzinfo=timezone.utc)
    _write_pack(packs_client._store, "v_1")
    _write_pack(packs_client._store, "v_2")
    _seed_build(build_id="b1", status="complete", pack_version="v_1", created_at=base)
    _seed_build(
        build_id="b2",
        status="complete",
        pack_version="v_2",
        created_at=base + timedelta(hours=1),
    )
    # Non-complete / version-less builds must NOT appear.
    _seed_build(
        build_id="b3", status="failed", pack_version=None, created_at=base + timedelta(hours=2)
    )
    _seed_build(
        build_id="b4", status="running", pack_version=None, created_at=base + timedelta(hours=3)
    )

    body = packs_client.get("/persona-packs").json()
    assert [p["version"] for p in body] == ["v_2", "v_1"]  # newest first
    assert all(p["id"] == p["version"] for p in body)
    assert all(p["status"] == "draft" for p in body)
    assert all(p["is_latest"] is False for p in body)


def test_promote_writes_pointer_and_flips_status(packs_client) -> None:
    base = datetime(2026, 6, 15, tzinfo=timezone.utc)
    _write_pack(packs_client._store, "v_1")
    _write_pack(packs_client._store, "v_2")
    _seed_build(build_id="b1", status="complete", pack_version="v_1", created_at=base)
    _seed_build(
        build_id="b2",
        status="complete",
        pack_version="v_2",
        created_at=base + timedelta(hours=1),
    )

    resp = packs_client.post("/persona-packs/v_1/promote")
    assert resp.status_code == 200
    promoted = resp.json()
    assert promoted["version"] == "v_1"
    assert promoted["status"] == "promoted"
    assert promoted["is_latest"] is True

    # The pointer was written so the loader resolves latest → v_1.
    assert packs_client._loader.resolve_latest_version(_CUSTOMER_ID) == "v_1"
    # And GET /persona-packs/latest resolves to that snapshot.
    latest = packs_client.get("/persona-packs/latest")
    assert latest.status_code == 200
    assert latest.json()["customer_id"] == _CUSTOMER_ID

    # A follow-up list reflects the flip.
    by_version = {p["version"]: p for p in packs_client.get("/persona-packs").json()}
    assert by_version["v_1"]["status"] == "promoted"
    assert by_version["v_1"]["is_latest"] is True
    assert by_version["v_2"]["status"] == "draft"
    assert by_version["v_2"]["is_latest"] is False


def test_promote_unknown_version_404(packs_client) -> None:
    base = datetime(2026, 6, 15, tzinfo=timezone.utc)
    _write_pack(packs_client._store, "v_1")
    _seed_build(build_id="b1", status="complete", pack_version="v_1", created_at=base)

    assert packs_client.post("/persona-packs/v_9/promote").status_code == 404


def test_promote_latest_sentinel_rejected(packs_client) -> None:
    assert packs_client.post("/persona-packs/latest/promote").status_code == 400


def test_promote_version_beyond_recent_page_resolves_metadata(packs_client) -> None:
    """A complete version older than the 50-row recent page still promotes with
    its real metadata (stability/persona_count), not a zeroed PackSummary.

    Seed >50 newer builds so the target falls off `list_recent`'s default page;
    `get_by_pack_version` must still find it.
    """
    base = datetime(2026, 6, 15, tzinfo=timezone.utc)
    # The old target version, with a readable snapshot + populated metadata.
    _write_pack(packs_client._store, "v_old")
    _seed_build(
        build_id="b-old",
        status="complete",
        pack_version="v_old",
        created_at=base,
        stability=0.91,
        persona_count=5,
    )
    # 60 newer complete builds bury it past the default 50-row recent page.
    for i in range(60):
        _seed_build(
            build_id=f"b{i}",
            status="complete",
            pack_version=f"v_new_{i}",
            created_at=base + timedelta(hours=i + 1),
        )

    resp = packs_client.post("/persona-packs/v_old/promote")
    assert resp.status_code == 200, resp.text
    promoted = resp.json()
    assert promoted["version"] == "v_old"
    assert promoted["status"] == "promoted"
    assert promoted["is_latest"] is True
    # Metadata is the real build's, not a zeroed fallback.
    assert promoted["stability_score"] == 0.91
    assert promoted["persona_count"] == 5


def test_get_by_pack_version_ignores_incomplete_and_other_customers() -> None:
    """Unit coverage for the new repo method: only this customer's COMPLETE build
    with the exact version is returned."""
    import asyncio

    repo = get_in_memory_persona_build_repo()
    repo._builds.clear()
    base = datetime(2026, 6, 15, tzinfo=timezone.utc)
    repo._builds["x1"] = {
        "id": "x1",
        "customer_id": _CUSTOMER_ID,
        "connection_id": "c",
        "status": "running",
        "pack_version": "v_x",
        "stability_score": 0.5,
        "persona_count": 1,
        "error": None,
        "created_at": base,
        "completed_at": None,
    }
    repo._builds["x2"] = {
        "id": "x2",
        "customer_id": "other",
        "connection_id": "c",
        "status": "complete",
        "pack_version": "v_x",
        "stability_score": 0.5,
        "persona_count": 1,
        "error": None,
        "created_at": base,
        "completed_at": base,
    }
    repo._builds["x3"] = {
        "id": "x3",
        "customer_id": _CUSTOMER_ID,
        "connection_id": "c",
        "status": "complete",
        "pack_version": "v_x",
        "stability_score": 0.77,
        "persona_count": 4,
        "error": None,
        "created_at": base,
        "completed_at": base,
    }

    found = asyncio.run(repo.get_by_pack_version(_CUSTOMER_ID, "v_x"))
    assert found is not None and found["id"] == "x3"
    assert asyncio.run(repo.get_by_pack_version(_CUSTOMER_ID, "v_missing")) is None
