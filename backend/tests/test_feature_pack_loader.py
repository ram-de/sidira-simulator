"""FeaturePackLoader tests against the committed demo fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from pythia_simulator.adapters.base import ArtifactNotFound, ArtifactSchemaError
from pythia_simulator.adapters.feature_pack_loader import FeaturePackLoader
from pythia_simulator.adapters.r2 import LocalArtifactStore

# Walk up from tests/ → backend/ → repo root, then into local-artifacts.
_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"


@pytest.fixture
def loader() -> FeaturePackLoader:
    store = LocalArtifactStore(_FIXTURE_ROOT)
    return FeaturePackLoader(store)


def test_resolve_latest_version_returns_pointer_content(loader: FeaturePackLoader) -> None:
    assert loader.resolve_latest_version("demo") == "2026-W21"


def test_resolve_latest_raises_for_unknown_customer(loader: FeaturePackLoader) -> None:
    with pytest.raises(ArtifactNotFound):
        loader.resolve_latest_version("does-not-exist")


def test_load_latest_manifest_returns_expected_capabilities(
    loader: FeaturePackLoader,
) -> None:
    manifest = loader.load_latest_manifest("demo")
    assert manifest.customer_id == "acme"  # fixture content; demo is the storage prefix
    assert manifest.snapshot_version == "2026-W21"
    assert set(manifest.capabilities) == {"reorder", "checkout"}


def test_load_capability_reorder(loader: FeaturePackLoader) -> None:
    cap = loader.load_capability("demo", "2026-W21", "reorder")
    assert cap.name == "reorder"
    assert "# Reorder" in cap.reverse_prd
    assert len(cap.reverse_figma.screens) >= 3
    # roles inferred from screens + transitions
    assert {"guest", "member", "premium_member"} <= set(cap.roles)


def test_load_capability_checkout(loader: FeaturePackLoader) -> None:
    cap = loader.load_capability("demo", "2026-W21", "checkout")
    assert cap.name == "checkout"
    assert "Place order" in cap.reverse_prd
    # checkout fixture should have at least one transition role-gated to guest
    role_gated_transitions = [t for t in cap.reverse_figma.transitions if t.role_gated]
    assert any("guest" in (t.role_gated or []) for t in role_gated_transitions)


def test_load_capability_missing_raises_artifact_not_found(
    loader: FeaturePackLoader,
) -> None:
    with pytest.raises(ArtifactNotFound):
        loader.load_capability("demo", "2026-W21", "nonexistent-capability")


def test_load_latest_capability_resolves_pointer_and_returns(
    loader: FeaturePackLoader,
) -> None:
    cap = loader.load_latest_capability("demo", "reorder")
    assert cap.name == "reorder"


def test_schema_error_propagates(tmp_path: Path) -> None:
    """If a manifest exists but is malformed, raise ArtifactSchemaError (not silently fall through)."""
    bad_root = tmp_path
    base = bad_root / "customers/demo/featurepacks"
    base.mkdir(parents=True)
    (base / "latest").write_text("v_bad")
    (base / "v_bad").mkdir()
    (base / "v_bad" / "manifest.json").write_text("{not valid json")

    bad_store = LocalArtifactStore(bad_root)
    bad_loader = FeaturePackLoader(bad_store)
    with pytest.raises(ArtifactSchemaError):
        bad_loader.load_latest_manifest("demo")
