"""PersonaPackLoader tests + fixture validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from pythia_simulator.adapters.base import ArtifactNotFound, ArtifactSchemaError
from pythia_simulator.adapters.persona_loader import PersonaPackLoader
from pythia_simulator.adapters.r2 import LocalArtifactStore

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"


@pytest.fixture
def loader() -> PersonaPackLoader:
    return PersonaPackLoader(LocalArtifactStore(_FIXTURE_ROOT))


def test_resolve_latest_version(loader: PersonaPackLoader) -> None:
    assert loader.resolve_latest_version("demo") == "v_1"


def test_resolve_latest_missing_raises(loader: PersonaPackLoader) -> None:
    with pytest.raises(ArtifactNotFound):
        loader.resolve_latest_version("does-not-exist")


def test_load_latest_returns_valid_pack(loader: PersonaPackLoader) -> None:
    pack = loader.load_latest("demo")
    assert pack.version == "v_1"
    assert pack.customer_id == "demo"
    assert pack.schema_version == "1.0"
    assert pack.stability_score >= 0.65, "fixture should pass the Phase 6 v1.1 threshold"


def test_fixture_persona_count_and_ids(loader: PersonaPackLoader) -> None:
    pack = loader.load_latest("demo")
    assert len(pack.personas) == 6
    ids = {p.id for p in pack.personas}
    assert ids == {
        "maya_late_night_premium",
        "dom_promo_driven_restaurant",
        "priya_grocery_stockup",
        "lex_new_explorer",
        "jordan_lapsing_disengaged",
        "sam_speed_pragmatist",
    }


def test_fixture_weights_sum_to_one(loader: PersonaPackLoader) -> None:
    """Weights across personas should sum to ~1.0 for each weighting scheme."""
    pack = loader.load_latest("demo")
    for scheme_name, scheme in [
        ("head_count", pack.weights.head_count),
        ("order_weighted", pack.weights.order_weighted),
        ("revenue_weighted", pack.weights.revenue_weighted),
    ]:
        assert scheme is not None, f"{scheme_name} scheme missing"
        total = sum(scheme.values())
        assert abs(total - 1.0) < 0.001, f"{scheme_name} weights sum to {total}, expected 1.0"


def test_fixture_weights_keyed_by_persona_id(loader: PersonaPackLoader) -> None:
    """Every persona must appear in head_count; every key in head_count must be a real persona."""
    pack = loader.load_latest("demo")
    persona_ids = {p.id for p in pack.personas}
    weight_ids = set(pack.weights.head_count.keys())
    assert weight_ids == persona_ids, (
        f"weight keys diverge from persona ids — missing weights: "
        f"{persona_ids - weight_ids}, orphan weights: {weight_ids - persona_ids}"
    )


def test_every_persona_has_behavioral_snapshot(loader: PersonaPackLoader) -> None:
    """Phase 6 v1.1 plans to require this; fixture should already comply."""
    pack = loader.load_latest("demo")
    for persona in pack.personas:
        assert persona.behavioral_snapshot, f"{persona.id} missing behavioral_snapshot"
        assert persona.description, f"{persona.id} missing description"


def test_load_at_specific_version(loader: PersonaPackLoader) -> None:
    pack = loader.load_at_version("demo", "v_1")
    assert pack.version == "v_1"


def test_schema_error_on_corrupt_pack(tmp_path: Path) -> None:
    base = tmp_path / "customers/demo/personas"
    base.mkdir(parents=True)
    (base / "latest").write_text("v_bad")
    (base / "v_bad").mkdir()
    (base / "v_bad" / "persona_pack.json").write_text('{"version": "v_bad", "incomplete": true}')

    bad_loader = PersonaPackLoader(LocalArtifactStore(tmp_path))
    with pytest.raises(ArtifactSchemaError):
        bad_loader.load_latest("demo")
