"""Unit tests for the persona-build binding helpers (#268).

These cover the pure-Python (pandas-free) layer that translates the wizard's
group-only ``column_mapping`` into the ``sidira-personas`` pipeline config:
adapter-type inference and config assembly. They run without the ML stack, so
they exercise exactly the code that ships in the API image.
"""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from sidira_simulator.services.persona_builder import (
    BuildConfig,
    EstimabilityBuildConfig,
    LeverRegistryEntry,
    MetricRegistryEntry,
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


# ── estimability block (#568) ────────────────────────────────────────────────


def test_absent_estimability_omits_the_key_entirely():
    """No estimability block ⇒ no ``estimability`` key in cfg ⇒ pipeline builds
    no manifest (today's exact behavior; the config is byte-identical)."""
    cfg = _build_pipeline_config(_rows(), _mapping(), _cfg(), "cust1")
    assert "estimability" not in cfg


def test_populated_estimability_threads_and_excludes_none():
    est = EstimabilityBuildConfig(
        enabled=True,
        treatments=["reminder_email_sent"],
        outcomes=["reactivated_30d"],
        nc_diagnostics=True,
    )
    cfg = _build_pipeline_config(_rows(), _mapping(), _cfg(estimability=est), "cust1")
    block = cfg["estimability"]
    assert block["enabled"] is True
    assert block["treatments"] == ["reminder_email_sent"]
    assert block["outcomes"] == ["reactivated_30d"]
    assert block["nc_diagnostics"] is True
    # exclude_none drops the unset optional knobs (they fall through to the
    # pipeline's own documented defaults).
    assert "auto_neg_controls" not in block
    assert "max_treatments" not in block
    assert "max_outcomes" not in block
    assert "max_rows" not in block
    assert "neg_control_map" not in block
    assert "extra_outcome_hints" not in block


def test_estimability_enabled_false_survives_exclude_none():
    """A caller can pass the block but opt out — ``enabled`` is a real bool, so
    ``enabled=False`` is threaded (not dropped by exclude_none)."""
    est = EstimabilityBuildConfig(enabled=False)
    cfg = _build_pipeline_config(_rows(), _mapping(), _cfg(estimability=est), "cust1")
    assert cfg["estimability"] == {"enabled": False, "nc_diagnostics": False}


def test_estimability_round_trips_through_config_json():
    """The worker reconstructs the job via BuildConfig.model_validate(config_json);
    a new pydantic field round-trips automatically (worker fidelity)."""
    payload = _cfg(
        estimability=EstimabilityBuildConfig(
            treatments=["t"],
            outcomes=["y"],
            neg_control_map={"t": ["nc1", "nc2"]},
            nc_diagnostics=True,
        )
    )
    restored = BuildConfig.model_validate(payload.model_dump(mode="json"))
    assert restored.estimability is not None
    assert restored.estimability.treatments == ["t"]
    assert restored.estimability.outcomes == ["y"]
    assert restored.estimability.neg_control_map == {"t": ["nc1", "nc2"]}
    assert restored.estimability.nc_diagnostics is True
    # And it threads identically after reconstruction.
    cfg = _build_pipeline_config(_rows(), _mapping(), restored, "cust1")
    assert cfg["estimability"]["neg_control_map"] == {"t": ["nc1", "nc2"]}


def test_estimability_absent_round_trips_as_none():
    restored = BuildConfig.model_validate(_cfg().model_dump(mode="json"))
    assert restored.estimability is None


def test_estimability_forbids_unknown_keys():
    with pytest.raises(ValidationError):
        EstimabilityBuildConfig(bogus_key=1)


# ── metric/lever registry compilation (#596/#597) ────────────────────────────


def test_registry_only_config_compiles_into_pipeline_keys():
    """A registry-only declaration compiles into the plain outcomes/treatments/
    neg_control_map keys the producer consumes."""
    est = EstimabilityBuildConfig(
        metric_registry=[
            MetricRegistryEntry(
                column="reactivated_30d",
                semantic_type="rate",
                pre_period_column="reactivated_30d_pre",
            ),
            MetricRegistryEntry(column="orders_90d", semantic_type="count"),
        ],
        lever_registry=[LeverRegistryEntry(column="reminder_email_sent")],
    )
    compiled = est.compiled()
    assert compiled["outcomes"] == ["reactivated_30d", "orders_90d"]
    assert compiled["treatments"] == ["reminder_email_sent"]
    assert compiled["neg_control_map"] == {"reactivated_30d": ["reactivated_30d_pre"]}
    # The registries ride along verbatim (producer ignores unknown keys; they
    # persist in config_json for audit).
    assert compiled["metric_registry"][0]["column"] == "reactivated_30d"
    assert compiled["lever_registry"][0]["column"] == "reminder_email_sent"


def test_explicit_neg_control_map_wins_over_pre_period_link():
    """An explicit neg_control_map key beats the registry-derived pre-period
    link for the same column; non-conflicting links still merge in."""
    est = EstimabilityBuildConfig(
        neg_control_map={"y1": ["explicit_nc"]},
        metric_registry=[
            MetricRegistryEntry(column="y1", pre_period_column="y1_pre"),  # conflict
            MetricRegistryEntry(column="y2", pre_period_column="y2_pre"),  # merges
        ],
    )
    compiled = est.compiled()
    assert compiled["neg_control_map"] == {"y1": ["explicit_nc"], "y2": ["y2_pre"]}


def test_explicit_order_preserved_and_registry_columns_appended_deduped():
    est = EstimabilityBuildConfig(
        outcomes=["y_first", "y_second"],
        treatments=["t_first"],
        metric_registry=[
            MetricRegistryEntry(column="y_second"),  # already declared → deduped
            MetricRegistryEntry(column="y_third"),
        ],
        lever_registry=[
            LeverRegistryEntry(column="t_first"),  # already declared → deduped
            LeverRegistryEntry(column="t_second"),
        ],
    )
    compiled = est.compiled()
    assert compiled["outcomes"] == ["y_first", "y_second", "y_third"]
    assert compiled["treatments"] == ["t_first", "t_second"]


def test_no_registry_compiled_equals_plain_model_dump():
    """Backward compatibility: without registries, compiled() must be exactly
    the old model_dump(exclude_none=True) — byte-identical pipeline config."""
    est = EstimabilityBuildConfig(
        enabled=True,
        treatments=["t"],
        outcomes=["y"],
        neg_control_map={"t": ["nc1"]},
        nc_diagnostics=True,
        max_rows=5000,
    )
    assert est.compiled() == est.model_dump(exclude_none=True)


def test_duplicate_metric_registry_column_rejected_naming_it():
    with pytest.raises(ValidationError, match="duplicate column 'y1' in metric_registry"):
        EstimabilityBuildConfig(
            metric_registry=[
                MetricRegistryEntry(column="y1"),
                MetricRegistryEntry(column="y1"),
            ]
        )


def test_duplicate_lever_registry_column_rejected_naming_it():
    with pytest.raises(ValidationError, match="duplicate column 't1' in lever_registry"):
        EstimabilityBuildConfig(
            lever_registry=[
                LeverRegistryEntry(column="t1"),
                LeverRegistryEntry(column="t1"),
            ]
        )


def test_pre_period_column_equal_to_column_rejected():
    with pytest.raises(ValidationError, match="'y1'.*pre_period_column"):
        EstimabilityBuildConfig(
            metric_registry=[MetricRegistryEntry(column="y1", pre_period_column="y1")]
        )


def test_registry_typo_rejected_at_build_config_parse():
    """extra='forbid' still protects the wire: a typo'd registry key fails at
    BuildConfig parse (422 at the API boundary)."""
    with pytest.raises(ValidationError):
        BuildConfig(
            connection_id="c1",
            source_query="SELECT * FROM users",
            column_mapping=_mapping(),
            estimability={"metric_registryy": [{"column": "y"}]},
        )
    # Entry-level typos are forbidden too.
    with pytest.raises(ValidationError):
        MetricRegistryEntry(column="y", pre_period_col="y_pre")
    with pytest.raises(ValidationError):
        LeverRegistryEntry(column="t", displayname="T")


def test_registry_round_trips_through_config_json():
    """The worker reconstructs the job via BuildConfig.model_validate(config_json);
    the registry must survive that persistence path intact."""
    payload = _cfg(
        estimability=EstimabilityBuildConfig(
            metric_registry=[
                MetricRegistryEntry(
                    column="reactivated_30d",
                    display_name="Reactivated (30d)",
                    semantic_type="rate",
                    description="Share of lapsed users active again within 30 days",
                    synonyms=["winback_30d"],
                    pre_period_column="reactivated_30d_pre",
                )
            ],
            lever_registry=[
                LeverRegistryEntry(column="reminder_email_sent", display_name="Reminder email")
            ],
        )
    ).model_dump(mode="json")
    restored = BuildConfig.model_validate(payload)
    assert restored.model_dump(mode="json") == payload
    est = restored.estimability
    assert est is not None
    entry = est.metric_registry[0]
    assert entry.column == "reactivated_30d"
    assert entry.semantic_type == "rate"
    assert entry.synonyms == ["winback_30d"]
    assert entry.pre_period_column == "reactivated_30d_pre"
    assert est.lever_registry[0].column == "reminder_email_sent"
    # And it compiles identically after reconstruction, all the way through
    # _build_pipeline_config.
    cfg = _build_pipeline_config(_rows(), _mapping(), restored, "cust1")
    assert cfg["estimability"]["outcomes"] == ["reactivated_30d"]
    assert cfg["estimability"]["treatments"] == ["reminder_email_sent"]
    assert cfg["estimability"]["neg_control_map"] == {
        "reactivated_30d": ["reactivated_30d_pre"]
    }
