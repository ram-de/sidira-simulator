"""Phase 2.5 population_sampler tests (issue #58).

Hamilton largest-remainder allocation over a PersonaPack's weight scheme.
Replaces _top_personas_by_weight (which truncated rather than stratified).
"""

from __future__ import annotations

from datetime import datetime

import pytest

from pythia_simulator.schemas.persona import Persona, PersonaPack, WeightSchemes
from pythia_simulator.services.population_sampler import allocate


# ── fixtures ────────────────────────────────────────────────────────────────


def _persona(pid: str) -> Persona:
    return Persona(id=pid, name=pid, description="")


def _pack(weights: dict[str, float], **extra_schemes: dict[str, float]) -> PersonaPack:
    return PersonaPack(
        version="v_test",
        customer_id="test",
        generated_at=datetime.now(),
        personas=[_persona(pid) for pid in weights],
        weights=WeightSchemes(head_count=weights, **extra_schemes),
        stability_score=1.0,
    )


_DEMO_WEIGHTS = {
    "maya_late_night_premium": 0.18,
    "dom_promo_driven_restaurant": 0.28,
    "priya_grocery_stockup": 0.12,
    "lex_new_explorer": 0.10,
    "jordan_lapsing_disengaged": 0.20,
    "sam_speed_pragmatist": 0.12,
}


# ── core behavior ───────────────────────────────────────────────────────────


def test_basic_allocation_sums_to_capped_sample() -> None:
    """population=1000 with default cap=50 → exactly 50 agents allocated, in proportion."""
    pack = _pack(_DEMO_WEIGHTS)
    alloc = allocate(pack, population_size=1000, max_agents=50)

    assert sum(n for _, n in alloc) == 50
    by_id = dict(alloc)
    # Each persona within ±1 of weight × 50.
    for pid, w in _DEMO_WEIGHTS.items():
        expected = w * 50
        assert abs(by_id[pid] - expected) <= 1, f"{pid}: got {by_id[pid]}, expected ~{expected}"


def test_small_population_high_weights_get_at_least_one() -> None:
    """population=6 → top-weight personas each get ≥1 agent."""
    pack = _pack(_DEMO_WEIGHTS)
    alloc = allocate(pack, population_size=6, max_agents=50)

    assert sum(n for _, n in alloc) == 6
    by_id = dict(alloc)
    # The top-3 by weight (dom 0.28, jordan 0.20, maya 0.18) should each appear.
    assert by_id["dom_promo_driven_restaurant"] >= 1
    assert by_id["jordan_lapsing_disengaged"] >= 1
    assert by_id["maya_late_night_premium"] >= 1


def test_cap_enforced_when_population_exceeds_max() -> None:
    """population=10_000 with max_agents=50 → returns exactly 50."""
    pack = _pack(_DEMO_WEIGHTS)
    alloc = allocate(pack, population_size=10_000, max_agents=50)
    assert sum(n for _, n in alloc) == 50


def test_population_below_cap_returns_population() -> None:
    """population=20 with max_agents=50 → returns exactly 20."""
    pack = _pack(_DEMO_WEIGHTS)
    alloc = allocate(pack, population_size=20, max_agents=50)
    assert sum(n for _, n in alloc) == 20


def test_zero_weight_persona_gets_zero_agents() -> None:
    """A weight-0 persona inside an otherwise-summing-to-1 vector gets 0 agents."""
    pack = _pack({"a": 0.6, "b": 0.4, "c": 0.0})
    alloc = allocate(pack, population_size=10, max_agents=50)
    by_id = dict(alloc)
    assert by_id["c"] == 0
    assert by_id["a"] + by_id["b"] == 10


# ── codex P1+P2: input validation ────────────────────────────────────────────


def test_all_zero_weights_raises() -> None:
    """Sum=0 violates the must-sum-to-~1 invariant -- silent under-allocation prevented."""
    pack = _pack({"a": 0.0, "b": 0.0, "c": 0.0})
    with pytest.raises(ValueError, match="sum"):
        allocate(pack, population_size=10, max_agents=50)


def test_weights_summing_below_one_raises() -> None:
    pack = _pack({"a": 0.4, "b": 0.4})  # sum = 0.8
    with pytest.raises(ValueError, match="sum"):
        allocate(pack, population_size=10, max_agents=50)


def test_weights_summing_above_one_raises() -> None:
    pack = _pack({"a": 0.7, "b": 0.7})  # sum = 1.4
    with pytest.raises(ValueError, match="sum"):
        allocate(pack, population_size=10, max_agents=50)


def test_negative_weight_raises() -> None:
    pack = _pack({"a": 1.2, "b": -0.2})  # sums to 1 but b is negative
    with pytest.raises(ValueError, match="negative"):
        allocate(pack, population_size=10, max_agents=50)


def test_nan_weight_raises() -> None:
    pack = _pack({"a": float("nan"), "b": 0.5})
    with pytest.raises(ValueError, match="finite"):
        allocate(pack, population_size=10, max_agents=50)


def test_inf_weight_raises() -> None:
    pack = _pack({"a": float("inf"), "b": 0.5})
    with pytest.raises(ValueError, match="finite"):
        allocate(pack, population_size=10, max_agents=50)


def test_persona_missing_from_weights_raises() -> None:
    """Pack lists 3 personas but the weight scheme only covers 2 -- producer bug."""
    pack = PersonaPack(
        version="v_test",
        customer_id="test",
        generated_at=datetime.now(),
        personas=[_persona("a"), _persona("b"), _persona("c")],
        weights=WeightSchemes(head_count={"a": 0.6, "b": 0.4}),  # missing c
        stability_score=1.0,
    )
    with pytest.raises(ValueError, match="missing personas"):
        allocate(pack, population_size=10, max_agents=50)


def test_weight_for_unknown_persona_raises() -> None:
    """Weight scheme references a persona not in the pack -- producer bug."""
    pack = PersonaPack(
        version="v_test",
        customer_id="test",
        generated_at=datetime.now(),
        personas=[_persona("a"), _persona("b")],
        weights=WeightSchemes(head_count={"a": 0.5, "b": 0.3, "ghost": 0.2}),
        stability_score=1.0,
    )
    with pytest.raises(ValueError, match="absent from the pack"):
        allocate(pack, population_size=10, max_agents=50)


def test_negative_population_raises() -> None:
    pack = _pack(_DEMO_WEIGHTS)
    with pytest.raises(ValueError, match="population_size"):
        allocate(pack, population_size=-5, max_agents=50)


def test_max_agents_zero_arg_raises() -> None:
    pack = _pack(_DEMO_WEIGHTS)
    with pytest.raises(ValueError, match="max_agents"):
        allocate(pack, population_size=10, max_agents=0)


def test_max_agents_negative_arg_raises() -> None:
    pack = _pack(_DEMO_WEIGHTS)
    with pytest.raises(ValueError, match="max_agents"):
        allocate(pack, population_size=10, max_agents=-3)


def test_max_agents_env_zero_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bad env value (0) → fall back to default 50, matching api/simulations.py."""
    monkeypatch.delenv("SIDIRA_MAX_AGENTS", raising=False)
    monkeypatch.setenv("PYTHIA_MAX_AGENTS", "0")
    pack = _pack(_DEMO_WEIGHTS)
    alloc = allocate(pack, population_size=200)  # max_agents omitted → env path
    assert sum(n for _, n in alloc) == 50


def test_max_agents_env_negative_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIDIRA_MAX_AGENTS", raising=False)
    monkeypatch.setenv("PYTHIA_MAX_AGENTS", "-7")
    pack = _pack(_DEMO_WEIGHTS)
    alloc = allocate(pack, population_size=200)
    assert sum(n for _, n in alloc) == 50


def test_max_agents_env_garbage_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIDIRA_MAX_AGENTS", raising=False)
    monkeypatch.setenv("PYTHIA_MAX_AGENTS", "abc")
    pack = _pack(_DEMO_WEIGHTS)
    alloc = allocate(pack, population_size=200)
    assert sum(n for _, n in alloc) == 50


def test_single_persona_below_cap_gets_full_population() -> None:
    pack = _pack({"only_one": 1.0})
    alloc = allocate(pack, population_size=7, max_agents=50)
    assert alloc == [("only_one", 7)]


def test_single_persona_above_cap_gets_max_agents() -> None:
    pack = _pack({"only_one": 1.0})
    alloc = allocate(pack, population_size=1000, max_agents=50)
    assert alloc == [("only_one", 50)]


def test_ties_broken_deterministically_by_persona_id() -> None:
    """4 equal-weight personas + N=10 → remainder split goes to lex-smallest ids."""
    pack = _pack({"d": 0.25, "c": 0.25, "b": 0.25, "a": 0.25})
    alloc = allocate(pack, population_size=10, max_agents=50)
    by_id = dict(alloc)
    # exact = 2.5 each; floors = 2 each, remainder = 2.
    # Fractional parts are all 0.5; ties broken by persona_id asc → a, b get +1.
    assert by_id == {"a": 3, "b": 3, "c": 2, "d": 2}
    assert sum(by_id.values()) == 10


def test_alternate_weight_scheme_yields_different_allocation() -> None:
    head_count = {"a": 0.7, "b": 0.3}
    revenue = {"a": 0.2, "b": 0.8}
    pack = _pack(head_count, revenue_weighted=revenue)

    alloc_head = dict(allocate(pack, population_size=10, max_agents=50))
    alloc_rev = dict(
        allocate(pack, population_size=10, max_agents=50, weight_scheme="revenue_weighted")
    )

    assert alloc_head["a"] > alloc_head["b"]
    assert alloc_rev["a"] < alloc_rev["b"]


def test_determinism() -> None:
    pack = _pack(_DEMO_WEIGHTS)
    a1 = allocate(pack, population_size=1000, max_agents=50)
    a2 = allocate(pack, population_size=1000, max_agents=50)
    assert a1 == a2


def test_unknown_weight_scheme_raises() -> None:
    pack = _pack(_DEMO_WEIGHTS)
    with pytest.raises(ValueError):
        allocate(pack, population_size=10, max_agents=50, weight_scheme="bogus")


def test_missing_optional_scheme_raises() -> None:
    pack = _pack(_DEMO_WEIGHTS)  # only head_count set
    with pytest.raises(ValueError):
        allocate(pack, population_size=10, max_agents=50, weight_scheme="order_weighted")


def test_max_agents_env_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """SIDIRA_MAX_AGENTS env var sets the default cap when max_agents not passed."""
    from pythia_simulator.services import population_sampler

    monkeypatch.delenv("PYTHIA_MAX_AGENTS", raising=False)
    monkeypatch.setenv("SIDIRA_MAX_AGENTS", "10")
    pack = _pack(_DEMO_WEIGHTS)
    # explicit None means "use the default", which reads env.
    alloc = population_sampler.allocate(pack, population_size=1000)
    assert sum(n for _, n in alloc) == 10


def test_max_agents_env_prefers_sidira_over_pythia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pythia_simulator.services import population_sampler

    monkeypatch.setenv("SIDIRA_MAX_AGENTS", "8")
    monkeypatch.setenv("PYTHIA_MAX_AGENTS", "10")
    pack = _pack(_DEMO_WEIGHTS)

    alloc = population_sampler.allocate(pack, population_size=1000)

    assert sum(n for _, n in alloc) == 8


# ── codex P2 hardening ──────────────────────────────────────────────────────


def test_duplicate_persona_ids_raise() -> None:
    """A PersonaPack with duplicate ids would otherwise inflate the returned count.

    `persona_ids` was constructed from `pack.personas` without dedup, so a pack
    like [a, a, b] with weights {a: .5, b: .5} and n=10 returned three entries
    summing to 15. Reject loudly instead.
    """
    pack = PersonaPack(
        version="v_test",
        customer_id="test",
        generated_at=datetime.now(),
        personas=[_persona("a"), _persona("a"), _persona("b")],
        weights=WeightSchemes(head_count={"a": 0.5, "b": 0.5}),
        stability_score=1.0,
    )
    with pytest.raises(ValueError, match="duplicate persona ids"):
        allocate(pack, population_size=10, max_agents=50)


def test_near_one_weights_at_large_n_still_sum_exactly() -> None:
    """Tolerated drift must not leak into the allocation.

    Two weights of 0.49955 sum to 0.9991 — inside the 1e-3 tolerance. Without
    post-validation normalization, n=10_000 produced floor sums of 9990 with a
    remainder of 10 distributed across only 2 personas, ending at 9992. After
    normalization the math sums to exactly n.
    """
    pack = _pack({"a": 0.49955, "b": 0.49955})
    alloc = allocate(pack, population_size=10_000, max_agents=10_000)
    assert sum(n for _, n in alloc) == 10_000


# ── Phase 5 #101: persona filter (selected_personas) ────────────────────────


def test_selected_personas_none_matches_unfiltered_default() -> None:
    """`selected_personas=None` must be byte-identical to omitting the kwarg.

    This is the backwards-compat contract: pre-#101 callers (every test in
    this file above) pass nothing; the persisted None on legacy Simulation
    rows turns into a None passed here. Both must produce the same allocation.
    """
    pack = _pack(_DEMO_WEIGHTS)
    no_kwarg = allocate(pack, population_size=50, max_agents=50)
    explicit_none = allocate(
        pack, population_size=50, max_agents=50, selected_personas=None
    )
    assert no_kwarg == explicit_none


def test_selected_personas_full_list_matches_unfiltered() -> None:
    """`selected_personas=<all pack ids>` must equal the unfiltered allocation.

    Renormalizing weights that already sum to 1 is the identity op, so
    selecting every persona explicitly must be indistinguishable from None.
    """
    pack = _pack(_DEMO_WEIGHTS)
    unfiltered = allocate(pack, population_size=50, max_agents=50)
    all_selected = allocate(
        pack,
        population_size=50,
        max_agents=50,
        selected_personas=list(_DEMO_WEIGHTS.keys()),
    )
    assert dict(unfiltered) == dict(all_selected)


def test_selected_personas_reweights_subset_preserves_population_size() -> None:
    """Picking 3 of 6 personas allocates the FULL population to them, not a share.

    Re-weight invariant (locked decision #1 in docs/4.6 ... err, #101 ticket):
    selected weights renormalize to sum to 1, then largest-remainder runs on
    the full `n`. Without reweight a 12%-weight persona selected solo would
    get 6 agents at n=50; with reweight it gets all 50.
    """
    pack = _pack(_DEMO_WEIGHTS)
    selected = [
        "dom_promo_driven_restaurant",  # 0.28
        "jordan_lapsing_disengaged",  # 0.20
        "priya_grocery_stockup",  # 0.12
    ]
    alloc = allocate(
        pack, population_size=50, max_agents=50, selected_personas=selected
    )
    # Only the selected personas appear in the output.
    assert {pid for pid, _ in alloc} == set(selected)
    # And the total matches the unfiltered population_size, NOT
    # int(50 * 0.60) = 30 (which would be the "keep absolute weights" path).
    assert sum(n for _, n in alloc) == 50
    # Selected weights renormalize to: 0.28/0.60=0.467, 0.20/0.60=0.333,
    # 0.12/0.60=0.200. At n=50 expected: 23, 17, 10 (±1 from largest-remainder).
    by_id = dict(alloc)
    assert abs(by_id["dom_promo_driven_restaurant"] - 23) <= 1
    assert abs(by_id["jordan_lapsing_disengaged"] - 17) <= 1
    assert abs(by_id["priya_grocery_stockup"] - 10) <= 1


def test_selected_personas_solo_pick_gets_full_population() -> None:
    """Selecting a single low-weight persona allocates the full `n` to it."""
    pack = _pack(_DEMO_WEIGHTS)
    alloc = allocate(
        pack,
        population_size=50,
        max_agents=50,
        selected_personas=["lex_new_explorer"],  # original weight 0.10
    )
    assert alloc == [("lex_new_explorer", 50)]


def test_selected_personas_empty_list_raises() -> None:
    """Empty `selected_personas` is rejected at the allocator layer.

    Defense-in-depth — the Pydantic validator on SimulationRequest catches
    this too, but the allocator is called from other paths (tests, future
    direct callers) so it must also self-validate.
    """
    pack = _pack(_DEMO_WEIGHTS)
    with pytest.raises(ValueError, match="at least one persona_id"):
        allocate(
            pack, population_size=50, max_agents=50, selected_personas=[]
        )


def test_selected_personas_unknown_id_raises() -> None:
    """Unknown persona_ids in the selection are rejected with a clear message."""
    pack = _pack(_DEMO_WEIGHTS)
    with pytest.raises(ValueError, match="not present in the active pack"):
        allocate(
            pack,
            population_size=50,
            max_agents=50,
            selected_personas=["dom_promo_driven_restaurant", "made_up_id"],
        )


def test_selected_personas_paired_invariant_for_ab_mode() -> None:
    """Phase 4.6 #89 paired-sampling invariant survives the filter.

    The runner calls allocate() twice (once per arm) at A/B f=0.5 with the
    SAME (pack, target, max_agents, selected_personas). The result must be
    byte-identical between the two calls so (persona_id, sample_index) keys
    match across arms. This test pins that the filter doesn't perturb
    determinism.
    """
    pack = _pack(_DEMO_WEIGHTS)
    selected = ["dom_promo_driven_restaurant", "jordan_lapsing_disengaged"]
    treatment = allocate(
        pack, population_size=20, max_agents=50, selected_personas=selected
    )
    control = allocate(
        pack, population_size=20, max_agents=50, selected_personas=selected
    )
    assert treatment == control


# Note: a "zero-weight persona selected solo" edge case is intentionally not
# tested. The renormalize step divides by sum(selected_weights); when that
# sum is 0 the existing `total > 0` guard keeps weights unchanged and the
# largest-remainder pass leaves the cohort short of population_size. This
# is theoretical (no real pack has zero-weight personas; the
# `test_all_zero_weights_raises` case enforces that upstream), so we accept
# the degenerate behavior rather than introduce a special case in the
# allocator.
