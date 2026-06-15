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
    render_individual_row,
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


# ── agent-behavior-spec §2 step-2: the per-agent individual row (layer 4) ─────
#
# render_individual_row z-scores ONE sample row against the persona centroid in
# ADAPTED-FEATURE space (raw units): z = (row[f] - centroid_full[f]) /
# feature_scale[f]. These are the v1.1 fields (centroid_full / feature_scale /
# sample_rows) — distinct from centroid_features (population z-scores) the
# centroid tier uses. The reference frame is agent-vs-persona, not
# persona-vs-population.


# Sentinel so a caller can pass an EMPTY field (the v1.0-degradation cases)
# distinctly from "not passed" (use the default) — `field or default` would
# wrongly substitute the default for a falsy empty dict/list.
_UNSET: object = object()


def _persona_v11(
    *,
    centroid_full: object = _UNSET,
    feature_scale: object = _UNSET,
    sample_rows: object = _UNSET,
) -> Persona:
    """A v1.1 persona carrying the individual-row inputs (raw adapted units).

    Defaults give two features and two rows, with integer-divisible values so the
    z-scores land exactly on bucket/threshold edges (no float drift): row 0 is
    distinctive (order frequency +2.0 SD, browse dependency -0.5 SD off the
    cluster mean), row 1 is an average member (both features at the centroid → all
    sub-threshold).
    """
    return Persona(
        id="p_v11",
        name="DashPass Power",
        description="Heavy weekly user who orders for the family.",
        # centroid_features (population z-scores) is intentionally present but
        # MUST NOT be read by render_individual_row — the tiers never mix.
        centroid_features={"order_frequency_z": 99.0},
        centroid_full=(
            {"order_frequency_28d": 10.0, "browse_dependency": 4.0}
            if centroid_full is _UNSET
            else centroid_full
        ),
        feature_scale=(
            {"order_frequency_28d": 2.0, "browse_dependency": 2.0}
            if feature_scale is _UNSET
            else feature_scale
        ),
        sample_rows=(
            [
                {"order_frequency_28d": 14.0, "browse_dependency": 3.0},  # +2.0, -0.5
                {"order_frequency_28d": 10.0, "browse_dependency": 4.0},  # 0, 0 typical
            ]
            if sample_rows is _UNSET
            else sample_rows
        ),
    )


def test_individual_row_z_scores_against_centroid_full() -> None:
    profile = render_individual_row(_persona_v11(), sample_index=0)

    assert profile.grounded is True
    assert profile.source_tier == "individual_row_synthetic"
    assert profile.suppressed_count == 0
    by_feature = {d.feature: d for d in profile.deltas}

    # z = (14.0 - 10.0) / 2.0 = +2.0 → dramatically higher.
    assert by_feature["order_frequency_28d"].z == 2.0
    assert by_feature["order_frequency_28d"].direction == "higher"
    assert by_feature["order_frequency_28d"].magnitude == "dramatically"
    assert by_feature["order_frequency_28d"].label == "order frequency 28d"

    # z = (3.0 - 4.0) / 2.0 = -0.5 → somewhat lower (exactly at the threshold edge).
    assert by_feature["browse_dependency"].z == -0.5
    assert by_feature["browse_dependency"].direction == "lower"
    assert by_feature["browse_dependency"].magnitude == "somewhat"


def test_individual_row_ignores_centroid_features_namespace() -> None:
    # centroid_features carries a wild z (99.0) under a *_z key; the individual
    # row must z-score ONLY the adapted-feature-space fields and never surface it.
    profile = render_individual_row(_persona_v11(), sample_index=0)
    assert "order_frequency_z" not in {d.feature for d in profile.deltas}
    assert all(d.z != 99.0 for d in profile.deltas)


def test_individual_row_render_block_shape() -> None:
    block = render_individual_row(_persona_v11(), sample_index=0).render()
    assert block is not None
    assert block.startswith("## What's distinctive about you")
    assert "**dramatically higher** order frequency 28d" in block
    assert "DashPass Power" in block
    # The GMM-synthetic honesty hedge: a representative individual, not a record.
    assert "not an exact personal record" in block


def test_individual_row_suppresses_sub_threshold_but_counts() -> None:
    # Row 1 sits exactly at the centroid on both features → both |z| = 0.0,
    # suppressed, nothing rendered, but it is a real (grounded) average member.
    profile = render_individual_row(_persona_v11(), sample_index=1)
    assert profile.deltas == []
    assert profile.suppressed_count == 2
    assert profile.grounded is True
    assert profile.source_tier == "individual_row_synthetic"
    assert profile.render() is None


def test_individual_row_selection_is_deterministic_by_sample_index() -> None:
    p = _persona_v11()
    first = render_individual_row(p, sample_index=0)
    again = render_individual_row(p, sample_index=0)
    assert first.model_dump() == again.model_dump()


def test_individual_row_selection_wraps_modulo_len() -> None:
    # Two rows: index 2 wraps to row 0 (the distinctive one); index 1 is row 1
    # (the typical one). Selection is sample_index % len(sample_rows).
    p = _persona_v11()
    assert (
        render_individual_row(p, sample_index=2).model_dump()
        == render_individual_row(p, sample_index=0).model_dump()
    )
    assert (
        render_individual_row(p, sample_index=1).model_dump()
        != render_individual_row(p, sample_index=0).model_dump()
    )


def test_individual_row_paired_twins_draw_identical_row() -> None:
    # The #90 paired invariant: selection keys on sample_index ALONE (not the
    # arm), so a treatment agent and its control twin — which share sample_index
    # — render the byte-identical individual row.
    p = _persona_v11()
    treatment = render_individual_row(p, sample_index=7)
    control = render_individual_row(p, sample_index=7)
    assert treatment.render() == control.render()


def test_individual_row_absent_v11_fields_is_ungrounded() -> None:
    # A v1.0 pack (no centroid_full / feature_scale / sample_rows) degrades to an
    # ungrounded profile whose render() is None, so the composer falls back to
    # the centroid tier. Each missing field independently triggers the fallback.
    base = _persona(None)  # plain v1.0 persona, no v1.1 fields at all
    profile = render_individual_row(base, sample_index=0)
    assert profile.grounded is False
    assert profile.source_tier == "none"
    assert profile.deltas == []
    assert profile.render() is None

    no_rows = render_individual_row(_persona_v11(sample_rows=[]), sample_index=0)
    assert no_rows.source_tier == "none"
    no_centroid = render_individual_row(_persona_v11(centroid_full={}), sample_index=0)
    assert no_centroid.source_tier == "none"
    no_scale = render_individual_row(_persona_v11(feature_scale={}), sample_index=0)
    assert no_scale.source_tier == "none"


def test_individual_row_skips_non_finite_values() -> None:
    # NaN/inf in the row, centroid, or scale must be skipped — never rendered as
    # a half-formed delta (the FM-3 honesty rule). good_feat survives.
    p = _persona_v11(
        centroid_full={"good_feat": 0.0, "nan_c": 1.0, "inf_s": 1.0},
        feature_scale={"good_feat": 1.0, "nan_c": 1.0, "inf_s": math.inf},
        sample_rows=[{"good_feat": 1.5, "nan_c": math.nan, "inf_s": 5.0}],
    )
    profile = render_individual_row(p, sample_index=0)
    assert {d.feature for d in profile.deltas} == {"good_feat"}
    assert profile.suppressed_count == 0


def test_individual_row_skips_non_positive_scale() -> None:
    # A zero or negative feature_scale would divide-by-zero / flip the sign; the
    # producer floors std to epsilon, so this only trips on a malformed pack.
    p = _persona_v11(
        centroid_full={"good_feat": 0.0, "zero_scale": 0.0},
        feature_scale={"good_feat": 1.0, "zero_scale": 0.0},
        sample_rows=[{"good_feat": 1.5, "zero_scale": 9.0}],
    )
    profile = render_individual_row(p, sample_index=0)
    assert {d.feature for d in profile.deltas} == {"good_feat"}


def test_individual_row_skips_features_missing_from_row_or_scale() -> None:
    # A feature must appear in all three of centroid_full / row / feature_scale
    # to be z-scored; a partial key set is skipped, not fabricated.
    p = _persona_v11(
        centroid_full={"in_all": 0.0, "missing_from_row": 0.0, "missing_from_scale": 0.0},
        feature_scale={"in_all": 1.0, "missing_from_row": 1.0},
        sample_rows=[{"in_all": 2.0, "missing_from_scale": 2.0}],
    )
    profile = render_individual_row(p, sample_index=0)
    assert {d.feature for d in profile.deltas} == {"in_all"}


def test_individual_row_all_malformed_is_ungrounded() -> None:
    # Row inputs present but no feature yields a usable delta (all non-finite):
    # report ungrounded so a broken row can't masquerade as a real draw.
    p = _persona_v11(
        centroid_full={"a": math.nan, "b": 1.0},
        feature_scale={"a": 1.0, "b": math.inf},
        sample_rows=[{"a": 1.0, "b": 2.0}],
    )
    profile = render_individual_row(p, sample_index=0)
    assert profile.grounded is False
    assert profile.source_tier == "none"
    assert profile.deltas == []
    assert profile.suppressed_count == 0
    assert profile.render() is None


def test_individual_row_deltas_sorted_most_salient_first() -> None:
    p = _persona_v11(
        centroid_full={"big": 0.0, "alpha": 0.0, "zeta": 0.0},
        feature_scale={"big": 1.0, "alpha": 1.0, "zeta": 1.0},
        # |z|: big=3.0, alpha=1.0, zeta=1.0 → big first, then the 1.0 tie sorts
        # alpha before zeta by name.
        sample_rows=[{"big": 3.0, "alpha": -1.0, "zeta": 1.0}],
    )
    order = [d.feature for d in render_individual_row(p, sample_index=0).deltas]
    assert order == ["big", "alpha", "zeta"]


def test_individual_row_tunable_threshold() -> None:
    p = _persona_v11(
        centroid_full={"a": 0.0, "b": 0.0},
        feature_scale={"a": 1.0, "b": 1.0},
        sample_rows=[{"a": 0.7, "b": 1.3}],  # |z|: a=0.7, b=1.3
    )
    profile = render_individual_row(p, sample_index=0, salience_threshold=1.0)
    assert {d.feature for d in profile.deltas} == {"b"}
    assert profile.suppressed_count == 1
