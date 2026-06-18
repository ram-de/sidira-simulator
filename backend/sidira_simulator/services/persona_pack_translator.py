"""Translate a sidira-personas *producer* pack into the consumer ``PersonaPack``.

The producer (``sidira-personas``) and the consumer (this repo) duplicate the
Persona Pack schema until the shared ``pythia-schemas`` package lands, and the
two use **different field names** at the top level and for the step-1 centroid
tier. This module is the single, tested seam that maps the producer's serialized
JSON — ``dataclasses.asdict`` output, i.e. the on-the-wire pack — into the
consumer's pydantic :class:`PersonaPack`.

It consumes the wire **dict**, NOT producer objects: the simulator venv does not
``import sidira_personas`` (a separate repo), so the contract between the two is
the JSON, and that is exactly what we translate here. ``persona_builder`` (the
Phase-4.5 build orchestrator, still a stub) will call this after the library
emits a pack, before writing to R2.

Field map (producer → consumer)::

    PersonaPack
        company_id          → customer_id
        run_id              → version              (override via ``version=``)
        created_at          → generated_at         (ISO str → datetime, pydantic-coerced)
        overall_stability   → stability_score
        schema_version      → schema_version       ("1.0" | "1.1")
        weights             ← per-persona weights (transposed, see below)
    Persona
        id / name / description / jtbd                  → same
        top_features[].{feature, z_delta}               → centroid_features {feature: z_delta}
        centroid_full / feature_scale / sample_rows / posterior_mean → same (v1.1, 1:1)

The producer carries ``weights`` **per persona** (``{by_headcount, by_orders,
by_revenue}``); the consumer carries them **per pack** as
:class:`WeightSchemes` (``{scheme: {persona_id: weight}}``). We transpose:
``head_count`` is always present; ``order_weighted`` / ``revenue_weighted`` are
emitted only when **every** persona has a non-null value (a partial scheme would
fail the consumer's ``allocate()`` contract — see ``_build_weight_schemes``).

Dropped (no consumer field): ``Persona.size``, ``Persona.stability``,
``Persona.centroid`` (top-only — superseded by ``centroid_full``), and the
``group``/``centroid_value``/``population_mean``/``population_std`` members of
each ``FeatureDelta`` (only ``z_delta`` survives, as the step-1 centroid tier).

Mapped when present (producer #342): ``behavioral_seeds`` → ``BehavioralSeedSchema``
(the five identity-draw pools the simulator's ``identity_seed`` service reads).
Absent / null on the producer side (no-LLM builds, v1.0 packs) → ``None``, and the
simulator falls back to its generic default pool exactly as before.

Defaulted (the producer never emits it): ``behavioral_snapshot`` (``{}``).

v1.0 packs translate cleanly: the v1.1 quad is absent, so each Persona keeps its
schema defaults (empty ``centroid_full``/``feature_scale``/``sample_rows``,
``posterior_mean=None``) and the simulator degrades to the centroid-population
profile — exactly as it does for a hand-authored v1.0 pack.
"""

from __future__ import annotations

from typing import Any, Mapping

from sidira_simulator.schemas.persona import (
    BehavioralSeedSchema,
    Persona,
    PersonaPack,
    WeightSchemes,
)


def translate_producer_pack(
    producer: Mapping[str, Any],
    *,
    version: str | None = None,
    is_starter: bool = False,
) -> PersonaPack:
    """Map a producer pack (parsed ``persona_pack.json``) to a consumer ``PersonaPack``.

    Args:
        producer: The producer pack as a plain dict (``json.load`` of the
            ``sidira-personas`` ``persona_pack.json``).
        version: Override for the consumer ``version`` (the R2 path segment, e.g.
            ``"v_1"``). Defaults to the producer's ``run_id`` when omitted.
        is_starter: Stamped onto the pack; real translated packs are never
            starters, but the flag is exposed for symmetry with the loader.

    Returns:
        A validated :class:`PersonaPack`.

    Raises:
        ValueError: If a required producer field is missing (``company_id``,
            ``personas``, or a usable ``version``/``run_id``).
    """
    customer_id = producer.get("company_id")
    if not customer_id:
        raise ValueError("producer pack missing required 'company_id'")

    raw_personas = producer.get("personas")
    if not isinstance(raw_personas, list) or not raw_personas:
        raise ValueError("producer pack missing or empty 'personas'")

    resolved_version = version or producer.get("run_id")
    if not resolved_version:
        raise ValueError("producer pack missing 'run_id' and no explicit version= override given")

    personas = [_translate_persona(p) for p in raw_personas]
    weights = _build_weight_schemes(raw_personas)

    return PersonaPack(
        version=resolved_version,
        customer_id=customer_id,
        generated_at=producer.get("created_at"),
        schema_version=producer.get("schema_version", "1.0"),
        personas=personas,
        weights=weights,
        stability_score=float(producer.get("overall_stability", 0.0)),
        is_starter=is_starter,
    )


def _translate_persona(p: Mapping[str, Any]) -> Persona:
    """Map one producer persona dict to a consumer :class:`Persona`."""
    persona_id = p.get("id")
    if not persona_id:
        raise ValueError("producer persona missing required 'id'")

    centroid_features = {
        fd["feature"]: float(fd["z_delta"])
        for fd in p.get("top_features", [])
        if isinstance(fd, Mapping) and "feature" in fd and "z_delta" in fd
    }

    return Persona(
        id=persona_id,
        name=p.get("name", persona_id),
        description=p.get("description", ""),
        jtbd=p.get("jtbd"),
        centroid_features=centroid_features,
        # v1.1 quad — keys are identical producer↔consumer, pass straight through.
        # Absent on v1.0 packs → schema defaults (degrade to centroid tier).
        centroid_full=p.get("centroid_full", {}),
        feature_scale=p.get("feature_scale", {}),
        sample_rows=p.get("sample_rows", []),
        posterior_mean=p.get("posterior_mean"),
        behavioral_seeds=_translate_behavioral_seeds(p.get("behavioral_seeds")),
    )


def _translate_behavioral_seeds(raw: Any) -> BehavioralSeedSchema | None:
    """Map the producer's ``behavioral_seeds`` object into ``BehavioralSeedSchema``.

    The producer (#342) emits the five identity-draw pools field-for-field, or
    ``null`` when LLM naming was off/unavailable. ``None`` (and any non-dict)
    passes through as ``None`` so the simulator's ``identity_seed`` service falls
    back to its generic default pool — the v1.0 / no-LLM behavior. Missing list
    keys default to empty (pydantic ``default_factory=list``), matching the
    consumer schema's optionality field-for-field.
    """
    if not isinstance(raw, Mapping):
        return None
    return BehavioralSeedSchema(
        age_bands=list(raw.get("age_bands", [])),
        locale_bands=list(raw.get("locale_bands", [])),
        tenure_bands=list(raw.get("tenure_bands", [])),
        current_state_pool=list(raw.get("current_state_pool", [])),
        recent_gripe_pool=list(raw.get("recent_gripe_pool", [])),
    )


def _build_weight_schemes(raw_personas: list[Mapping[str, Any]]) -> WeightSchemes:
    """Transpose producer per-persona weights into the consumer's per-pack schemes.

    The consumer's ``allocate()`` (population_sampler) requires every *active*
    (non-None) scheme to cover **every** persona in the pack and sum to ~1.0 —
    a partial scheme raises at allocation time. So an optional scheme is emitted
    only when **all** personas carry a non-null value; a single missing persona
    drops the whole scheme to ``None`` rather than shipping a sparse one that
    validates as a ``PersonaPack`` but explodes the first time it is selected.

    This matches the producer, which computes ``by_orders``/``by_revenue`` as
    population fractions for all personas or none (gated on the configured
    order/revenue columns), so a complete scheme also sums to ~1.0 by
    construction. ``head_count`` is always built (a missing ``by_headcount``
    defaults to 0.0 — it is a required producer field, so this is only a guard).
    """
    head_count: dict[str, float] = {}
    order_vals: dict[str, float | None] = {}
    revenue_vals: dict[str, float | None] = {}

    for p in raw_personas:
        pid = p["id"]
        w = p.get("weights") or {}
        head_count[pid] = float(w.get("by_headcount") or 0.0)
        order_vals[pid] = w.get("by_orders")
        revenue_vals[pid] = w.get("by_revenue")

    return WeightSchemes(
        head_count=head_count,
        order_weighted=_complete_scheme(order_vals),
        revenue_weighted=_complete_scheme(revenue_vals),
    )


def _complete_scheme(vals: Mapping[str, float | None]) -> dict[str, float] | None:
    """Return the scheme as a complete ``{persona_id: float}`` dict, or ``None``.

    ``None`` if *any* persona's value is missing — a partial optional scheme is
    never emitted (see :func:`_build_weight_schemes`).
    """
    if not vals or any(v is None for v in vals.values()):
        return None
    return {pid: float(v) for pid, v in vals.items()}
