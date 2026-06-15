"""Persona Pack schema — produced by sidira-personas, consumed here.

Duplicated from sidira-personas until the shared pythia-schemas package lands.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WeightSchemes(BaseModel):
    head_count: dict[str, float]
    order_weighted: dict[str, float] | None = None
    revenue_weighted: dict[str, float] | None = None


class BehavioralSeedSchema(BaseModel):
    """Per-persona pools that identity_seed draws from (sidira-personas v1.1).

    Ordered most-common-first so a uniform draw yields a realistic-ish
    distribution. Optional on Persona — v1.0 packs lack this field and the
    simulator's identity_seed service falls back to a generic default schema.
    """

    age_bands: list[str] = Field(default_factory=list)
    locale_bands: list[str] = Field(default_factory=list)
    tenure_bands: list[str] = Field(default_factory=list)
    current_state_pool: list[str] = Field(default_factory=list)
    recent_gripe_pool: list[str] = Field(default_factory=list)


class Persona(BaseModel):
    """One persona — the template an AgentInstance is created from."""

    id: str
    name: str
    description: str
    jtbd: str | None = Field(default=None, description="Jobs-to-be-done summary")
    behavioral_snapshot: dict[str, float | int | str] = Field(default_factory=dict)
    centroid_features: dict[str, float] = Field(default_factory=dict)
    behavioral_seeds: BehavioralSeedSchema | None = None

    # --- Persona Pack v1.1 (sidira-personas#7) — the per-agent individual-row
    # inputs (agent-behavior-spec §2 layer 4). All additive + defaulted, so v1.0
    # packs (which omit them) still validate and the simulator degrades to the
    # centroid-population profile. Unlike `centroid_features` (population
    # z-scores, keyed `*_z`), these three live in ADAPTED-FEATURE space (raw
    # units, keyed by raw feature name) and are mutually consistent, so the
    # within-cluster z is computed directly: z = (row[f] - centroid_full[f]) /
    # feature_scale[f]. They never mix with `centroid_features`' key namespace.
    centroid_full: dict[str, float] = Field(
        default_factory=dict,
        description="Cluster mean over ALL adapted features (raw units). The "
        "subtrahend for the per-agent within-cluster z-score — distinct from "
        "centroid_features (population z-scores). Empty on v1.0 packs.",
    )
    feature_scale: dict[str, float] = Field(
        default_factory=dict,
        description="Within-cluster std per feature (zero-floored by the "
        "producer), same keys as centroid_full. The z-score denominator. Empty "
        "on v1.0 packs.",
    )
    sample_rows: list[dict[str, float]] = Field(
        default_factory=list,
        description="N privacy-clean synthetic rows (covariance-aware GMM draws) "
        "in adapted-feature space, keyed by raw feature name. Selected per-agent "
        "by (sample_index) to render layer 4. Empty on v1.0 packs.",
    )
    posterior_mean: dict[str, float] | None = Field(
        default=None,
        description="Mean GMM soft-membership vector for this cluster, keyed by "
        "component index (P01, P02, …) — NOT persona id. Carried for forward "
        "compatibility; the named soft-membership hedge is a follow-up pending a "
        "component→persona-id map. None for FIXED_* / v1.0 packs.",
    )


class PersonaPack(BaseModel):
    version: str
    customer_id: str
    generated_at: datetime
    schema_version: Literal["1.0", "1.1"] = "1.0"
    personas: list[Persona]
    weights: WeightSchemes
    stability_score: float
    is_starter: bool = Field(
        default=False,
        description=(
            "True for the generic, product-agnostic starter pack the loader serves "
            "when a tenant has no Persona Pack yet (#212). A starter is a placeholder "
            "so the product is clickable immediately; it is NOT built from customer "
            "data and never persisted. Real packs (built or sample-cloned) carry False."
        ),
    )
