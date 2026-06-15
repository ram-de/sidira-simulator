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


def test_summary_returns_name_and_roles() -> None:
    """GET /feature-pack/summary projects each capability to name + roles.

    Powers the browse page's group-by-role view (#207); the names-only manifest
    can't carry roles, so the summary endpoint reads them per capability.
    """
    _use_loader(LocalArtifactStore(_FIXTURE_ROOT))
    resp = TestClient(app).get("/feature-pack/summary")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["snapshot_version"]
    assert body["generated_at"]
    by_name = {c["name"]: c for c in body["capabilities"]}
    assert "reorder" in by_name
    # Roles are synthesized from reverse-Figma screen.role + transition.role_gated.
    assert {"guest", "member", "premium_member"} <= set(by_name["reorder"]["roles"])


def test_summary_is_version_pinned_to_manifest() -> None:
    """The summary's snapshot_version matches the manifest the list route serves."""
    _use_loader(LocalArtifactStore(_FIXTURE_ROOT))
    client = TestClient(app)
    manifest = client.get("/capabilities").json()
    summary = client.get("/feature-pack/summary").json()
    assert summary["snapshot_version"] == manifest["snapshot_version"]
    # Same membership as the manifest — no orphans, nothing dropped.
    assert {c["name"] for c in summary["capabilities"]} == set(manifest["capabilities"])


def test_summary_no_pointer_returns_404(tmp_path: Path) -> None:
    """An empty tenant (no `latest` pointer) is a 404, not a 500."""
    _use_loader(LocalArtifactStore(tmp_path))
    resp = TestClient(app).get("/feature-pack/summary")
    assert resp.status_code == 404, resp.text


def test_summary_resilient_to_corrupt_capability(tmp_path: Path) -> None:
    """A capability with corrupt reverse-Figma still appears, with empty roles.

    The whole list must not 502 because one body is unreadable: the name is
    manifest-guaranteed, so the row is returned with `roles: []` and its detail
    route surfaces the real error on open.
    """
    store = LocalArtifactStore(tmp_path)
    base = "customers/demo/featurepacks/2026-W21/capabilities/broken"
    _write_manifest(store, "2026-W21", ["broken"])
    store.write_text(f"{base}/reverse-prd.md", "# Broken\n")
    store.write_text(f"{base}/reverse-figma.json", '{"screens": "not-a-list"}')
    _use_loader(store)
    resp = TestClient(app).get("/feature-pack/summary")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["capabilities"] == [{"name": "broken", "roles": []}]


def test_capability_named_summary_resolves_to_detail_not_projection(tmp_path: Path) -> None:
    """A capability literally named `summary` still reaches its own detail page.

    The summary projection lives at /feature-pack/summary, NOT /capabilities/summary,
    so the dynamic /capabilities/{name} detail route owns `summary` like any other
    slug. This is the guard against the route-shadow that a dedicated prefix removes:
    a manifest the crawler wrote (separate repo, unvalidated here) can list `summary`
    and the detail link must still deserialize a CapabilityRecord, not a summary.
    """
    store = LocalArtifactStore(tmp_path)
    base = "customers/demo/featurepacks/2026-W21/capabilities/summary"
    _write_manifest(store, "2026-W21", ["summary"])
    store.write_text(f"{base}/reverse-prd.md", "# Summary\n")
    store.write_text(f"{base}/reverse-figma.json", '{"screens": [], "transitions": []}')
    _use_loader(store)
    resp = TestClient(app).get("/capabilities/summary")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # The detail shape, not the projection: a CapabilityRecord wraps `capability`.
    assert body["capability"]["name"] == "summary"
    assert "capabilities" not in body


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
