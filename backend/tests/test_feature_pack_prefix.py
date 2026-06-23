"""Feature-pack R2 prefix helper — the safety crux of #215/#245 PR 2.

``feature_pack_prefix`` is the SOLE place that decides a pack's R2 prefix. The
default-setup branch MUST be byte-identical to legacy prod (the Founders org's
real pack lives only on an EC2 bind-mount at that exact path), and a named setup
MUST be a distinct, non-colliding prefix. These assertions lock both.
"""

from __future__ import annotations

import pytest

from sidira_simulator.adapters.feature_pack_loader import (
    FeaturePackLoader,
    UnsafeSetupId,
    feature_pack_prefix,
)
from sidira_simulator.adapters.r2 import LocalArtifactStore


@pytest.mark.parametrize(
    "evil",
    [
        "../../other_customer",
        "..",
        "a/b",
        "with space",
        "UPPER",  # must be lowercase to match the mint regex
        "-leading-dash",
        "x" * 49,  # too long
    ],
)
def test_prefix_rejects_unsafe_setup_id(evil: str) -> None:
    """A non-slug setup_id can never become an R2 key segment — the helper (the
    sole prefix decider) refuses it, so path traversal cannot escape the tenant
    prefix (codex P1)."""
    with pytest.raises(UnsafeSetupId):
        feature_pack_prefix("org_abc", evil)


def test_default_setup_prefix_is_byte_identical_to_legacy() -> None:
    # The legacy, pre-#215 prefix — copied verbatim from the loader's old key
    # construction. If this ever drifts, historical sims + the bind-mount pack
    # silently stop resolving. This is the non-negotiable assertion.
    assert feature_pack_prefix("org_abc") == "customers/org_abc/featurepacks"
    # Explicit "default" must equal the implicit default — same legacy path.
    assert (
        feature_pack_prefix("org_abc", "default")
        == feature_pack_prefix("org_abc")
        == "customers/org_abc/featurepacks"
    )
    # No `setups/` segment anywhere in the default path.
    assert "setups/" not in feature_pack_prefix("org_abc", "default")


def test_named_setup_prefix_is_distinct_and_scoped() -> None:
    assert (
        feature_pack_prefix("org_abc", "mobile-ios")
        == "customers/org_abc/setups/mobile-ios/featurepacks"
    )
    # Distinct from the default prefix — no collision.
    assert feature_pack_prefix("org_abc", "mobile-ios") != feature_pack_prefix("org_abc")


def test_default_loader_keys_unchanged_vs_legacy(tmp_path) -> None:
    """End-to-end: a loader pointed at the legacy layout resolves the default
    setup with no code-side path change (the demo fixture lives at the legacy
    customers/<id>/featurepacks/ path)."""
    from pathlib import Path

    fixture_root = Path(__file__).resolve().parents[2] / "local-artifacts"
    loader = FeaturePackLoader(LocalArtifactStore(fixture_root))
    # Implicit default and explicit "default" both read the legacy fixture.
    assert loader.resolve_latest_version("demo") == "2026-W21"
    assert loader.resolve_latest_version("demo", "default") == "2026-W21"


def test_named_setup_loader_reads_its_own_prefix(tmp_path) -> None:
    """A pack written under a named setup's prefix resolves only via that
    setup_id — and the legacy/default prefix does NOT see it (no collision)."""
    store = LocalArtifactStore(tmp_path)
    cust = "org_xyz"
    setup = "mobile-ios"
    # Write a minimal pack ONLY under the named-setup prefix.
    base = feature_pack_prefix(cust, setup)
    store.write_text(f"{base}/latest", "2026-W30")
    store.write_text(
        f"{base}/2026-W30/manifest.json",
        '{"customer_id": "org_xyz", "snapshot_version": "2026-W30", '
        '"generated_at": "2026-07-20T00:00:00Z", "capabilities": []}',
    )
    loader = FeaturePackLoader(store)

    # Resolves under the named setup.
    assert loader.resolve_latest_version(cust, setup) == "2026-W30"
    manifest = loader.load_latest_manifest(cust, setup)
    assert manifest.snapshot_version == "2026-W30"

    # The default/legacy prefix sees nothing — proving no cross-setup collision.
    from sidira_simulator.adapters.base import ArtifactNotFound
    import pytest

    with pytest.raises(ArtifactNotFound):
        loader.resolve_latest_version(cust)  # default setup, empty
