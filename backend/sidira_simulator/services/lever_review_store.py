"""R2 sidecar persistence for human lever reviews (#565 parts 2 & 3).

Mirrors the decision-verdict sidecar (``services.decision_flow``): a small JSON
artifact beside the pack, best-effort read (never 500s a GET), authoritative
write. Keyed by PACK VERSION (not sim_id) because a review applies to a lever in
a pack's estimability manifest:

    customers/<customer_id>/personas/<version>/estimability_manifest.json  (worker)
    customers/<customer_id>/personas/<version>/lever_review.json           ← here

The review log is latest-per-lever: an upsert replaces any prior decision for the
same (treatment, outcome). Single-file read-modify-write — fine for the
white-glove single-reviewer flow; a note for future multi-reviewer concurrency.
"""

from __future__ import annotations

import structlog

from sidira_simulator.adapters.r2 import ArtifactStore
from sidira_simulator.schemas.lever_review import (
    LeverReview,
    LeverReviewLog,
    LeverReviewRequest,
)

log = structlog.get_logger(__name__)


def lever_review_key(customer_id: str, pack_version: str) -> str:
    """R2 key for a pack's lever-review sidecar (beside the estimability manifest)."""
    return f"customers/{customer_id}/personas/{pack_version}/lever_review.json"


def read_lever_reviews(
    store: ArtifactStore, customer_id: str, pack_version: str
) -> LeverReviewLog:
    """Best-effort read of the review sidecar. A miss OR a malformed body returns
    an EMPTY log (never raises) so a GET can always fold reviews in — a pack with
    no reviews yet is the common case, not an error."""
    key = lever_review_key(customer_id, pack_version)
    try:
        raw = store.read_text(key)
    except FileNotFoundError:
        return LeverReviewLog(pack_version=pack_version)
    except Exception as exc:  # noqa: BLE001 — an optional read must never break GET.
        log.warning(
            "lever_review.read_failed",
            customer_id=customer_id,
            pack_version=pack_version,
            error=str(exc),
        )
        return LeverReviewLog(pack_version=pack_version)
    try:
        return LeverReviewLog.model_validate_json(raw)
    except Exception as exc:  # noqa: BLE001 — a malformed sidecar is treated as empty.
        log.warning(
            "lever_review.malformed",
            customer_id=customer_id,
            pack_version=pack_version,
            error=str(exc),
        )
        return LeverReviewLog(pack_version=pack_version)


def apply_lever_review(
    store: ArtifactStore,
    customer_id: str,
    pack_version: str,
    request: LeverReviewRequest,
    *,
    reviewer: str,
    reviewed_at: str,
) -> LeverReview | None:
    """Record / replace / clear one lever's review, then persist the whole log.

    Read-modify-write: drops any existing decision for the same (treatment,
    outcome), then — unless the request is ``cleared`` — appends the new review.
    Returns the stored ``LeverReview`` (None when the decision was ``cleared``).
    Raises on a store WRITE failure (the caller surfaces it — a review write that
    silently no-ops would mislead the reviewer into thinking their call landed).
    """
    review_log = read_lever_reviews(store, customer_id, pack_version)
    kept = [
        r
        for r in review_log.reviews
        if not (r.treatment == request.treatment and r.outcome == request.outcome)
    ]

    stored: LeverReview | None = None
    if request.decision != "cleared":
        stored = LeverReview(
            treatment=request.treatment,
            outcome=request.outcome,
            decision=request.decision,
            note=request.note,
            reviewer=reviewer,
            reviewed_at=reviewed_at,
            guard_trips_at_review=request.guard_trips_at_review,
            decisive_nc_at_review=request.decisive_nc_at_review,
        )
        kept.append(stored)

    review_log = LeverReviewLog(pack_version=pack_version, reviews=kept)
    store.write_text(
        lever_review_key(customer_id, pack_version),
        review_log.model_dump_json(indent=2),
    )
    return stored


__all__ = ["lever_review_key", "read_lever_reviews", "apply_lever_review"]
