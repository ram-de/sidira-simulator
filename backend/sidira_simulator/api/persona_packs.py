"""Persona pack routes — list all versions, read one, promote a draft to latest."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sidira_simulator.schemas.persona import PersonaPack

router = APIRouter(prefix="/persona-packs", tags=["persona-packs"])


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
async def list_packs() -> list[PackSummary]:
    """List all pack versions for the customer, newest first."""
    raise HTTPException(
        status_code=501,
        detail="Phase 4.5 — read persona_pack_versions scoped to customer, resolve `latest` pointer",
    )


@router.get("/{pack_id}", response_model=PersonaPack)
async def get_pack(pack_id: str) -> PersonaPack:
    """Full pack contents including persona descriptions, weights, stability."""
    raise HTTPException(
        status_code=501,
        detail="Phase 4.5 — read persona_pack.json from R2 at the pack's version path",
    )


@router.post("/{pack_id}/promote", response_model=PackSummary)
async def promote_pack(pack_id: str) -> PackSummary:
    """Atomically update the customer's `latest` pointer to this pack version."""
    raise HTTPException(
        status_code=501,
        detail=(
            "Phase 4.5 — verify pack is DRAFT, set status=PROMOTED, "
            "write customers/<id>/personas/latest pointer atomically"
        ),
    )
