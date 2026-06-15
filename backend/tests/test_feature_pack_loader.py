"""FeaturePackLoader tests against the committed demo fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidira_simulator.adapters.base import ArtifactNotFound, ArtifactSchemaError
from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.r2 import LocalArtifactStore

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


def _write_pack(root: Path, figma: dict) -> None:
    """Write a minimal one-capability pack with the given reverse-figma body."""
    base = root / "customers/demo/featurepacks/2026-W30"
    (base / "capabilities/account").mkdir(parents=True)
    (root / "customers/demo/featurepacks/latest").write_text("2026-W30")
    (base / "manifest.json").write_text(
        '{"customer_id": "acme", "snapshot_version": "2026-W30",'
        ' "generated_at": "2026-07-20T00:00:00Z", "capabilities": ["account"]}'
    )
    (base / "capabilities/account/reverse-prd.md").write_text("# Account")
    import json

    (base / "capabilities/account/reverse-figma.json").write_text(json.dumps(figma))


def test_external_transition_round_trips_through_loader(tmp_path: Path) -> None:
    # sidira-crawler#14: a boundary edge whose target left the capability is
    # flagged external by the crawler; the loader must surface that flag so a
    # consumer can tell a seam-crossing hop from an in-capability one.
    _write_pack(
        tmp_path,
        {
            "screens": [{"id": "/account::s1", "name": "Account"}],
            "transitions": [
                {
                    "trigger": "click link 'Manage plan'",
                    "from_screen": "/account::s1",
                    "to_screen": "/account/plan::s9",
                    "external": True,
                },
                {
                    "trigger": "click link 'Edit'",
                    "from_screen": "/account::s1",
                    "to_screen": "/account::s1",
                },
            ],
        },
    )
    cap = FeaturePackLoader(LocalArtifactStore(tmp_path)).load_capability(
        "demo", "2026-W30", "account"
    )
    by_target = {t.to_screen: t for t in cap.reverse_figma.transitions}
    assert by_target["/account/plan::s9"].external is True
    # An edge omitting the field (older packs, in-capability hops) defaults False.
    assert by_target["/account::s1"].external is False


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
