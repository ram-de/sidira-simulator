"""PersonaPackLoader tests + fixture validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidira_simulator.adapters.base import ArtifactNotFound, ArtifactSchemaError
from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.r2 import LocalArtifactStore

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


# ── #212 starter pack ─────────────────────────────────────────────────────


def test_load_latest_serves_starter_when_no_pack(tmp_path: Path) -> None:
    """A tenant with no `latest` pointer gets the generic starter, not a 404."""
    loader = PersonaPackLoader(LocalArtifactStore(tmp_path))
    pack = loader.load_latest("brand_new_org")
    assert pack.is_starter is True
    assert pack.customer_id == "brand_new_org"
    assert pack.version == "starter-v1"
    assert len(pack.personas) >= 1


def test_starter_does_not_persist_anything(tmp_path: Path) -> None:
    """Serving the starter must not write a `latest` pointer — that's the
    invariant the sample-workspace clone relies on to still see an empty
    tenant and seed it (#212). (LocalArtifactStore mkdir's parent dirs on
    every read, so dir presence is not a persist signal; the pointer file is.)"""
    loader = PersonaPackLoader(LocalArtifactStore(tmp_path))
    loader.load_latest("brand_new_org")
    assert not (tmp_path / "customers/brand_new_org/personas/latest").exists()
    assert not (tmp_path / "customers/brand_new_org/personas/starter-v1").exists()
    with pytest.raises(ArtifactNotFound):
        loader.resolve_latest_version("brand_new_org")


def test_real_pack_takes_precedence_over_starter(loader: PersonaPackLoader) -> None:
    """A tenant that actually has a pack reads it, not the starter."""
    pack = loader.load_latest("demo")
    assert pack.is_starter is False
    assert pack.version == "v_1"


def test_starter_weights_sum_to_one_and_keyed_by_ids(tmp_path: Path) -> None:
    loader = PersonaPackLoader(LocalArtifactStore(tmp_path))
    pack = loader.load_latest("brand_new_org")
    persona_ids = {p.id for p in pack.personas}
    assert set(pack.weights.head_count.keys()) == persona_ids
    assert abs(sum(pack.weights.head_count.values()) - 1.0) < 0.001


def test_starter_personas_are_well_formed(tmp_path: Path) -> None:
    loader = PersonaPackLoader(LocalArtifactStore(tmp_path))
    pack = loader.load_latest("brand_new_org")
    for persona in pack.personas:
        assert persona.name
        assert persona.description
        assert persona.behavioral_snapshot
