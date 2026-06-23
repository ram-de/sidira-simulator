"""Feature Pack archive (soft-delete / hide-from-Library) endpoint tests (#214).

The integrity invariant: archiving a pack VERSION hides it from the Library but
must NEVER break a historical simulation that froze that version. These tests pin
both halves:

  * archived pack is hidden from the Library listing endpoints by default, and
    visible again with ``?include_archived=true``;
  * an archived version is STILL resolvable by ``FeaturePackLoader`` (the path the
    running simulation uses), so a past run replays unchanged.

Archive state lives in a tiny DB table (``archived_feature_packs``); the suite uses
the process-wide in-memory repo, reset per test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.r2 import LocalArtifactStore
from sidira_simulator.adapters.repositories import (
    get_in_memory_archived_feature_pack_repo,
)
from sidira_simulator.api.deps import current_customer_id, get_feature_pack_loader
from sidira_simulator.main import app


@pytest.fixture(autouse=True)
def _customer() -> None:
    app.dependency_overrides[current_customer_id] = lambda: "demo"
    # The archive marker repo is process-wide in-memory; clear it each test so
    # state never leaks between cases.
    get_in_memory_archived_feature_pack_repo()._archived.clear()
    yield
    app.dependency_overrides.clear()
    get_in_memory_archived_feature_pack_repo()._archived.clear()


def _store(tmp_path: Path, version: str = "2026-W21") -> LocalArtifactStore:
    """A store with one pack version for tenant demo, pointed to by `latest`."""
    store = LocalArtifactStore(tmp_path)
    manifest = {
        "customer_id": "demo",
        "snapshot_version": version,
        "generated_at": "2026-05-25T00:00:00Z",
        "capabilities": ["reorder"],
    }
    base = f"customers/demo/featurepacks/{version}/capabilities/reorder"
    store.write_text("customers/demo/featurepacks/latest", version)
    store.write_text(
        f"customers/demo/featurepacks/{version}/manifest.json", json.dumps(manifest)
    )
    store.write_text(f"{base}/reverse-prd.md", "# Reorder\n")
    store.write_text(
        f"{base}/reverse-figma.json",
        '{"screens": [{"id": "s1", "name": "Cart", "role": "member"}], "transitions": []}',
    )
    return store


def _use_loader(store: LocalArtifactStore) -> None:
    app.dependency_overrides[get_feature_pack_loader] = lambda: FeaturePackLoader(store)


def test_archive_hides_pack_from_library_list(tmp_path: Path) -> None:
    """After archiving the latest version, GET /capabilities reads as 404 (empty)."""
    store = _store(tmp_path)
    _use_loader(store)
    client = TestClient(app)

    # Visible before archiving.
    assert client.get("/capabilities").status_code == 200

    archived = client.post("/featurepacks/2026-W21/archive")
    assert archived.status_code == 200, archived.text
    assert archived.json() == {
        "customer_id": "demo",
        "pack_version": "2026-W21",
        "archived": True,
    }

    # Hidden from the Library now — same 404 an empty tenant would render.
    assert client.get("/capabilities").status_code == 404
    # …and from the summary projection the browse page reads.
    assert client.get("/feature-pack/summary").status_code == 404


def test_include_archived_shows_hidden_pack(tmp_path: Path) -> None:
    """?include_archived=true is the Library's "Show archived" opt-in."""
    store = _store(tmp_path)
    _use_loader(store)
    client = TestClient(app)
    client.post("/featurepacks/2026-W21/archive")

    resp = client.get("/capabilities", params={"include_archived": "true"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["snapshot_version"] == "2026-W21"

    summary = client.get("/feature-pack/summary", params={"include_archived": "true"})
    assert summary.status_code == 200, summary.text
    assert summary.json()["snapshot_version"] == "2026-W21"


def test_archived_pack_still_resolvable_for_running_sim(tmp_path: Path) -> None:
    """THE integrity invariant: archive hides from the Library but the version stays
    resolvable by FeaturePackLoader — the exact path a frozen historical sim uses.

    The loader never consults the archive marker, so a past run that froze this
    version replays unchanged.
    """
    store = _store(tmp_path)
    _use_loader(store)
    client = TestClient(app)
    client.post("/featurepacks/2026-W21/archive")

    # The Library hides it…
    assert client.get("/capabilities").status_code == 404
    # …but the running-sim resolution path resolves it byte-for-byte.
    loader = FeaturePackLoader(store)
    manifest = loader.load_manifest_at_version("demo", "2026-W21")
    assert manifest.snapshot_version == "2026-W21"
    capability = loader.load_capability("demo", "2026-W21", "reorder")
    assert capability.name == "reorder"


def test_manifest_reports_true_archive_state(tmp_path: Path) -> None:
    """The manifest carries the REAL archive state so the Library labels the version
    from fact, not by guessing from the toggle (codex P2).

    Not archived -> archived=false even with ?include_archived; archived ->
    archived=true under the toggle.
    """
    store = _store(tmp_path)
    _use_loader(store)
    client = TestClient(app)

    # Live pack, default view: archived=false.
    assert client.get("/capabilities").json()["archived"] is False
    # Live pack, include_archived: still false (the flag is fact, not the toggle).
    assert (
        client.get("/capabilities", params={"include_archived": "true"}).json()[
            "archived"
        ]
        is False
    )

    client.post("/featurepacks/2026-W21/archive")
    shown = client.get("/capabilities", params={"include_archived": "true"}).json()
    assert shown["archived"] is True


def test_unarchive_restores_pack_to_library(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _use_loader(store)
    client = TestClient(app)
    client.post("/featurepacks/2026-W21/archive")
    assert client.get("/capabilities").status_code == 404

    restored = client.post("/featurepacks/2026-W21/unarchive")
    assert restored.status_code == 200, restored.text
    assert restored.json()["archived"] is False
    assert client.get("/capabilities").status_code == 200


def test_archive_is_idempotent(tmp_path: Path) -> None:
    """Re-archiving an already-archived version is a no-op, not an error."""
    store = _store(tmp_path)
    _use_loader(store)
    client = TestClient(app)
    assert client.post("/featurepacks/2026-W21/archive").status_code == 200
    assert client.post("/featurepacks/2026-W21/archive").status_code == 200
    assert client.get("/capabilities").status_code == 404


def test_unarchive_unknown_marker_is_noop(tmp_path: Path) -> None:
    """Unarchiving a version that was never archived returns archived=false."""
    store = _store(tmp_path)
    _use_loader(store)
    resp = TestClient(app).post("/featurepacks/2026-W21/unarchive")
    assert resp.status_code == 200, resp.text
    assert resp.json()["archived"] is False


def test_archive_phantom_version_404s(tmp_path: Path) -> None:
    """Archiving a version that does not exist in R2 is a 404 — you can't soft-delete
    a pack that was never crawled."""
    store = _store(tmp_path)
    _use_loader(store)
    resp = TestClient(app).post("/featurepacks/2099-W01/archive")
    assert resp.status_code == 404, resp.text


def test_empty_tenant_list_unaffected_by_archive(tmp_path: Path) -> None:
    """An empty tenant (no pack) still 404s; the archive filter never masks a real
    'no pack yet' from a 'hidden pack'."""
    _use_loader(LocalArtifactStore(tmp_path))
    assert TestClient(app).get("/capabilities").status_code == 404
