"""Read-only presentation view of the estimability manifest — the "lever cards".

`#565` surfaces the build-time estimability manifest to a human reviewer as a
list of **reviewable lever cards**: one per precomputed (treatment → outcome)
candidate, showing the direction-only verdict and the negative-control guard
evidence so a PM can sanity-check what the engine will and won't trust.

This module is the presentation projection the read route returns, deliberately
distinct from the raw :class:`~sidira_simulator.schemas.estimability.EstimabilityManifest`
(which mirrors the worker artifact verbatim, point estimates and all):

- **The treatment→outcome effect MAGNITUDES are omitted.** `naive_ate` /
  `t_learner_ate` / `ipw_ate` / `naive_adjusted_gap` never leave the API. The
  product is direction-only and must never surface an effect magnitude
  (DESIGN.md honesty law); enforcing that at the boundary means a rendered
  surface *cannot* leak one, no matter what a future frontend does.
- **The NC-guard residuals ARE surfaced.** `neg_control_effect` /
  `neg_control_effects` are trust *diagnostics* — spurious measured movement on
  a variable the lever cannot cause — not a prediction of the lever's effect.
  They are the whole point of a "reviewable" card, so they stay.
- **Support diagnostics stay too.** `overlap_fraction` and the treated/control
  counts are evidence about whether the estimate is supportable, not an effect
  size, so they help a reviewer without implying a magnitude.

Pure and side-effect-free: an ``EstimabilityManifest`` in, a
``LeverCardManifest`` out. Mirrors ``persona_pack_view.build_persona_pack_detail``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from sidira_simulator.schemas.estimability import (
    CandidateEffect,
    EstimabilityManifest,
)


class LeverCard(BaseModel):
    """One reviewable (treatment → outcome) lever — direction + NC-guard verdict.

    A record for human review, not the raw candidate: the treatment's own effect
    magnitudes are intentionally absent (direction-only product). ``guard_trips``
    is the tri-state the card renders — ``True`` untrustworthy (effect
    indistinguishable from confounding bias), ``False`` trustworthy empirical,
    ``None`` NC evidence not precomputed (→ "not validated", the honest
    empty-state; never dressed up as trust).
    """

    model_config = ConfigDict(extra="forbid")

    treatment: str
    outcome: str
    # The covariate adjustment set the estimate conditioned on — shown as
    # provenance so a reviewer can see what was (and wasn't) controlled for.
    covariates: list[str] = []
    supportable: bool
    support_reasons: list[str] = []
    n_treat: int | None = None
    n_control: int | None = None
    # A support diagnostic (propensity overlap), NOT an effect magnitude.
    overlap_fraction: float | None = None
    # The direction-only verdict (the manifest's ``sign_adjusted``). None when the
    # candidate is not supportable (no estimate was computed).
    direction: Literal["positive", "negative"] | None = None
    # --- Negative-control guard: the reviewable trust evidence. ---
    guard_trips: bool | None = None
    guard_floor: float | None = None
    guard_ratio: float | None = None
    guard_confidence: str | None = None
    guard_reason: str | None = None
    # Decisive (max-|effect|) NC residual, and the per-control residual map.
    # Diagnostics about confounding, not a prediction of the lever's own effect.
    neg_control_effect: float | None = None
    neg_control_effects: dict[str, float] = {}


class LeverCardManifest(BaseModel):
    """The lever cards for one persona pack, plus manifest provenance."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: str
    pack_version: str
    feature_store: str
    built_at: str | None = None
    levers: list[LeverCard] = []


def _card_from_candidate(effect: CandidateEffect) -> LeverCard:
    """Project one manifest candidate onto its review card, dropping ATE magnitudes."""
    return LeverCard(
        treatment=effect.treatment,
        outcome=effect.outcome,
        covariates=list(effect.covariates),
        supportable=effect.supportable,
        support_reasons=list(effect.support_reasons),
        n_treat=effect.n_treat,
        n_control=effect.n_control,
        overlap_fraction=effect.overlap_fraction,
        direction=effect.sign_adjusted,
        guard_trips=effect.guard_trips,
        guard_floor=effect.guard_floor,
        guard_ratio=effect.guard_ratio,
        guard_confidence=effect.guard_confidence,
        guard_reason=effect.guard_reason,
        neg_control_effect=effect.neg_control_effect,
        neg_control_effects=dict(effect.neg_control_effects),
    )


def build_lever_card_view(manifest: EstimabilityManifest) -> LeverCardManifest:
    """Assemble the human-facing lever-card view from an estimability manifest.

    Pure transform: every candidate becomes a card in manifest order, with the
    treatment→outcome point estimates stripped and the NC-guard evidence carried
    through. The frontend renders these as a register of reviewable records.
    """
    return LeverCardManifest(
        manifest_version=manifest.manifest_version,
        pack_version=manifest.pack_version,
        feature_store=manifest.feature_store,
        built_at=manifest.built_at,
        levers=[_card_from_candidate(e) for e in manifest.candidate_effects],
    )


__all__ = ["LeverCard", "LeverCardManifest", "build_lever_card_view"]
