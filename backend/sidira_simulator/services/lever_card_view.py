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
from sidira_simulator.schemas.lever_review import LeverReview, LeverReviewLog

# Cap on the structural/behavioural column-name lists in the coverage summary —
# the summary must stay a bounded payload however wide the feature store is
# (500-column stores exist). Overflow is recorded as an explicit truncation
# count, never silently dropped.
COVERAGE_NAME_CAP = 50


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
    # --- Per-lever grounding-completeness (#564): the producer's verdict on
    # whether this lever's empirical route has everything it needs (treatment +
    # outcome columns, adjustment covariates, a vouched negative control, no
    # structurally-missing referenced column). ``grounding_gaps`` names the
    # failures with the producer's fixed tokens (``no_treatment_column`` /
    # ``no_outcome_column`` / ``insufficient_covariates`` /
    # ``no_vouched_negative_control`` / ``structurally_missing_column``); empty
    # iff complete. Tri-state: ``None`` = legacy manifest (pre-#564 producer) —
    # the honest "unknown", never dressed up as complete. Orthogonal to
    # ``supportable``.
    grounding_complete: bool | None = None
    grounding_gaps: list[str] = []
    # The human review of THIS lever (#565 parts 2 & 3), or None if unreviewed.
    # The auto-guard fields above stay the raw machine verdict; the review is the
    # human layer over them. Display rule (frontend): a "rejected" review overrides
    # the lever to abstain; a "vouched" review confirms but never upgrades a
    # guard-abstained lever into trust.
    review: LeverReview | None = None


class CoverageSummary(BaseModel):
    """Pack-level data-coverage summary (#564) — bounded, counts + capped names.

    A deliberate SUMMARY of the manifest's per-column coverage list, not the list
    itself: a 500-column store must not turn the card payload into a dump. Counts
    are complete; only the *name lists* are capped (at ``COVERAGE_NAME_CAP``) with
    an explicit truncation count for the overflow. "Present" columns are counted
    but never enumerated — the interesting review evidence is what's missing.
    """

    model_config = ConfigDict(extra="forbid")

    total_columns: int
    present_count: int
    behavioural_count: int
    structural_count: int
    # Config-expected columns absent from the source entirely (observed=False) —
    # a subset of the structural count: "declared but never tracked".
    expected_absent_count: int
    # Capped name lists for the two missing classes (review evidence).
    structural_columns: list[str] = []
    behavioural_columns: list[str] = []
    # How many names the caps cut (0 = the lists above are complete).
    structural_truncated: int = 0
    behavioural_truncated: int = 0


class LeverCardManifest(BaseModel):
    """The lever cards for one persona pack, plus manifest provenance."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: str
    pack_version: str
    feature_store: str
    built_at: str | None = None
    levers: list[LeverCard] = []
    # Pack-level coverage summary (#564). None ⇔ the manifest carries no coverage
    # list (legacy, pre-#564 producer) — the honest "unknown", distinct from a
    # real all-present summary.
    coverage: CoverageSummary | None = None


def _card_from_candidate(
    effect: CandidateEffect, review: LeverReview | None
) -> LeverCard:
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
        grounding_complete=effect.grounding_complete,
        grounding_gaps=list(effect.grounding_gaps),
        review=review,
    )


def _coverage_summary(manifest: EstimabilityManifest) -> CoverageSummary | None:
    """Fold the manifest's per-column coverage list into the bounded summary.

    Returns None when the manifest carries no coverage list — a legacy (pre-#564)
    producer artifact, surfaced as the honest "unknown" rather than a fabricated
    all-present summary. Counts are exact; name lists are capped at
    ``COVERAGE_NAME_CAP`` with the overflow recorded, never silently dropped.
    """
    if not manifest.coverage:
        return None
    structural = [c.name for c in manifest.coverage if c.missingness == "structural"]
    behavioural = [c.name for c in manifest.coverage if c.missingness == "behavioural"]
    return CoverageSummary(
        total_columns=len(manifest.coverage),
        present_count=sum(1 for c in manifest.coverage if c.missingness == "present"),
        behavioural_count=len(behavioural),
        structural_count=len(structural),
        expected_absent_count=sum(1 for c in manifest.coverage if not c.observed),
        structural_columns=structural[:COVERAGE_NAME_CAP],
        behavioural_columns=behavioural[:COVERAGE_NAME_CAP],
        structural_truncated=max(0, len(structural) - COVERAGE_NAME_CAP),
        behavioural_truncated=max(0, len(behavioural) - COVERAGE_NAME_CAP),
    )


def build_lever_card_view(
    manifest: EstimabilityManifest, reviews: LeverReviewLog | None = None
) -> LeverCardManifest:
    """Assemble the human-facing lever-card view from an estimability manifest.

    Pure transform: every candidate becomes a card in manifest order, with the
    treatment→outcome point estimates stripped and the NC-guard evidence carried
    through. When a ``reviews`` log is supplied, each card is matched to its human
    review by (treatment, outcome) — an unreviewed lever keeps ``review=None``.
    The frontend renders these as a register of reviewable records.
    """
    by_lever: dict[tuple[str, str], LeverReview] = {}
    if reviews is not None:
        # Latest-per-lever already (the store dedupes on write); if a malformed
        # log somehow carried duplicates, last-wins is a safe, deterministic pick.
        for r in reviews.reviews:
            by_lever[(r.treatment, r.outcome)] = r

    return LeverCardManifest(
        manifest_version=manifest.manifest_version,
        pack_version=manifest.pack_version,
        feature_store=manifest.feature_store,
        built_at=manifest.built_at,
        levers=[
            _card_from_candidate(e, by_lever.get((e.treatment, e.outcome)))
            for e in manifest.candidate_effects
        ],
        coverage=_coverage_summary(manifest),
    )


__all__ = [
    "LeverCard",
    "LeverCardManifest",
    "CoverageSummary",
    "COVERAGE_NAME_CAP",
    "build_lever_card_view",
]
