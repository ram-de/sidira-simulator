"""Sample-workspace clone endpoint tests.

The clone reads the committed streamly_sample fixture through a
LocalArtifactStore rooted at a tmp copy, writes into the same store under the
target tenant, and the loaders must round-trip the result exactly as if the
crawler/persona-builder had produced it.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.r2 import FallbackArtifactStore, LocalArtifactStore
from sidira_simulator.api.deps import current_customer_id, get_artifact_store
from sidira_simulator.main import app

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
TARGET = "org_acme_target"


@pytest.fixture
def store_root(tmp_path: Path) -> Path:
    shutil.copytree(
        _FIXTURE_ROOT / "customers/streamly_sample",
        tmp_path / "customers/streamly_sample",
    )
    return tmp_path


@pytest.fixture
def client(store_root: Path) -> TestClient:
    app.dependency_overrides[get_artifact_store] = lambda: LocalArtifactStore(store_root)
    app.dependency_overrides[current_customer_id] = lambda: TARGET
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_clone_returns_201_with_summary(client: TestClient) -> None:
    resp = client.post("/sample-workspace")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["source"] == "streamly_sample"
    assert body["persona_pack_version"] == "v_1"
    assert body["persona_count"] == 6
    assert body["feature_pack_version"] == "2026-W21"
    assert body["capabilities"] == ["continue_watching", "browse_recommendations"]


def test_cloned_packs_round_trip_through_loaders(client: TestClient, store_root: Path) -> None:
    assert client.post("/sample-workspace").status_code == 201
    store = LocalArtifactStore(store_root)

    pack = PersonaPackLoader(store).load_latest(TARGET)
    assert pack.customer_id == TARGET
    assert pack.version == "v_1"
    assert len(pack.personas) == 6
    assert abs(sum(pack.weights.head_count.values()) - 1.0) < 0.001

    fp_loader = FeaturePackLoader(store)
    manifest = fp_loader.load_latest_manifest(TARGET)
    assert manifest.customer_id == TARGET
    for name in manifest.capabilities:
        capability = fp_loader.load_latest_capability(TARGET, name)
        assert capability.reverse_prd
        assert capability.surfaces


def test_seeded_feature_pack_served_through_pack_bucket_split(
    client: TestClient, store_root: Path
) -> None:
    """Regression (#208 fallout): in prod the clone writes via get_store() (the
    writable bind-mount) while Feature Packs are read via get_featurepack_store()
    (the read-only R2 pack bucket). Before the read-through fallback, the seeded
    feature pack landed where the loader never looked, so a freshly seeded tenant
    showed a persona pack but "no feature pack".

    Reproduce the split: read the feature pack through a FallbackArtifactStore
    whose primary (the pack bucket) does NOT have the sample tenant, and whose
    secondary is the writable store the clone wrote to. The seeded pack must
    still resolve, exactly as it now does in prod.
    """
    assert client.post("/sample-workspace").status_code == 201

    writable = LocalArtifactStore(store_root)  # what the clone wrote to (bind-mount)
    empty_pack_bucket = LocalArtifactStore(store_root / "_empty_r2_pack")  # R2 lacks it
    fp_read_store = FallbackArtifactStore(primary=empty_pack_bucket, secondary=writable)

    loader = FeaturePackLoader(fp_read_store)
    manifest = loader.load_latest_manifest(TARGET)
    assert manifest.customer_id == TARGET
    assert manifest.capabilities
    for name in manifest.capabilities:
        capability = loader.load_latest_capability(TARGET, name)
        assert capability.reverse_prd


def test_clone_rewrites_customer_id_in_persona_manifest(
    client: TestClient, store_root: Path
) -> None:
    assert client.post("/sample-workspace").status_code == 201
    manifest = json.loads(
        (store_root / f"customers/{TARGET}/personas/v_1/manifest.json").read_text()
    )
    assert manifest["customer_id"] == TARGET
    assert manifest["persona_count"] == 6


def test_clone_leaves_source_untouched(client: TestClient, store_root: Path) -> None:
    before = sorted(
        p.relative_to(store_root).as_posix()
        for p in (store_root / "customers/streamly_sample").rglob("*")
    )
    assert client.post("/sample-workspace").status_code == 201
    after = sorted(
        p.relative_to(store_root).as_posix()
        for p in (store_root / "customers/streamly_sample").rglob("*")
    )
    assert before == after
    src_pack = json.loads(
        (store_root / "customers/streamly_sample/personas/v_1/persona_pack.json").read_text()
    )
    assert src_pack["customer_id"] == "streamly_sample"


def test_second_clone_conflicts(client: TestClient) -> None:
    assert client.post("/sample-workspace").status_code == 201
    resp = client.post("/sample-workspace")
    assert resp.status_code == 409
    assert "already has" in resp.json()["detail"]


def test_clone_refuses_when_target_has_only_personas(client: TestClient, store_root: Path) -> None:
    """A tenant with real persona data (but no feature pack yet) must not be seeded."""
    pointer = store_root / f"customers/{TARGET}/personas/latest"
    pointer.parent.mkdir(parents=True)
    pointer.write_text("v_9")
    assert client.post("/sample-workspace").status_code == 409


def test_clone_503_when_source_missing(tmp_path: Path) -> None:
    app.dependency_overrides[get_artifact_store] = lambda: LocalArtifactStore(tmp_path)
    app.dependency_overrides[current_customer_id] = lambda: TARGET
    try:
        resp = TestClient(app).post("/sample-workspace")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 503
    assert "streamly_sample" in resp.json()["detail"]


def test_retry_succeeds_after_partial_clone(client: TestClient, store_root: Path) -> None:
    """Pointer-last ordering: a partial tree without pointers reads as empty,
    so a retry POST re-clones cleanly instead of 409ing."""
    partial = store_root / f"customers/{TARGET}/personas/v_1"
    partial.mkdir(parents=True)
    partial.joinpath("persona_pack.json").write_text("{}")  # debris, no `latest` pointer
    resp = client.post("/sample-workspace")
    assert resp.status_code == 201
    store = LocalArtifactStore(store_root)
    assert PersonaPackLoader(store).load_latest(TARGET).customer_id == TARGET


def test_retry_recovers_interrupted_clone(client: TestClient, store_root: Path) -> None:
    """codex R1-P1: a clone that died between the two pointer writes leaves a
    personas pointer to a `cloned_from`-marked manifest and no featurepacks
    pointer. The retry must recognize that as sample debris and re-seed
    instead of 409ing forever."""
    assert client.post("/sample-workspace").status_code == 201
    # Reproduce the interrupted state: featurepacks pointer never landed.
    (store_root / f"customers/{TARGET}/featurepacks/latest").unlink()

    resp = client.post("/sample-workspace")
    assert resp.status_code == 201, resp.text
    store = LocalArtifactStore(store_root)
    assert FeaturePackLoader(store).load_latest_manifest(TARGET).customer_id == TARGET


def test_cloned_persona_manifest_carries_sample_marker(
    client: TestClient, store_root: Path
) -> None:
    assert client.post("/sample-workspace").status_code == 201
    manifest = json.loads(
        (store_root / f"customers/{TARGET}/personas/v_1/manifest.json").read_text()
    )
    assert manifest["cloned_from"] == "streamly_sample"
    # The source manifest must NOT carry the marker.
    src = json.loads(
        (store_root / "customers/streamly_sample/personas/v_1/manifest.json").read_text()
    )
    assert "cloned_from" not in src


def test_unmarked_personas_pointer_still_409s_without_feature_pack(
    client: TestClient, store_root: Path
) -> None:
    """Real persona data (no marker) with no feature pack yet must stay
    protected — only marker-bearing sample debris is overwritable."""
    base = store_root / f"customers/{TARGET}/personas"
    (base / "v_7").mkdir(parents=True)
    (base / "v_7/manifest.json").write_text(json.dumps({"customer_id": TARGET}))
    (base / "latest").write_text("v_7")
    assert client.post("/sample-workspace").status_code == 409


def test_non_object_source_manifest_maps_to_503(client: TestClient, store_root: Path) -> None:
    """codex R2-P2: a source persona manifest that is valid JSON but not an
    object (e.g. []) must hit the 503 contract, not raise TypeError → 500."""
    (store_root / "customers/streamly_sample/personas/v_1/manifest.json").write_text("[]")
    resp = client.post("/sample-workspace")
    assert resp.status_code == 503
    assert "incomplete" in resp.json()["detail"]


def test_corrupt_source_pack_maps_to_503(client: TestClient, store_root: Path) -> None:
    """codex R1-P2: a malformed deployed sample must surface as the route's
    'source incomplete' contract, not a raw 500."""
    (store_root / "customers/streamly_sample/personas/v_1/persona_pack.json").write_text(
        '{"version": "v_1", "broken": true}'
    )
    resp = client.post("/sample-workspace")
    assert resp.status_code == 503
    assert "incomplete" in resp.json()["detail"]
