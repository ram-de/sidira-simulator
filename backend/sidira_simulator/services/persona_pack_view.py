"""Read-only presentation view of a Persona Pack for the Library detail page.

`GET /persona-packs/{id}` returns the producer→consumer `PersonaPack` as-is —
including the bulky v1.1 arrays (`centroid_full` / `feature_scale` /
`sample_rows`), which are model inputs, not things a human reads. This module
assembles the *human-facing* projection the detail page renders (#25,
persona-pack-ui session):

- the centroid **"How you compare"** block (the persona-vs-population profile), and
- the per-member **"What's distinctive"** block (the individual-row tier),

both rendered through the single-sourced honesty/salience logic in
`behavioral_profile.py` — so the grounding/suppression/cap rules that govern
what the *agent* reads also govern what the *PM* sees, with no second
implementation to drift. It also folds the three weight schemes into per-persona
shares, carrying a truthful reason when an optional scheme is unavailable, and
exposes the pack's stability/honesty flags.

It deliberately does NOT echo the raw v1.1 arrays: the UI consumes the rendered
deltas, not the synthetic rows, and a real v1.1 pack's arrays would balloon the
payload for no reader.

Pure and side-effect-free: a `PersonaPack` in, a `PersonaPackDetail` out. The
view copy is third-person ("the {segment}") because the audience is a PM reading
records, not the agent being addressed as "you" in the prompt — the same
deltas, a different reader.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sidira_simulator.schemas.persona import Persona, PersonaPack
from sidira_simulator.services.behavioral_profile import (
    _MAX_INDIVIDUAL_ROW_DELTAS,
    BehavioralProfile,
    Direction,
    Magnitude,
    render_behavioral_profile,
    render_individual_row,
)

# Which synthetic member the detail page renders for the individual-row block.
# One representative draw (sample_index 0) is enough to *show* within-persona
# variety exists; the page is a record, not an explorer, so it does not page
# through all sample_rows. Deterministic, matching the consumer's selection math.
_REPRESENTATIVE_SAMPLE_INDEX = 0

# Human labels for the weight schemes (machine keys → record voice, §5.4).
_SCHEME_LABELS: dict[str, str] = {
    "head_count": "By headcount",
    "order_weighted": "By order volume",
    "revenue_weighted": "By revenue",
}
# Order schemes are presented in, headcount first (it is always present).
_SCHEME_ORDER: tuple[str, ...] = ("head_count", "order_weighted", "revenue_weighted")

# Why an optional scheme is absent. The producer emits order_weighted /
# revenue_weighted only when EVERY persona has a non-null value (the
# `_complete_scheme` rule in persona_pack_translator); a partial scheme is
# dropped rather than shown with holes. This is the honest reason the UI states.
_SCHEME_UNAVAILABLE_NOTE: dict[str, str] = {
    "order_weighted": (
        "Not shown — the source data did not carry order volume for every "
        "persona, so this weighting can't be computed without gaps."
    ),
    "revenue_weighted": (
        "Not shown — the source data did not carry revenue for every persona, "
        "so this weighting can't be computed without gaps."
    ),
}


class DeltaView(BaseModel):
    """One salient behavioral difference, as a comparative (never a raw number)."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(description="Humanized feature name, e.g. 'order frequency'.")
    direction: Direction
    magnitude: Magnitude


class ProfileBlockView(BaseModel):
    """A rendered behavioral-comparison block, with its honesty flags intact.

    `grounded`/`source_tier`/`suppressed_count` are carried straight from the
    renderer so the page can be as honest as the prompt: a thin or absent source
    is shown as such, never dressed up as a rich profile.
    """

    model_config = ConfigDict(extra="forbid")

    heading: str
    intro: str
    deltas: list[DeltaView] = Field(default_factory=list)
    tail_count: int = Field(
        default=0,
        description="Salient deltas beyond the shown handful (individual-row tier "
        "only) — counted, never silently dropped.",
    )
    suppressed_count: int = Field(
        default=0,
        description="Finite features below the salience threshold — counted, not dropped.",
    )
    grounded: bool
    source_tier: str
    note: str = Field(description="The honesty hedge shown beneath the deltas.")


class WeightSchemeView(BaseModel):
    """Pack-level availability of one weighting basis, with a reason when absent."""

    model_config = ConfigDict(extra="forbid")

    key: Literal["head_count", "order_weighted", "revenue_weighted"]
    label: str
    available: bool
    note: str | None = Field(
        default=None, description="Why this scheme is unavailable, when it is."
    )


class PersonaProfileView(BaseModel):
    """One persona as a record: its prose plus the rendered v1.1 richness."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    jtbd: str | None = None
    behavioral_snapshot: dict[str, float | int | str] = Field(default_factory=dict)
    # Per-scheme share for this persona, keyed by scheme key — only the schemes
    # available on the pack appear, so the UI never shows a hole.
    shares: dict[str, float] = Field(default_factory=dict)
    how_you_compare: ProfileBlockView | None = Field(
        default=None,
        description="Persona-vs-population centroid block; None when no feature is salient.",
    )
    distinctive: ProfileBlockView | None = Field(
        default=None,
        description="Per-member individual-row block; None on a v1.0 pack (no row inputs).",
    )


class PersonaPackDetail(BaseModel):
    """The full read-only detail view the Library renders for one pack."""

    model_config = ConfigDict(extra="forbid")

    version: str
    customer_id: str
    generated_at: datetime
    schema_version: str
    is_starter: bool
    stability_score: float
    persona_count: int
    has_individual_rows: bool = Field(
        description="True when the pack carries v1.1 row inputs (sample_rows) for at "
        "least one persona — i.e. the individual-row tier is available to render.",
    )
    weight_schemes: list[WeightSchemeView]
    personas: list[PersonaProfileView]


def _delta_views(profile: BehavioralProfile, *, cap: int | None) -> tuple[list[DeltaView], int]:
    """Project a profile's deltas to the view, applying the renderer's display cap.

    Returns (shown, tail_count). The centroid tier shows every salient delta
    (cap=None); the individual-row tier shows the most-divergent handful and
    tail-counts the rest, mirroring `_render_individual_row` so the prompt and
    the page truncate identically.
    """
    deltas = profile.deltas
    shown = deltas if cap is None else deltas[:cap]
    tail = len(deltas) - len(shown)
    views = [
        DeltaView(label=d.label, direction=d.direction, magnitude=d.magnitude) for d in shown
    ]
    return views, tail


def _centroid_block(persona: Persona) -> ProfileBlockView | None:
    """The persona-vs-population "How you compare" block, or None if nothing salient."""
    profile = render_behavioral_profile(persona)
    if not profile.deltas:
        return None
    views, _ = _delta_views(profile, cap=None)
    return ProfileBlockView(
        heading="How this segment compares",
        intro=(
            f"Compared with the typical user, the {persona.name} segment tends to show:"
        ),
        deltas=views,
        tail_count=0,
        suppressed_count=profile.suppressed_count,
        grounded=profile.grounded,
        source_tier=profile.source_tier,
        note=(
            "These are tendencies of the segment, not exact figures — a modelled "
            "centroid, not a personal record."
        ),
    )


def _distinctive_block(persona: Persona) -> ProfileBlockView | None:
    """The per-member individual-row block, or None on a v1.0 pack (no row inputs)."""
    profile = render_individual_row(persona, _REPRESENTATIVE_SAMPLE_INDEX)
    if not profile.deltas:
        return None
    views, tail = _delta_views(profile, cap=_MAX_INDIVIDUAL_ROW_DELTAS)
    return ProfileBlockView(
        heading="What's distinctive about one member",
        intro=(
            f"A representative individual from the {persona.name} segment — not the "
            "average member — tends to show:"
        ),
        deltas=views,
        tail_count=tail,
        suppressed_count=profile.suppressed_count,
        grounded=profile.grounded,
        source_tier=profile.source_tier,
        note=(
            "The behavioral texture of one synthetic member (a privacy-clean "
            "modelled draw), not a real person's history."
        ),
    )


def _weight_schemes(pack: PersonaPack) -> list[WeightSchemeView]:
    """Which weighting bases the pack carries, with an honest reason when one is absent."""
    present = {
        "head_count": pack.weights.head_count,
        "order_weighted": pack.weights.order_weighted,
        "revenue_weighted": pack.weights.revenue_weighted,
    }
    schemes: list[WeightSchemeView] = []
    for key in _SCHEME_ORDER:
        available = bool(present[key])
        schemes.append(
            WeightSchemeView(
                key=key,  # type: ignore[arg-type]
                label=_SCHEME_LABELS[key],
                available=available,
                note=None if available else _SCHEME_UNAVAILABLE_NOTE.get(key),
            )
        )
    return schemes


def _persona_shares(pack: PersonaPack, persona_id: str) -> dict[str, float]:
    """This persona's share under each AVAILABLE scheme (absent schemes omitted)."""
    by_scheme = {
        "head_count": pack.weights.head_count,
        "order_weighted": pack.weights.order_weighted,
        "revenue_weighted": pack.weights.revenue_weighted,
    }
    shares: dict[str, float] = {}
    for key, table in by_scheme.items():
        if not table:
            continue
        value = table.get(persona_id)
        if value is not None:
            shares[key] = value
    return shares


def build_persona_pack_detail(pack: PersonaPack) -> PersonaPackDetail:
    """Assemble the read-only detail view for a Persona Pack (pure).

    Renders each persona's centroid + individual-row blocks through the
    behavioral-profile renderers (so the honesty rules stay single-sourced),
    folds the weight schemes into per-persona shares with a truthful absent
    reason, and surfaces stability/version metadata — without echoing the bulky
    raw v1.1 arrays.
    """
    personas = [
        PersonaProfileView(
            id=p.id,
            name=p.name,
            description=p.description,
            jtbd=p.jtbd,
            behavioral_snapshot=p.behavioral_snapshot,
            shares=_persona_shares(pack, p.id),
            how_you_compare=_centroid_block(p),
            distinctive=_distinctive_block(p),
        )
        for p in pack.personas
    ]
    return PersonaPackDetail(
        version=pack.version,
        customer_id=pack.customer_id,
        generated_at=pack.generated_at,
        schema_version=pack.schema_version,
        is_starter=pack.is_starter,
        stability_score=pack.stability_score,
        persona_count=len(pack.personas),
        has_individual_rows=any(p.distinctive is not None for p in personas),
        weight_schemes=_weight_schemes(pack),
        personas=personas,
    )
