"""
Self-validating tests for the persona-pack capability scorer (ticket #518).

Synthetic packs whose answer is KNOWN by construction — a rich multi-class pack, a
thin order-history pack, a pure-telemetry pack, and a degenerate (constant) pack —
assert the scorer's coverage vector, answerable surface, and gap list behave.

Run: /opt/homebrew/bin/python3.11 -m pytest test_pack_capability.py -q
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pack_capability import score_pack

SEED = 0


def _rng() -> np.random.Generator:
    return np.random.default_rng(SEED)


# --------------------------------------------------------------------------- #
# Synthetic packs
# --------------------------------------------------------------------------- #
def make_rich_pack(n: int = 250) -> pd.DataFrame:
    """Broad coverage across A/B/C/D/E + guards, all columns varying."""
    rng = _rng()
    f = lambda lo, hi: rng.uniform(lo, hi, n)  # noqa: E731
    return pd.DataFrame({
        # A1 experiment-history (requires_variation) — wide spread
        "treatment_family": rng.choice(["cta", "layout", "pricing", "promo"], n),
        "historical_lift_sign_on_metric": rng.choice([-1, 1], n),
        "historical_effect_size_p50": f(-1.0, 1.0),
        "n_prior_experiments": rng.integers(1, 50, n),
        # A2 CUPED (requires_variation)
        "pre_period_orders": rng.integers(0, 40, n).astype(float),
        "cuped_covariate_outcome": f(0, 1),
        # B1 lifecycle/RFM/habit
        "orders_l28d": rng.integers(0, 30, n),
        "recency_days": rng.integers(0, 120, n),
        "tenure_days": rng.integers(0, 900, n),
        "reorder_rate": f(0, 1),
        # B2 monetization/membership
        "ltv_pred": f(0, 500),
        "churn_risk_score": f(0, 1),
        "is_member_flag": rng.integers(0, 2, n),
        # B3 elasticity (requires_variation) — wide
        "implied_fee_elasticity_segment": f(-2, 2),
        "pct_orders_with_coupon_180d": f(0, 1),
        # B7 friction
        "rage_tap_rate": f(0, 0.3),
        "default_acceptance_rate": f(0, 1),
        # C1 friction & funnel telemetry
        "mistap_rate_30d": f(0, 0.2),
        "time_to_first_action_ms_p50": f(200, 4000),
        "cart_abandon_rate": f(0, 1),
        "step_completion_rate": f(0, 1),
        # C2 attention
        "hover_dwell_ms": f(0, 5000),
        "scroll_depth_p50": f(0, 1),
        "truncation_view_without_expand_rate": f(0, 1),
        # C3 latency
        "surface_render_ms_p50": f(100, 3000),
        "crash_rate": f(0, 0.05),
        # C4 session intent
        "session_intent_score": f(0, 1),
        "time_of_day_bucket": rng.integers(0, 6, n),
        # C5 search intent
        "search_to_order_rate": f(0, 1),
        "query_refinement_count": rng.integers(0, 8, n),
        # D1 device
        "platform": rng.choice(["ios", "android", "web"], n),
        "device_tier": rng.choice(["low", "high"], n),
        # D2 temporal/external
        "day_of_week": rng.integers(0, 7, n),
        "competitor_density_zone": f(0, 1),
        # E1 item
        "item_pcvr": f(0, 1),
        "avg_rating": f(1, 5),
        "item_price": f(2, 60),
        # E2 merchant
        "merchant_rating": f(1, 5),
        "prep_time_p50": f(5, 45),
        "commission_rate": f(0.1, 0.3),
        # E3 treatment-surface composition
        "primary_cta_size_px": f(24, 64),
        "interactive_element_count": rng.integers(2, 20, n),
        "text_char_length": rng.integers(8, 200, n),
        # Guards H1/H2/H3
        "neg_control_outcome_l1": f(-1, 1),
        "srm_pvalue": f(0, 1),
        "telemetry_coverage_score": f(0.4, 1.0),
    })


def make_thin_order_pack(n: int = 150) -> pd.DataFrame:
    """Only B1/B2-style order-history columns — NO telemetry, NO UI surface."""
    rng = _rng()
    f = lambda lo, hi: rng.uniform(lo, hi, n)  # noqa: E731
    return pd.DataFrame({
        "orders_lifetime": rng.integers(0, 200, n),
        "orders_l28d": rng.integers(0, 30, n),
        "recency_days": rng.integers(0, 120, n),
        "frequency_decile": rng.integers(0, 10, n),
        "tenure_days": rng.integers(0, 900, n),
        "reorder_rate": f(0, 1),
        "monetary_l90d": f(0, 1000),
        "ltv_pred": f(0, 500),
        "churn_risk_score": f(0, 1),
        "is_member_flag": rng.integers(0, 2, n),
    })


def make_telemetry_pack(n: int = 200) -> pd.DataFrame:
    """C1 friction telemetry present + varying; little else."""
    rng = _rng()
    f = lambda lo, hi: rng.uniform(lo, hi, n)  # noqa: E731
    return pd.DataFrame({
        "mistap_rate_30d": f(0, 0.2),
        "rage_click_rate_per_session": f(0, 0.3),
        "time_to_first_action_ms_p50": f(200, 4000),
        "cart_abandon_rate": f(0, 1),
        "step_completion_rate": f(0, 1),
        "median_dwell_ms_on_surface": f(0, 6000),
    })


def make_degenerate_pack(n: int = 80) -> pd.DataFrame:
    """B1-style columns that NEVER vary — present but degenerate."""
    return pd.DataFrame({
        "orders_l28d": np.full(n, 5),
        "recency_days": np.full(n, 10),
        "tenure_days": np.full(n, 365),
        "reorder_rate": np.full(n, 0.5),
    })


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_rich_pack_scores_high_and_answers_ui_and_pricing():
    prof = score_pack(make_rich_pack())
    assert prof.score > 55, f"rich pack should score >55, got {prof.score}"

    surface = set(prof.answerable) | set(prof.partial)
    assert "ui_friction_flow" in surface
    assert "pricing_promo" in surface

    # Strong UI coverage → ui_friction_flow fully answerable here.
    assert "ui_friction_flow" in prof.answerable
    assert prof.per_class["C1"]["status"] == "validated"

    # requires_variation classes still validate when given wide spread.
    assert prof.per_class["A2"]["status"] == "validated"
    assert prof.per_class["B3"]["status"] == "validated"

    # Gaps remain for top-of-funnel / cold-start families.
    assert prof.gap_list, "rich pack should still list gaps"
    assert any("acquisition" in g for g in prof.gap_list)


def test_thin_order_pack_cannot_do_ui_and_scores_lower():
    rich = score_pack(make_rich_pack())
    thin = score_pack(make_thin_order_pack())

    assert thin.score < rich.score
    # No telemetry → UI is NOT answerable.
    assert "ui_friction_flow" not in thin.answerable
    # Prescriptive gap must name the missing friction class C1.
    ui_gaps = [g for g in thin.gap_list if "ui_friction_flow" in g]
    assert ui_gaps and any("C1" in g for g in ui_gaps), thin.gap_list


def test_telemetry_pack_unlocks_ui_friction():
    prof = score_pack(make_telemetry_pack())
    assert prof.per_class["C1"]["status"] == "validated"
    surface = set(prof.answerable) | set(prof.partial)
    assert "ui_friction_flow" in surface


@pytest.mark.parametrize(
    "factory",
    [make_rich_pack, make_thin_order_pack, make_telemetry_pack, make_degenerate_pack],
)
def test_aesthetic_and_net_new_always_abstain(factory):
    prof = score_pack(factory())
    assert "aesthetic_brand" in prof.abstain
    assert "net_new" in prof.abstain
    assert "aesthetic_brand" not in prof.answerable
    assert "net_new" not in prof.answerable


def test_degenerate_pack_is_present_weak_not_validated():
    prof = score_pack(make_degenerate_pack())
    b1 = prof.per_class["B1"]
    assert b1["status"] == "present-weak"
    assert b1["variance_ok"] is False
    assert b1["matched_columns"], "B1 columns should still be detected as present"


# --------------------------------------------------------------------------- #
# Product-agnosticism: the SAME abstract class recognised across verticals
# --------------------------------------------------------------------------- #
def make_marketplace_pack(n: int = 120) -> pd.DataFrame:
    """A marketplace pack: order history + supply entity + UI friction telemetry."""
    rng = _rng()
    f = lambda lo, hi: rng.uniform(lo, hi, n)  # noqa: E731
    return pd.DataFrame({
        "orders_90d": rng.integers(0, 40, n),
        "merchant_rating": f(1, 5),
        "gov_l90d": f(0, 500),                       # gross order value (supply econ.)
        "mis_tap_rate_30d": f(0, 0.2),               # C1 friction telemetry
        "time_to_select_ms_p50": f(200, 4000),       # C1 friction telemetry
    })


def make_saas_pack(n: int = 120) -> pd.DataFrame:
    """A SaaS pack: engagement + monetization + the SAME UI friction telemetry."""
    rng = _rng()
    f = lambda lo, hi: rng.uniform(lo, hi, n)  # noqa: E731
    return pd.DataFrame({
        "active_days_30": rng.integers(0, 30, n),
        "seats_used": rng.integers(1, 50, n),
        "mrr_usd": f(0, 5000),
        "mis_tap_rate_30d": f(0, 0.2),               # C1 friction telemetry
        "time_to_complete_workflow_ms": f(500, 8000),  # C1 friction telemetry
    })


def test_same_class_recognised_across_verticals():
    """C1 (per-surface friction) is the SAME abstract class — validated from
    marketplace columns AND from SaaS columns. This is the product-agnosticism
    proof: one concept, two vertical column vocabularies."""
    mkt = score_pack(make_marketplace_pack(), vertical="marketplace")
    saas = score_pack(make_saas_pack(), vertical="saas")

    # SAME class C1 validated in BOTH, from DIFFERENT vertical columns.
    assert mkt.per_class["C1"]["status"] == "validated", mkt.per_class["C1"]
    assert saas.per_class["C1"]["status"] == "validated", saas.per_class["C1"]

    # BOTH can ground (answer or partial) the UI friction flow family.
    for prof in (mkt, saas):
        surface = set(prof.answerable) | set(prof.partial)
        assert "ui_friction_flow" in surface, (prof.vertical, surface)

    assert mkt.mapping_source == "adapter:marketplace"
    assert saas.mapping_source == "adapter:saas"
    assert mkt.vertical == "marketplace"
    assert saas.vertical == "saas"


def test_single_sided_vertical_has_no_two_sided_supply_entity():
    """HONEST: a SaaS pack must NOT match the two-sided supply entity (E2) even if
    a column looks supply-ish — single-sided products can't run those experiments."""
    saas = score_pack(make_saas_pack(), vertical="saas")
    assert saas.per_class["E2"]["status"] == "absent"
    # And marketplace_supply stays an abstain (structural, plus E2 absent).
    assert "marketplace_supply" in saas.abstain


def test_unknown_vertical_raises():
    with pytest.raises(ValueError, match="unknown vertical"):
        score_pack(make_saas_pack(), vertical="does_not_exist")


def test_column_map_overrides_names():
    """The explicit column_map ('Map step') decides presence regardless of the
    column NAMES — even names that no pattern would ever match."""
    rng = _rng()
    n = 120
    f = lambda lo, hi: rng.uniform(lo, hi, n)  # noqa: E731
    pack = pd.DataFrame({
        "xq7_weird_unmatchable": f(0, 1),
        "zz9_alien_column": f(0, 5),
    })
    cmap = {"xq7_weird_unmatchable": "C1", "zz9_alien_column": "E1"}
    prof = score_pack(pack, column_map=cmap)

    assert prof.mapping_source == "column_map"
    assert prof.per_class["C1"]["matched_columns"] == ["xq7_weird_unmatchable"]
    assert prof.per_class["E1"]["matched_columns"] == ["zz9_alien_column"]
    # A class with no mapped column stays absent.
    assert prof.per_class["B1"]["status"] == "absent"


def test_generic_fallback_when_no_vertical_or_map():
    prof = score_pack(make_rich_pack())
    assert prof.mapping_source == "generic"
    assert prof.vertical is None
    assert "generic patterns only" in prof.summary()
