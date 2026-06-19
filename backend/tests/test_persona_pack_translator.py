"""Tests for the sidira-personas producer → consumer pack translator.

The translator (`persona_pack_translator.translate_producer_pack`) is the seam
that turns a producer `persona_pack.json` (different top-level + step-1 field
names) into the consumer `PersonaPack`. These cover the field mapping, the
per-persona → per-pack weights transpose, the v1.1 quad passthrough, v1.0
degradation, and — the point of the whole exercise — that a translated v1.1
pack makes `render_individual_row` actually fire (§2 step-2 activation).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from sidira_simulator.schemas.persona import BehavioralSeedSchema, PersonaPack
from sidira_simulator.services import identity_seed as identity_seed_module
from sidira_simulator.services.behavioral_profile import (
    _MAX_INDIVIDUAL_ROW_DELTAS,
    render_individual_row,
)
from sidira_simulator.services.identity_seed import draw_identity_seed
from sidira_simulator.services.persona_pack_translator import translate_producer_pack
from sidira_simulator.services.population_sampler import allocate


def _producer_behavioral_seeds() -> dict:
    """The producer's #342 ``behavioral_seeds`` object — the five identity-draw
    pools, most-common-first."""
    return {
        "age_bands": ["25-34", "35-44"],
        "locale_bands": ["urban_us", "suburban_us"],
        "tenure_bands": ["established (1-3y)", "veteran (3y+)"],
        "current_state_pool": [
            "weekday evening, in a hurry",
            "weekend, browsing options",
            "post-work, decision-fatigued",
            "late night, comfort mood",
            "lunch break, time-boxed",
        ],
        "recent_gripe_pool": [
            "fees added up at checkout",
            "delivery later than estimated",
            "promo code didn't apply",
            "order arrived cold",
        ],
    }

# A trimmed slice of a REAL producer pack: `sidira-personas run --no-llm` on a
# SYNTHETIC parquet (privacy-clean by construction). Keeps 2 personas (a GMM
# persona P01 + a prefilter FIXED_DORMANT) and the 12 most distinctive features
# of the live 114-feature pack, at 3 sample rows each — exercising the producer's
# real field shapes end-to-end without committing a 628 KB artifact.
_REAL_FIXTURE = Path(__file__).parent / "fixtures" / "producer_pack_v1_1_sample.json"


def _producer_persona_v11(persona_id: str = "P01") -> dict:
    """A producer-format persona with the v1.1 quad and a distinctive sample row.

    Mirrors the real `sidira-personas` shape: per-persona `weights`, a
    `top_features` list of FeatureDelta dicts, a top-only `centroid`, plus the
    v1.1 fields. The single sample row is far enough from `centroid_full` (z=3.0
    on order_frequency_28d) that `render_individual_row` emits a block.
    """
    return {
        "id": persona_id,
        "name": "DashPass Power",
        "description": "Orders often, leans on the app, low price sensitivity.",
        "jtbd": "Get dinner handled fast without thinking about it.",
        "size": 408,
        "weights": {"by_headcount": 0.30, "by_orders": 0.42, "by_revenue": None},
        "stability": 0.67,
        "top_features": [
            {
                "feature": "order_frequency_28d",
                "group": "behavioral_patterns",
                "centroid_value": 10.0,
                "population_mean": 6.0,
                "population_std": 4.0,
                "z_delta": 1.0,
            },
            {
                "feature": "browse_dependency",
                "group": "channel_tech_behavior",
                "centroid_value": 4.0,
                "population_mean": 3.0,
                "population_std": 2.0,
                "z_delta": 0.5,
            },
        ],
        "centroid": {"order_frequency_28d": 10.0},
        "centroid_full": {"order_frequency_28d": 10.0, "browse_dependency": 4.0},
        "feature_scale": {"order_frequency_28d": 2.0, "browse_dependency": 2.0},
        "sample_rows": [
            {"order_frequency_28d": 16.0, "browse_dependency": 4.0},
            {"order_frequency_28d": 10.0, "browse_dependency": 4.0},
        ],
        "posterior_mean": {"P01": 0.7, "P02": 0.3},
    }


def _producer_pack_v11() -> dict:
    """A full producer pack (top-level + 2 personas) in v1.1 format."""
    return {
        "schema_version": "1.1",
        "company_id": "doordash",
        "run_id": "dd-20260517T162638",
        "created_at": "2026-05-17T16:27:04.655377",
        "n_users": 8823,
        "feature_groups": ["behavioral_patterns", "channel_tech_behavior"],
        "personas": [
            _producer_persona_v11("P01"),
            _producer_persona_v11("P02"),
        ],
        "cluster_method": "gmm",
        "k_selected": 2,
        "encoder_method": "pca",
        "embedding_dim_per_group": 8,
        "overall_stability": 0.67,
        "notes": {},
    }


# --- top-level field mapping ------------------------------------------------


def test_top_level_fields_mapped():
    pack = translate_producer_pack(_producer_pack_v11())

    assert isinstance(pack, PersonaPack)
    assert pack.customer_id == "doordash"  # company_id → customer_id
    assert pack.version == "dd-20260517T162638"  # run_id → version
    assert pack.schema_version == "1.1"
    assert pack.stability_score == pytest.approx(0.67)  # overall_stability
    assert pack.generated_at.year == 2026 and pack.generated_at.month == 5
    assert pack.is_starter is False
    assert [p.id for p in pack.personas] == ["P01", "P02"]


def test_version_override_wins_over_run_id():
    pack = translate_producer_pack(_producer_pack_v11(), version="v_3")
    assert pack.version == "v_3"


def test_is_starter_flag_passthrough():
    pack = translate_producer_pack(_producer_pack_v11(), is_starter=True)
    assert pack.is_starter is True


# --- persona / step-1 centroid mapping --------------------------------------


def test_centroid_features_from_top_features():
    pack = translate_producer_pack(_producer_pack_v11())
    p = pack.personas[0]
    # top_features[].{feature: z_delta} — drops group/centroid_value/pop_* members.
    assert p.centroid_features == {
        "order_frequency_28d": 1.0,
        "browse_dependency": 0.5,
    }
    # producer-only fields that have no consumer home are not smuggled in.
    assert "size" not in p.model_dump()
    assert p.behavioral_snapshot == {}
    assert p.behavioral_seeds is None


# --- weights transpose (per-persona → per-pack) -----------------------------


def test_weights_transposed_to_schemes():
    pack = translate_producer_pack(_producer_pack_v11())
    assert pack.weights.head_count == {"P01": 0.30, "P02": 0.30}
    # by_orders present on both → order_weighted scheme built (complete).
    assert pack.weights.order_weighted == {"P01": 0.42, "P02": 0.42}
    # by_revenue null on every persona → scheme stays None (not a dict of zeros).
    assert pack.weights.revenue_weighted is None


def test_optional_scheme_emitted_only_when_complete():
    """An optional scheme is built only when EVERY persona has a non-null value;
    a single missing one drops the whole scheme to None — never a sparse dict
    (which would fail the consumer's allocate() coverage/sum contract)."""
    producer = _producer_pack_v11()
    # by_revenue non-null on only one persona → still None (incomplete).
    producer["personas"][1]["weights"]["by_revenue"] = 0.55
    assert translate_producer_pack(producer).weights.revenue_weighted is None

    # set it on BOTH → now the complete scheme is emitted.
    producer["personas"][0]["weights"]["by_revenue"] = 0.45
    pack = translate_producer_pack(producer)
    assert pack.weights.revenue_weighted == {"P01": 0.45, "P02": 0.55}


def test_partial_order_weighted_dropped():
    """by_orders missing on one persona → order_weighted drops to None rather
    than shipping a scheme that omits a persona present in the pack."""
    producer = _producer_pack_v11()
    producer["personas"][0]["weights"]["by_orders"] = None
    assert translate_producer_pack(producer).weights.order_weighted is None


def test_translated_schemes_pass_allocate_contract():
    """Every scheme the translator emits must satisfy allocate()'s coverage +
    sum-to-1.0 contract — the whole reason partial schemes are dropped. Use
    producer weights that actually sum to 1.0 across personas (real packs do)."""
    producer = _producer_pack_v11()
    for pid_idx, hc, orders in ((0, 0.6, 0.7), (1, 0.4, 0.3)):
        producer["personas"][pid_idx]["weights"] = {
            "by_headcount": hc,
            "by_orders": orders,
            "by_revenue": None,
        }
    pack = translate_producer_pack(producer)

    for scheme in ("head_count", "order_weighted"):
        alloc = allocate(pack, 10, weight_scheme=scheme)
        assert sum(c for _, c in alloc) == 10  # no crash, counts conserved
    # revenue_weighted is None → selecting it raises, never silently miscounts.
    with pytest.raises(ValueError, match="revenue_weighted"):
        allocate(pack, 10, weight_scheme="revenue_weighted")


def test_missing_by_headcount_defaults_zero():
    producer = _producer_pack_v11()
    del producer["personas"][0]["weights"]["by_headcount"]
    pack = translate_producer_pack(producer)
    assert pack.weights.head_count["P01"] == 0.0


# --- v1.1 quad passthrough (1:1) --------------------------------------------


def test_v11_quad_passes_through_unchanged():
    producer = _producer_pack_v11()
    pack = translate_producer_pack(producer)
    p = pack.personas[0]
    src = producer["personas"][0]
    assert p.centroid_full == src["centroid_full"]
    assert p.feature_scale == src["feature_scale"]
    assert p.sample_rows == src["sample_rows"]
    assert p.posterior_mean == src["posterior_mean"]


# --- v1.0 degradation -------------------------------------------------------


def test_v10_pack_degrades_to_empty_quad():
    """A producer pack without the v1.1 quad still translates; the consumer
    Persona keeps schema defaults so the simulator falls back to centroid tier."""
    producer = _producer_pack_v11()
    producer["schema_version"] = "1.0"
    for persona in producer["personas"]:
        for f in ("centroid_full", "feature_scale", "sample_rows", "posterior_mean"):
            persona.pop(f, None)

    pack = translate_producer_pack(producer)
    assert pack.schema_version == "1.0"
    p = pack.personas[0]
    assert p.centroid_full == {}
    assert p.feature_scale == {}
    assert p.sample_rows == []
    assert p.posterior_mean is None
    # the step-1 centroid tier still carries over.
    assert p.centroid_features


# --- required-field validation ----------------------------------------------


def test_missing_company_id_raises():
    producer = _producer_pack_v11()
    del producer["company_id"]
    with pytest.raises(ValueError, match="company_id"):
        translate_producer_pack(producer)


def test_missing_personas_raises():
    producer = _producer_pack_v11()
    producer["personas"] = []
    with pytest.raises(ValueError, match="personas"):
        translate_producer_pack(producer)


def test_missing_run_id_and_no_override_raises():
    producer = _producer_pack_v11()
    del producer["run_id"]
    with pytest.raises(ValueError, match="run_id"):
        translate_producer_pack(producer)


def test_missing_run_id_but_override_given_ok():
    producer = _producer_pack_v11()
    del producer["run_id"]
    pack = translate_producer_pack(producer, version="v_1")
    assert pack.version == "v_1"


def test_persona_missing_id_raises():
    producer = _producer_pack_v11()
    del producer["personas"][0]["id"]
    with pytest.raises(ValueError, match="id"):
        translate_producer_pack(producer)


# --- end-to-end: the activation the whole PR exists for ---------------------


def test_translated_v11_pack_fires_render_individual_row():
    """The point of step-2 activation: a translated v1.1 pack must make
    `render_individual_row` produce a grounded individual-row block, not degrade
    to the centroid tier."""
    pack = translate_producer_pack(_producer_pack_v11())
    persona = pack.personas[0]

    profile = render_individual_row(persona, sample_index=0)
    assert profile.source_tier == "individual_row_synthetic"
    block = profile.render()
    assert block is not None and block.strip()
    # row 0 has order_frequency_28d=16 vs centroid 10, scale 2 → z=+3.0.
    assert "distinctive" in block.lower()


def test_translated_pack_paired_twins_draw_identical_row():
    """Row selection keys on sample_index alone, so the same index on the same
    translated persona is deterministic — preserving the #90 paired invariant."""
    pack = translate_producer_pack(_producer_pack_v11())
    persona = pack.personas[0]
    a = render_individual_row(persona, sample_index=4)
    b = render_individual_row(persona, sample_index=4)
    assert a.model_dump() == b.model_dump()


def test_translation_does_not_mutate_input():
    producer = _producer_pack_v11()
    before = copy.deepcopy(producer)
    translate_producer_pack(producer)
    assert producer == before


# --- against a REAL (synthetic-data) producer pack --------------------------


def test_real_producer_fixture_translates_and_fires():
    """The full activation, end-to-end on a real producer pack: load the
    `sidira-personas`-emitted JSON, translate it, and confirm the resulting
    PersonaPack drives a grounded individual-row block on a live persona."""
    producer = json.loads(_REAL_FIXTURE.read_text())
    pack = translate_producer_pack(producer, version="v_1")

    assert pack.schema_version == "1.1"
    assert pack.customer_id == "doordash"
    ids = [p.id for p in pack.personas]
    assert ids == ["P01", "FIXED_DORMANT"]

    p01 = pack.personas[0]
    profile = render_individual_row(p01, sample_index=0)
    assert profile.source_tier == "individual_row_synthetic"
    assert profile.render()

    # The degenerate constant-in-cluster feature (producer scale ~1e-9) must NOT
    # surface as the agent's headline trait — the floored-scale guard drops it.
    assert "dashpass_status_subscribed" not in {d.feature for d in profile.deltas}
    assert profile.deltas, "expected at least one genuine distinctive feature"
    assert all(abs(d.z) < 1e3 for d in profile.deltas)


def test_real_fixed_persona_has_null_posterior_but_still_grounds():
    """A prefilter FIXED_* persona carries no GMM posterior (null) yet still has
    a populated v1.1 quad, so it grounds an individual-row block all the same."""
    producer = json.loads(_REAL_FIXTURE.read_text())
    pack = translate_producer_pack(producer, version="v_1")

    fixed = pack.personas[1]
    assert fixed.id == "FIXED_DORMANT"
    assert fixed.posterior_mean is None
    assert fixed.centroid_full and fixed.feature_scale and fixed.sample_rows

    profile = render_individual_row(fixed, sample_index=0)
    assert profile.source_tier == "individual_row_synthetic"
    assert profile.render()


# --- behavioral_seeds: producer #342 → consumer identity_seed (the gap) ------


def test_behavioral_seeds_mapped_from_producer():
    """A producer pack carrying #342 behavioral_seeds → the translated Persona
    carries a BehavioralSeedSchema, field-for-field, instead of defaulting None."""
    producer = _producer_pack_v11()
    seeds = _producer_behavioral_seeds()
    producer["personas"][0]["behavioral_seeds"] = seeds

    pack = translate_producer_pack(producer)
    p = pack.personas[0]
    assert isinstance(p.behavioral_seeds, BehavioralSeedSchema)
    assert p.behavioral_seeds.age_bands == seeds["age_bands"]
    assert p.behavioral_seeds.locale_bands == seeds["locale_bands"]
    assert p.behavioral_seeds.tenure_bands == seeds["tenure_bands"]
    assert p.behavioral_seeds.current_state_pool == seeds["current_state_pool"]
    assert p.behavioral_seeds.recent_gripe_pool == seeds["recent_gripe_pool"]
    # a persona WITHOUT the field still translates to None (no-LLM / v1.0 path)
    assert pack.personas[1].behavioral_seeds is None


def test_behavioral_seeds_absent_or_null_translates_to_none():
    """No behavioral_seeds key, or an explicit null, → None (simulator falls back
    to its generic default pool, exactly as today)."""
    producer = _producer_pack_v11()
    assert translate_producer_pack(producer).personas[0].behavioral_seeds is None

    producer["personas"][0]["behavioral_seeds"] = None
    assert translate_producer_pack(producer).personas[0].behavioral_seeds is None


def test_translated_behavioral_seeds_drive_identity_seed_without_fallback_warn(capsys):
    """The point of #342 task C: a translated pack WITH behavioral_seeds makes
    `draw_identity_seed` draw from the per-persona pools and NOT emit the
    'identity_seed fallback active' warning."""
    identity_seed_module._fallback_warned.clear()
    try:
        producer = _producer_pack_v11()
        seeds = _producer_behavioral_seeds()
        producer["personas"][0]["behavioral_seeds"] = seeds

        pack = translate_producer_pack(producer)
        persona = pack.personas[0]

        drawn = [draw_identity_seed(persona, sample_index=i, run_seed=7) for i in range(20)]
        # every field comes from THIS persona's pool, never the generic default
        for s in drawn:
            assert s.age_band in seeds["age_bands"]
            assert s.tenure_band in seeds["tenure_bands"]
            assert s.current_state in seeds["current_state_pool"]
            assert s.recent_gripe in seeds["recent_gripe_pool"]

        out = capsys.readouterr().out
        assert "identity_seed fallback active" not in out
        assert "cross-persona variance degraded" not in out
        assert persona.id not in identity_seed_module._fallback_warned
    finally:
        identity_seed_module._fallback_warned.clear()


def test_persona_without_seeds_still_warns_fallback(capsys):
    """Control: a persona translated WITHOUT behavioral_seeds (no-LLM/v1.0 pack)
    still trips the fallback warning — proving the warning fires on the gap and
    the WITH-seeds test above genuinely closes it."""
    identity_seed_module._fallback_warned.clear()
    try:
        pack = translate_producer_pack(_producer_pack_v11())
        persona = pack.personas[0]
        assert persona.behavioral_seeds is None
        draw_identity_seed(persona, sample_index=0, run_seed=7)
        out = capsys.readouterr().out
        assert "cross-persona variance degraded" in out
    finally:
        identity_seed_module._fallback_warned.clear()


# --- against the reproducible synthetic harness (sidira-simulator#247) -------
#
# Unlike _REAL_FIXTURE (a DoorDash-shaped pack with a hand-curated degenerate-
# scale edge case), this fixture is a trimmed slice of the *reproducible*
# `sidira-personas run --config config/synthetic.yaml --no-llm` output
# (ram-de/sidira-personas#13) — no Snowflake, no API key, no real data. It is
# the cross-repo regression guard for the dormant §2 individual-row chain: as
# either repo evolves, a genuine current-harness pack must keep translating and
# firing. See sidira-simulator#247.
_SYNTH_FIXTURE = Path(__file__).parent / "fixtures" / "producer_pack_synthetic_e2e.json"


def test_synthetic_harness_pack_translates_and_all_fire():
    """A pack from the live `config/synthetic.yaml` harness translates cleanly and
    every persona (discovered + FIXED) fires the synthetic individual-row tier."""
    producer = json.loads(_SYNTH_FIXTURE.read_text())
    pack = translate_producer_pack(producer)

    assert pack.schema_version == "1.1"
    assert pack.customer_id == "synthetic"
    assert {p.id for p in pack.personas} == {"P05", "FIXED_DORMANT"}

    for persona in pack.personas:
        profile = render_individual_row(persona, sample_index=0)
        assert profile.source_tier == "individual_row_synthetic", persona.id
        assert profile.grounded, persona.id
        assert profile.render().strip(), persona.id


def test_synthetic_harness_weight_schemes_transpose_and_allocate():
    """`order_weighted` survives the per-persona→per-pack transpose; the synthetic
    config carries no revenue column, so `revenue_weighted` drops to None rather
    than shipping a partial scheme that would fail `allocate()`. Both live schemes
    must clear allocate()'s coverage + sum-to-1.0 contract end-to-end."""
    producer = json.loads(_SYNTH_FIXTURE.read_text())
    pack = translate_producer_pack(producer)
    persona_ids = {p.id for p in pack.personas}

    assert pack.weights.head_count is not None
    assert pack.weights.order_weighted is not None
    assert pack.weights.revenue_weighted is None
    # both complete schemes cover every persona and sum to ~1.0
    for scheme in (pack.weights.head_count, pack.weights.order_weighted):
        assert set(scheme) == persona_ids
        assert abs(sum(scheme.values()) - 1.0) < 1e-6

    # and they actually allocate without tripping _validate_weights. Pin
    # max_agents so the count is conserved exactly regardless of any ambient
    # SIDIRA_MAX_AGENTS/PYTHIA_MAX_AGENTS env cap.
    for scheme in ("head_count", "order_weighted"):
        alloc = allocate(pack, 40, weight_scheme=scheme, max_agents=40)
        assert sum(c for _, c in alloc) == 40
        assert {pid for pid, _ in alloc} == persona_ids
    with pytest.raises(ValueError, match="revenue_weighted"):
        allocate(pack, 40, weight_scheme="revenue_weighted", max_agents=40)


def test_synthetic_harness_delta_cap_renders_with_truthful_tail():
    """A real harness persona has far more than the cap of distinctive features;
    the rendered block must show at most _MAX_INDIVIDUAL_ROW_DELTAS bullets and
    own the remainder with a truthful tail rather than silently dropping them."""
    producer = json.loads(_SYNTH_FIXTURE.read_text())
    pack = translate_producer_pack(producer)
    p05 = next(p for p in pack.personas if p.id == "P05")

    profile = render_individual_row(p05, sample_index=0)
    bullets = [ln for ln in profile.render().splitlines() if ln.lstrip().startswith("- ")]
    assert len(bullets) <= _MAX_INDIVIDUAL_ROW_DELTAS
    # the persona genuinely has more deltas than the cap, so the tail must appear
    assert len(profile.deltas) > _MAX_INDIVIDUAL_ROW_DELTAS
    assert "further" in profile.render().lower()


def test_synthetic_harness_fixed_persona_grounds_with_null_posterior():
    """The prefilter FIXED_DORMANT persona from the synthetic harness carries no
    GMM posterior yet still grounds an individual-row block from its v1.1 quad."""
    producer = json.loads(_SYNTH_FIXTURE.read_text())
    pack = translate_producer_pack(producer)
    fixed = next(p for p in pack.personas if p.id == "FIXED_DORMANT")

    assert fixed.posterior_mean is None
    assert fixed.centroid_full and fixed.feature_scale and fixed.sample_rows
    profile = render_individual_row(fixed, sample_index=0)
    assert profile.source_tier == "individual_row_synthetic"
    assert profile.render().strip()
