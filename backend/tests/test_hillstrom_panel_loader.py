"""Tests for the committed Hillstrom v1.1 persona panel + its loader (#222 PR-B).

Unlike the synthetic Upworthy panel, the Hillstrom panel is a REAL pack derived
from the trial's 64,000 customers via the sidira-personas GMM pipeline — so it is
the FIRST benchmark panel carrying the v1.1 quantitative quad (centroid_full /
feature_scale / sample_rows / posterior_mean) and the first to drive the
`render_individual_row` (`individual_row_synthetic`) tier rather than the
centroid fallback. These tests pin the committed pack's v1.1 completeness, the
allocate() coverage+sum contract, and that the individual-row renderer actually
fires on it.
"""

from __future__ import annotations

import math

import pytest

from sidira_simulator.adapters.hillstrom_panel_loader import (
    HILLSTROM_PANEL_ID,
    HILLSTROM_PANEL_WEIGHT_SCHEME,
    hillstrom_panel_registration,
    hillstrom_segment_subpack,
    load_hillstrom_panel,
    segment_persona_ids,
)
from sidira_simulator.schemas.persona import PersonaPack
from sidira_simulator.services.behavioral_profile import render_individual_row
from sidira_simulator.services.population_sampler import allocate


def test_panel_loads_and_validates() -> None:
    pack = load_hillstrom_panel()
    assert isinstance(pack, PersonaPack)
    assert pack.version == HILLSTROM_PANEL_ID
    assert pack.is_starter is False
    # A real, measured pack — not a synthetic fixture.
    assert pack.schema_version == "1.1"
    assert pack.personas


def test_panel_is_real_v1_1_with_complete_quantitative_quad() -> None:
    """The headline contract: EVERY persona carries the full v1.1 quad with
    consistent keys (centroid_full and feature_scale share a key set; sample_rows
    are present). This is what separates the real Hillstrom pack from the
    synthetic Upworthy panel (which carries none of it)."""
    pack = load_hillstrom_panel()
    for p in pack.personas:
        assert p.centroid_full, p.id
        assert p.feature_scale, p.id
        assert p.sample_rows, p.id
        # centroid_full and feature_scale must share a key set so the within-cluster
        # z-score (row - centroid)/scale is computable for the rendered features.
        assert set(p.centroid_full) == set(p.feature_scale), p.id
        # Every sample row keys into the same adapted-feature space.
        for row in p.sample_rows:
            assert set(row).issubset(set(p.centroid_full)), p.id


def test_gender_affinity_separation_is_preserved() -> None:
    """The sellable heterogeneity prerequisite (STAGE 1 gate): the committed pack
    must still contain at least one clear men's-buyer cluster (mens high, womens
    low) AND one clear women's-buyer cluster — else the benchmark can never predict
    'men respond more to the men's e-mail'. Read straight off centroid_full."""
    pack = load_hillstrom_panel()
    affinities = [
        p.centroid_full.get("mens", 0.0) - p.centroid_full.get("womens", 0.0) for p in pack.personas
    ]
    assert max(affinities) > 0.5, "no clear men's-buyer cluster"
    assert min(affinities) < -0.5, "no clear women's-buyer cluster"


def test_render_individual_row_fires_not_fallback() -> None:
    """The individual-row tier MUST fire on this pack (the benchmark's headline):
    a grounded `individual_row_synthetic` profile, NOT the v1.0 centroid fallback
    (which returns grounded=False / source_tier='none')."""
    pack = load_hillstrom_panel()
    fired = 0
    for p in pack.personas:
        prof = render_individual_row(p, sample_index=0)
        # On a pack with the v1.1 quad the renderer must NOT degrade to fallback.
        assert prof.source_tier == "individual_row_synthetic", p.id
        assert prof.grounded is True, p.id
        if prof.deltas:
            fired += 1
    # At least some personas surface salient per-agent deltas (real within-cluster
    # variety), proving the row tier produced signal, not just a non-fallback tag.
    assert fired >= 1


def test_individual_rows_vary_across_sample_index() -> None:
    """Different sample_index values draw DIFFERENT synthetic rows → different
    rendered profiles, which is the within-persona variety the row tier exists to
    create. (If every draw rendered identically the tier would add nothing.)"""
    pack = load_hillstrom_panel()
    p = pack.personas[0]
    renders = {render_individual_row(p, sample_index=i).render() for i in range(len(p.sample_rows))}
    # More than one distinct rendering across the sample-row pool.
    assert len(renders) >= 2


def test_head_count_weights_cover_every_persona_and_sum_to_one() -> None:
    pack = load_hillstrom_panel()
    persona_ids = {p.id for p in pack.personas}
    weights = pack.weights.head_count
    assert set(weights) == persona_ids
    assert all(w >= 0 for w in weights.values())
    assert math.isclose(sum(weights.values()), 1.0, abs_tol=1e-3)
    assert HILLSTROM_PANEL_WEIGHT_SCHEME == "head_count"


def test_allocate_succeeds_and_covers_all_personas() -> None:
    pack = load_hillstrom_panel()
    n = 40
    alloc = allocate(pack, population_size=n, max_agents=100)
    assert sum(count for _, count in alloc) == n
    assert {pid for pid, _ in alloc} == {p.id for p in pack.personas}


def test_loader_round_trips_and_caches() -> None:
    pack = load_hillstrom_panel()
    again = load_hillstrom_panel()
    assert again is pack  # lru_cache
    reparsed = PersonaPack.model_validate_json(pack.model_dump_json())
    assert reparsed == pack


def test_segment_persona_ids_map_to_four_distinct_cohorts() -> None:
    """The endpoint-#3 conditioning map: the four persona-aligned strata each
    resolve to a non-empty cohort, and the four cohorts are mutually DISTINCT
    (each is a different GMM cluster) — proof the pack can condition the audience
    per stratum and that the >=8 by-segment cases carry real heterogeneity signal
    rather than re-using one persona across strata."""
    pack = load_hillstrom_panel()
    strata = ["mens_buyer", "womens_buyer", "high_spender", "mid_tier"]
    cohorts = {s: segment_persona_ids(pack, s) for s in strata}
    for s, ids in cohorts.items():
        assert ids, s  # non-empty
    # All four cohorts are distinct singletons (one persona each) — maximally
    # separable conditioning, so every stratum adds its own signal.
    flat = [pid for ids in cohorts.values() for pid in ids]
    assert len(flat) == len(set(flat)), f"strata share a persona: {cohorts}"


def test_segment_persona_ids_rejects_unknown_stratum() -> None:
    pack = load_hillstrom_panel()
    with pytest.raises(ValueError):
        segment_persona_ids(pack, "not_a_stratum")


def test_high_vs_mid_spender_resolve_to_different_cohorts() -> None:
    """The spend axis (the finer stratification that lifts the case count past the
    8-experiment floor) genuinely separates: high_spender and mid_tier — both
    both-gender strata — resolve to DIFFERENT persona cohorts, not the same one."""
    pack = load_hillstrom_panel()
    high = segment_persona_ids(pack, "high_spender")
    mid = segment_persona_ids(pack, "mid_tier")
    assert high and mid
    assert set(high).isdisjoint(set(mid))


def test_segment_subpack_is_conditioned_and_renormalized() -> None:
    """A segment sub-pack restricts to the stratum's personas with head_count
    renormalized to ~1.0, and carries a stratum-suffixed version (so a run's
    panel_id traces to the conditioned cohort) — and allocate() works on it."""
    from sidira_simulator.services.population_sampler import allocate

    pack = load_hillstrom_panel()
    sub = hillstrom_segment_subpack(pack, "mens_buyer")
    assert 0 < len(sub.personas) < len(pack.personas)
    assert set(sub.weights.head_count) == {p.id for p in sub.personas}
    assert math.isclose(sum(sub.weights.head_count.values()), 1.0, abs_tol=1e-6)
    assert sub.version.endswith(":mens_buyer")
    # The conditioned cohort allocates cleanly (the full population on the cohort).
    alloc = allocate(sub, population_size=10, max_agents=100)
    assert sum(c for _, c in alloc) == 10


def test_registration_metadata() -> None:
    reg = hillstrom_panel_registration()
    pack = load_hillstrom_panel()
    assert reg.panel_id == HILLSTROM_PANEL_ID
    assert reg.version == pack.version
    assert reg.persona_count == len(pack.personas)
    assert reg.weight_scheme == "head_count"
    assert reg.schema_version == "1.1"
    # A real measured pack — NOT synthetic-generic, and individual-row capable.
    assert reg.is_synthetic_generic is False
    assert reg.is_individual_row_capable is True
