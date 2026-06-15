"""Persona pack routes — list all versions, read one, promote a draft to latest."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sidira_simulator.adapters.base import ArtifactNotFound
from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.api.deps import current_customer_id, get_persona_loader
from sidira_simulator.schemas.persona import PersonaPack
from sidira_simulator.services.persona_pack_view import (
    PersonaPackDetail,
    build_persona_pack_detail,
)

router = APIRouter(prefix="/persona-packs", tags=["persona-packs"])

# Sentinel pack_id that resolves to the customer's active pack via the `latest`
# pointer, so the Library can deep-link to "the current pack" without first
# fetching its version. Mirrors how the Feature Pack browse page addresses the
# latest snapshot (#207).
LATEST = "latest"


class PackStatus(str, Enum):
    DRAFT = "draft"
    PROMOTED = "promoted"
    RETIRED = "retired"


class PackSummary(BaseModel):
    """Lightweight pack metadata for list views."""

    id: str
    version: str
    status: PackStatus
    stability_score: float
    persona_count: int
    created_at: datetime
    promoted_at: datetime | None = None
    is_latest: bool = False


@router.get("", response_model=list[PackSummary])
async def list_packs(customer_id: str = Depends(current_customer_id)) -> list[PackSummary]:
    """List all pack versions for the customer, newest first."""
    raise HTTPException(
        status_code=501,
        detail="Phase 4.5 — read persona_pack_versions scoped to customer, resolve `latest` pointer",
    )


def _load_pack(loader: PersonaPackLoader, customer_id: str, pack_id: str) -> PersonaPack:
    """Resolve a pack id to its contents, applying the `latest`/starter rules.

    `pack_id="latest"` resolves the active pack via the `latest` pointer — the
    same in-memory starter fallback as `GET /personas` (#212): a tenant with no
    pack yet gets the generic starter pack (`is_starter=True`) so the page
    renders rather than 404-ing. An explicit version loads that exact snapshot
    and 404s if it is missing (a real not-found, not an empty tenant).
    """
    try:
        if pack_id == LATEST:
            return loader.load_latest(customer_id)
        return loader.load_at_version(customer_id, pack_id)
    except ArtifactNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=f"No persona pack {pack_id!r} for customer {customer_id!r}.",
        ) from exc


@router.get("/{pack_id}", response_model=PersonaPack)
async def get_pack(
    pack_id: str,
    customer_id: str = Depends(current_customer_id),
    loader: PersonaPackLoader = Depends(get_persona_loader),
) -> PersonaPack:
    """Full raw pack contents — persona descriptions, weights, stability.

    The producer→consumer `PersonaPack` as-is, including the v1.1 model-input
    arrays (`centroid_full` / `feature_scale` / `sample_rows`). For the
    human-facing rendered view (the behavioral-comparison blocks, weight schemes,
    honesty flags) the Library detail page uses `/{pack_id}/detail` instead.
    """
    return _load_pack(loader, customer_id, pack_id)


@router.get("/{pack_id}/detail", response_model=PersonaPackDetail)
async def get_pack_detail(
    pack_id: str,
    customer_id: str = Depends(current_customer_id),
    loader: PersonaPackLoader = Depends(get_persona_loader),
) -> PersonaPackDetail:
    """Read-only presentation view for the Library's persona-pack detail page (#25).

    Renders each persona's centroid **"How you compare"** block and per-member
    **individual-row** block through the single-sourced honesty/salience logic in
    `behavioral_profile.py`, folds the three weight schemes into per-persona
    shares (with a truthful reason when an optional scheme is unavailable), and
    surfaces the stability/honesty flags — without echoing the bulky raw v1.1
    arrays. On a v1.0 pack the individual-row block degrades to absent (honest
    empty-state), never a fabricated row. Same `latest`/starter/404 rules as the
    raw `GET /{pack_id}`.
    """
    return build_persona_pack_detail(_load_pack(loader, customer_id, pack_id))


@router.post("/{pack_id}/promote", response_model=PackSummary)
async def promote_pack(
    pack_id: str, customer_id: str = Depends(current_customer_id)
) -> PackSummary:
    """Atomically update the customer's `latest` pointer to this pack version."""
    raise HTTPException(
        status_code=501,
        detail=(
            "Phase 4.5 — verify pack is DRAFT, set status=PROMOTED, "
            "write customers/<id>/personas/latest pointer atomically"
        ),
    )
