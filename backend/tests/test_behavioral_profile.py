"""Tests for services.behavioral_profile (agent-behavior-spec §2, step 1).

Covers the pure centroid → population-relative-delta renderer: the salience
threshold, direction/magnitude derivation, deterministic ordering, the honesty
flags (grounded / source_tier / suppressed_count), and the graceful-degradation
paths (no centroid, all-typical, malformed values). The composer wiring is
tested separately in test_prompt_composer.py.
"""

from __future__ import annotations

import math

from sidira_simulator.schemas.persona import Persona
from sidira_simulator.services.behavioral_profile import (
    DEFAULT_SALIENCE_THRESHOLD,
    render_behavioral_profile,
)


def _persona(centroid: dict[str, float] | None) -> Persona:
    return Persona(
        id="p_test",
        name="Heavy Reorderer",
        description="Orders the same few things, often.",
        centroid_features=centroid or {},
    )


def test_renders_salient_deltas_with_direction_and_magnitude() -> None:
    profile = render_behavioral_profile(
        _persona(
            {
                "order_frequency_z": 1.62,  # much higher
                "browse_dependency_z": -1.33,  # much lower
                "promo_sensitivity_z": 2.4,  # dramatically higher
            }
        )
    )

    assert profile.grounded is True
    assert profile.source_tier == "centroid_population"
    assert profile.suppressed_count == 0
    by_feature = {d.feature: d for d in profile.deltas}

    assert by_feature["order_frequency_z"].direction == "higher"
    assert by_feature["order_frequency_z"].magnitude == "much"
    assert by_feature["order_frequency_z"].label == "order frequency"

    assert by_feature["browse_dependency_z"].direction == "lower"
    assert by_feature["browse_dependency_z"].magnitude == "much"

    assert by_feature["promo_sensitivity_z"].magnitude == "dramatically"


def test_drops_features_below_salience_threshold_but_counts_them() -> None:
    profile = render_behavioral_profile(
        _persona(
            {
                "order_frequency_z": 1.5,  # salient
                "tip_rate_z": 0.3,  # below 0.5 → suppressed
                "session_len_z": -0.49,  # below 0.5 → suppressed
            }
        )
    )

    rendered_features = {d.feature for d in profile.deltas}
    assert rendered_features == {"order_frequency_z"}
    # Sub-threshold features are counted, never silently dropped (the §1 honesty
    # rule).
    assert profile.suppressed_count == 2
    assert profile.grounded is True


def test_threshold_boundary_is_inclusive() -> None:
    # Exactly at the threshold renders; just under does not.
    profile = render_behavioral_profile(
        _persona({"at_edge_z": DEFAULT_SALIENCE_THRESHOLD, "under_z": 0.499})
    )
    assert {d.feature for d in profile.deltas} == {"at_edge_z"}
    assert profile.suppressed_count == 1


def test_magnitude_buckets_at_edges() -> None:
    profile = render_behavioral_profile(
        _persona(
            {
                "a_z": 0.5,  # somewhat (0.5 <= |z| < 1.0)
                "b_z": 0.99,  # somewhat
                "c_z": 1.0,  # much (1.0 <= |z| < 2.0)
                "d_z": 1.99,  # much
                "e_z": 2.0,  # dramatically (|z| >= 2.0)
            }
        )
    )
    mag = {d.feature: d.magnitude for d in profile.deltas}
    assert mag == {
        "a_z": "somewhat",
        "b_z": "somewhat",
        "c_z": "much",
        "d_z": "much",
        "e_z": "dramatically",
    }


def test_deltas_sorted_most_salient_first_then_by_name() -> None:
    profile = render_behavioral_profile(
        _persona(
            {
                "zeta_z": 1.0,  # tie on |z| with alpha → name breaks tie
                "alpha_z": -1.0,
                "big_z": 3.0,
            }
        )
    )
    order = [d.feature for d in profile.deltas]
    # Largest |z| first; the 1.0-tie sorts alpha before zeta.
    assert order == ["big_z", "alpha_z", "zeta_z"]


def test_no_centroid_is_ungrounded_and_renders_nothing() -> None:
    profile = render_behavioral_profile(_persona(None))
    assert profile.grounded is False
    assert profile.source_tier == "none"
    assert profile.deltas == []
    assert profile.render() is None


def test_all_typical_segment_is_grounded_but_renders_nothing() -> None:
    # Centroid present but every feature sub-threshold: a real, grounded finding
    # ("this segment behaves typically") that still emits no block.
    profile = render_behavioral_profile(_persona({"x_z": 0.1, "y_z": -0.2}))
    assert profile.grounded is True
    assert profile.source_tier == "centroid_population"
    assert profile.suppressed_count == 2
    assert profile.render() is None


def test_non_finite_values_are_skipped_not_rendered() -> None:
    profile = render_behavioral_profile(
        _persona({"good_z": 1.4, "nan_z": math.nan, "inf_z": math.inf})
    )
    assert {d.feature for d in profile.deltas} == {"good_z"}
    # Malformed values are skipped, not counted as suppressed (suppressed means
    # "real but not salient").
    assert profile.suppressed_count == 0


def test_all_malformed_centroid_is_ungrounded() -> None:
    # centroid_features present but EVERY value is non-finite: there is no usable
    # signal, so the honesty flags must report ungrounded — a broken pack must not
    # masquerade as real centroid data to any caller reading source_tier/grounded.
    profile = render_behavioral_profile(
        _persona({"a_z": math.nan, "b_z": math.inf, "c_z": -math.inf})
    )
    assert profile.grounded is False
    assert profile.source_tier == "none"
    assert profile.deltas == []
    assert profile.suppressed_count == 0
    assert profile.render() is None


def test_one_finite_among_malformed_stays_grounded() -> None:
    # A single sub-threshold-but-finite value is still real centroid data, so the
    # profile stays grounded even though it renders no block (distinguishes the
    # all-malformed ungrounded path from the all-typical grounded path).
    profile = render_behavioral_profile(_persona({"typical_z": 0.1, "nan_z": math.nan}))
    assert profile.grounded is True
    assert profile.source_tier == "centroid_population"
    assert profile.suppressed_count == 1
    assert profile.render() is None


def test_humanize_strips_z_suffix_and_unslugs() -> None:
    profile = render_behavioral_profile(
        _persona({"reorder_propensity_zscore": 1.5, "loyalty_z": 2.0})
    )
    labels = {d.label for d in profile.deltas}
    assert "reorder propensity" in labels
    assert "loyalty" in labels


def test_tunable_threshold() -> None:
    centroid = {"a_z": 0.7, "b_z": 1.3}
    # A stricter threshold suppresses the smaller delta.
    profile = render_behavioral_profile(_persona(centroid), salience_threshold=1.0)
    assert {d.feature for d in profile.deltas} == {"b_z"}
    assert profile.suppressed_count == 1


def test_render_block_shape() -> None:
    profile = render_behavioral_profile(_persona({"order_frequency_z": 1.6}))
    block = profile.render()
    assert block is not None
    assert block.startswith("## How you compare")
    assert "**much higher** order frequency" in block
    assert "Heavy Reorderer" in block
    # The measured-vs-proxy honesty hedge: framed as a segment tendency.
    assert "tendencies of your segment" in block


def test_deterministic_across_calls() -> None:
    centroid = {"a_z": 1.2, "b_z": -2.1, "c_z": 0.8}
    p = _persona(centroid)
    first = render_behavioral_profile(p)
    second = render_behavioral_profile(p)
    assert first.model_dump() == second.model_dump()
