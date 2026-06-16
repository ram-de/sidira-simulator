"""Tests for the pre-registered Upworthy Tier-0 panel (#222).

The panel is a SYNTHETIC general-US-news-audience PersonaPack, fixed and
pre-registered as the Upworthy CTR-benchmark population. It is a *generic* pack
by design: no behavioral rows / centroid features, so the simulator degrades to
its generic identity path. These tests pin that intent plus the schema /
allocate() contracts (the #246 coverage+sum bug class).
"""

from __future__ import annotations

import math

import pytest

from sidira_simulator.adapters.upworthy_panel_loader import (
    UPWORTHY_PANEL_ID,
    UPWORTHY_PANEL_WEIGHT_SCHEME,
    load_upworthy_panel,
    upworthy_panel_registration,
)
from sidira_simulator.schemas.persona import PersonaPack
from sidira_simulator.services.population_sampler import allocate

# Intended size of the pre-registered panel. Pinned so an accidental
# add/remove of a persona trips a test rather than silently changing the
# benchmark population.
EXPECTED_PERSONA_COUNT = 12


def test_panel_loads_and_validates() -> None:
    pack = load_upworthy_panel()
    assert isinstance(pack, PersonaPack)
    assert pack.version == UPWORTHY_PANEL_ID
    # Not a starter pack — it is a purpose-built (if synthetic) benchmark panel.
    assert pack.is_starter is False


def test_persona_count_is_as_intended() -> None:
    pack = load_upworthy_panel()
    assert len(pack.personas) == EXPECTED_PERSONA_COUNT
    # Ids are unique (allocate() rejects dupes, but pin it here too).
    ids = [p.id for p in pack.personas]
    assert len(ids) == len(set(ids))


def test_head_count_weights_cover_every_persona_and_sum_to_one() -> None:
    """The #246 contract: the weight scheme must give EVERY persona a value
    and sum to ~1.0, or allocate()'s coverage+sum validation fails."""
    pack = load_upworthy_panel()
    persona_ids = {p.id for p in pack.personas}
    weights = pack.weights.head_count

    assert set(weights) == persona_ids, "head_count must cover exactly the personas"
    assert all(w >= 0 for w in weights.values())
    assert math.isclose(sum(weights.values()), 1.0, abs_tol=1e-3)
    # Only the head_count scheme is carried (generic pack: no order/revenue signal).
    assert pack.weights.order_weighted is None
    assert pack.weights.revenue_weighted is None
    assert UPWORTHY_PANEL_WEIGHT_SCHEME == "head_count"


def test_allocate_succeeds_and_covers_all_personas() -> None:
    """allocate() must succeed (coverage+sum contract) and, at a population
    >= persona count, hand every persona at least one agent."""
    pack = load_upworthy_panel()
    n = 60
    alloc = allocate(pack, population_size=n, max_agents=100)

    # Counts sum to the effective sample size.
    assert sum(count for _, count in alloc) == n
    # Every persona is represented in the allocation tuples...
    allocated_ids = {pid for pid, _ in alloc}
    assert allocated_ids == {p.id for p in pack.personas}
    # ...and with n >> persona count, each gets at least one agent.
    assert all(count >= 1 for _, count in alloc)


def test_allocate_small_population_still_valid() -> None:
    """A population smaller than the persona count still allocates cleanly
    (sums correctly, no crash) — the degenerate end of the #246 contract."""
    pack = load_upworthy_panel()
    alloc = allocate(pack, population_size=3, max_agents=100)
    assert sum(count for _, count in alloc) == 3


def test_panel_has_no_behavioral_or_centroid_data() -> None:
    """Generic-tier intent: NO fabricated behavioral rows / centroid features,
    so identity-depth degrades to generic (correct for Upworthy)."""
    pack = load_upworthy_panel()
    for p in pack.personas:
        assert p.behavioral_snapshot == {}, p.id
        assert p.centroid_features == {}, p.id
        assert p.centroid_full == {}, p.id
        assert p.feature_scale == {}, p.id
        assert p.sample_rows == [], p.id
        assert p.posterior_mean is None, p.id
        assert p.behavioral_seeds is None, p.id
        # Descriptive fields ARE present — these drive the generic identity path.
        assert p.description.strip()
        assert p.jtbd and p.jtbd.strip()


def test_loader_round_trips() -> None:
    """load_upworthy_panel() round-trips: re-validating its JSON dump yields an
    equal pack (lru_cache returns the same object across calls)."""
    pack = load_upworthy_panel()
    again = load_upworthy_panel()
    assert again is pack  # cached
    reparsed = PersonaPack.model_validate_json(pack.model_dump_json())
    assert reparsed == pack


def test_registration_metadata() -> None:
    reg = upworthy_panel_registration()
    pack = load_upworthy_panel()
    assert reg.panel_id == UPWORTHY_PANEL_ID
    assert reg.version == pack.version
    assert reg.persona_count == len(pack.personas) == EXPECTED_PERSONA_COUNT
    assert reg.weight_scheme == "head_count"
    # Synthetic-generic: it carries no measured behavioral data.
    assert reg.is_synthetic_generic is True


@pytest.mark.parametrize("scheme", ["order_weighted", "revenue_weighted"])
def test_panel_does_not_offer_extra_weight_schemes(scheme: str) -> None:
    """The generic pack carries only head_count; asking allocate() for a scheme
    it doesn't have should raise rather than silently miscount."""
    pack = load_upworthy_panel()
    with pytest.raises(ValueError):
        allocate(pack, population_size=10, max_agents=100, weight_scheme=scheme)
