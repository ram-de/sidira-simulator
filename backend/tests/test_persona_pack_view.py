"""Tests for services.persona_pack_view (#25, persona-pack-ui session).

The read-only presentation view the Library detail page renders: the centroid
"How you compare" block, the per-member individual-row block, all three weight
schemes with a truthful reason when one is absent, and the honesty flags carried
straight from the renderers. Covers the v1.0 degradation (no individual-row, no
fabricated row) and the v1.1 individual-row tier on a hand-built pack.
"""

from __future__ import annotations

from datetime import datetime

from sidira_simulator.schemas.persona import Persona, PersonaPack, WeightSchemes
from sidira_simulator.services.behavioral_profile import _MAX_INDIVIDUAL_ROW_DELTAS
from sidira_simulator.services.persona_pack_view import build_persona_pack_detail


def _v10_pack() -> PersonaPack:
    """A v1.0 pack: centroid_features present, NO v1.1 row inputs, all 3 schemes."""
    persona = Persona(
        id="p_heavy",
        name="Heavy Reorderer",
        description="Orders the same few things, often.",
        jtbd="Refill the staples without thinking.",
        behavioral_snapshot={"weekly_orders": 4.4, "tier": "dashpass"},
        centroid_features={
            "order_frequency_z": 1.62,  # much higher
            "browse_dependency_z": -1.33,  # much lower
            "noise_z": 0.1,  # sub-threshold → suppressed, counted
        },
    )
    other = Persona(
        id="p_light",
        name="Occasional Browser",
        description="Drops in now and then.",
        centroid_features={"order_frequency_z": -0.9},
    )
    return PersonaPack(
        version="v_1",
        customer_id="demo",
        generated_at=datetime(2026, 6, 1),
        schema_version="1.0",
        personas=[persona, other],
        weights=WeightSchemes(
            head_count={"p_heavy": 0.7, "p_light": 0.3},
            order_weighted={"p_heavy": 0.85, "p_light": 0.15},
            revenue_weighted=None,  # absent — must be reported with a reason
        ),
        stability_score=0.82,
    )


def test_v10_pack_renders_centroid_block_no_individual_row() -> None:
    detail = build_persona_pack_detail(_v10_pack())
    assert detail.schema_version == "1.0"
    assert detail.persona_count == 2
    assert detail.has_individual_rows is False

    heavy = next(p for p in detail.personas if p.id == "p_heavy")
    # Centroid tier renders, with the honesty flags intact.
    assert heavy.how_you_compare is not None
    block = heavy.how_you_compare
    assert block.grounded is True
    assert block.source_tier == "centroid_population"
    assert block.suppressed_count == 1  # noise_z below threshold, counted not dropped
    labels = {d.label: d for d in block.deltas}
    assert labels["order frequency"].direction == "higher"
    assert labels["order frequency"].magnitude == "much"
    assert labels["browse dependency"].direction == "lower"
    # v1.0 pack → no fabricated individual row.
    assert heavy.distinctive is None


def test_weight_schemes_availability_and_reason() -> None:
    detail = build_persona_pack_detail(_v10_pack())
    by_key = {s.key: s for s in detail.weight_schemes}
    assert by_key["head_count"].available is True
    assert by_key["order_weighted"].available is True
    assert by_key["revenue_weighted"].available is False
    # Absent optional scheme carries an honest, human reason — never a silent hole.
    assert by_key["revenue_weighted"].note
    assert by_key["head_count"].note is None


def test_persona_shares_only_for_available_schemes() -> None:
    detail = build_persona_pack_detail(_v10_pack())
    heavy = next(p for p in detail.personas if p.id == "p_heavy")
    assert heavy.shares["head_count"] == 0.7
    assert heavy.shares["order_weighted"] == 0.85
    # No hole for the unavailable scheme — the key is simply absent.
    assert "revenue_weighted" not in heavy.shares


def test_v11_pack_renders_individual_row_block() -> None:
    """A v1.1 pack (sample_rows + centroid_full + feature_scale) renders the tier."""
    persona = Persona(
        id="p_v11",
        name="Power User",
        description="A frequent, high-intent member.",
        centroid_features={"order_frequency_z": 1.5},
        centroid_full={"orders": 10.0, "browse": 5.0},
        feature_scale={"orders": 2.0, "browse": 1.0},
        # Row diverges hard on `orders` (z=+3 → dramatically), flat on `browse`.
        sample_rows=[{"orders": 16.0, "browse": 5.0}],
    )
    pack = PersonaPack(
        version="v_2",
        customer_id="demo",
        generated_at=datetime(2026, 6, 1),
        schema_version="1.1",
        personas=[persona],
        weights=WeightSchemes(head_count={"p_v11": 1.0}),
        stability_score=0.9,
    )
    detail = build_persona_pack_detail(pack)
    assert detail.has_individual_rows is True
    block = detail.personas[0].distinctive
    assert block is not None
    assert block.grounded is True
    assert block.source_tier == "individual_row_synthetic"
    assert len(block.deltas) <= _MAX_INDIVIDUAL_ROW_DELTAS
    orders = next(d for d in block.deltas if d.label == "orders")
    assert orders.direction == "higher"
    assert orders.magnitude == "dramatically"


def test_v11_all_typical_row_still_reports_tier_available() -> None:
    """Row inputs present but the representative row is all-typical (no salient
    deltas): `has_individual_rows` must stay True (tier available, nothing
    distinctive) — distinguishable from a v1.0 pack with no row tier at all."""
    persona = Persona(
        id="p_avg",
        name="Average Member",
        description="A member who sits right on the segment norm.",
        centroid_features={"order_frequency_z": 1.5},
        centroid_full={"orders": 10.0, "browse": 5.0},
        feature_scale={"orders": 2.0, "browse": 1.0},
        # Row sits exactly on the centroid → every within-cluster z is 0.
        sample_rows=[{"orders": 10.0, "browse": 5.0}],
    )
    pack = PersonaPack(
        version="v_2",
        customer_id="demo",
        generated_at=datetime(2026, 6, 1),
        schema_version="1.1",
        personas=[persona],
        weights=WeightSchemes(head_count={"p_avg": 1.0}),
        stability_score=0.9,
    )
    detail = build_persona_pack_detail(pack)
    assert detail.has_individual_rows is True  # tier available…
    assert detail.personas[0].distinctive is None  # …but nothing distinctive to show
