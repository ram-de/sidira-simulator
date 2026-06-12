"""Loader smoke tests on the first crawler-GENERATED pack (streamly-sandbox).

`demo` and `streamly_sample` are hand-authored fixtures; this pack was
synthesized by sidira-crawler from a real sandbox walk and imported verbatim
from R2 (#190) — the first time the crawler's pack schema meets this loader
on generated data. Every capability is round-tripped rather than
spot-checking a known one, and assertions stay structural: the content
belongs to the generator, never to this repo (GENERATED, NEVER AUTHORED).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.r2 import LocalArtifactStore

# Walk up from tests/ → backend/ → repo root, then into local-artifacts.
_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"

_CUSTOMER = "streamly-sandbox"


@pytest.fixture
def loader() -> FeaturePackLoader:
    store = LocalArtifactStore(_FIXTURE_ROOT)
    return FeaturePackLoader(store)


def test_latest_pointer_resolves(loader: FeaturePackLoader) -> None:
    assert loader.resolve_latest_version(_CUSTOMER) == "2026-W24"


def test_manifest_is_the_crawled_snapshot(loader: FeaturePackLoader) -> None:
    manifest = loader.load_latest_manifest(_CUSTOMER)
    assert manifest.customer_id == _CUSTOMER
    assert manifest.snapshot_version == "2026-W24"
    assert len(manifest.capabilities) == 13
    assert len(set(manifest.capabilities)) == 13


def test_every_capability_round_trips(loader: FeaturePackLoader) -> None:
    """Load every capability the manifest names — any crawler/simulator
    schema drift surfaces here, on real generated data."""
    version = loader.resolve_latest_version(_CUSTOMER)
    manifest = loader.load_manifest_at_version(_CUSTOMER, version)
    for name in manifest.capabilities:
        cap = loader.load_capability(_CUSTOMER, version, name)
        assert cap.name == name
        assert cap.surfaces, f"{name}: no surfaces"
        assert cap.reverse_prd.strip(), f"{name}: empty reverse-PRD"
        assert cap.reverse_figma.screens, f"{name}: no figma screens"
        # Surfaces are derived from figma screen ids — they must agree.
        assert len(cap.surfaces) == len(cap.reverse_figma.screens), name
