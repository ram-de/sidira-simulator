"""Capabilities route — lists capabilities from the customer's latest Feature Pack."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from pythia_simulator.schemas.feature_pack import FeaturePackManifest

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


@router.get("", response_model=FeaturePackManifest)
async def list_capabilities() -> FeaturePackManifest:
    """Return the latest Feature Pack manifest for the authenticated customer."""
    raise HTTPException(
        status_code=501, detail="list_capabilities — wires FeaturePackLoader once tenancy is in"
    )
