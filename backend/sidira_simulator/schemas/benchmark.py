"""Benchmark adapter schemas (agent-behavior-spec §1 / ticket #222).

The Tier-0 benchmark must render archived public experiments to agents in the
EXACT format customer PRDs use — the *treatment-rendering parity* constraint
(#222 §6.2 / treatment-rendering-layer.md §4). The renderer
(`services.treatment_renderer.render_state_diff`) is shared infra; the adapter
lives at the edge, turning an archived experiment into the *same*
`(Capability, Hypothesis)` pair production builds: control = current state,
treatment = proposed state, everything else "explicitly NOT changing".

This module defines the source side (an Upworthy clickability test) and the
`BenchmarkCase` the adapter emits. Ground-truth outcomes ride along on the case
so the eval can score predicted-vs-observed lift without re-joining the archive.

Upworthy is the first/easiest target (#222 artifact 1): a headline A/B/n test on
a promoted story card. CTR (clicks / impressions) is the measured outcome — the
"text/CTR easy regime" the ticket flags us to caveat honestly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sidira_simulator.schemas.feature_pack import Capability
from sidira_simulator.schemas.simulation import Hypothesis


class UpworthyVariant(BaseModel):
    """One headline package within a clickability test.

    `impressions` must be > 0 so `ctr` is well-defined — a package with zero
    impressions carries no outcome signal and cannot anchor a benchmark case.
    """

    model_config = ConfigDict(extra="forbid")

    headline: str
    clicks: int = Field(ge=0)
    impressions: int = Field(gt=0)
    # The story image's identity. ReverseFigma cannot encode image *content*, so
    # the adapter can only certify a pair as a pure headline swap by checking this
    # identity is EQUAL across arms; a differing eyecatcher is an unrepresentable
    # (image / multi-factor) change, recorded as skipped rather than faked as copy.
    #
    # REQUIRED with no default: the importer must make a deliberate choice per
    # variant, so "didn't bother to record it" can never masquerade as a held-fixed
    # image. A real id names the image; `None` is the explicit "no distinguishing
    # image on this card" sentinel — a defined, held-fixed state, NOT "unknown".
    # Two None variants therefore certify "neither card has an image", which the
    # equality check correctly treats as held-fixed. An importer that cannot make
    # that assertion must reject the row upstream, not pass None.
    eyecatcher_id: str | None

    @model_validator(mode="after")
    def _clicks_within_impressions(self) -> UpworthyVariant:
        # CTR is clicks / impressions, a probability — clicks > impressions yields
        # ctr > 1, which is physically impossible and means a malformed archive row
        # or a mis-mapped column. Reject at the boundary so impossible data can
        # never propagate into a ground-truth label.
        if self.clicks > self.impressions:
            raise ValueError(
                f"clicks ({self.clicks}) exceed impressions ({self.impressions}); "
                "ctr > 1 is impossible — malformed archive row"
            )
        return self

    @property
    def ctr(self) -> float:
        return self.clicks / self.impressions


class UpworthyTest(BaseModel):
    """A single clickability test: ≥2 headline variants competing on one story."""

    model_config = ConfigDict(extra="forbid")

    test_id: str
    variants: list[UpworthyVariant] = Field(min_length=2)
    # Free-text description of the underlying story, shared across all variants.
    # Optional: the archive does not always carry article text.
    article_context: str | None = None


class GroundTruth(BaseModel):
    """Measured outcome for one (control, treatment) pair — the scoring label.

    Carried on the `BenchmarkCase` so predicted lift can be scored against the
    observed lift without re-joining the source archive. `observed_lift` is the
    signed delta in the native metric (treatment − control), NOT a percentage.
    """

    model_config = ConfigDict(extra="forbid")

    metric_name: str = "ctr"
    control_metric: float = Field(ge=0.0)
    treatment_metric: float = Field(ge=0.0)
    observed_lift: float
    winner: Literal["control", "treatment", "tie"]


class BenchmarkCase(BaseModel):
    """One renderable benchmark unit: the SAME `(Capability, Hypothesis)` shape
    production builds, plus the measured ground truth.

    The whole point of the adapter is that `render_state_diff(case.capability,
    case.hypothesis)` is the exact production call — no benchmark-only rendering
    path. Parity is therefore structural, not asserted by string-matching.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str
    source: str
    capability: Capability
    hypothesis: Hypothesis
    ground_truth: GroundTruth


class SkippedPair(BaseModel):
    """A (control, treatment) pair the adapter could not represent as a state-diff.

    Recorded rather than dropped (the no-silent-degradation rule shared with the
    §3a choice-set's grounded/fallback flags): a pair that swaps the image — or
    otherwise can't be expressed as a `Hypothesis` + structural diff — is the §4
    forcing-function signal that the *production* path can't represent that change
    class either, not a case to quietly omit from the benchmark's denominator.
    """

    model_config = ConfigDict(extra="forbid")

    control_index: int
    treatment_index: int
    reason: str


class UpworthyAdaptationResult(BaseModel):
    """Output of enumerating a whole test: representable cases + recorded skips."""

    model_config = ConfigDict(extra="forbid")

    cases: list[BenchmarkCase] = Field(default_factory=list)
    skipped: list[SkippedPair] = Field(default_factory=list)

    @model_validator(mode="after")
    def _nonempty_coverage(self) -> UpworthyAdaptationResult:
        # A test that yields neither a case nor a recorded skip means the
        # enumerator silently produced nothing — exactly the masquerade the
        # skip list exists to prevent. Surface it loudly.
        if not self.cases and not self.skipped:
            raise ValueError("adaptation produced neither cases nor skips")
        return self
