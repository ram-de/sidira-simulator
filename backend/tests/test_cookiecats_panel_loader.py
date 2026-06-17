"""Tests for the committed Cookie Cats v1.1 persona panel + its loader.

Like the Hillstrom panel, the Cookie Cats panel is a v1.1 pack carrying the
quantitative quad (centroid_full / feature_scale / sample_rows / posterior_mean)
so it drives the `render_individual_row` tier rather than the centroid fallback.
These tests pin the committed pack's v1.1 completeness, the STAGE-1 engagement-
separation gate, the allocate() coverage+sum contract, the individual-row
renderer firing, and the per-engagement-octile conditioning map.
"""

from __future__ import annotations

import math

import pytest

from sidira_simulator.adapters.cookiecats_panel_loader import (
    COOKIECATS_PANEL_ID,
    COOKIECATS_PANEL_WEIGHT_SCHEME,
    cookiecats_panel_registration,
    cookiecats_segment_subpack,
    load_cookiecats_panel,
    segment_persona_ids,
)
from sidira_simulator.schemas.persona import PersonaPack
from sidira_simulator.services.behavioral_profile import render_individual_row
from sidira_simulator.services.population_sampler import allocate

_ENGAGEMENT_FEATURE = "sum_gamerounds"


def test_panel_loads_and_validates() -> None:
    pack = load_cookiecats_panel()
    assert isinstance(pack, PersonaPack)
    assert pack.version == COOKIECATS_PANEL_ID
    assert pack.is_starter is False
    assert pack.schema_version == "1.1"
    assert pack.personas


def test_panel_is_real_v1_1_with_complete_quantitative_quad() -> None:
    pack = load_cookiecats_panel()
    for p in pack.personas:
        assert p.centroid_full, p.id
        assert p.feature_scale, p.id
        assert p.sample_rows, p.id
        assert set(p.centroid_full) == set(p.feature_scale), p.id
        for row in p.sample_rows:
            assert set(row).issubset(set(p.centroid_full)), p.id


def test_engagement_separation_is_preserved() -> None:
    """The STAGE-1 gate: the committed pack must contain DISTINCT engagement tiers
    — the spread of the `sum_gamerounds` centroid across clusters must be clearly
    separated (>0.5σ), else the by-engagement heterogeneity endpoint is meaningless
    (every stratum would condition on an indistinguishable cohort)."""
    pack = load_cookiecats_panel()
    centroids = sorted(p.centroid_full.get(_ENGAGEMENT_FEATURE, 0.0) for p in pack.personas)
    # The lowest and highest engagement clusters are clearly separated.
    assert centroids[-1] - centroids[0] > 0.5, "no clear engagement separation"
    # Each adjacent pair of tiers is also separated (no two collapsed clusters).
    assert all(b - a > 0.3 for a, b in zip(centroids, centroids[1:])), "adjacent tiers too close"


def test_render_individual_row_fires_not_fallback() -> None:
    pack = load_cookiecats_panel()
    fired = 0
    for p in pack.personas:
        prof = render_individual_row(p, sample_index=0)
        assert prof.source_tier == "individual_row_synthetic", p.id
        assert prof.grounded is True, p.id
        if prof.deltas:
            fired += 1
    assert fired >= 1


def test_individual_rows_vary_across_sample_index() -> None:
    pack = load_cookiecats_panel()
    p = max(pack.personas, key=lambda pp: len(pp.sample_rows))
    renders = {render_individual_row(p, sample_index=i).render() for i in range(len(p.sample_rows))}
    assert len(renders) >= 2


def test_head_count_weights_cover_every_persona_and_sum_to_one() -> None:
    pack = load_cookiecats_panel()
    persona_ids = {p.id for p in pack.personas}
    weights = pack.weights.head_count
    assert set(weights) == persona_ids
    assert all(w >= 0 for w in weights.values())
    assert math.isclose(sum(weights.values()), 1.0, abs_tol=1e-3)
    assert COOKIECATS_PANEL_WEIGHT_SCHEME == "head_count"


def test_allocate_succeeds_and_covers_all_personas() -> None:
    pack = load_cookiecats_panel()
    n = 40
    alloc = allocate(pack, population_size=n, max_agents=100)
    assert sum(count for _, count in alloc) == n
    assert {pid for pid, _ in alloc} == {p.id for p in pack.personas}


def test_loader_round_trips_and_caches() -> None:
    pack = load_cookiecats_panel()
    again = load_cookiecats_panel()
    assert again is pack  # lru_cache
    reparsed = PersonaPack.model_validate_json(pack.model_dump_json())
    assert reparsed == pack


def test_segment_persona_ids_map_octiles_low_to_heavy() -> None:
    """The conditioning map: the lowest octile conditions on the LOW-engagement
    persona and the highest octile on the HEAVY-engagement persona (octiles map
    onto the engagement-ordered clusters)."""
    pack = load_cookiecats_panel()
    ordered = sorted(pack.personas, key=lambda p: p.centroid_full[_ENGAGEMENT_FEATURE])
    low_persona = ordered[0].id
    heavy_persona = ordered[-1].id
    assert segment_persona_ids(pack, "eng_o1") == [low_persona]
    assert segment_persona_ids(pack, "eng_o8") == [heavy_persona]


def test_segment_persona_ids_cover_all_octiles_nonempty() -> None:
    pack = load_cookiecats_panel()
    for n in range(1, 9):
        ids = segment_persona_ids(pack, f"eng_o{n}")
        assert ids, n


def test_segment_persona_ids_rejects_unknown_stratum() -> None:
    pack = load_cookiecats_panel()
    with pytest.raises(ValueError):
        segment_persona_ids(pack, "not_a_stratum")
    with pytest.raises(ValueError):
        segment_persona_ids(pack, "eng_o99")  # out of range


def test_segment_subpack_is_conditioned_and_renormalized() -> None:
    pack = load_cookiecats_panel()
    sub = cookiecats_segment_subpack(pack, "eng_o1")
    assert 0 < len(sub.personas) < len(pack.personas)
    assert set(sub.weights.head_count) == {p.id for p in sub.personas}
    assert math.isclose(sum(sub.weights.head_count.values()), 1.0, abs_tol=1e-6)
    assert sub.version.endswith(":eng_o1")
    alloc = allocate(sub, population_size=10, max_agents=100)
    assert sum(c for _, c in alloc) == 10


def test_low_and_heavy_octiles_condition_on_different_cohorts() -> None:
    pack = load_cookiecats_panel()
    low = segment_persona_ids(pack, "eng_o1")
    heavy = segment_persona_ids(pack, "eng_o8")
    assert low and heavy
    assert set(low).isdisjoint(set(heavy))


def test_registration_metadata() -> None:
    reg = cookiecats_panel_registration()
    pack = load_cookiecats_panel()
    assert reg.panel_id == COOKIECATS_PANEL_ID
    assert reg.version == pack.version
    assert reg.persona_count == len(pack.personas)
    assert reg.weight_scheme == "head_count"
    assert reg.schema_version == "1.1"
    assert reg.is_synthetic_generic is False
    assert reg.is_individual_row_capable is True
