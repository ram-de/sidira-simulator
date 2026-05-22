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
    monkeypatch.setenv("PYTHIA_MAX_AGENTS", "0")
    pack = _pack(_DEMO_WEIGHTS)
    alloc = allocate(pack, population_size=200)  # max_agents omitted → env path
    assert sum(n for _, n in alloc) == 50


def test_max_agents_env_negative_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTHIA_MAX_AGENTS", "-7")
    pack = _pack(_DEMO_WEIGHTS)
    alloc = allocate(pack, population_size=200)
    assert sum(n for _, n in alloc) == 50


def test_max_agents_env_garbage_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
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
    """PYTHIA_MAX_AGENTS env var sets the default cap when max_agents not passed."""
    from pythia_simulator.services import population_sampler

    monkeypatch.setenv("PYTHIA_MAX_AGENTS", "10")
    pack = _pack(_DEMO_WEIGHTS)
    # explicit None means "use the default", which reads env.
    alloc = population_sampler.allocate(pack, population_size=1000)
    assert sum(n for _, n in alloc) == 10


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
