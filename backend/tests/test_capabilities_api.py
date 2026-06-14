"""GET /capabilities/{name} endpoint tests.

Powers the Library's capability-detail page (#207 browsability). The list route
(GET /capabilities) is exercised via the loader tests; here we cover the
single-capability read and its error surfaces.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.r2 import LocalArtifactStore
from sidira_simulator.api.deps import current_customer_id, get_feature_pack_loader
from sidira_simulator.main import app

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"


@pytest.fixture(autouse=True)
def _customer() -> None:
    app.dependency_overrides[current_customer_id] = lambda: "demo"
    yield
    app.dependency_overrides.clear()


def _use_loader(store: LocalArtifactStore) -> None:
    app.dependency_overrides[get_feature_pack_loader] = lambda: FeaturePackLoader(store)


def _write_manifest(store: LocalArtifactStore, version: str, capabilities: list[str]) -> None:
    """Write a `latest` pointer + manifest listing `capabilities` for tenant demo."""
    store.write_text("customers/demo/featurepacks/latest", version)
    store.write_text(
        f"customers/demo/featurepacks/{version}/manifest.json",
        json.dumps(
            {
                "customer_id": "demo",
                "snapshot_version": version,
                "generated_at": "2026-05-25T00:00:00Z",
                "capabilities": capabilities,
            }
        ),
    )


def test_get_capability_returns_prd_and_figma() -> None:
    """Happy path: the demo `reorder` capability resolves via the latest pointer."""
    _use_loader(LocalArtifactStore(_FIXTURE_ROOT))
    resp = TestClient(app).get("/capabilities/reorder")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Provenance comes from the same read that served the body (#207).
    assert body["snapshot_version"]
    assert body["generated_at"]
    cap = body["capability"]
    assert cap["name"] == "reorder"
    assert "# Reorder" in cap["reverse_prd"]
    assert len(cap["reverse_figma"]["screens"]) >= 3
    assert {"guest", "member", "premium_member"} <= set(cap["roles"])


def test_get_capability_missing_returns_404() -> None:
    """An unknown capability name in an otherwise-valid pack is a 404."""
    _use_loader(LocalArtifactStore(_FIXTURE_ROOT))
    resp = TestClient(app).get("/capabilities/nonexistent-capability")
    assert resp.status_code == 404, resp.text


def test_get_capability_no_pointer_returns_404(tmp_path: Path) -> None:
    """An empty tenant (no `latest` pointer) is a 404, not a 500."""
    _use_loader(LocalArtifactStore(tmp_path))
    resp = TestClient(app).get("/capabilities/reorder")
    assert resp.status_code == 404, resp.text


def test_get_capability_corrupt_figma_returns_502(tmp_path: Path) -> None:
    """A stored reverse-Figma that fails schema validation surfaces as 502."""
    store = LocalArtifactStore(tmp_path)
    base = "customers/demo/featurepacks/2026-W21/capabilities/broken"
    _write_manifest(store, "2026-W21", ["broken"])
    store.write_text(f"{base}/reverse-prd.md", "# Broken\n")
    store.write_text(f"{base}/reverse-figma.json", '{"screens": "not-a-list"}')
    _use_loader(store)
    resp = TestClient(app).get("/capabilities/broken")
    assert resp.status_code == 502, resp.text


def test_get_capability_orphaned_dir_returns_404(tmp_path: Path) -> None:
    """A capability dropped from the manifest but left on disk is a 404.

    A crawl that drops a capability rewrites the manifest but may leave the old
    capabilities/<name>/ directory behind. Loading by storage path alone would
    serve that orphan; the endpoint must gate on manifest membership so a direct
    or bookmarked URL can't surface a dropped capability as current.
    """
    store = LocalArtifactStore(tmp_path)
    # Manifest lists only `kept`, but a valid `dropped` directory still exists.
    _write_manifest(store, "2026-W21", ["kept"])
    base = "customers/demo/featurepacks/2026-W21/capabilities/dropped"
    store.write_text(f"{base}/reverse-prd.md", "# Dropped\n")
    store.write_text(f"{base}/reverse-figma.json", '{"screens": []}')
    _use_loader(store)
    resp = TestClient(app).get("/capabilities/dropped")
    assert resp.status_code == 404, resp.text
