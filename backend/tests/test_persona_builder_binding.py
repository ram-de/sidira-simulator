"""Unit tests for the persona-build binding helpers (#268).

These cover the pure-Python (pandas-free) layer that translates the wizard's
group-only ``column_mapping`` into the ``sidira-personas`` pipeline config:
adapter-type inference and config assembly. They run without the ML stack, so
they exercise exactly the code that ships in the API image.
"""
from __future__ import annotations

import json

from sidira_simulator.services.persona_builder import (
    BuildConfig,
    _build_pipeline_config,
    _infer_adapter_type,
)


# ── _infer_adapter_type ─────────────────────────────────────────────────────


def test_infer_flag_from_binary_ints():
    assert _infer_adapter_type([0, 1, 1, 0, None]) == ("flag", None)


def test_infer_flag_from_bool_strings():
    assert _infer_adapter_type(["true", "false", "true"]) == ("flag", None)


def test_infer_ratio_for_unit_interval():
    assert _infer_adapter_type([0.1, 0.5, 0.99, 0.0]) == ("ratio", None)


def test_infer_count_for_nonneg_integers():
    assert _infer_adapter_type([3, 7, 0, 42]) == ("count", None)


def test_infer_score_for_continuous_outside_unit():
    atype, keys = _infer_adapter_type([1.4, -2.0, 8.3])
    assert atype == "score"
    assert keys is None


def test_infer_categorical_for_strings():
    assert _infer_adapter_type(["US", "DE", "FR"]) == ("categorical", None)


def test_infer_tenure_from_iso_dates():
    atype, keys = _infer_adapter_type(["2024-01-02", "2023-11-30", "2025-06-01"])
    assert atype == "tenure_days"
    assert keys is None


def test_infer_tenure_from_native_date_objects():
    """Snowflake returns native DATE columns as datetime.date — must still infer
    tenure (date is not a subclass of datetime)."""
    import datetime as _dt

    vals = [_dt.date(2024, 1, 2), _dt.datetime(2023, 11, 30, 9, 0), _dt.date(2025, 6, 1)]
    assert _infer_adapter_type(vals) == ("tenure_days", None)


def test_infer_json_ratios_with_union_keys():
    rows = [
        json.dumps({"mon": 0.5, "tue": 0.5}),
        json.dumps({"mon": 0.2, "wed": 0.8}),
    ]
    atype, keys = _infer_adapter_type(rows)
    assert atype == "json_ratios"
    assert keys == ["mon", "tue", "wed"]


def test_infer_json_counts_for_integer_valued_objects():
    rows = [{"food": 4, "tech": 1}, {"food": 2, "home": 9}]
    atype, keys = _infer_adapter_type(rows)
    assert atype == "json_counts"
    assert keys == ["food", "home", "tech"]


def test_infer_empty_column_falls_back_to_categorical():
    assert _infer_adapter_type([None, "", None]) == ("categorical", None)


# ── _build_pipeline_config ──────────────────────────────────────────────────


def _rows():
    return [
        {
            "consumer_id": "u1",
            "snapshot_date": "2025-01-01",
            "total_orders_lifetime": 12,
            "convenience_ratio": 0.4,
            "deal_seeker_flag": 1,
            "region": "US",
            "signup_date": "2023-06-01",
        },
        {
            "consumer_id": "u2",
            "snapshot_date": "2025-01-01",
            "total_orders_lifetime": 3,
            "convenience_ratio": 0.9,
            "deal_seeker_flag": 0,
            "region": "DE",
            "signup_date": "2024-02-15",
        },
    ]


def _mapping():
    return {
        "total_orders_lifetime": "behavioral_patterns",
        "convenience_ratio": "value_sensitivity",
        "deal_seeker_flag": "value_sensitivity",
        "region": "demographic_identity",
        "signup_date": "loyalty_lifecycle",
        "consumer_id": None,  # unmapped → dropped
    }


def _cfg(**overrides):
    base = dict(
        connection_id="c1",
        source_query="SELECT * FROM users",
        column_mapping=_mapping(),
    )
    base.update(overrides)
    return BuildConfig(**base)


def test_feature_groups_carry_inferred_types():
    cfg = _build_pipeline_config(_rows(), _mapping(), _cfg(), "cust1")
    groups = cfg["feature_groups"]
    by_name = {s["name"]: s for grp in groups.values() for s in grp}
    assert by_name["total_orders_lifetime"]["type"] == "count"
    assert by_name["convenience_ratio"]["type"] == "ratio"
    assert by_name["deal_seeker_flag"]["type"] == "flag"
    assert by_name["region"]["type"] == "categorical"
    assert by_name["signup_date"]["type"] == "tenure_days"
    # Unmapped columns never appear.
    assert "consumer_id" not in by_name


def test_unmapped_columns_excluded_and_groups_keyed_by_group():
    cfg = _build_pipeline_config(_rows(), _mapping(), _cfg(), "cust1")
    assert set(cfg["feature_groups"]) == {
        "behavioral_patterns",
        "value_sensitivity",
        "demographic_identity",
        "loyalty_lifecycle",
    }
    names = {s["name"] for s in cfg["feature_groups"]["value_sensitivity"]}
    assert names == {"convenience_ratio", "deal_seeker_flag"}


def test_company_id_and_user_id_detected():
    cfg = _build_pipeline_config(_rows(), _mapping(), _cfg(), "cust1")
    assert cfg["company_id"] == "cust1"
    assert cfg["source"]["user_id_column"] == "consumer_id"


def test_snapshot_column_detected_when_tenure_present():
    cfg = _build_pipeline_config(_rows(), _mapping(), _cfg(), "cust1")
    assert cfg["snapshot_date_column"] == "snapshot_date"


def test_orders_column_detected_for_weight_scheme():
    cfg = _build_pipeline_config(
        _rows(), _mapping(), _cfg(weight_schemes=["order_weighted"]), "cust1"
    )
    assert cfg["weights"]["orders_column"] == "total_orders_lifetime"


def test_weight_schemes_translated_and_headcount_forced():
    cfg = _build_pipeline_config(
        _rows(), _mapping(), _cfg(weight_schemes=["order_weighted"]), "cust1"
    )
    schemes = cfg["weights"]["schemes"]
    assert "orders" in schemes
    assert schemes[0] == "headcount"  # always present for PersonaWeights.by_headcount


def test_k_auto_yields_range_and_explicit_k_yields_singleton():
    auto = _build_pipeline_config(_rows(), _mapping(), _cfg(k="auto"), "cust1")
    assert auto["cluster"]["k_range"] == [3, 8]
    fixed = _build_pipeline_config(_rows(), _mapping(), _cfg(k=5), "cust1")
    assert fixed["cluster"]["k_range"] == [5, 5]


def test_stability_threshold_propagates_into_cluster_cfg():
    cfg = _build_pipeline_config(
        _rows(), _mapping(), _cfg(stability_threshold=0.7), "cust1"
    )
    assert cfg["cluster"]["stability_threshold"] == 0.7
