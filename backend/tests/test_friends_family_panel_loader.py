"""Tests for the committed Friends-&-Family v1.1 persona panel + its loader (#443).

The F&F validation panel is a v1.1 pack DERIVED from the game's pre-treatment
Table A (``player_features``) via the sidira-personas GMM pipeline — so it carries
the v1.1 quantitative quad (centroid_full / feature_scale / sample_rows /
posterior_mean) and drives the ``render_individual_row``
(``individual_row_synthetic``) tier rather than the centroid fallback. Unlike the
no-LLM Hillstrom / Cookie Cats builds it is built with ``require_llm=True``, so
EVERY persona also carries non-null ``behavioral_seeds`` — which means a run does
NOT log ``identity_seed fallback active`` for this pack.

The committed pack is currently built from a SYNTHETIC ``player_features.csv``
(ticket #443) so the data → pack → loader path is testable before any real
player exists; these tests pin the committed pack's v1.1 + behavioral_seeds
completeness, the allocate() coverage+sum contract, the individual-row renderer
firing, and the no-fallback identity-seed draw.
"""

from __future__ import annotations

import math

from sidira_simulator.adapters.friends_family_panel_loader import (
    FRIENDS_FAMILY_PANEL_ID,
    FRIENDS_FAMILY_PANEL_WEIGHT_SCHEME,
    friends_family_panel_registration,
    load_friends_family_panel,
)
from sidira_simulator.schemas.persona import PersonaPack
from sidira_simulator.services import identity_seed as identity_seed_module
from sidira_simulator.services.behavioral_profile import render_individual_row
from sidira_simulator.services.identity_seed import draw_identity_seed
from sidira_simulator.services.population_sampler import allocate


def test_panel_loads_and_validates() -> None:
    pack = load_friends_family_panel()
    assert isinstance(pack, PersonaPack)
    assert pack.version == FRIENDS_FAMILY_PANEL_ID
    assert pack.is_starter is False
    # A real, derived v1.1 pack — not a synthetic-generic starter fixture.
    assert pack.schema_version == "1.1"
    assert pack.personas


def test_panel_is_real_v1_1_with_complete_quantitative_quad() -> None:
    """The headline contract: EVERY persona carries the full v1.1 quad with
    consistent keys (centroid_full and feature_scale share a key set; sample_rows
    are present and key into the same adapted-feature space)."""
    pack = load_friends_family_panel()
    for p in pack.personas:
        assert p.centroid_full, p.id
        assert p.feature_scale, p.id
        assert p.sample_rows, p.id
        assert set(p.centroid_full) == set(p.feature_scale), p.id
        for row in p.sample_rows:
            assert set(row).issubset(set(p.centroid_full)), p.id


def test_every_persona_carries_behavioral_seeds() -> None:
    """The F&F-specific contract (require_llm build): EVERY persona carries
    non-null, non-empty ``behavioral_seeds`` — the per-persona identity pools that
    keep ``identity_seed`` from falling back to its generic default. This is what
    separates the F&F pack from the no-LLM Hillstrom / Cookie Cats packs."""
    pack = load_friends_family_panel()
    for p in pack.personas:
        bs = p.behavioral_seeds
        assert bs is not None, p.id
        # At least one pool populated (the draw needs real choices, not '(unknown)').
        assert any(
            (
                bs.age_bands,
                bs.locale_bands,
                bs.tenure_bands,
                bs.current_state_pool,
                bs.recent_gripe_pool,
            )
        ), p.id


def test_render_individual_row_fires_not_fallback() -> None:
    """The individual-row tier MUST fire on this pack: a grounded
    ``individual_row_synthetic`` profile, NOT the v1.0 centroid fallback."""
    pack = load_friends_family_panel()
    fired = 0
    for p in pack.personas:
        prof = render_individual_row(p, sample_index=0)
        assert prof.source_tier == "individual_row_synthetic", p.id
        assert prof.grounded is True, p.id
        if prof.deltas:
            fired += 1
    assert fired >= 1


def test_individual_rows_vary_across_sample_index() -> None:
    """Different sample_index values draw DIFFERENT synthetic rows → different
    rendered profiles (the within-persona variety the row tier exists to create)."""
    pack = load_friends_family_panel()
    p = pack.personas[0]
    renders = {
        render_individual_row(p, sample_index=i).render() for i in range(len(p.sample_rows))
    }
    assert len(renders) >= 2


def test_identity_seed_draws_without_fallback_warning() -> None:
    """Drawing an identity seed for EVERY persona must NOT trip the
    ``identity_seed fallback active`` path — proof the pack's per-persona
    behavioral_seeds are present and used (the #443 deliverable). We assert the
    fallback set stays empty for this pack's persona ids after a draw per persona."""
    pack = load_friends_family_panel()
    # Clear any cross-test fallback bookkeeping so this assertion is about THIS pack.
    identity_seed_module._fallback_warned.clear()
    for p in pack.personas:
        seed = draw_identity_seed(p, sample_index=0, run_seed=443)
        # A real draw from real pools never yields the empty-pool sentinel.
        assert seed.age_band != "(unknown)", p.id
        assert seed.current_state != "(unknown)", p.id
    # The fallback-warned set only gains an id when behavioral_seeds is None.
    drawn_ids = {p.id for p in pack.personas}
    assert identity_seed_module._fallback_warned.isdisjoint(drawn_ids)


def test_head_count_weights_cover_every_persona_and_sum_to_one() -> None:
    pack = load_friends_family_panel()
    persona_ids = {p.id for p in pack.personas}
    weights = pack.weights.head_count
    assert set(weights) == persona_ids
    assert all(w >= 0 for w in weights.values())
    assert math.isclose(sum(weights.values()), 1.0, abs_tol=1e-3)
    assert FRIENDS_FAMILY_PANEL_WEIGHT_SCHEME == "head_count"


def test_allocate_succeeds_and_covers_all_personas() -> None:
    pack = load_friends_family_panel()
    n = 40
    alloc = allocate(pack, population_size=n, max_agents=100)
    assert sum(count for _, count in alloc) == n
    assert {pid for pid, _ in alloc} == {p.id for p in pack.personas}


def test_loader_round_trips_and_caches() -> None:
    pack = load_friends_family_panel()
    again = load_friends_family_panel()
    assert again is pack  # lru_cache
    reparsed = PersonaPack.model_validate_json(pack.model_dump_json())
    assert reparsed == pack


def test_registration_metadata() -> None:
    reg = friends_family_panel_registration()
    pack = load_friends_family_panel()
    assert reg.panel_id == FRIENDS_FAMILY_PANEL_ID
    assert reg.version == pack.version
    assert reg.persona_count == len(pack.personas)
    assert reg.weight_scheme == "head_count"
    assert reg.schema_version == "1.1"
    # A derived measured pack — NOT synthetic-generic; individual-row capable AND
    # behavioral-seeds complete (no identity_seed fallback).
    assert reg.is_synthetic_generic is False
    assert reg.is_individual_row_capable is True
    assert reg.is_behavioral_seeds_complete is True
