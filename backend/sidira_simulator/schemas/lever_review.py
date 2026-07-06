"""Human lever-review records — the vouch/override layer over the estimability guard.

`#565` parts 2 & 3. The read-only lever card (#577) surfaces the build-time
estimability guard verdict per (treatment → outcome) lever. This adds the HUMAN
layer: a reviewer, looking at the measured negative-control diagnostics, records
whether they **vouch** the lever's reading or **reject** it — persisted beside the
pack so the decision survives and can be shown back on the card.

**Honesty invariants (why this is not a rubber-stamp):**
- A **reject** can force a lever to abstain even when the auto-guard called it
  trustworthy (a human catches confounding the guard missed — the conservative
  direction). A **vouch** does NOT upgrade a guard-abstained lever into "trust";
  it records agreement, never manufactures trust the data doesn't support. That
  asymmetry keeps abstain-by-default intact.
- Each review snapshots the guard verdict the human SAW when deciding
  (``guard_trips_at_review`` / ``decisive_nc_at_review``) so a later calibration
  pass (the accuracy-scorecard epic) can join human-judgment × auto-verdict ×
  ground-truth. Direction-only; no effect magnitude is stored.

The stored record is direction-only and additive to the manifest — it lives in
its own sidecar, never mutating the worker-written estimability artifact.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# What a reviewer can express. "cleared" is a REQUEST-only verb (it deletes the
# lever's stored review); a persisted review is only ever "vouched" or "rejected".
LeverDecision = Literal["vouched", "rejected"]
LeverDecisionRequest = Literal["vouched", "rejected", "cleared"]


class LeverReview(BaseModel):
    """One human review of a (treatment → outcome) lever, persisted per pack."""

    model_config = ConfigDict(extra="forbid")

    treatment: str
    outcome: str
    decision: LeverDecision
    note: str | None = None
    # Who recorded it (Clerk ``sub`` via current_user_id) + when (ISO-8601 UTC).
    reviewer: str
    reviewed_at: str
    # Calibration snapshot — the auto-guard verdict shown to the human at review
    # time. Lets a later calibration analysis compare human judgment against the
    # guard against eventual ground truth. None when the guard was not validated.
    guard_trips_at_review: bool | None = None
    decisive_nc_at_review: str | None = None


class LeverReviewRequest(BaseModel):
    """POST body to record/replace/clear a reviewer's decision on one lever."""

    model_config = ConfigDict(extra="forbid")

    treatment: str
    outcome: str
    decision: LeverDecisionRequest
    note: str | None = Field(default=None, max_length=2000)
    # Echoed guard snapshot the client saw (from the lever card it is acting on),
    # stored verbatim for calibration. Optional/advisory — the server does not
    # recompute the guard here; it records what the reviewer was looking at.
    guard_trips_at_review: bool | None = None
    decisive_nc_at_review: str | None = None


class LeverReviewLog(BaseModel):
    """All human reviews for one pack — latest-per-lever, in an R2 sidecar."""

    model_config = ConfigDict(extra="forbid")

    pack_version: str
    reviews: list[LeverReview] = []


__all__ = [
    "LeverDecision",
    "LeverDecisionRequest",
    "LeverReview",
    "LeverReviewRequest",
    "LeverReviewLog",
]
